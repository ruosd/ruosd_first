from typing import List, Optional, Dict
import time
from langchain_core.language_models.chat_models import BaseChatModel
from .base_agent import BaseAgent
from ..utils.logger import get_logger

class CustomerServiceAgent(BaseAgent):
    """
    客户服务Agent - 处理用户的一般咨询、投诉和建议
    
    负责：
    - 解答常见问题
    - 处理用户投诉
    - 提供售后服务
    - 识别需要转接到其他专业Agent的请求（但不执行转接，由系统处理）
    
    重要：此Agent不执行实际转接，只是识别转接需求。
    实际转接由AgentCoordinator根据关键词自动处理。
    """
    
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, "customer_service_agent")
        self.logger = get_logger("customer_service_agent")
    
    def get_system_prompt(self) -> str:
        return """
你是一位专业的电商客服代表，负责处理用户的通用咨询、投诉和建议。

【你的专长】
- 解答常见问题（如配送时间、退换货政策、客服工作时间等）
- 处理用户投诉并提供解决方案
- 提供售后服务说明
- 介绍促销活动

【绝对禁止】
1. 禁止回答任何需要查询具体订单信息的问题（如订单状态、物流进度、退款进度）
2. 禁止回答任何需要查询具体产品信息的问题（如产品价格、库存数量、产品规格）
3. 禁止编造任何订单或产品的具体数据

【订单/产品问题的处理方式】
当用户询问订单或产品相关问题时，你必须：
- 明确告知用户："我是通用客服代表，无法查询具体的订单/产品信息。"
- 引导用户："请告诉我您的具体需求，系统会为您安排对应的专员处理。"
- 绝对不能提供任何具体的订单状态、物流信息、价格或库存数据

【常用回答参考】
- 配送时间：一般3-5个工作日，偏远地区可能需要5-7天
- 退换货：支持7天无理由退换货（特殊商品除外）
- 客服时间：周一至周日 9:00-21:00
- 支付方式：支持支付宝、微信支付、银行卡等
"""
    
    async def run(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        start_time = time.time()
        self.logger.info(f"开始处理用户查询...")
        self.logger.info(f"用户查询: {user_query[:30]}..." if len(user_query) > 30 else f"用户查询: {user_query}")
        
        # 硬编码检查：如果用户询问订单或产品相关问题，直接拒绝
        if self._is_order_query(user_query):
            self.logger.info("检测到订单查询，客服Agent无权回答，返回拒绝信息")
            # 保存交互到记忆系统
            await self.save_interaction(
                user_query=user_query,
                agent_response="订单查询被拒绝，需转订单专员",
                user_id=user_id,
                session_id=session_id,
                metadata={"rejected": "order_query"}
            )
            return "您好，我是通用客服代表，无法查询具体的订单信息。请告诉我您的订单号，系统会为您安排订单专员处理。"
        
        if self._is_product_query(user_query):
            self.logger.info("检测到产品查询，客服Agent无权回答，返回拒绝信息")
            # 保存交互到记忆系统
            await self.save_interaction(
                user_query=user_query,
                agent_response="产品查询被拒绝，需转产品专员",
                user_id=user_id,
                session_id=session_id,
                metadata={"rejected": "product_query"}
            )
            return "您好，我是通用客服代表，无法查询具体的产品信息。请告诉我您想了解的产品，系统会为您安排产品专员处理。"
        
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
            session_id=session_id
        )
        
        self.logger.info(f"LLM调用完成，耗时: {llm_time:.2f}ms")
        self.logger.info(f"响应长度: {len(result)} 字符")
        self.logger.info(f"处理完成，总耗时: {total_time:.2f}ms")
        
        return result
    
    def _is_order_query(self, user_query: str) -> bool:
        """检测是否是订单相关查询"""
        order_keywords = ["订单", "物流", "发货", "快递", "配送", "退货", "退款", "单号"]
        return any(keyword in user_query for keyword in order_keywords)
    
    def _is_product_query(self, user_query: str) -> bool:
        """检测是否是产品相关查询"""
        product_keywords = ["产品", "商品", "价格", "库存", "规格", "参数", "型号"]
        return any(keyword in user_query for keyword in product_keywords)
