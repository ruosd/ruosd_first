"""
Graph 协调器 — 统一对话协调入口

合并原 AgentCoordinator（问题重写、Agent转接）和原 GraphCoordinator（LangGraph 路由）。
"""

from collections.abc import AsyncGenerator

from ..services.agent_manager import AgentManager
from ..services.llm_service import LLMService
from ..services.question_rewriter import QuestionRewriter
from ..utils.logger import get_logger
from .agent_graph import SYSTEM_PROMPTS, build_agent_graph
from .state import AgentState
from .tools import ORDER_TOOLS, PRODUCT_TOOLS, SERVICE_TOOLS

logger = get_logger("graph_coordinator")


class GraphCoordinator:
    """
    LangGraph 对话协调器

    功能：
    - 问题重写：将口语化问题转换为专业格式
    - LangGraph 意图识别 + Agent 路由
    - 主动转接检测
    - 记忆系统集成
    """

    # 转接关键词
    TRANSFER_KEYWORDS = ["转接", "转给", "转至", "转移到", "切换到"]

    def __init__(self, llm=None):
        """初始化协调器

        Args:
            llm: LangChain ChatModel 实例（可选，未提供时延迟初始化）
        """
        self.llm = llm
        self.graph = None
        self.agent_manager = AgentManager()
        self._llm_service = None
        self._question_rewriter = None
        self.rewrite_enabled = True

        if llm is not None:
            self.graph = build_agent_graph(llm)
            logger.info("GraphCoordinator 已初始化，使用 LangGraph")

    def _ensure_llm(self):
        """确保 LLM 可用（延迟初始化）"""
        if self.llm is None:
            self._llm_service = LLMService()
            self.llm = self._llm_service.llm
            if self.llm:
                self.graph = build_agent_graph(self.llm)
                logger.info("LLM 延迟初始化完成")

    @property
    def question_rewriter(self):
        if self._question_rewriter is None:
            svc = self._llm_service or LLMService()
            self._question_rewriter = QuestionRewriter(svc)
        return self._question_rewriter

    async def route_query(
        self,
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        current_agent: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        路由用户查询到合适的 Agent 并获取回复

        Args:
            user_query: 用户消息
            conversation_history: 对话历史
            current_agent: 当前活跃 Agent
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            {"response": "AI回复", "agent": "order_agent"}
        """
        self._ensure_llm()

        # 问题重写
        original_query = user_query
        if self.rewrite_enabled:
            user_query = await self.question_rewriter.rewrite(
                user_query, conversation_history
            )
            if user_query != original_query:
                logger.info(f"问题已重写: {original_query} -> {user_query}")

        # 主动转接检测
        transfer_target = self._check_transfer_request(user_query)
        if transfer_target and self.agent_manager.has_agent(transfer_target):
            logger.info(f"检测到主动转接请求，目标: {transfer_target}")
            if current_agent and session_id:
                await self._transfer_memory(
                    current_agent, transfer_target, session_id, user_id
                )
            return await self._run_agent(
                transfer_target, user_query, conversation_history, user_id, session_id
            )

        # 走 LangGraph
        if self.graph is None:
            return {
                "response": "服务暂时不可用，请稍后重试。",
                "agent": "customer_service_agent",
            }

        initial_state: AgentState = {
            "messages": conversation_history or [],
            "user_query": user_query,
            "intent": "",
            "context": "",
            "agent_output": "",
            "final_response": "",
            "user_id": user_id,
            "session_id": session_id,
            "current_agent": current_agent,
        }

        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"LangGraph 执行失败: {e}", exc_info=True)
            return {
                "response": "抱歉，服务暂时不可用，请稍后重试。",
                "agent": "customer_service_agent",
            }

        response = final_state.get("final_response", "")
        intent = final_state.get("intent", "service")
        agent_name_map = {
            "order": "order_agent",
            "product": "product_agent",
            "service": "customer_service_agent",
        }
        return {"response": response, "agent": agent_name_map.get(intent, "customer_service_agent")}

    async def route_query_stream(
        self,
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        current_agent: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式路由 — 逐 token 输出

        Yields:
            token1, token2, ..., "[END]|agent_name|session_id"
        """
        self._ensure_llm()

        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        from .intent_router import create_intent_classifier

        # 意图识别
        try:
            classifier = create_intent_classifier(self.llm)
            intent_state = await classifier({
                "messages": conversation_history or [],
                "user_query": user_query,
                "intent": "", "context": "", "agent_output": "", "final_response": "",
                "user_id": user_id or "", "session_id": session_id or "",
                "current_agent": current_agent or "",
            })
            intent = intent_state.get("intent", "service")
        except Exception as e:
            logger.warning(f"意图识别失败: {e}，默认路由到客服")
            intent = "service"

        tools_map = {"order": ORDER_TOOLS, "product": PRODUCT_TOOLS, "service": SERVICE_TOOLS}
        prompt_map = {"order": SYSTEM_PROMPTS["order"], "product": SYSTEM_PROMPTS["product"], "service": SYSTEM_PROMPTS["service"]}
        agent_map = {"order": "order_agent", "product": "product_agent", "service": "customer_service_agent"}
        tools = tools_map.get(intent, SERVICE_TOOLS)
        prompt = prompt_map.get(intent, SYSTEM_PROMPTS["service"])
        agent_name = agent_map.get(intent, "customer_service_agent")

        # ReAct 循环
        llm_with_tools = self.llm.bind_tools(tools, max_tokens=512)
        current_messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_query),
        ]

        for _ in range(3):
            response = await llm_with_tools.ainvoke(current_messages)

            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool_func = next((t for t in tools if t.name == tc.get("name", "")), None)
                    if tool_func:
                        result = await tool_func.ainvoke(tc.get("args", {}))
                        current_messages.append(response)
                        current_messages.append(AIMessage(content=f"工具 {tc['name']} 返回:\n{result}"))
                continue

            full_response = ""
            try:
                async for chunk in llm_with_tools.astream(current_messages):
                    if hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
                        yield chunk.content
            except Exception:
                if not full_response:
                    yield "抱歉，服务暂时不可用。"

            yield f"[END]|{agent_name}|{session_id or ''}"
            return

        yield "抱歉，处理您的请求时遇到了问题。"
        yield f"[END]|{agent_name}|{session_id or ''}"

    def _check_transfer_request(self, user_query: str) -> str | None:
        """检测用户是否主动要求转接"""
        if not any(kw in user_query for kw in self.TRANSFER_KEYWORDS):
            return None
        agent_keywords = {
            "order_agent": ["订单", "订单专员", "物流"],
            "product_agent": ["产品", "产品专员"],
            "customer_service_agent": ["客服", "人工", "投诉"],
        }
        for agent_name, keywords in agent_keywords.items():
            if any(kw in user_query for kw in keywords) and self.agent_manager.has_agent(agent_name):
                    return agent_name
        return None

    async def _transfer_memory(self, from_agent: str, to_agent: str, session_id: str, user_id: str | None):
        """Agent 转接时传递记忆"""
        try:
            from ..services.memory_service import get_memory_service
            ms = await get_memory_service()
            await ms.transfer_memory_between_agents(from_agent, to_agent, session_id, user_id)
        except Exception as e:
            logger.warning(f"记忆传递失败: {e}")

    async def _run_agent(self, agent_name, user_query, history, user_id, session_id):
        """直接运行指定 Agent（用于主动转接）"""
        agent = self.agent_manager.get_agent(agent_name)
        if not agent:
            return {"response": "该服务暂不可用。", "agent": "system"}
        response = await agent.run(user_query, history, user_id, session_id)
        return {"response": response, "agent": agent_name}

    def get_available_agents(self) -> list[str]:
        """获取所有可用的 Agent 名称"""
        return list(self.agent_manager.agents.keys())
