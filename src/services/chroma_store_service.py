import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

from ..utils.settings import settings
from .ollama_embedding_service import get_ollama_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    chunk_id: str
    content: str
    metadata: dict[str, Any]
    distance: float
    parent_content: str | None = None
    parent_metadata: dict[str, Any] | None = None


@dataclass
class CollectionStats:
    """集合统计信息"""
    name: str
    document_count: int
    embedding_dimension: int
    metadata: dict[str, Any]


class ChromaStoreService:
    """
    ChromaDB 存储服务 - 向量存储和检索
    支持分层检索：找到小块后自动找回对应大块
    """

    def __init__(self, persist_directory: str | None = None):
        self.persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        self.client = None
        self._embedding_service = None
        self._initialized = False

    async def _get_embedding_service(self):
        """获取嵌入服务"""
        if self._embedding_service is None:
            self._embedding_service = await get_ollama_embedding_service()
        return self._embedding_service

    def _get_client(self) -> chromadb.Client:
        """获取或创建ChromaDB客户端（支持本地持久化和HTTP远程两种模式）"""
        if self.client is None:
            # 禁用遥测，避免版本兼容性问题
            import os
            os.environ["ANONYMIZED_TELEMETRY"] = "False"

            # 如果配置了 CHROMA_USE_HTTP=true，使用 HttpClient 连接远程 ChromaDB 服务器
            if settings.CHROMA_USE_HTTP and settings.CHROMA_HOST:
                self.client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB HTTP客户端已连接: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            else:
                self.client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB 持久化客户端已创建，路径: {self.persist_dir}")
        return self.client

    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return

        # 预热嵌入服务
        await self._get_embedding_service()
        self._initialized = True
        logger.info(f"ChromaDB存储服务初始化完成，持久化目录: {self.persist_dir}")

    def _get_collection_name(self, collection_type: str) -> str:
        """获取集合名称"""
        collection_map = {
            "short_term": settings.CHROMA_COLLECTION_SHORT_TERM,
            "long_term": settings.CHROMA_COLLECTION_LONG_TERM,
            "knowledge": settings.CHROMA_COLLECTION_KNOWLEDGE,
            "product": settings.CHROMA_COLLECTION_PRODUCT,
        }
        return collection_map.get(collection_type, collection_type)

    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: dict[str, Any] | None = None
    ):
        """
        获取或创建集合

        Args:
            collection_name: 集合名称
            metadata: 集合元数据

        Returns:
            Collection对象
        """
        client = self._get_client()
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {"created_at": datetime.now().isoformat()}
        )
        return collection

    async def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
        enable_parent_retrieval: bool = False
    ) -> bool:
        """
        添加文档到集合

        Args:
            collection_name: 集合名称
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: ID列表
            enable_parent_retrieval: 是否启用父块检索

        Returns:
            是否成功
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            embedding_service = await self._get_embedding_service()

            # 过滤元数据中的 None 值（ChromaDB 不支持 None）
            filtered_metadatas = []
            for metadata in metadatas:
                filtered_metadata = {}
                for key, value in metadata.items():
                    if value is None:
                        filtered_metadata[key] = ""  # 将 None 替换为空字符串
                    elif isinstance(value, (str, int, float, bool)):
                        filtered_metadata[key] = value
                    else:
                        filtered_metadata[key] = str(value)  # 其他类型转为字符串
                filtered_metadatas.append(filtered_metadata)

            # 批量生成向量
            zero_vector_count = 0
            vectors = []
            for doc in documents:
                vector = await embedding_service.get_embedding(doc)
                if vector:
                    # 检查是否为零向量
                    if all(v == 0.0 for v in vector):
                        zero_vector_count += 1
                        logger.warning(f"文档 {doc[:50]}... 返回零向量，Ollama 嵌入服务可能未正常工作")
                    vectors.append(vector)
                else:
                    zero_vector_count += 1
                    logger.warning(f"文档 {doc[:50]}... 向量生成失败")
                    vectors.append([0.0] * 1024)  # bge-m3默认维度

            if zero_vector_count > 0:
                if zero_vector_count == len(documents):
                    # 全部失败 — 拒绝写入，避免存储无效数据
                    logger.error(
                        f"❌ 全部 {len(documents)} 个文档块向量生成失败。"
                        f"请检查 Ollama 嵌入服务 (OLLAMA_BASE_URL={settings.OLLAMA_BASE_URL})。"
                    )
                    return False
                else:
                    # 部分失败 — 记录警告但仍写入有效数据
                    logger.warning(
                        f"⚠️ {zero_vector_count}/{len(documents)} 个文档块的向量生成失败，"
                        f"有效向量仍会写入。请检查 Ollama 服务。"
                    )

            # 添加到集合
            collection.add(
                documents=documents,
                metadatas=filtered_metadatas,
                ids=ids,
                embeddings=vectors
            )

            logger.info(f"添加 {len(documents)} 个文档到集合 {collection_name}")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    async def add_documents_batch(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
        batch_size: int = 100
    ) -> tuple[int, int]:
        """
        批量添加文档

        Args:
            collection_name: 集合名称
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: ID列表
            batch_size: 批次大小

        Returns:
            (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            try:
                if await self.add_documents(collection_name, batch_docs, batch_meta, batch_ids):
                    success_count += len(batch_docs)
                else:
                    fail_count += len(batch_docs)
            except Exception as e:
                logger.error(f"批次 {i // batch_size} 添加失败: {e}")
                fail_count += len(batch_docs)

        return success_count, fail_count

    async def search(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        filter_dict: dict[str, Any] | None = None,
        enable_parent_retrieval: bool = True
    ) -> list[SearchResult]:
        """
        语义检索

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            n_results: 返回数量
            filter_dict: 过滤条件
            enable_parent_retrieval: 是否启用父块检索

        Returns:
            检索结果列表
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            embedding_service = await self._get_embedding_service()

            # 生成查询向量
            query_vector = await embedding_service.get_embedding(query_text)
            if not query_vector:
                logger.warning("查询向量生成失败")
                return []

            # 执行检索
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                where=filter_dict,
                include=["documents", "metadatas", "distances"]
            )

            # 解析结果
            search_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    content = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # 如果启用父块检索，尝试获取父块内容
                    parent_content = None
                    parent_metadata = None
                    if enable_parent_retrieval and metadata.get("parent_id"):
                        parent_results = collection.get(
                            ids=[metadata["parent_id"]],
                            include=["documents", "metadatas"]
                        )
                        if parent_results["documents"]:
                            parent_content = parent_results["documents"][0]
                            parent_metadata = parent_results["metadatas"][0] if parent_results["metadatas"] else None

                    result = SearchResult(
                        chunk_id=chunk_id,
                        content=content,
                        metadata=metadata,
                        distance=distance,
                        parent_content=parent_content,
                        parent_metadata=parent_metadata
                    )
                    search_results.append(result)

            logger.info(f"检索完成，返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    async def search_with_context(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        filter_dict: dict[str, Any] | None = None
    ) -> str:
        """
        检索并返回带上下文的文本

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            n_results: 返回数量
            filter_dict: 过滤条件

        Returns:
            拼接的上下文文本
        """
        results = await self.search(
            collection_name, query_text, n_results, filter_dict, enable_parent_retrieval=True
        )

        if not results:
            return ""

        context_parts = []
        for result in results:
            # 优先使用父块内容，如果父块不存在则使用当前块
            if result.parent_content:
                context_parts.append(f"[来源: {result.metadata.get('section_title', '未知')}]\n{result.parent_content}")
            else:
                context_parts.append(f"[来源: {result.metadata.get('chunk_id', '未知')}]\n{result.content}")

        return "\n\n---\n\n".join(context_parts)

    def delete_documents(self, collection_name: str, ids: list[str]) -> bool:
        """
        删除文档

        Args:
            collection_name: 集合名称
            ids: 文档ID列表

        Returns:
            是否成功
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=ids)
            logger.info(f"删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def delete_by_filter(self, collection_name: str, filter_dict: dict[str, Any]) -> bool:
        """
        按条件删除文档

        Args:
            collection_name: 集合名称
            filter_dict: 过滤条件

        Returns:
            是否成功
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(where=filter_dict)
            logger.info(f"按条件删除文档: {filter_dict}")
            return True
        except Exception as e:
            logger.error(f"按条件删除失败: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """删除整个集合"""
        try:
            client = self._get_client()
            client.delete_collection(name=collection_name)
            logger.info(f"集合已删除: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    def get_collection_stats(self, collection_name: str) -> CollectionStats | None:
        """
        获取集合统计信息

        Args:
            collection_name: 集合名称

        Returns:
            集合统计信息
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()

            # 尝试获取一条数据获取向量维度
            sample = collection.peek(limit=1)
            embed_dim = 1024  # bge-m3 默认维度

            if sample and sample.get("embeddings") and len(sample["embeddings"]) > 0:
                embed_dim = len(sample["embeddings"][0])

            return CollectionStats(
                name=collection_name,
                document_count=count,
                embedding_dimension=embed_dim,
                metadata=collection.metadata or {}
            )
        except Exception as e:
            logger.error(f"获取集合统计失败: {e}")
            return None

    def list_collections(self) -> list[str]:
        """
        列出所有集合

        Returns:
            集合名称列表
        """
        client = self._get_client()
        collections = client.list_collections()
        return [col.name for col in collections]

    def get_all_documents(
        self,
        collection_name: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        获取集合中的所有文档

        Args:
            collection_name: 集合名称
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            文档列表，包含content、metadata、id
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            # 获取所有文档ID
            all_ids = collection.get()["ids"]

            # 分页处理
            paginated_ids = all_ids[offset:offset + limit]

            if not paginated_ids:
                return []

            # 获取指定ID的文档内容
            results = collection.get(
                ids=paginated_ids,
                include=["documents", "metadatas"]
            )

            documents = []
            for i, doc_id in enumerate(paginated_ids):
                documents.append({
                    "chunk_id": doc_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })

            return documents

        except Exception as e:
            logger.error(f"获取所有文档失败: {e}")
            return []

    def get_document_count(self, collection_name: str) -> int:
        """
        获取集合中的文档总数

        Args:
            collection_name: 集合名称

        Returns:
            文档数量
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"获取文档数量失败: {e}")
            return 0


# 单例实例
_chroma_store_service = None


async def get_chroma_store_service() -> ChromaStoreService:
    """
    获取ChromaDB存储服务单例

    Returns:
        ChromaStoreService 实例
    """
    global _chroma_store_service
    if _chroma_store_service is None:
        _chroma_store_service = ChromaStoreService()
        await _chroma_store_service.initialize()
    return _chroma_store_service
