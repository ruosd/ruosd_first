"""
问题重写服务 - 将用户随意的问题转换为更专业、更清晰的格式

该服务使用LLM将用户的自然语言问题进行规范化处理，
使其更有利于Agent解读和处理。
"""

import re
from typing import Optional
import time
from ..utils.logger import get_logger

logger = get_logger("question_rewriter")


class QuestionRewriter:
    """
    用户问题重写器
    
    将用户随意的口语化问题转换为更专业、结构化的问题格式，
    提高Agent理解和处理问题的准确性。
    """
    
    def __init__(self, llm_service):
        """
        初始化问题重写器
        
        Args:
            llm_service: LLM服务实例，用于调用LLM进行问题重写
        """
        self.llm_service = llm_service
        self.enabled = True  # 是否启用问题重写功能
        
        # 缓存已处理的问题，避免重复处理
        self.cache = {}
        self.cache_size = 1000
    
    def _clean_cache(self):
        """清理缓存，保持缓存大小在限制范围内"""
        if len(self.cache) > self.cache_size:
            # 删除最旧的一半缓存
            keys = list(self.cache.keys())[:self.cache_size // 2]
            for key in keys:
                del self.cache[key]
    
    def _is_already_formal(self, question: str) -> bool:
        """
        判断问题是否已经是比较规范的格式
        
        Args:
            question: 用户问题
            
        Returns:
            bool: 是否已经规范
        """
        # 如果问题包含以下特征，认为已经比较规范
        formal_patterns = [
            r'^请(帮我)?',           # 以"请"开头
            r'(查询|查看|获取|确认)(一下)?',  # 包含查询动词
            r'^[你我他][是有想]',       # 以人称代词开头的陈述句
            r'^(订单|产品|物流|客服)',   # 以业务关键词开头
            r'^\d{4,20}$',           # 纯数字订单号
        ]
        
        for pattern in formal_patterns:
            if re.search(pattern, question):
                return True
        return False
    
    def _preprocess_question(self, question: str) -> str:
        """
        预处理问题，去除多余字符
        
        Args:
            question: 用户问题
            
        Returns:
            str: 预处理后的问题
        """
        # 去除首尾空白
        question = question.strip()
        
        # 去除多余的标点符号
        question = re.sub(r'[!！]{2,}', '！', question)
        question = re.sub(r'[?？]{2,}', '？', question)
        question = re.sub(r'[.。]{2,}', '。', question)
        
        # 去除表情符号
        question = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', question)
        
        # 去除特殊字符
        question = re.sub(r'[*#@$%^&()_+=\[\]{}|;:\\<>]', '', question)
        
        return question
    
    async def rewrite(self, question: str, conversation_history: Optional[list] = None) -> str:
        """
        重写用户问题，使其更专业、更清晰
        
        Args:
            question: 用户原始问题
            conversation_history: 对话历史（可选）
            
        Returns:
            str: 重写后的专业问题
        """
        if not self.enabled:
            return question
        
        # 预处理问题
        original_question = question
        question = self._preprocess_question(question)
        
        # 如果问题过短，直接返回
        if len(question) < 2:
            return original_question
        
        # 检查是否已经是规范格式
        if self._is_already_formal(question):
            logger.info(f"问题已规范，无需重写: {question}")
            return question
        
        # 检查缓存
        if question in self.cache:
            logger.info(f"命中缓存，直接返回重写结果")
            return self.cache[question]
        
        try:
            start_time = time.time()
            
            # 构建重写提示词
            system_prompt = """
你是一个专业的问题重写助手。请将用户的口语化问题转换为更正式、更清晰的专业表达，同时保持原意不变。

要求：
1. 使用正式、礼貌的语言
2. 明确表达用户的核心需求
3. 去除冗余和口语化表达
4. 保持问题的完整性和准确性
5. 输出格式：直接输出重写后的问题，不要添加其他内容

示例：
输入：苹果16多少钱
输出：请帮我查询苹果16的价格

输入：订单到哪了
输出：请帮我查询订单的物流状态

输入：这个能退吗
输出：请问该商品是否支持退货

输入：什么时候发货
输出：请告诉我订单的发货时间

输入：手机有货吗
输出：请帮我查询该手机的库存情况
"""
            
            # 如果有对话历史，添加到上下文中
            context = ""
            if conversation_history and len(conversation_history) > 0:
                context = "\n参考历史对话：\n"
                for msg in conversation_history[-3:]:  # 取最近3条
                    role = "用户" if msg["role"] == "user" else "客服"
                    context += f"{role}: {msg['content']}\n"
            
            prompt = f"{system_prompt}\n\n输入：{question}{context}\n\n输出："
            
            # 调用LLM进行重写
            response = await self.llm_service.generate_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.3,  # 较低温度，保持一致性
                stop_tokens=["\n"]
            )
            
            rewritten_question = response.strip()
            
            # 如果重写结果与原问题相同或质量不高，返回原问题
            if not rewritten_question or len(rewritten_question) < 2:
                logger.info(f"重写结果无效，返回原问题")
                return question
            
            # 更新缓存
            self.cache[question] = rewritten_question
            self._clean_cache()
            
            elapsed_time = (time.time() - start_time) * 1000
            logger.info(f"问题重写完成，耗时: {elapsed_time:.2f}ms")
            logger.info(f"原问题: {original_question}")
            logger.info(f"重写后: {rewritten_question}")
            
            return rewritten_question
            
        except Exception as e:
            logger.error(f"问题重写失败: {str(e)}", exc_info=True)
            # 如果重写失败，返回原问题
            return original_question
    
    def enable(self):
        """启用问题重写功能"""
        self.enabled = True
        logger.info("问题重写功能已启用")
    
    def disable(self):
        """禁用问题重写功能"""
        self.enabled = False
        logger.info("问题重写功能已禁用")
    
    def is_enabled(self) -> bool:
        """检查是否启用问题重写功能"""
        return self.enabled
