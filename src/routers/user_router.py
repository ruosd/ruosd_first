"""
用户路由 - 处理用户注册、登录等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
from src.services import get_user_service
from src.models.user import User
from src.utils.logger import get_logger
from src.utils.password import hash_password, verify_password
from src.utils.settings import settings
from src.utils.redis_client import get_redis_client
import hashlib

logger = get_logger("user_router")

router = APIRouter(prefix="/api", tags=["用户接口"])
limiter = Limiter(key_func=get_remote_address)

# JWT配置 - 密钥强制从环境变量读取，无默认值
SECRET_KEY = settings.JWT_SECRET_KEY
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY 环境变量未设置，请复制 .env.example 到 .env 并配置密钥"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# 安全依赖
security = HTTPBearer()

# 请求模型
class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=32, description="用户名")
    email: str = Field(..., min_length=5, max_length=128, description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码（最少6位）")
    nickname: Optional[str] = Field("", max_length=64, description="昵称")
    phone: Optional[str] = Field("", max_length=20, description="手机号")
    role: Optional[str] = Field("user", max_length=16, description="角色")

class LoginRequest(BaseModel):
    """登录请求"""
    username_or_email: str = Field(..., min_length=2, max_length=128, description="用户名或邮箱")
    password: str = Field(..., min_length=1, max_length=128, description="密码")

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1, max_length=128, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码（最少6位）")

class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    nickname: Optional[str] = Field(None, max_length=64, description="昵称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    avatar: Optional[str] = Field(None, max_length=256, description="头像URL")

class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")

class LogoutRequest(BaseModel):
    """登出请求（可选的 refresh_token 用于同时销毁）"""
    refresh_token: Optional[str] = Field(None, description="刷新令牌，提供后会同时销毁")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    to_encode["type"] = "access"
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    """创建JWT刷新令牌"""
    to_encode = data.copy()
    to_encode["type"] = "refresh"
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def _get_blacklist_key(token: str) -> str:
    """获取Token黑名单的Redis键（SHA256哈希，防止JWT payload信息泄露）"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return f"token_blacklist:{token_hash}"

def _blacklist_token(token: str, ttl: int):
    """将Token加入黑名单"""
    try:
        redis_client = get_redis_client()
        conn = redis_client.get_connection()
        if conn:
            conn.setex(_get_blacklist_key(token), ttl, "1")
    except Exception as e:
        logger.warning(f"Token黑名单操作失败: {e}")

def _is_token_blacklisted(token: str) -> bool:
    """检查Token是否在黑名单中。Redis不可用时 fail-closed：拒绝访问"""
    try:
        redis_client = get_redis_client()
        conn = redis_client.get_connection()
        if conn is None:
            logger.warning("Redis不可用，Token黑名单检查fail-closed")
            return True
        return bool(conn.exists(_get_blacklist_key(token)))
    except Exception as e:
        logger.error(f"Token黑名单检查失败(fail-closed): {e}")
        return True

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前登录用户"""
    token = credentials.credentials

    if _is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="令牌已失效")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="无效的凭证类型")
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的凭证")

        user_service = get_user_service()
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效")

@router.post("/register", summary="用户注册")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """
    用户注册接口
    
    Args:
        request: 注册请求，包含用户名、邮箱、密码等信息
        
    Returns:
        注册结果和用户信息
    """
    try:
        user_service = get_user_service()
        
        # 验证参数
        if len(body.username) < 3 or len(body.username) > 50:
            raise HTTPException(status_code=400, detail="用户名长度必须在3-50个字符之间")
        
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        # 注册用户
        user, error_message = user_service.register_user(
            username=body.username,
            email=body.email,
            password=body.password,
            nickname=body.nickname,
            phone=body.phone,
            role=body.role
        )
        
        if not user:
            raise HTTPException(status_code=400, detail=error_message or "注册失败")
        
        # 生成访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"user_id": user.id, "username": user.username, "role": user.role}
        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data)

        return {
            "status": "success",
            "message": "注册成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname,
                "phone": user.phone,
                "role": user.role,
                "status": user.status
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login", summary="用户登录")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """
    用户登录接口（支持普通用户和管理员）
    
    Args:
        request: 登录请求，包含用户名/邮箱和密码
        
    Returns:
        登录结果、用户信息和访问令牌
    """
    try:
        user_service = get_user_service()
        
        # 登录验证
        user = user_service.login_user(body.username_or_email, body.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")
        
        # 生成访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"user_id": user.id, "username": user.username, "role": user.role}
        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data)

        return {
            "status": "success",
            "message": "登录成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname,
                "phone": user.phone,
                "role": user.role,
                "status": user.status
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login/admin", summary="管理员登录")
@limiter.limit("5/minute")
async def admin_login(request: Request, body: LoginRequest):
    """
    管理员登录接口（仅限管理员角色）
    
    Args:
        request: 登录请求，包含用户名/邮箱和密码
        
    Returns:
        登录结果、用户信息和访问令牌
    """
    try:
        user_service = get_user_service()
        
        # 登录验证
        user = user_service.login_user(body.username_or_email, body.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")
        
        # 验证管理员角色
        if not user.is_admin():
            raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")
        
        # 生成访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"user_id": user.id, "username": user.username, "role": user.role}
        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data)

        return {
            "status": "success",
            "message": "管理员登录成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname,
                "phone": user.phone,
                "role": user.role,
                "status": user.status
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员登录失败: {e}")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@router.get("/user/me", summary="获取当前用户信息")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的详细信息
    
    Returns:
        当前用户信息
    """
    return {
        "status": "success",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "phone": current_user.phone,
            "avatar": current_user.avatar,
            "role": current_user.role,
            "status": current_user.status,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        }
    }

@router.put("/user/me", summary="更新当前用户信息")
async def update_current_user(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user)
):
    """
    更新当前登录用户的信息
    
    Args:
        request: 更新请求，包含昵称、手机号、头像等
        
    Returns:
        更新结果
    """
    try:
        user_service = get_user_service()
        
        update_data = {}
        if request.nickname is not None:
            update_data["nickname"] = request.nickname
        if request.phone is not None:
            update_data["phone"] = request.phone
        if request.avatar is not None:
            update_data["avatar"] = request.avatar
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有需要更新的信息")
        
        success = user_service.update_user(current_user.id, **update_data)
        
        if success:
            return {
                "status": "success",
                "message": "用户信息更新成功"
            }
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/user/me/password", summary="修改当前用户密码")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    修改当前登录用户的密码
    
    Args:
        request: 修改密码请求，包含旧密码和新密码
        
    Returns:
        修改结果
    """
    try:
        user_service = get_user_service()
        
        if len(request.new_password) < 6:
            raise HTTPException(status_code=400, detail="新密码长度至少6位")

        success = user_service.change_password(
            user_id=current_user.id,
            old_password=request.old_password,
            new_password=request.new_password
        )
        
        if success:
            return {
                "status": "success",
                "message": "密码修改成功"
            }
        else:
            raise HTTPException(status_code=400, detail="旧密码不正确")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users", summary="获取用户列表", dependencies=[Depends(get_current_user)])
async def get_users(role: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """
    获取用户列表（管理员权限）
    
    Args:
        role: 用户角色过滤
        
    Returns:
        用户列表
    """
    try:
        # 验证管理员权限
        if not current_user.is_admin():
            raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")
        
        user_service = get_user_service()
        users = user_service.get_all_users(role)
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname,
                "phone": user.phone,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            })
        
        return {
            "status": "success",
            "users": user_list,
            "total": len(user_list)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/{user_id}", summary="获取用户详情", dependencies=[Depends(get_current_user)])
async def get_user_detail(user_id: int, current_user: User = Depends(get_current_user)):
    """
    获取指定用户的详细信息（管理员权限）
    
    Args:
        user_id: 用户ID
        
    Returns:
        用户详细信息
    """
    try:
        # 验证管理员权限或自己查看自己
        if not current_user.is_admin() and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="权限不足")
        
        user_service = get_user_service()
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "status": "success",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname,
                "phone": user.phone,
                "avatar": user.avatar,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/users/{user_id}", summary="删除用户", dependencies=[Depends(get_current_user)])
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    """
    删除用户（管理员权限）
    
    Args:
        user_id: 用户ID
        
    Returns:
        删除结果
    """
    try:
        # 验证管理员权限
        if not current_user.is_admin():
            raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")
        
        # 不能删除自己
        if current_user.id == user_id:
            raise HTTPException(status_code=400, detail="不能删除自己")
        
        user_service = get_user_service()
        success = user_service.delete_user(user_id)
        
        if success:
            return {
                "status": "success",
                "message": "用户删除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/refresh", summary="刷新访问令牌")
@limiter.limit("10/minute")
async def refresh_token(request: Request, body: RefreshRequest):
    """使用刷新令牌获取新的访问令牌"""
    try:
        if _is_token_blacklisted(body.refresh_token):
            raise HTTPException(status_code=401, detail="刷新令牌已失效")

        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的刷新令牌类型")

        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")

        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的刷新令牌")

        user_service = get_user_service()
        user = user_service.get_user_by_id(user_id)
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": user_id, "username": username, "role": role},
            expires_delta=access_token_expires
        )

        return {
            "status": "success",
            "message": "令牌刷新成功",
            "access_token": access_token
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="刷新令牌已过期，请重新登录")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="刷新令牌无效")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/logout", summary="用户登出")
@limiter.limit("10/minute")
async def logout(request: LogoutRequest = LogoutRequest(), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """登出用户，将 Access Token 和 Refresh Token（如提供）加入黑名单"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        ttl = payload.get("exp", 0) - int(datetime.utcnow().timestamp())
        if ttl > 0:
            _blacklist_token(token, ttl)

        if request.refresh_token:
            try:
                refresh_payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                refresh_ttl = refresh_payload.get("exp", 0) - int(datetime.utcnow().timestamp())
                if refresh_ttl > 0:
                    _blacklist_token(request.refresh_token, refresh_ttl)
            except jwt.PyJWTError:
                pass

        return {
            "status": "success",
            "message": "登出成功"
        }
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效")
    except Exception as e:
        logger.error(f"登出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")