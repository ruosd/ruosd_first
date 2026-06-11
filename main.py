from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.routers import chat_router, system_router, admin_router, user_router
from src.services import AgentManager, ProductService, OrderService, KnowledgeBase, ConversationService
from src.agents import CustomerServiceAgent, OrderAgent, ProductAgent
from src.utils import get_logger
from src.utils.settings import settings

# 导入LangChain的ChatOpenAI用于连接阿里云百炼（从langchain_community导入）
from langchain_openai import ChatOpenAI

# 初始化日志
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动应用...")
    
    try:
        # 初始化 MySQL 连接（用户、订单等模块依赖）
        from src.utils import get_mysql_client
        mysql = get_mysql_client()
        if mysql.is_connected():
            logger.info("MySQL连接已就绪")
        else:
            logger.warning("MySQL连接未就绪，部分功能不可用")

        # 初始化服务
        product_service = ProductService()
        order_service = OrderService()
        
        # 检查MySQL连接状态
        if hasattr(order_service, '_mysql_available') and order_service._mysql_available:
            logger.info("✅ MySQL数据库连接成功")
            # 查询订单数量验证
            test_count = await order_service.get_order_count()
            logger.info(f"✅ MySQL订单表已初始化，共 {test_count} 条订单")
        else:
            logger.warning("⚠️ MySQL数据库连接失败，使用模拟数据")
            
        knowledge_base = KnowledgeBase()
        conversation_service = ConversationService()
        logger.info("服务初始化完成")
        
        # 初始化Agent管理器
        agent_manager = AgentManager()
        
        # 配置阿里云百炼模型（使用OpenAI兼容模式）
        llm = ChatOpenAI(
            model_name=settings.ALIYUN_MODEL_NAME,
            openai_api_key=settings.ALIYUN_API_KEY,
            openai_api_base=settings.ALIYUN_API_BASE,
            temperature=0.7,
            max_tokens=2048
        )
        
        logger.info(f"已连接到阿里云百炼模型: {settings.ALIYUN_MODEL_NAME}")
        
        # 注册Agent
        agent_manager.register_agent(CustomerServiceAgent(llm))
        agent_manager.register_agent(OrderAgent(llm, order_service))
        agent_manager.register_agent(ProductAgent(llm, product_service))
        
        logger.info(f"已注册 {len(agent_manager.list_agents())} 个Agent")
        
        # 存储服务实例到应用状态
        app.state.services = {
            "product_service": product_service,
            "order_service": order_service,
            "knowledge_base": knowledge_base,
            "conversation_service": conversation_service,
            "agent_manager": agent_manager,
            "llm": llm
        }
        
        logger.info("应用启动完成")
        
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}", exc_info=True)
        raise
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭应用...")
    try:
        # 清理资源
        if hasattr(app.state, 'services'):
            services = app.state.services
            if 'conversation_service' in services:
                # 清理过期会话
                expired_count = await services['conversation_service'].clean_expired_sessions()
                logger.info(f"清理了 {expired_count} 个过期会话")
        
        logger.info("应用关闭完成")
    except Exception as e:
        logger.error(f"应用关闭时出错: {str(e)}", exc_info=True)

# 创建 FastAPI 应用
app = FastAPI(
    title="多Agent电商客服系统",
    description="基于LangChain和FastAPI的企业级多Agent电商客服解决方案，使用阿里云百炼deepseek-v4-pro模型",
    version="1.0.0",
    lifespan=lifespan
)

# 创建限流器 — 基于客户端 IP 地址追踪请求频率
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置CORS中间件 — 只允许白名单中的域名访问
cors_origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 安全 Headers — 缓解 XSS、MIME sniffing、clickjacking
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Prometheus 指标监控 — 自动追踪请求数、延迟、状态码
instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app, endpoint="/metrics", include_in_schema=True)

# 注册路由
app.include_router(chat_router)
app.include_router(system_router)
app.include_router(admin_router)
app.include_router(user_router)

# ── 全局异常处理器 — 将 AppError 转为统一格式响应 ──
from src.utils.errors import AppError

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.warning(f"[{exc.code.value}] {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )

# 根路径
@app.get("/")
async def root():
    """根路径 - 返回API信息"""
    return {
        "message": "多Agent电商客服系统API",
        "version": "1.0.0",
        "status": "running",
        "model": settings.ALIYUN_MODEL_NAME,
        "endpoints": {
            "docs": "/docs",
            "chat": "/api/chat",
            "health": "/health",
            "admin": "/api/admin/collections"
        }
    }

# 健康检查 — 逐项探测所有依赖
@app.get("/health")
async def health_check():
    """
    依赖健康检查

    返回每个依赖的状态:
      - up: 正常
      - down: 不可用
      - not_configured: 未配置
    """
    from src.services.chroma_store_service import get_chroma_store_service
    from src.services.ollama_embedding_service import get_ollama_embedding_service

    checks = {}

    # 1. MySQL 数据库
    try:
        from src.utils import get_mysql_client
        mysql = get_mysql_client()
        checks["database"] = "up" if mysql.is_connected() else "down"
    except Exception:
        checks["database"] = "down"

    # 2. Redis
    try:
        from src.utils.redis_client import get_redis_client
        redis = get_redis_client()
        checks["redis"] = "up" if redis.get_connection() else "down"
    except Exception:
        checks["redis"] = "down"

    # 3. ChromaDB 向量数据库
    try:
        chroma = await get_chroma_store_service()
        chroma.list_collections()
        checks["chromadb"] = "up"
    except Exception:
        checks["chromadb"] = "down"

    # 4. Ollama 嵌入服务
    try:
        ollama = await get_ollama_embedding_service()
        available = await ollama.is_available()
        checks["ollama"] = "up" if available else "down"
    except Exception:
        checks["ollama"] = "down"

    # 5. LLM API（最关键的依赖）
    try:
        from src.services.llm_service import LLMService
        svc = LLMService()
        # 轻量探测：发一个短请求看 API 是否响应
        resp = await svc.generate_text("ping", max_tokens=1, temperature=0)
        checks["llm"] = "up" if resp else "down"
    except Exception:
        checks["llm"] = "down"

    # 判定整体状态
    down_count = sum(1 for v in checks.values() if v == "down")
    if down_count == 0:
        overall = "healthy"
    elif down_count <= 2:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "version": "1.0.0",
        "model": settings.ALIYUN_MODEL_NAME,
        "checks": checks,
    }

# 系统信息
@app.get("/system/info")
async def system_info():
    """获取系统信息"""
    agent_manager = AgentManager()
    
    return {
        "system": "多Agent电商客服系统",
        "version": "1.0.0",
        "model": settings.ALIYUN_MODEL_NAME,
        "agents": agent_manager.list_agents(),
        "features": [
            "多Agent协作",
            "智能路由",
            "对话历史管理",
            "产品查询",
            "订单管理",
            "知识库问答"
        ],
        "provider": "阿里云百炼"
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"正在启动服务器，端口: {settings.APP_PORT}")
    logger.info(f"使用模型: {settings.ALIYUN_MODEL_NAME}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=True,  # 开发模式，生产环境设为False
        log_level="info"
    )