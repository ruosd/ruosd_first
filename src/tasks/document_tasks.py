"""
文档处理 Celery 任务 — 将耗时的向量化操作从 HTTP 请求中剥离

原理:
  用户上传文件 → API 立即返回 task_id → Celery Worker 后台处理
  → 用户轮询 task_id 查询进度 → 处理完成后获取结果
"""

import uuid
from .celery_app import app
from src.services import DocumentProcessor, get_chroma_store_service
from src.services.document_processor import DocumentType
from src.services.ollama_embedding_service import get_ollama_embedding_service
from src.utils.logger import get_logger

logger = get_logger("document_tasks")


@app.task(bind=True, name="process_document")
def process_document_task(
    self,
    content: str,
    doc_id: str,
    doc_type: str = "TXT",
    collection_name: str = "knowledge_base",
) -> dict:
    """
    异步处理文档并导入向量库

    Args:
        content: 文档文本内容
        doc_id: 文档ID
        doc_type: 文档类型
        collection_name: 目标集合名称

    Returns:
        {"status": "success"/"failed", "chunks": N, "collection": "..."}
    """
    import asyncio

    async def _run():
        # 预检 Ollama
        ollama = await get_ollama_embedding_service()
        if not await ollama.is_available():
            return {"status": "failed", "error": "Ollama 不可用"}

        # 解析文档类型
        try:
            dtype = DocumentType[doc_type]
        except KeyError:
            return {"status": "failed", "error": f"不支持的文档类型: {doc_type}"}

        # 处理文档
        processor = DocumentProcessor()
        unique_doc_id = f"{doc_id}_{uuid.uuid4().hex[:8]}"
        doc = processor.process_text(content, doc_id=unique_doc_id, doc_type=dtype)

        # 准备数据
        documents, metadatas, ids = [], [], []
        for section in doc.sections:
            for chunk in section.chunks:
                documents.append(chunk.content)
                metadatas.append({
                    "section_title": section.section_title,
                    "doc_id": doc_id,
                    "chunk_index": chunk.chunk_index,
                })
                ids.append(f"{unique_doc_id}_{chunk.chunk_id}")

        # 导入 ChromaDB
        chroma = await get_chroma_store_service()
        success = await chroma.add_documents(
            collection_name, documents, metadatas, ids, enable_parent_retrieval=True
        )

        if success:
            return {
                "status": "success",
                "doc_id": unique_doc_id,
                "chunks": len(documents),
                "sections": len(doc.sections),
                "collection": collection_name,
            }
        else:
            return {"status": "failed", "error": "向量生成或写入失败"}

    return asyncio.run(_run())
