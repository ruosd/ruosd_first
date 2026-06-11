import ollama
import logging
from typing import List, Optional, Union
from ..utils.settings import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingService:
    """
    Ollama 嵌入服务 - 封装 bge-m3:latest 向量生成能力
    """
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self._client = None
        self._available = None
    
    def _get_client(self):
        """获取或创建 Ollama 客户端"""
        if self._client is None:
            self._client = ollama.Client(host=self.base_url, timeout=self.timeout)
        return self._client
    
    async def is_available(self) -> bool:
        """
        检查 Ollama 服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        if self._available is not None:
            return self._available
        
        try:
            client = self._get_client()
            # 列出模型验证连接
            models = client.list()
            # 检查目标模型是否存在
            model_names = [m.get('name', '') for m in models.get('models', [])]
            self._available = self.model in model_names
            if not self._available:
                logger.warning(f"Ollama 模型 {self.model} 未找到，可用模型: {model_names}")
            else:
                logger.info(f"Ollama 服务可用，模型: {self.model}")
        except Exception as e:
            logger.error(f"Ollama 服务不可用: {e}")
            self._available = False
        
        return self._available
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取单条文本的向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量列表，失败返回None
        """
        if not text or not text.strip():
            return None
        
        try:
            client = self._get_client()
            response = client.embeddings(model=self.model, prompt=text.strip())
            embedding = response.get('embedding')
            
            if embedding:
                logger.debug(f"向量生成成功，维度: {len(embedding)}")
                return embedding
            
            return None
        except Exception as e:
            logger.error(f"向量生成失败: {e}")
            return None
    
    async def get_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量获取文本向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，顺序与输入一致
        """
        if not texts:
            return []
        
        results = []
        for text in texts:
            embedding = await self.get_embedding(text)
            results.append(embedding)
        
        return results
    
    async def get_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
        """
        分批获取文本向量（适合大量文本）
        
        Args:
            texts: 文本列表
            batch_size: 批次大小
            
        Returns:
            向量列表，顺序与输入一致
        """
        if not texts:
            return []
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"处理批次 {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")
            
            batch_results = await self.get_embeddings(batch)
            results.extend(batch_results)
        
        return results


# 单例实例
_ollama_embedding_service = None


async def get_ollama_embedding_service() -> OllamaEmbeddingService:
    """
    获取 Ollama 嵌入服务单例
    
    Returns:
        OllamaEmbeddingService 实例
    """
    global _ollama_embedding_service
    if _ollama_embedding_service is None:
        _ollama_embedding_service = OllamaEmbeddingService()
        # 预热检查
        await _ollama_embedding_service.is_available()
    return _ollama_embedding_service
