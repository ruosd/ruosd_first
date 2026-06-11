from abc import ABC, abstractmethod
from typing import Any

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel


class BaseAgent(ABC):
    def __init__(self, llm: BaseChatModel, agent_name: str):
        self.llm = llm
        self.agent_name = agent_name
        self.system_prompt = ""
        self._memory_service = None

    async def _get_memory_service(self):
        """获取记忆服务（延迟导入避免循环依赖）"""
        if self._memory_service is None:
            from ..services import get_memory_service
            self._memory_service = await get_memory_service()
        return self._memory_service

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def build_messages(
        self,
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        memory_context: str | None = None
    ) -> list:
        """
        构建消息列表，支持记忆上下文

        Args:
            user_query: 用户查询
            conversation_history: 对话历史
            memory_context: 记忆上下文

        Returns:
            消息列表
        """
        messages = [SystemMessage(content=self.get_system_prompt())]

        # 添加记忆上下文
        if memory_context:
            memory_prompt = f"""
以下是与当前问题相关的记忆信息：

{memory_context}

请根据以上记忆信息回答用户问题。
"""
            messages.append(SystemMessage(content=memory_prompt))

        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_query))
        return messages

    async def recall_context(
        self,
        user_query: str,
        user_id: str | None = None,
        session_id: str | None = None,
        memory_types: list | None = None
    ) -> str:
        """
        检索相关记忆上下文

        Args:
            user_query: 用户查询
            user_id: 用户ID
            session_id: 会话ID
            memory_types: 记忆类型列表

        Returns:
            记忆上下文文本
        """
        from ..services import MemoryType

        if memory_types is None:
            memory_types = [MemoryType.SHORT_TERM, MemoryType.LONG_TERM]

        memory_service = await self._get_memory_service()
        return await memory_service.retrieve_memory_context(
            query_text=user_query,
            memory_types=memory_types,
            user_id=user_id,
            session_id=session_id,
            n_results=5
        )

    async def save_interaction(
        self,
        user_query: str,
        agent_response: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None
    ):
        """
        保存Agent交互到记忆系统

        Args:
            user_query: 用户查询
            agent_response: Agent响应
            user_id: 用户ID
            session_id: 会话ID
            metadata: 元数据
        """
        memory_service = await self._get_memory_service()
        await memory_service.save_agent_interaction(
            user_query=user_query,
            agent_response=agent_response,
            agent_type=self.agent_name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata
        )

    @abstractmethod
    async def run(
        self,
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        session_id: str | None = None
    ) -> str:
        pass

    def get_agent_info(self) -> dict[str, str]:
        return {
            "agent_name": self.agent_name,
            "description": self.__doc__ or "No description available"
        }
