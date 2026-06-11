"""
LLM服务模块 - 提供统一的LLM调用接口

该模块封装了对LLM模型的调用，提供简洁的文本生成接口。
内置指数退避重试机制，应对网络抖动等临时性故障。
"""

import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIError, APITimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils.logger import get_logger
from ..utils.settings import settings

logger = get_logger("llm_service")


class LLMService:
    """
    LLM服务封装类

    提供统一的LLM调用接口，支持文本生成、对话等功能。
    """

    def __init__(self):
        """初始化LLM服务"""
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        """初始化LLM模型"""
        try:
            self.llm = ChatOpenAI(
                model_name=settings.ALIYUN_MODEL_NAME,
                openai_api_key=settings.ALIYUN_API_KEY,
                openai_api_base=settings.ALIYUN_API_BASE,
                temperature=0.7,
                max_tokens=2048
            )
            logger.info(f"LLM服务初始化完成，使用模型: {settings.ALIYUN_MODEL_NAME}")
        except Exception as e:
            logger.error(f"LLM服务初始化失败: {str(e)}", exc_info=True)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIError, APITimeoutError, APIConnectionError, ConnectionError, TimeoutError)),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"LLM调用失败 (第{retry_state.attempt_number}次)，"
            f"{retry_state.outcome.exception() if retry_state.outcome else '未知错误'}，"
            f"将在 {retry_state.next_action.sleep:.1f} 秒后重试"
        )
    )
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop_tokens: list[str] | None = None
    ) -> str:
        """
        生成文本响应

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            temperature: 温度参数（控制随机性）
            stop_tokens: 停止词列表

        Returns:
            str: 生成的文本响应
        """
        if not self.llm:
            self._init_llm()

        start_time = time.time()

        try:
            # 使用 bind 创建临时实例，不修改共享 llm，并发安全
            llm = self.llm.bind(temperature=temperature, max_tokens=max_tokens)
            if stop_tokens:
                llm = llm.bind(stop=stop_tokens)

            response = await llm.ainvoke(prompt)
            content = response.content.strip() if hasattr(response, "content") else str(response).strip()

            elapsed_time = (time.time() - start_time) * 1000
            logger.debug(f"LLM调用完成，耗时: {elapsed_time:.2f}ms，响应长度: {len(content)}")
            return content

        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(f"LLM调用失败，耗时: {elapsed_time:.2f}ms，错误: {str(e)}", exc_info=True)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIError, APITimeoutError, APIConnectionError, ConnectionError, TimeoutError)),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"LLM对话失败 (第{retry_state.attempt_number}次)，"
            f"将在 {retry_state.next_action.sleep:.1f} 秒后重试"
        )
    )
    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """
        对话模式生成响应

        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            max_tokens: 最大生成token数
            temperature: 温度参数

        Returns:
            str: 生成的响应文本
        """
        if not self.llm:
            self._init_llm()

        start_time = time.time()

        try:
            llm = self.llm.bind(temperature=temperature, max_tokens=max_tokens)

            lc_messages = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))

            response = await llm.ainvoke(lc_messages)
            content = response.content.strip() if hasattr(response, "content") else str(response).strip()

            elapsed_time = (time.time() - start_time) * 1000
            logger.debug(f"LLM对话完成，耗时: {elapsed_time:.2f}ms")
            return content

        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(f"LLM对话失败，耗时: {elapsed_time:.2f}ms，错误: {str(e)}", exc_info=True)
            raise

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型配置信息
        """
        return {
            "model_name": settings.ALIYUN_MODEL_NAME,
            "api_base": settings.ALIYUN_API_BASE,
            "temperature": self.llm.temperature if self.llm else 0.7,
            "max_tokens": 2048
        }
