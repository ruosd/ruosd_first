"""
Agent 协作图 — LangGraph 核心编排

流程图:
  START → classify_intent → route_by_intent → [order|product|service]_agent → summarize → END

每个 Agent 节点内部包含 ReAct 循环:
  LLM 思考 → 调用工具 → 获取结果 → LLM 再思考 → ... → 最终回复
"""

from typing import Literal
import time
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .state import AgentState
from .intent_router import create_intent_classifier
from .tools import ORDER_TOOLS, PRODUCT_TOOLS, SERVICE_TOOLS
from ..utils.logger import get_logger
from ..utils.metrics import MetricsCollector

logger = get_logger("agent_graph")

# ── 系统提示词 ──
SYSTEM_PROMPTS = {
    "order": """你是订单客服助手。你可以使用以下工具获取真实数据:
- query_order: 查询订单详情（含物流）
- list_user_orders: 查看用户订单列表
- search_orders: 按关键词搜索订单

请用友好语气回复。如信息不足请引导用户提供订单号。""",

    "product": """你是产品顾问助手。你可以使用以下工具:
- search_product: 搜索产品
- get_product_detail: 查看产品详情

请用专业语气回复。推荐时说明理由。""",

    "service": """你是通用客服助手。你可以使用以下工具:
- search_knowledge: 从知识库搜索政策和流程

请用耐心友善的语气回复。对投诉先表达理解和歉意。""",
}


def build_agent_graph(llm) -> StateGraph:
    """
    构建完整的 Agent 协作图

    Args:
        llm: LangChain ChatModel 实例（ChatOpenAI）

    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(AgentState)

    # ── 节点定义 ──

    # 意图识别节点（第二步创建，现在接入 LLM）
    intent_classifier = create_intent_classifier(llm)

    # Agent 节点工厂（普通函数，返回异步节点函数）
    def make_agent_node(agent_type: str):
        """创建特定类型的 Agent 节点"""
        tools_map = {
            "order": ORDER_TOOLS,
            "product": PRODUCT_TOOLS,
            "service": SERVICE_TOOLS,
        }

        tools = tools_map[agent_type]
        prompt = SYSTEM_PROMPTS[agent_type]
        # 优化: 限制 512 token（节省约 40% 推理时间）
        llm_with_tools = llm.bind_tools(tools, max_tokens=512)

        async def agent_node(state: AgentState) -> dict:
            """Agent 节点: 用 LLM + 工具处理用户问题"""
            query = state.get("user_query", "")
            intent = state.get("intent", agent_type)
            messages = list(state.get("messages", []))
            context = state.get("context", "")

            # 构建消息
            system_msg = SystemMessage(content=prompt)
            if context:
                system_msg = SystemMessage(
                    content=prompt + f"\n\n相关背景信息:\n{context}"
                )

            human_msg = HumanMessage(content=query)

            # ReAct 循环: LLM ↔ 工具调用
            # 最多迭代 5 轮，防止死循环
            current_messages = [system_msg, human_msg]
            for _ in range(5):
                llm_start = time.time()
                response = await llm_with_tools.ainvoke(current_messages)
                llm_latency = (time.time() - llm_start) * 1000
                session_id = state.get("session_id", "")
                MetricsCollector.record_llm_call(agent_type, llm_latency, True, session_id)

                # 检查是否有工具调用
                if hasattr(response, "tool_calls") and response.tool_calls:
                    # LLM 决定调用工具
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        logger.info(
                            f"[{agent_type}_agent] 调用工具: {tool_name}({tool_args})"
                        )

                        # 查找并执行工具
                        tool_func = next(
                            (t for t in tools if t.name == tool_name), None
                        )
                        if tool_func:
                            tool_start = time.time()
                            result = await tool_func.ainvoke(tool_args)
                            tool_latency = (time.time() - tool_start) * 1000
                            MetricsCollector.record_tool_call(agent_type, tool_name, tool_latency, True, session_id)
                            # 追加工具结果到消息
                            current_messages.append(response)
                            current_messages.append(
                                AIMessage(content=f"工具 {tool_name} 返回:\n{result}")
                            )
                        else:
                            logger.warning(f"未知工具: {tool_name}")
                            MetricsCollector.record_tool_call(agent_type, tool_name, 0, False, session_id, "未知工具")
                            break  # 避免死循环
                else:
                    # LLM 直接回复，结束循环
                    logger.info(
                        f"[{agent_type}_agent] 回复: {str(response.content)[:80]}..."
                    )
                    return {
                        "agent_output": response.content,
                        "messages": [
                            {"role": "assistant", "content": response.content}
                        ],
                    }

            # 超过最大迭代次数
            return {
                "agent_output": "抱歉，处理您的请求时遇到了问题，请稍后重试。",
                "messages": [{"role": "assistant", "content": "处理超时，请重试"}],
            }

        return agent_node

    # ── 注册节点 ──
    graph.add_node("classify_intent", intent_classifier)
    graph.add_node("order_agent", make_agent_node("order"))
    graph.add_node("product_agent", make_agent_node("product"))
    graph.add_node("service_agent", make_agent_node("service"))
    graph.add_node("summarize", _summarize_node)

    # ── 定义流程 ──
    graph.set_entry_point("classify_intent")

    # 条件路由: 根据意图分发
    graph.add_conditional_edges(
        "classify_intent",
        _route_by_intent,
        {
            "order": "order_agent",
            "product": "product_agent",
            "service": "service_agent",
        },
    )

    # 所有 Agent 执行完毕后进入汇总节点
    graph.add_edge("order_agent", "summarize")
    graph.add_edge("product_agent", "summarize")
    graph.add_edge("service_agent", "summarize")

    # 汇总后结束
    graph.add_edge("summarize", END)

    return graph.compile()


# ── 辅助函数 ──

def _route_by_intent(state: AgentState) -> Literal["order", "product", "service"]:
    """根据意图选择 Agent 分支"""
    intent = state.get("intent", "service")
    if intent in ("order", "product", "service"):
        return intent
    logger.warning(f"未知意图: '{intent}'，默认路由到客服")
    return "service"


def _summarize_node(state: AgentState) -> dict:
    """
    汇总节点: 取 Agent 输出作为最终回复

    当前为简单透传，未来可扩展为多 Agent 协作时合并多个 Agent 的产出。
    """
    output = state.get("agent_output", "抱歉，暂时无法处理您的请求。")
    return {"final_response": output}
