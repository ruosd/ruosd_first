import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from .chroma_store_service import get_chroma_store_service, SearchResult
from ..utils.settings import settings

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    KNOWLEDGE = "knowledge"
    PRODUCT = "product"


@dataclass
class MemoryItem:
    """记忆项"""
    memory_id: str
    content: str
    memory_type: MemoryType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryService:
    """
    记忆管理服务 - 分层记忆管理
    支持短期记忆、长期记忆、知识库记忆
    """
    
    def __init__(self):
        self._chroma_service = None
        self._memory_enabled = settings.MEMORY_ENABLED
        self._top_k = settings.TOP_K_RETRIEVAL
        self._importance_threshold = settings.MEMORY_IMPORTANCE_THRESHOLD
        self._short_term_ttl = settings.SHORT_TERM_MEMORY_TTL
        self._long_term_retention_days = settings.LONG_TERM_MEMORY_RETENTION_DAYS
    
    async def _get_chroma_service(self):
        """获取ChromaDB服务"""
        if self._chroma_service is None:
            self._chroma_service = await get_chroma_store_service()
        return self._chroma_service
    
    async def initialize(self):
        """初始化记忆服务"""
        await self._get_chroma_service()
        logger.info("记忆管理服务初始化完成")
    
    def _generate_memory_id(self) -> str:
        """生成记忆ID"""
        return f"mem_{uuid.uuid4().hex[:16]}"
    
    def _calculate_importance(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Dict[str, Any]
    ) -> float:
        """
        计算记忆重要性
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据
            
        Returns:
            重要性分数 0-1
        """
        importance = 0.5
        
        # 根据类型调整
        if memory_type == MemoryType.KNOWLEDGE:
            importance = 0.8
        elif memory_type == MemoryType.PRODUCT:
            importance = 0.7
        elif memory_type == MemoryType.LONG_TERM:
            importance = 0.6
        
        # 检查关键词
        important_keywords = [
            "订单号", "订单", "物流", "发货", "退款",
            "产品", "价格", "规格", "库存",
            "客服", "投诉", "问题", "重要"
        ]
        for keyword in important_keywords:
            if keyword in content:
                importance += 0.1
                break
        
        # 元数据中的重要性标记
        if metadata.get("is_important"):
            importance = 1.0
        
        # 限制在0-1之间
        return min(max(importance, 0.0), 1.0)
    
    async def save_memory(
        self,
        content: str,
        memory_type: MemoryType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            user_id: 用户ID
            session_id: 会话ID
            agent_type: Agent类型
            metadata: 其他元数据
            
        Returns:
            记忆ID
        """
        if not self._memory_enabled:
            logger.debug("记忆功能已禁用")
            return None
        
        metadata = metadata or {}
        memory_id = self._generate_memory_id()
        importance = self._calculate_importance(content, memory_type, metadata)
        
        # 构建元数据
        full_metadata = {
            "memory_type": memory_type.value,
            "user_id": user_id or "",
            "session_id": session_id or "",
            "agent_type": agent_type or "",
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            **metadata
        }
        
        # 获取集合名称
        collection_name = self._get_collection_name_for_type(memory_type)
        
        # 保存到ChromaDB
        chroma_service = await self._get_chroma_service()
        success = await chroma_service.add_documents(
            collection_name=collection_name,
            documents=[content],
            metadatas=[full_metadata],
            ids=[memory_id]
        )
        
        if success:
            logger.debug(f"保存记忆成功: {memory_id}, 类型: {memory_type.value}")
            return memory_id
        else:
            logger.warning(f"保存记忆失败: {content[:50]}...")
            return None
    
    def _get_collection_name_for_type(self, memory_type: MemoryType) -> str:
        """根据记忆类型获取集合名称"""
        if memory_type == MemoryType.SHORT_TERM:
            return settings.CHROMA_COLLECTION_SHORT_TERM
        elif memory_type == MemoryType.LONG_TERM:
            return settings.CHROMA_COLLECTION_LONG_TERM
        elif memory_type == MemoryType.KNOWLEDGE:
            return settings.CHROMA_COLLECTION_KNOWLEDGE
        elif memory_type == MemoryType.PRODUCT:
            return settings.CHROMA_COLLECTION_PRODUCT
        else:
            return settings.CHROMA_COLLECTION_SHORT_TERM
    
    async def retrieve_memory(
        self,
        query_text: str,
        memory_types: Optional[List[MemoryType]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        n_results: Optional[int] = None
    ) -> List[SearchResult]:
        """
        检索相关记忆
        
        Args:
            query_text: 查询文本
            memory_types: 记忆类型列表
            user_id: 用户ID过滤
            session_id: 会话ID过滤
            n_results: 返回数量
            
        Returns:
            检索结果列表
        """
        if not self._memory_enabled:
            return []
        
        memory_types = memory_types or [
            MemoryType.SHORT_TERM,
            MemoryType.LONG_TERM,
            MemoryType.KNOWLEDGE
        ]
        
        n_results = n_results or self._top_k
        all_results = []
        chroma_service = await self._get_chroma_service()
        
        # 构建过滤条件
        filter_dict = {}
        if user_id:
            filter_dict["user_id"] = user_id
        if session_id:
            filter_dict["session_id"] = session_id
        
        # 从每个集合中检索
        for mem_type in memory_types:
            collection_name = self._get_collection_name_for_type(mem_type)
            results = await chroma_service.search(
                collection_name=collection_name,
                query_text=query_text,
                n_results=n_results,
                filter_dict=filter_dict if filter_dict else None
            )
            all_results.extend(results)
        
        # 按距离排序，只返回最佳结果
        all_results.sort(key=lambda x: x.distance)
        return all_results[:n_results]
    
    async def retrieve_memory_context(
        self,
        query_text: str,
        memory_types: Optional[List[MemoryType]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        n_results: Optional[int] = None
    ) -> str:
        """
        检索记忆并返回拼接的上下文
        
        Args:
            query_text: 查询文本
            memory_types: 记忆类型列表
            user_id: 用户ID过滤
            session_id: 会话ID过滤
            n_results: 返回数量
            
        Returns:
            上下文文本
        """
        results = await self.retrieve_memory(
            query_text, memory_types, user_id, session_id, n_results
        )
        
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            # 优先使用父块内容
            if result.parent_content:
                source = result.metadata.get("section_title", "未知")
                context_parts.append(f"[相关知识: {source}]\n{result.parent_content}")
            else:
                source = result.metadata.get("memory_type", "记忆")
                context_parts.append(f"[{source}]\n{result.content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    async def save_agent_interaction(
        self,
        user_query: str,
        agent_response: str,
        agent_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        保存Agent交互（用户查询 + Agent响应）
        
        Args:
            user_query: 用户查询
            agent_response: Agent响应
            agent_type: Agent类型
            user_id: 用户ID
            session_id: 会话ID
            metadata: 元数据
            
        Returns:
            (用户记忆ID, Agent记忆ID)
        """
        metadata = metadata or {}
        
        # 保存用户查询到短期记忆
        user_meta = {
            "role": "user",
            "agent_type": agent_type,
            **metadata
        }
        user_mem_id = await self.save_memory(
            content=user_query,
            memory_type=MemoryType.SHORT_TERM,
            user_id=user_id,
            session_id=session_id,
            agent_type=agent_type,
            metadata=user_meta
        )
        
        # 保存Agent响应到短期记忆
        agent_meta = {
            "role": "assistant",
            "agent_type": agent_type,
            **metadata
        }
        agent_mem_id = await self.save_memory(
            content=agent_response,
            memory_type=MemoryType.SHORT_TERM,
            user_id=user_id,
            session_id=session_id,
            agent_type=agent_type,
            metadata=agent_meta
        )
        
        # 如果重要性足够高，也保存到长期记忆
        combined_content = f"用户: {user_query}\n客服: {agent_response}"
        importance = self._calculate_importance(combined_content, MemoryType.LONG_TERM, metadata)
        
        if importance >= self._importance_threshold:
            await self.save_memory(
                content=combined_content,
                memory_type=MemoryType.LONG_TERM,
                user_id=user_id,
                session_id=session_id,
                agent_type=agent_type,
                metadata={
                    "role": "conversation",
                    "source": "auto_upgrade",
                    "importance": importance,
                    **metadata
                }
            )
        
        return user_mem_id, agent_mem_id
    
    async def transfer_memory_between_agents(
        self,
        from_agent: str,
        to_agent: str,
        session_id: str,
        user_id: Optional[str] = None
    ) -> int:
        """
        在Agent之间传递记忆
        
        Args:
            from_agent: 源Agent
            to_agent: 目标Agent
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            传递的记忆数量
        """
        # 检索相关记忆
        memories = await self.retrieve_memory(
            query_text="",
            memory_types=[MemoryType.SHORT_TERM],
            user_id=user_id,
            session_id=session_id,
            n_results=20
        )
        
        transferred_count = 0
        for mem in memories:
            # 只转移来自源Agent的记忆
            if mem.metadata.get("agent_type") == from_agent:
                # 复制记忆，标记为已传递
                await self.save_memory(
                    content=mem.content,
                    memory_type=MemoryType.SHORT_TERM,
                    user_id=user_id,
                    session_id=session_id,
                    agent_type=to_agent,
                    metadata={
                        "transferred_from": from_agent,
                        "transferred_to": to_agent,
                        "original_memory_id": mem.chunk_id,
                        **mem.metadata
                    }
                )
                transferred_count += 1
        
        logger.info(f"Agent记忆传递完成: {from_agent} -> {to_agent}, 数量: {transferred_count}")
        return transferred_count
    
    async def cleanup_old_memories(self) -> int:
        """
        清理过期记忆
        
        Returns:
            清理的记忆数量
        """
        chroma_service = await self._get_chroma_service()
        cleanup_count = 0
        
        # 清理短期记忆（TTL过期）
        short_term_collection = self._get_collection_name_for_type(MemoryType.SHORT_TERM)
        # ChromaDB不直接支持按时间删除，这里记录一下需要后续实现
        logger.info(f"跳过短期记忆自动清理（ChromaDB限制）")
        
        # 清理长期记忆（超过保留天数）
        long_term_collection = self._get_collection_name_for_type(MemoryType.LONG_TERM)
        cutoff_date = datetime.now() - timedelta(days=self._long_term_retention_days)
        logger.info(f"长期记忆保留天数: {self._long_term_retention_days}")
        
        # TODO: 实现真正的按时间清理
        
        return cleanup_count
    
    async def get_memory_stats(self, memory_type: Optional[MemoryType] = None) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Args:
            memory_type: 记忆类型，如果不指定则返回所有
            
        Returns:
            统计信息
        """
        chroma_service = await self._get_chroma_service()
        stats = {}
        short_term_count = 0
        long_term_count = 0
        knowledge_count = 0
        product_count = 0
        
        if memory_type:
            collection_name = self._get_collection_name_for_type(memory_type)
            collection_stats = chroma_service.get_collection_stats(collection_name)
            if collection_stats:
                stats[memory_type.value] = {
                    "document_count": collection_stats.document_count,
                    "embedding_dimension": collection_stats.embedding_dimension,
                    "metadata": collection_stats.metadata
                }
                # 设置对应的count字段
                if memory_type == MemoryType.SHORT_TERM:
                    short_term_count = collection_stats.document_count
                elif memory_type == MemoryType.LONG_TERM:
                    long_term_count = collection_stats.document_count
                elif memory_type == MemoryType.KNOWLEDGE:
                    knowledge_count = collection_stats.document_count
                elif memory_type == MemoryType.PRODUCT:
                    product_count = collection_stats.document_count
        else:
            for mem_type in MemoryType:
                collection_name = self._get_collection_name_for_type(mem_type)
                collection_stats = chroma_service.get_collection_stats(collection_name)
                if collection_stats:
                    stats[mem_type.value] = {
                        "document_count": collection_stats.document_count,
                        "embedding_dimension": collection_stats.embedding_dimension,
                        "metadata": collection_stats.metadata
                    }
                    # 设置对应的count字段
                    if mem_type == MemoryType.SHORT_TERM:
                        short_term_count = collection_stats.document_count
                    elif mem_type == MemoryType.LONG_TERM:
                        long_term_count = collection_stats.document_count
                    elif mem_type == MemoryType.KNOWLEDGE:
                        knowledge_count = collection_stats.document_count
                    elif mem_type == MemoryType.PRODUCT:
                        product_count = collection_stats.document_count
        
        # 添加前端期望的count字段
        stats["short_term_count"] = short_term_count
        stats["long_term_count"] = long_term_count
        stats["knowledge_count"] = knowledge_count
        stats["product_count"] = product_count
        
        return stats


# 单例实例
_memory_service = None


async def get_memory_service() -> MemoryService:
    """
    获取记忆管理服务单例
    
    Returns:
        MemoryService 实例
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
        await _memory_service.initialize()
    return _memory_service
