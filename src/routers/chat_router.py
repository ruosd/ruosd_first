import contextlib
import time

import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.responses import StreamingResponse

from ..graph.graph_coordinator import GraphCoordinator
from ..models.conversation import ChatResponse
from ..services.conversation_service import ConversationService
from ..services.history_compressor import compress_history
from ..utils.logger import get_logger
from ..utils.settings import settings

router = APIRouter(prefix="/api/chat", tags=["聊天"])
limiter = Limiter(key_func=get_remote_address)

# 初始化服务
conversation_service = ConversationService()

# LangGraph 协调器（延迟初始化）
_graph_coordinator = None


def _get_coordinator():
    """获取协调器（单例延迟初始化）"""
    global _graph_coordinator
    if _graph_coordinator is not None:
        return _graph_coordinator

    llm = _get_llm()
    if llm:
        try:
            _graph_coordinator = GraphCoordinator(llm)
            logger.info("已启用 LangGraph 协调器")
            return _graph_coordinator
        except Exception as e:
            logger.warning(
                f"LangGraph 初始化失败: {type(e).__name__}: {e}"
            )

    _graph_coordinator = GraphCoordinator()
    logger.info("使用 GraphCoordinator（无 LLM 模式）")
    return _graph_coordinator


logger = get_logger("chat_router")

# JWT 密钥（与 admin_router/user_router 共用）
_JWT_SECRET = settings.JWT_SECRET_KEY or "dev-secret-change-me"

# LLM 引用（延迟初始化，用于对话摘要）
_llm = None


def _get_llm():
    """获取 LLM 实例（延迟初始化避免循环依赖）"""
    global _llm
    if _llm is None:
        from ..services.llm_service import LLMService
        _llm = LLMService().llm
    return _llm


def _extract_user_id(authorization: str | None = None) -> str | None:
    """从 Authorization Header 中提取用户ID（多租户隔离的核心）"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ", 1)[1]
        payload = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")  # sub 字段存储用户名
    except Exception:
        return None

class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    user_id: str | None = Field(None, max_length=64, description="用户ID")

class CreateConversationResponse(BaseModel):
    """创建会话响应"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="响应消息")

class SendMessageRequest(BaseModel):
    """发送消息请求"""
    session_id: str = Field(..., min_length=8, max_length=128, description="会话ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息（最长2000字符）")
    current_agent: str | None = Field(None, max_length=64, description="当前活跃的Agent名称")

class ConversationHistoryResponse(BaseModel):
    """对话历史响应"""
    session_id: str = Field(..., description="会话ID")
    history: list[dict] = Field(..., description="对话历史")
    message_count: int = Field(..., description="消息数量")

@router.post("/conversation", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest | None = None,
    authorization: str | None = Header(None)
):
    """创建新的对话会话，自动从 JWT 令牌提取用户身份"""
    start_time = time.time()
    logger.info("========== 创建会话请求 ==========")

    try:
        # 优先使用请求中的 user_id，其次从 JWT 令牌提取
        user_id = request.user_id if request else None
        if not user_id:
            token_user = _extract_user_id(authorization)
            if token_user:
                user_id = token_user
        logger.info(f"用户ID: {user_id if user_id else '未提供'}（会话将按此ID隔离记忆数据）")

        logger.info("开始创建会话...")
        session_id = await conversation_service.create_conversation(user_id)

        latency = (time.time() - start_time) * 1000
        logger.info(f"会话创建成功，Session ID: {session_id}，耗时: {latency:.2f}ms")
        logger.info("========== 创建会话完成 ==========\n")

        return CreateConversationResponse(
            session_id=session_id,
            message="会话创建成功"
        )
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        logger.error(f"创建会话失败，耗时: {latency:.2f}ms，错误: {str(e)}", exc_info=True)
        logger.info("========== 创建会话失败 ==========\n")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}") from e

@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(request: Request, body: SendMessageRequest, authorization: str | None = Header(None)):
    """发送消息并获取AI回复（自动按用户隔离记忆）"""
    start_time = time.time()
    logger.info("========== 发送消息请求 ==========")

    try:
        logger.info(f"Session ID: {body.session_id}")
        logger.info(f"用户消息: {body.message[:50]}..." if len(body.message) > 50 else f"用户消息: {body.message}")
        logger.info(f"当前Agent: {body.current_agent if body.current_agent else '无'}")

        # 获取对话历史
        logger.info("步骤1: 获取对话历史...")
        history_start = time.time()
        history = await conversation_service.get_conversation_history(body.session_id)
        history_time = (time.time() - history_start) * 1000
        logger.info(f"对话历史获取完成，消息数量: {len(history)}，耗时: {history_time:.2f}ms")

        # 步骤1.5: 压缩超长对话历史（节省 token 成本）
        original_count = len(history)
        history = await compress_history(history, _get_llm())
        if len(history) != original_count:
            logger.info(f"对话历史已压缩: {original_count} → {len(history)} 条消息")

        # 获取用户ID（从会话中，或从 JWT 令牌提取）
        user_id = await conversation_service.get_user_id(body.session_id)
        if not user_id:
            user_id = _extract_user_id(authorization)

        # 路由查询到合适的Agent
        logger.info("步骤2: 路由查询到合适的Agent...")
        route_start = time.time()
        result = await _get_coordinator().route_query(
            user_query=body.message,
            conversation_history=history,
            current_agent=body.current_agent,
            user_id=user_id,
            session_id=body.session_id
        )
        route_time = (time.time() - route_start) * 1000
        logger.info(f"路由查询完成，选择Agent: {result['agent']}，耗时: {route_time:.2f}ms")

        # 保存用户消息
        logger.info("步骤3: 保存用户消息...")
        save_start = time.time()
        await conversation_service.add_message(
            session_id=body.session_id,
            role="user",
            content=body.message
        )
        save_time = (time.time() - save_start) * 1000
        logger.info(f"用户消息保存完成，耗时: {save_time:.2f}ms")

        # 保存AI回复
        logger.info("步骤4: 保存AI回复...")
        await conversation_service.add_message(
            session_id=body.session_id,
            role="assistant",
            content=result["response"],
            agent_name=result["agent"]
        )
        logger.info("AI回复保存完成")

        total_time = (time.time() - start_time) * 1000
        logger.info(f"消息处理完成，总耗时: {total_time:.2f}ms")
        logger.info("========== 发送消息完成 ==========\n")

        return ChatResponse(
            response=result["response"],
            agent=result["agent"],
            session_id=body.session_id
        )
    except Exception as e:
        total_time = (time.time() - start_time) * 1000
        logger.error(f"消息处理失败，耗时: {total_time:.2f}ms，错误: {str(e)}", exc_info=True)
        logger.info("========== 发送消息失败 ==========\n")
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}") from e

# 流式响应端点

@router.post("/message/stream")
@limiter.limit("30/minute")
async def send_message_stream(request: Request, body: SendMessageRequest, authorization: str | None = Header(None)):
    """
    发送消息并获取流式AI回复（改善延迟体验）

    - **session_id**: 会话ID
    - **message**: 用户消息内容
    - **current_agent**: 当前活跃的Agent名称（可选）
    - 返回流式AI回复
    """
    start_time = time.time()
    logger.info("========== 发送消息请求(流式) ==========")

    try:
        logger.info(f"Session ID: {body.session_id}")
        logger.info(f"用户消息: {body.message[:50]}..." if len(body.message) > 50 else f"用户消息: {body.message}")
        logger.info(f"当前Agent: {body.current_agent if body.current_agent else '无'}")

        # 获取对话历史
        logger.info("步骤1: 获取对话历史...")
        history = await conversation_service.get_conversation_history(body.session_id)
        logger.info(f"对话历史获取完成，消息数量: {len(history)}")

        # 获取用户ID（从会话中，或从 JWT 令牌提取）
        user_id = await conversation_service.get_user_id(body.session_id)
        if not user_id:
            user_id = _extract_user_id(authorization)

        # 保存用户消息
        await conversation_service.add_message(
            session_id=body.session_id, role="user", content=body.message
        )

        coordinator = _get_coordinator()

        # 流式仅 GraphCoordinator 支持，旧版回退到伪流式
        if not hasattr(coordinator, "route_query_stream"):
            result = await coordinator.route_query(
                user_query=body.message, conversation_history=history,
                current_agent=body.current_agent, user_id=user_id, session_id=body.session_id,
            )
            resp = result["response"]
            agent = result["agent"]
            await conversation_service.add_message(
                session_id=body.session_id, role="assistant", content=resp, agent_name=agent,
            )

            async def fallback_gen():
                for i in range(0, len(resp), 10):
                    yield f"data: {resp[i:i+10]}\n\n"
                yield f"data: [END]|{agent}|{body.session_id}\n\n"
            return StreamingResponse(fallback_gen(), media_type="text/event-stream")

        async def generate():
            full_response = ""
            agent_name = "customer_service_agent"

            async for chunk in coordinator.route_query_stream(
                user_query=body.message,
                conversation_history=history,
                current_agent=body.current_agent,
                user_id=user_id,
                session_id=body.session_id,
            ):
                if chunk.startswith("[END]|"):
                    parts = chunk.split("|")
                    agent_name = parts[1] if len(parts) > 1 else agent_name
                    if full_response:
                        with contextlib.suppress(Exception):
                            await conversation_service.add_message(
                                session_id=body.session_id,
                                role="assistant", content=full_response, agent_name=agent_name,
                            )
                    yield f"data: [END]|{agent_name}|{body.session_id}\n\n"
                    logger.info(f"流式完成: {len(full_response)} 字符")
                else:
                    full_response += str(chunk)
                    yield f"data: {chunk}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        total_time = (time.time() - start_time) * 1000
        logger.error(f"消息处理失败(流式)，耗时: {total_time:.2f}ms，错误: {str(e)}", exc_info=True)
        logger.info("========== 发送消息(流式)失败 ==========\n")
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}") from e

@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str):
    """
    获取对话历史

    - **session_id**: 会话ID
    - 返回对话历史和消息数量
    """
    try:
        history = await conversation_service.get_conversation_history(session_id)
        return ConversationHistoryResponse(
            session_id=session_id,
            history=history,
            message_count=len(history)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}") from e

@router.delete("/conversation/{session_id}")
async def delete_conversation(session_id: str):
    """
    删除对话会话

    - **session_id**: 会话ID
    - 返回删除结果
    """
    try:
        success = await conversation_service.delete_conversation(session_id)
        if success:
            return {"status": "success", "message": "会话删除成功"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}") from e

@router.get("/sessions")
async def get_all_sessions():
    """
    获取所有活跃会话

    - 返回所有活跃会话的列表
    """
    try:
        sessions = conversation_service.get_all_sessions()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}") from e

@router.get("/conversation/{session_id}/export")
async def export_conversation(session_id: str):
    """
    导出对话历史为JSON格式

    - **session_id**: 会话ID
    - 返回JSON格式的对话历史
    """
    try:
        export_data = await conversation_service.export_conversation(session_id)
        if export_data:
            return {"data": export_data, "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出对话失败: {str(e)}") from e
