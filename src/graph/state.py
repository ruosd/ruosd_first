"""
Agent 协作状态定义 — LangGraph 的核心数据结构

原理:
  LangGraph 中所有 Agent 共享一个 State 对象。每个节点从 State 读取输入，
  写入输出，下一个节点继续处理。就像流水线上的托盘。
"""

from typing import TypedDict


class AgentState(TypedDict):
    """
    Agent 协作状态 — 在意图识别→路由→执行→汇总的流程中传递
    """

    # 完整对话历史
    messages: list[dict]

    # 当前轮次输入
    user_query: str

    # 意图识别结果: "order" / "product" / "service"
    intent: str

    # 从记忆/知识库检索的上下文
    context: str

    # Agent 执行后的输出
    agent_output: str

    # 最终返回给用户的回复
    final_response: str

    # 多租户
    user_id: str | None
    session_id: str | None

    # 当前 Agent（用于转接判断）
    current_agent: str | None
