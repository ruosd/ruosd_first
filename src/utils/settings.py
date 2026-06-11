import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载环境变量
load_dotenv(".env", encoding="utf-8")

class Settings(BaseModel):
    # 阿里云百炼配置
    ALIYUN_API_KEY: str = Field(default_factory=lambda: os.getenv("ALIYUN_API_KEY", ""))
    ALIYUN_API_BASE: str = Field(default_factory=lambda: os.getenv("ALIYUN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    ALIYUN_MODEL_NAME: str = Field(default_factory=lambda: os.getenv("ALIYUN_MODEL_NAME", "deepseek-v4-pro"))

    # Redis配置
    REDIS_HOST: str = Field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int = Field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    REDIS_DB: int = Field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    REDIS_PASSWORD: str = Field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))

    # MySQL数据库配置
    MYSQL_HOST: str = Field(default_factory=lambda: os.getenv("MYSQL_HOST", "localhost"))
    MYSQL_PORT: int = Field(default_factory=lambda: int(os.getenv("MYSQL_PORT", "3306")))
    MYSQL_USER: str = Field(default_factory=lambda: os.getenv("MYSQL_USER", "admin"))
    MYSQL_PASSWORD: str = Field(default_factory=lambda: os.getenv("MYSQL_PASSWORD", ""))
    MYSQL_DB: str = Field(default_factory=lambda: os.getenv("MYSQL_DB", "ecommerce"))

    # 日志配置
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    APP_PORT: int = Field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))

    # JWT & 认证配置
    JWT_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", ""))
    ADMIN_JWT_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("ADMIN_JWT_SECRET_KEY", ""))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default_factory=lambda: int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))

    # 管理员账号
    ADMIN_USERNAME: str = Field(default_factory=lambda: os.getenv("ADMIN_USERNAME", "admin"))
    ADMIN_PASSWORD: str = Field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))

    # CORS
    CORS_ORIGINS: str = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))

    # ==================== 记忆系统配置 ====================

    # Ollama 配置 (bge-m3:latest)
    OLLAMA_BASE_URL: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    OLLAMA_EMBEDDING_MODEL: str = Field(default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3:latest"))
    OLLAMA_TIMEOUT: int = Field(default_factory=lambda: int(os.getenv("OLLAMA_TIMEOUT", "30")))

    # ChromaDB 配置
    CHROMA_HOST: str = Field(default_factory=lambda: os.getenv("CHROMA_HOST", ""))  # 服务端模式时才需要
    CHROMA_PORT: int = Field(default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000")))
    CHROMA_USE_HTTP: bool = Field(default_factory=lambda: os.getenv("CHROMA_USE_HTTP", "false").lower() == "true")
    CHROMA_PERSIST_DIR: str = Field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"))
    CHROMA_ANONYMIZED_TELEMETRY: bool = Field(default_factory=lambda: os.getenv("CHROMA_ANONYMIZED_TELEMETRY", "false").lower() == "true")

    # 记忆系统配置
    MEMORY_ENABLED: bool = Field(default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() == "true")
    SHORT_TERM_MEMORY_TTL: int = Field(default_factory=lambda: int(os.getenv("SHORT_TERM_MEMORY_TTL", "86400")))  # 默认24小时
    LONG_TERM_MEMORY_RETENTION_DAYS: int = Field(default_factory=lambda: int(os.getenv("LONG_TERM_MEMORY_RETENTION_DAYS", "90")))  # 默认90天
    TOP_K_RETRIEVAL: int = Field(default_factory=lambda: int(os.getenv("TOP_K_RETRIEVAL", "5")))  # 默认检索Top 5
    MEMORY_IMPORTANCE_THRESHOLD: float = Field(default_factory=lambda: float(os.getenv("MEMORY_IMPORTANCE_THRESHOLD", "0.6")))  # 记忆重要性阈值

    # ChromaDB 集合名称
    CHROMA_COLLECTION_SHORT_TERM: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION_SHORT_TERM", "short_term_memory"))
    CHROMA_COLLECTION_LONG_TERM: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION_LONG_TERM", "long_term_memory"))
    CHROMA_COLLECTION_KNOWLEDGE: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION_KNOWLEDGE", "knowledge_base"))
    CHROMA_COLLECTION_PRODUCT: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION_PRODUCT", "product_memory"))

settings = Settings()
