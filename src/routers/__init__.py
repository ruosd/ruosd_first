from .admin_router import router as admin_router
from .chat_router import router as chat_router
from .system_router import router as system_router
from .user_router import router as user_router

__all__ = ["chat_router", "system_router", "admin_router", "user_router"]
