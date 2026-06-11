"""
统一错误码定义

用途: 前后端约定错误类型，前端根据 code 做业务处理，不依赖 message 文本。

使用方式:
    from src.utils.errors import AppError, ErrorCode
    raise AppError(ErrorCode.OLLAMA_UNAVAILABLE, status_code=503)
"""

from enum import Enum
from typing import Optional, Any


class ErrorCode(str, Enum):
    """错误码枚举 — 命名规则: 模块_具体问题"""

    # ── 认证 (AUTH) ──
    UNAUTHORIZED = "AUTH_UNAUTHORIZED"               # 未登录或 token 无效
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"             # token 已过期
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"  # 用户名或密码错误
    PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"     # 无权限

    # ── 请求校验 (VALIDATION) ──
    VALIDATION_ERROR = "VALIDATION_ERROR"             # 输入校验失败
    MISSING_FIELD = "VALIDATION_MISSING_FIELD"        # 缺少必填字段
    INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"       # 格式不正确

    # ── 限流 (RATE) ──
    RATE_LIMITED = "RATE_LIMITED"                     # 请求频率超限

    # ── 资源 (RESOURCE) ──
    NOT_FOUND = "RESOURCE_NOT_FOUND"                  # 资源不存在
    DUPLICATE = "RESOURCE_DUPLICATE"                  # 资源重复

    # ── 依赖服务 (SERVICE) ──
    OLLAMA_UNAVAILABLE = "SERVICE_OLLAMA_UNAVAILABLE"  # Ollama 嵌入服务不可用
    CHROMADB_ERROR = "SERVICE_CHROMADB_ERROR"          # ChromaDB 操作失败
    LLM_ERROR = "SERVICE_LLM_ERROR"                    # LLM 调用失败
    REDIS_ERROR = "SERVICE_REDIS_ERROR"                # Redis 操作失败
    MYSQL_ERROR = "SERVICE_MYSQL_ERROR"                # MySQL 操作失败

    # ── 内部错误 (INTERNAL) ──
    INTERNAL_ERROR = "INTERNAL_ERROR"                  # 未知内部错误


class AppError(Exception):
    """应用异常 — 携带错误码，方便前端统一处理"""

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        status_code: int = 400,
        details: Any = None,
    ):
        self.code = code
        self.message = message or self._default_message(code)
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    @staticmethod
    def _default_message(code: ErrorCode) -> str:
        defaults = {
            ErrorCode.UNAUTHORIZED: "请先登录",
            ErrorCode.TOKEN_EXPIRED: "登录已过期，请重新登录",
            ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
            ErrorCode.PERMISSION_DENIED: "无权限执行此操作",
            ErrorCode.VALIDATION_ERROR: "输入数据校验失败",
            ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后重试",
            ErrorCode.NOT_FOUND: "请求的资源不存在",
            ErrorCode.DUPLICATE: "资源已存在，请勿重复操作",
            ErrorCode.OLLAMA_UNAVAILABLE: "嵌入服务暂不可用",
            ErrorCode.CHROMADB_ERROR: "向量数据库操作失败",
            ErrorCode.LLM_ERROR: "AI 模型调用失败",
            ErrorCode.INTERNAL_ERROR: "服务器内部错误",
        }
        return defaults.get(code, "未知错误")

    def to_dict(self) -> dict:
        result = {"code": self.code.value, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result
