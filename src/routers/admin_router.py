"""
管理接口路由 - 用于查看和管理记忆系统数据
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import jwt
import uuid
from src.utils.errors import AppError, ErrorCode
from src.utils.password import hash_password, verify_password
from src.services import (
    get_chroma_store_service,
    get_memory_service,
    DocumentProcessor,
    MemoryType,
    DocumentType
)
from src.services.document_processor import ProcessedDocument
from src.utils.logger import get_logger
from src.utils.settings import settings

logger = get_logger("admin_router")
router = APIRouter(prefix="/api/admin", tags=["管理接口"])
limiter = Limiter(key_func=get_remote_address)

# JWT配置 — 密钥从环境变量读取，用户路由和管理路由使用不同密钥
SECRET_KEY = settings.ADMIN_JWT_SECRET_KEY
if not SECRET_KEY:
    raise RuntimeError(
        "ADMIN_JWT_SECRET_KEY 环境变量未设置，请复制 .env.example 到 .env 并配置"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 管理员账号 — 从环境变量读取，无默认密码
_ADMIN_USERNAME = settings.ADMIN_USERNAME
_ADMIN_PASSWORD = settings.ADMIN_PASSWORD
if not _ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_PASSWORD 环境变量未设置，请复制 .env.example 到 .env 并配置"
    )
ADMIN_ACCOUNTS = {
    _ADMIN_USERNAME: hash_password(_ADMIN_PASSWORD)
}

# 安全依赖
security = HTTPBearer()

# 登录请求模型
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")

# 文档处理请求模型
class DocumentProcessRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500000, description="文档内容（最长50万字符）")
    doc_id: str = Field(..., min_length=1, max_length=128, description="文档ID")
    doc_type: str = Field("TXT", max_length=10, description="文档类型")
    collection_name: str = Field("knowledge_base", max_length=64, description="目标集合名称")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前登录用户"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in ADMIN_ACCOUNTS:
            raise AppError(ErrorCode.UNAUTHORIZED, status_code=401)
        return username
    except jwt.PyJWTError:
        raise AppError(ErrorCode.UNAUTHORIZED, status_code=401)


@router.post("/login", summary="管理员登录")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """
    管理员登录接口
    
    Args:
        request: 登录请求，包含用户名和密码
        
    Returns:
        包含token的登录结果
    """
    try:
        username = body.username
        password = body.password
        
        # 验证用户名和密码
        if username not in ADMIN_ACCOUNTS:
            raise AppError(ErrorCode.INVALID_CREDENTIALS, status_code=401)

        # 验证密码（使用 bcrypt 安全比对）
        password_hash = ADMIN_ACCOUNTS.get(username)
        if not password_hash or not verify_password(password, password_hash):
            raise AppError(ErrorCode.INVALID_CREDENTIALS, status_code=401)
        
        # 生成JWT令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        logger.info(f"管理员登录成功: {username}")
        return {"status": "success", "username": username, "token": access_token}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="登录失败")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.get("/me", summary="获取当前用户信息", dependencies=[Depends(get_current_user)])
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """
    获取当前登录用户信息
    
    Returns:
        当前用户信息
    """
    return {"status": "success", "username": current_user}


@router.get("/collections", summary="列出所有向量集合")
async def list_collections():
    """
    列出 ChromaDB 中所有的向量集合
    
    Returns:
        集合名称列表
    """
    try:
        chroma_service = await get_chroma_store_service()
        collections = chroma_service.list_collections()
        return {"status": "success", "collections": collections}
    except Exception as e:
        logger.error(f"获取集合列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/collections/{collection_name}/stats", summary="获取集合统计信息")
async def get_collection_stats(collection_name: str):
    """
    获取指定集合的统计信息
    
    Args:
        collection_name: 集合名称
        
    Returns:
        集合统计信息（文档数、向量维度等）
    """
    try:
        chroma_service = await get_chroma_store_service()
        stats = chroma_service.get_collection_stats(collection_name)
        
        if stats:
            return {
                "status": "success",
                "data": {
                    "name": stats.name,
                    "document_count": stats.document_count,
                    "embedding_dimension": stats.embedding_dimension,
                    "metadata": stats.metadata
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取集合统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/collections/{collection_name}/search", summary="搜索集合中的文档")
async def search_collection(
    collection_name: str,
    query: str,
    n_results: int = Query(5, ge=1, le=20)
):
    """
    在指定集合中搜索相关文档
    
    Args:
        collection_name: 集合名称
        query: 搜索关键词
        n_results: 返回结果数量（默认5，范围1-20）
        
    Returns:
        搜索结果列表
    """
    try:
        chroma_service = await get_chroma_store_service()
        results = await chroma_service.search(collection_name, query, n_results=n_results)
        
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append({
                "index": i + 1,
                "chunk_id": result.chunk_id,
                "content": result.content,
                "distance": round(result.distance, 4),
                "metadata": result.metadata,
                "has_parent": result.parent_content is not None,
                "parent_section": result.metadata.get("section_title", "")
            })
        
        return {
            "status": "success",
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"搜索集合失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/collections/{collection_name}/documents", summary="获取集合中的所有文档")
async def get_all_documents(
    collection_name: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    获取集合中的所有文档（分页）
    
    Args:
        collection_name: 集合名称
        limit: 返回数量（默认50，范围1-200）
        offset: 偏移量（默认0）
        
    Returns:
        文档列表和总数
    """
    try:
        chroma_service = await get_chroma_store_service()
        
        # 检查集合是否存在
        collections = chroma_service.list_collections()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"集合 {collection_name} 不存在")
        
        documents = chroma_service.get_all_documents(collection_name, limit, offset)
        total_count = chroma_service.get_document_count(collection_name)
        
        return {
            "status": "success",
            "collection_name": collection_name,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "documents": documents
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/collections/{collection_name}/documents", summary="删除集合中的文档")
async def delete_documents(
    collection_name: str,
    ids: Optional[List[str]] = None,
    filter_dict: Optional[Dict[str, Any]] = None
):
    """
    删除集合中的文档
    
    Args:
        collection_name: 集合名称
        ids: 要删除的文档ID列表（与filter_dict二选一）
        filter_dict: 过滤条件（与ids二选一）
        
    Returns:
        删除结果
    """
    try:
        chroma_service = await get_chroma_store_service()
        
        if ids:
            success = chroma_service.delete_documents(collection_name, ids)
            return {
                "status": "success",
                "message": f"成功删除 {len(ids)} 个文档",
                "deleted_ids": ids
            }
        elif filter_dict:
            success = chroma_service.delete_by_filter(collection_name, filter_dict)
            return {
                "status": "success",
                "message": f"按条件删除成功",
                "filter": filter_dict
            }
        else:
            raise HTTPException(status_code=400, detail="请提供 ids 或 filter_dict 参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/collections/{collection_name}", summary="删除整个集合")
async def delete_collection(collection_name: str):
    """删除指定集合及其所有文档"""
    try:
        chroma_service = await get_chroma_store_service()
        success = chroma_service.delete_collection(collection_name)
        if success:
            logger.info(f"集合已删除: {collection_name}")
            return {"status": "success", "message": f"集合 {collection_name} 已删除"}
        else:
            raise HTTPException(status_code=500, detail=f"删除集合 {collection_name} 失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除集合失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/memory/stats", summary="获取记忆系统统计信息")
async def get_memory_stats():
    """
    获取记忆系统的整体统计信息
    
    Returns:
        各类型记忆的统计数据
    """
    try:
        memory_service = await get_memory_service()
        stats = await memory_service.get_memory_stats()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取记忆统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/memory/types", summary="获取记忆类型列表")
async def get_memory_types():
    """
    获取所有支持的记忆类型
    
    Returns:
        记忆类型枚举列表
    """
    try:
        types = [mt.name for mt in MemoryType]
        return {
            "status": "success",
            "memory_types": types,
            "descriptions": {
                "SHORT_TERM": "短期记忆（会话级，自动过期）",
                "LONG_TERM": "长期记忆（用户级，持久化）",
                "KNOWLEDGE": "知识库记忆（全局，文档导入）",
                "PRODUCT": "产品记忆（产品信息检索）"
            }
        }
    except Exception as e:
        logger.error(f"获取记忆类型失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class MemoryQueryRequest(BaseModel):
    """记忆检索请求"""
    query_text: str = Field("", description="查询文本")
    user_id: Optional[str] = Field(None, max_length=64)
    session_id: Optional[str] = Field(None, max_length=128)
    memory_types: Optional[List[str]] = Field(None, description="记忆类型列表")
    n_results: int = Field(5, description="返回结果数")


@router.post("/memory/query", summary="检索记忆上下文")
async def query_memory(req: MemoryQueryRequest):
    """
    检索与查询文本相关的记忆上下文
    
    Args:
        query_text: 查询文本
        user_id: 用户ID（可选）
        session_id: 会话ID（可选）
        memory_types: 记忆类型列表（可选，如 ["SHORT_TERM", "LONG_TERM"]）
        n_results: 返回结果数量（默认5）
        
    Returns:
        记忆上下文文本和相关记忆列表
    """
    try:
        memory_service = await get_memory_service()
        
        # 转换记忆类型
        if req.memory_types:
            try:
                types = [MemoryType[name] for name in req.memory_types]
            except KeyError as e:
                raise HTTPException(status_code=400, detail=f"无效的记忆类型: {e}")
        else:
            types = None
        
        # 检索上下文
        context = await memory_service.retrieve_memory_context(
            query_text=req.query_text,
            memory_types=types,
            user_id=req.user_id,
            session_id=req.session_id,
            n_results=req.n_results
        )
        
        return {
            "status": "success",
            "query": req.query_text,
            "context_length": len(context),
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检索记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/memory/cleanup", summary="清理过期记忆")
async def cleanup_memory(
    memory_type: Optional[str] = None,
    older_than_days: Optional[int] = 30
):
    """
    清理过期记忆
    
    Args:
        memory_type: 记忆类型（可选，不指定则清理所有类型）
        older_than_days: 清理多少天前的记忆（默认30天）
        
    Returns:
        清理结果
    """
    try:
        memory_service = await get_memory_service()
        
        # 转换记忆类型
        if memory_type:
            try:
                mem_type = MemoryType[memory_type]
            except KeyError:
                raise HTTPException(status_code=400, detail=f"无效的记忆类型: {memory_type}")
        else:
            mem_type = None
        
        cleaned_count = await memory_service.cleanup_old_memories(
            memory_type=mem_type,
            older_than_days=older_than_days
        )
        
        return {
            "status": "success",
            "message": f"成功清理 {cleaned_count} 条过期记忆",
            "memory_type": memory_type or "all",
            "older_than_days": older_than_days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/process", summary="处理文档并导入知识库")
@limiter.limit("10/minute")
async def process_and_import_document(
    request: Request,
    body: DocumentProcessRequest
):
    """
    处理文本内容并导入到知识库
    
    Args:
        request: 文档处理请求，包含：
            - content: 文档内容
            - doc_id: 文档ID
            - doc_type: 文档类型（TXT/PDF/DOCX，默认TXT）
            - collection_name: 目标集合名称（默认knowledge_base）
        
    Returns:
        处理结果和导入状态
    """
    try:
        # 预检 Ollama 嵌入服务 — 不可用时直接拒绝，防止写入无效向量
        from src.services.ollama_embedding_service import get_ollama_embedding_service
        embedding_service = await get_ollama_embedding_service()
        ollama_available = await embedding_service.is_available()
        if not ollama_available:
            raise AppError(ErrorCode.OLLAMA_UNAVAILABLE, status_code=503)

        # 转换文档类型
        try:
            document_type = DocumentType[body.doc_type]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"无效的文档类型: {body.doc_type}")
        
        # 处理文档
        # 添加时间戳避免重复上传时 ID 冲突
        unique_doc_id = f"{body.doc_id}_{uuid.uuid4().hex[:8]}"
        processor = DocumentProcessor()
        doc = processor.process_text(body.content, doc_id=unique_doc_id, doc_type=document_type)

        # 准备数据
        documents = []
        metadatas = []
        ids = []

        for section in doc.sections:
            for chunk in section.chunks:
                documents.append(chunk.content)
                metadatas.append({
                    "section_title": section.section_title,
                    "doc_id": body.doc_id,
                    "parent_id": chunk.parent_id,
                    "section_index": section.section_index,
                    "chunk_index": chunk.chunk_index
                })
                ids.append(f"{unique_doc_id}_{chunk.chunk_id}")
        
        # 导入到向量数据库
        chroma_service = await get_chroma_store_service()
        success = await chroma_service.add_documents(
            body.collection_name,
            documents,
            metadatas,
            ids,
            enable_parent_retrieval=True
        )
        
        return {
            "status": "success",
            "doc_id": unique_doc_id,
            "sections": len(doc.sections),
            "chunks": len(documents),
            "imported": success,
            "collection": body.collection_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/upload", summary="上传文件并导入知识库")
@limiter.limit("10/minute")
async def upload_and_import_document(
    request: Request,
    file: UploadFile = File(...),
    collection_name: str = Form("knowledge_base")
):
    """
    上传文件并导入到知识库
    
    Args:
        file: 上传的文件（支持 TXT、PDF、DOCX）
        collection_name: 目标集合名称（默认knowledge_base）
        
    Returns:
        处理结果和导入状态
    """
    try:
        # 预检 Ollama 嵌入服务 — 不可用时直接拒绝，防止写入无效向量
        from src.services.ollama_embedding_service import get_ollama_embedding_service
        embedding_service = await get_ollama_embedding_service()
        ollama_available = await embedding_service.is_available()
        if not ollama_available:
            raise AppError(ErrorCode.OLLAMA_UNAVAILABLE, status_code=503)

        # 读取文件内容
        content = await file.read()
        filename = file.filename or "unknown"
        ext = filename.split('.')[-1].upper() if '.' in filename else "TXT"
        supported_types = ["TXT", "PDF", "DOCX"]
        if ext not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}。支持的类型: {', '.join(supported_types)}"
            )

        # 将上传文件保存到临时目录，调用 DocumentProcessor 统一处理
        import tempfile
        doc_id = f"doc_{uuid.uuid4().hex[:8]}_{filename}"

        with tempfile.NamedTemporaryFile(suffix=f".{ext.lower()}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            processor = DocumentProcessor()
            doc = processor.process_file(tmp_path, doc_id=doc_id)
        finally:
            os.unlink(tmp_path)  # 删除临时文件
        
        # 准备数据
        documents = []
        metadatas = []
        ids = []
        
        for section in doc.sections:
            for chunk in section.chunks:
                documents.append(chunk.content)
                metadatas.append({
                    "section_title": section.section_title,
                    "doc_id": doc_id,
                    "parent_id": chunk.parent_id,
                    "section_index": section.section_index,
                    "chunk_index": chunk.chunk_index,
                    "filename": filename
                })
                ids.append(f"{doc_id}_{chunk.chunk_id}")
        
        # 导入到向量数据库
        chroma_service = await get_chroma_store_service()
        success = await chroma_service.add_documents(
            collection_name,
            documents,
            metadatas,
            ids,
            enable_parent_retrieval=True
        )
        
        logger.info(f"文件上传成功: {filename}, 导入 {len(documents)} 个文档块")
        
        return {
            "status": "success",
            "filename": filename,
            "doc_id": doc_id,
            "doc_type": ext,
            "sections": len(doc.sections),
            "chunks": len(documents),
            "imported": success,
            "collection": collection_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── 异步文件上传（Celery 任务队列）──

class AsyncUploadResponse(BaseModel):
    """异步上传响应"""
    task_id: str = Field(..., description="任务ID，用于查询处理状态")
    status: str = Field("processing", description="任务状态")


@router.post("/documents/upload-async", summary="异步上传文件（推荐）")
async def upload_async(
    content: str = Body(..., description="文档文本内容"),
    doc_id: str = Body(..., description="文档ID"),
    doc_type: str = Body("TXT", description="文档类型"),
    collection_name: str = Body("knowledge_base", description="目标集合"),
):
    """
    异步上传文档，立即返回任务ID。

    相比同步端点 /documents/upload，此端点：
    - 立即返回（不等待向量生成）
    - 后台 Celery Worker 处理文档
    - 通过 GET /documents/task/{task_id} 查询进度
    """
    from src.tasks.document_tasks import process_document_task

    # 提交异步任务
    task = process_document_task.delay(
        content=content,
        doc_id=doc_id,
        doc_type=doc_type,
        collection_name=collection_name,
    )

    logger.info(f"异步任务已提交: {task.id}, 文档: {doc_id}")
    return {"task_id": task.id, "status": "processing"}


@router.get("/documents/task/{task_id}", summary="查询异步任务状态")
async def get_task_status(task_id: str):
    """
    查询 Celery 任务状态

    状态说明:
      PENDING   - 等待执行
      STARTED   - 正在处理
      SUCCESS   - 处理完成（result 字段包含结果）
      FAILURE   - 处理失败（result 字段包含错误信息）
    """
    from celery.result import AsyncResult
    from src.tasks.celery_app import app as celery_app

    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.state,
    }

    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result)

    return response


@router.post("/seed", summary="填充测试数据")
async def seed_test_data():
    """一键填充: 3个用户 + 20条订单。测试账号: zhangsan/123456"""
    import random, traceback
    from datetime import datetime, timedelta
    from src.services import get_user_service

    logger.info("开始填充测试数据...")

    try:
        result = {"users": [], "orders": 0}

        # 注册用户
        test_users = [
            ("zhangsan", "zhangsan@test.com", "123456", "张三", "13800001111"),
            ("lisi", "lisi@test.com", "123456", "李四", "13800002222"),
            ("wangwu", "wangwu@test.com", "123456", "王五", "13800003333"),
        ]
        user_svc = get_user_service()
        for u in test_users:
            try:
                user_svc.register_user(u[0], u[1], u[2], u[3], u[4])
                result["users"].append(u[0])
                logger.info(f"  用户: {u[0]}")
            except Exception as e:
                result["users"].append(f"{u[0]}({e})")

        # 生成订单
        from src.utils.mysql_client import get_mysql_client
        mysql = get_mysql_client()
        if not mysql.is_connected():
            return {"status": "error", "message": "MySQL 不可用"}

        now = datetime.now()
        statuses = ["待付款","待发货","已发货","已送达","已完成","退款中","已退款"]
        products = [
            (1,"iPhone 15 Pro Max",9999),(2,"华为Mate 60 Pro",6999),
            (3,"小米14 Pro",4999),(4,"MacBook Air M2",7999),
            (5,"联想ThinkPad X1",9999),(6,"AirPods Pro 2",1899),
            (7,"华为FreeBuds Pro 3",1499),(8,"Apple Watch S9",3199),
            (9,"格力空调",3299),(10,"海尔冰箱",4999),
        ]
        companies = ["顺丰速运","京东物流","中通快递","圆通速递"]

        for i in range(1, 21):
            user = random.choice(test_users)
            prod = random.choice(products)
            status = random.choice(statuses)
            qty = random.randint(1, 2)
            oid = f"TEST{now.strftime('%Y%m%d')}{i:04d}"
            created = now - timedelta(days=random.randint(0, 30))
            ts = created.strftime("%Y-%m-%d %H:%M:%S")

            mysql.execute_update(
                "INSERT IGNORE INTO orders (order_id,user_id,status,total_amount,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (oid, user[0], status, prod[2]*qty, ts, ts))
            mysql.execute_update(
                "INSERT IGNORE INTO order_items (order_id,product_id,product_name,quantity,price) VALUES (%s,%s,%s,%s,%s)",
                (oid, prod[0], prod[1], qty, prod[2]))
            if status in ("已发货","已送达","已完成"):
                comp = random.choice(companies)
                mysql.execute_update(
                    "INSERT IGNORE INTO tracking_info (order_id,tracking_number,status,location,estimated_delivery,updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (oid, f"{comp[:2].upper()}{random.randint(10000000,99999999)}",
                     "已签收" if status!="已发货" else "运输中",
                     random.choice(["上海转运中心","北京分拨中心","广州集散中心"]),
                     (now+timedelta(days=random.randint(1,5))).strftime("%Y-%m-%d"), ts))
            result["orders"] += 1

        logger.info(f"填充完成: {len(result['users'])} 用户, {result['orders']} 订单")
        return {"status": "ok", "users": result["users"], "orders": result["orders"],
                "test_accounts": "zhangsan/123456, lisi/123456, wangwu/123456"}

    except Exception as e:
        logger.error(f"填充数据失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sql/users", summary="查看所有用户")
async def get_sql_users():
    """MySQL 用户表"""
    from src.utils.mysql_client import get_mysql_client
    mysql = get_mysql_client()
    if not mysql.is_connected():
        return {"count": 0, "users": [], "note": "MySQL 不可用"}
    rows = mysql.execute_query(
        "SELECT id, username, email, nickname, role, created_at FROM users ORDER BY created_at DESC"
    )
    return {"count": len(rows) if rows else 0, "users": rows or []}


@router.get("/sql/orders", summary="查看所有订单")
async def get_sql_orders():
    """MySQL 订单表"""
    from src.utils.mysql_client import get_mysql_client
    mysql = get_mysql_client()
    if not mysql.is_connected():
        return {"error": "MySQL 不可用", "orders": []}
    orders = mysql.execute_query(
        "SELECT order_id, user_id, status, total_amount, created_at FROM orders ORDER BY created_at DESC LIMIT 100"
    )
    return {"count": len(orders) if orders else 0, "orders": orders or []}


@router.get("/sql/products", summary="查看所有产品")
async def get_sql_products():
    """产品数据（内存模拟）"""
    from src.services import ProductService
    ps = ProductService()
    products = ps.get_all_products()
    return {"count": len(products), "products": products}


@router.get("/metrics", summary="Agent 指标汇总")
async def get_agent_metrics(days: int = Query(7, ge=1, le=90)):
    """查看 Agent 调用指标（LLM 调用、工具调用、意图分布）"""
    from src.utils.metrics import MetricsCollector
    return MetricsCollector.query_summary(days=days)


@router.get("/sql/conversations", summary="查看所有活跃会话")
async def get_sql_conversations():
    """Redis 活跃会话列表"""
    from src.utils.redis_client import get_redis_client
    redis = get_redis_client()
    conn = redis.get_connection()
    if not conn:
        return {"count": 0, "conversations": [], "note": "Redis 不可用"}
    results = []
    for sid in conn.smembers("session_index"):
        key = f"session:{sid}"
        data = conn.get(key)
        if data:
            import json
            try:
                results.append(json.loads(data) if isinstance(data, str) else data)
            except Exception:
                results.append({"session_id": sid})
    results.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return {"count": len(results), "conversations": results[:50]}


@router.get("/health", summary="管理接口健康检查")
async def health_check():
    """
    管理接口健康检查
    
    Returns:
        服务状态
    """
    return {
        "status": "healthy",
        "service": "admin_api",
        "timestamp": "now"
    }
