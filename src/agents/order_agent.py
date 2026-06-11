import time

from langchain_core.language_models.chat_models import BaseChatModel

from ..services.order_service import OrderService
from ..utils.logger import get_logger
from .base_agent import BaseAgent


class OrderAgent(BaseAgent):
    """
    订单Agent - 处理订单相关的所有查询

    负责：
    - 查询订单状态
    - 查询物流信息
    - 处理订单修改请求
    - 处理退款申请
    """

    def __init__(self, llm: BaseChatModel, order_service: OrderService):
        super().__init__(llm, "order_agent")
        self.order_service = order_service
        self.logger = get_logger("order_agent")

    def get_system_prompt(self) -> str:
        return """
你是一位专业的订单处理专员，负责处理用户的订单相关查询。

角色职责：
1. 查询订单状态
2. 查询物流信息
3. 处理订单修改请求
4. 处理退款申请

回复要求：
- 使用中文回复
- 提供准确的订单信息
- 如果需要用户提供更多信息（如订单号），请明确询问
- 保持专业、高效的服务态度
- 在回答中明确说明你是订单处理专员

重要规则：
- 你只能回答系统提供的真实订单数据
- 如果用户提供的订单号在系统中不存在，必须告知用户订单未找到
- 绝对不能编造或虚构任何订单信息
- 如果没有订单数据，请要求用户提供正确的订单号

订单状态说明：
- 待付款：订单已创建，等待付款
- 待发货：付款成功，等待商家发货
- 已发货：商家已发货，等待用户签收
- 已完成：订单已签收
- 已取消：订单已取消
"""

    async def run(
        self,
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        session_id: str | None = None
    ) -> str:
        start_time = time.time()
        self.logger.info("开始处理订单查询...")
        self.logger.info(f"用户查询: {user_query[:30]}..." if len(user_query) > 30 else f"用户查询: {user_query}")

        # 提取订单信息
        self.logger.info("提取订单信息...")
        order_info = await self._extract_order_info(user_query)

        if order_info:
            self.logger.info(f"检测到订单号: {order_info['order_id']}")
            self.logger.info("查询订单详情...")

            # 查询订单详情
            order_details = await self.order_service.get_order_details(order_info["order_id"])

            if order_details:
                self.logger.info("订单详情查询成功")
                order_context = f"\n订单详情：\n{order_details}"
                self.logger.info("准备构建消息...")
            else:
                # 订单不存在，直接返回错误信息
                self.logger.info(f"订单不存在: {order_info['order_id']}")
                return f"订单不存在。您提供的订单号 {order_info['order_id']} 未在系统中找到，请检查订单号是否正确。"
        else:
            self.logger.info("未检测到订单号，使用通用回复")
            order_context = ""

        # 检索记忆上下文
        self.logger.info("检索记忆上下文...")
        memory_context = await self.recall_context(
            user_query=user_query,
            user_id=user_id,
            session_id=session_id
        )

        # 构建消息
        self.logger.info("构建消息列表...")
        messages = self.build_messages(user_query, conversation_history, memory_context)

        if order_context:
            # 将订单详情添加到用户消息中
            messages[-1].content += order_context
            self.logger.info("已将订单详情添加到消息中")

        self.logger.info(f"消息数量: {len(messages)}")

        # 调用LLM生成响应
        self.logger.info("调用LLM生成响应...")
        llm_start = time.time()
        response = await self.llm.agenerate([messages])
        llm_time = (time.time() - llm_start) * 1000

        result = response.generations[0][0].text
        total_time = (time.time() - start_time) * 1000

        # 保存交互到记忆系统
        self.logger.info("保存交互到记忆系统...")
        await self.save_interaction(
            user_query=user_query,
            agent_response=result,
            user_id=user_id,
            session_id=session_id,
            metadata={"order_id": order_info["order_id"] if order_info else None}
        )

        self.logger.info(f"LLM调用完成，耗时: {llm_time:.2f}ms")
        self.logger.info(f"响应长度: {len(result)} 字符")
        self.logger.info(f"处理完成，总耗时: {total_time:.2f}ms")

        return result

    async def _extract_order_info(self, user_query: str) -> dict[str, str] | None:
        """从用户查询中提取订单信息"""
        import re
        self.logger.info("开始提取订单号...")

        # 匹配多种订单号格式
        patterns = [
            r'订单号[：:]?\s*([A-Za-z0-9]{4,20})',  # 订单号 + 数字
            r'订单[：:]?\s*([A-Za-z0-9]{4,20})',     # 订单 + 数字
            r'单号[：:]?\s*([A-Za-z0-9]{4,20})',     # 单号 + 数字
            r'号[码是为]?\s*([A-Za-z0-9]{4,20})',        # 号 + 数字
            r'^\s*([A-Za-z0-9]{4,20})\s*$',           # 纯订单号（单独一行）
            r'(\b[A-Za-z0-9]{8,20}\b)',               # 独立的8-20位字母数字串
        ]

        for pattern in patterns:
            match = re.search(pattern, user_query)
            if match:
                order_id = match.group(1)
                # 验证订单号是否合理（排除纯数字但长度小于4的情况）
                if len(order_id) >= 4:
                    self.logger.info(f"提取到订单号: {order_id}")
                    return {"order_id": order_id}

        self.logger.info("未匹配到订单号")
        return None
