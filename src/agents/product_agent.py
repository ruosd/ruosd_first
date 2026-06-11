from typing import List, Optional, Dict
import time
from langchain_core.language_models.chat_models import BaseChatModel
from .base_agent import BaseAgent
from ..services.product_service import ProductService
from ..utils.logger import get_logger

class ProductAgent(BaseAgent):
    """
    产品Agent - 处理产品相关的所有查询
    
    负责：
    - 查询产品详细信息
    - 推荐相关产品
    - 回答产品技术问题
    - 查询库存状态
    """
    
    def __init__(self, llm: BaseChatModel, product_service: ProductService):
        super().__init__(llm, "product_agent")
        self.product_service = product_service
        self.logger = get_logger("product_agent")
    
    def get_system_prompt(self) -> str:
        return """
你是一位专业的产品咨询专员，负责处理用户的产品相关查询。

角色职责：
1. 查询产品详细信息
2. 推荐相关产品
3. 回答产品技术问题
4. 查询库存状态

回复要求：
- 使用中文回复
- 提供准确的产品信息
- 如果需要用户提供更多信息（如产品名称或ID），请明确询问
- 保持专业、友好的服务态度
- 在回答中明确说明你是产品咨询专员

重要规则：
- 你只能回答系统提供的真实产品数据
- 如果用户询问的产品在系统中不存在，必须告知用户产品未找到
- 绝对不能编造或虚构任何产品信息
- 如果没有产品数据，请明确告知用户无法查询

产品信息结构：
- 产品名称
- 产品描述
- 价格
- 库存数量
- 规格参数
- 售后服务
"""
    
    async def run(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        start_time = time.time()
        self.logger.info(f"开始处理产品查询...")
        self.logger.info(f"用户查询: {user_query[:30]}..." if len(user_query) > 30 else f"用户查询: {user_query}")
        
        # 提取产品信息
        self.logger.info("提取产品信息...")
        product_info = await self._extract_product_info(user_query)
        
        if product_info:
            self.logger.info(f"检测到产品: {product_info['product_name']}")
            self.logger.info("查询产品详情...")
            
            # 查询产品详情
            product_details = await self.product_service.get_product_details(product_info["product_name"])
            
            if product_details:
                self.logger.info(f"产品详情查询成功")
                product_context = f"\n产品详情：\n{product_details}"
                self.logger.info(f"准备构建消息...")
            else:
                # 产品不存在，直接返回错误信息
                self.logger.info(f"产品不存在: {product_info['product_name']}")
                return f"抱歉，未查询到相关产品信息。您询问的 **{product_info['product_name']}** 未在系统中找到，请检查产品名称是否正确。"
        else:
            self.logger.info("未检测到产品关键词，使用通用回复")
            product_context = ""
        
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
        
        if product_context:
            # 将产品详情添加到用户消息中
            messages[-1].content += product_context
            self.logger.info("已将产品详情添加到消息中")
        
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
            metadata={"product_name": product_info["product_name"] if product_info else None}
        )
        
        self.logger.info(f"LLM调用完成，耗时: {llm_time:.2f}ms")
        self.logger.info(f"响应长度: {len(result)} 字符")
        self.logger.info(f"处理完成，总耗时: {total_time:.2f}ms")
        
        return result
    
    async def _extract_product_info(self, user_query: str) -> Optional[Dict[str, str]]:
        """从用户查询中提取产品信息"""
        import re
        self.logger.info("开始提取产品关键词...")
        
        # 尝试匹配品牌产品名（如：苹果16、华为Mate60、小米14）
        # 匹配以品牌关键词开头的产品名
        brand_patterns = [
            r'((?:苹果|华为|小米|三星|OPPO|VIVO|荣耀|一加|红米|iPhone|iphone|索尼|联想|戴尔|惠普|华硕|微软)[\u4e00-\u9fa5a-zA-Z0-9]{0,30})',
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, user_query)
            if match:
                product_name = match.group(1)
                if len(product_name) >= 2:  # 至少2个字符
                    self.logger.info(f"匹配到品牌产品名: {product_name}")
                    return {"product_name": product_name}
        
        # 常见产品类型关键词
        product_keywords = [
            "手机", "电脑", "笔记本", "平板", "耳机", "手表", "手环",
            "充电器", "数据线", "键盘", "鼠标", "音响", "相机",
            "摄像机", "游戏机", "路由器", "移动硬盘", "U盘", "内存条"
        ]
        
        for keyword in product_keywords:
            if keyword in user_query:
                self.logger.info(f"匹配到产品关键词: {keyword}")
                return {"product_name": keyword}
        
        self.logger.info("未匹配到产品关键词")
        return None
