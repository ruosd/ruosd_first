from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: str = "user"  # user 或 admin
    nickname: str = ""
    phone: str = ""
    avatar: str = ""
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def is_admin(self) -> bool:
        """判断是否为管理员"""
        return self.role == "admin"
    
    def is_active(self) -> bool:
        """判断用户是否激活"""
        return self.status == "active"