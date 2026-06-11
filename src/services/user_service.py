import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from src.models.user import User
from src.utils import get_mysql_client
from src.utils.logger import get_logger
from src.utils.password import hash_password, verify_password

logger = get_logger("user_service")


def parse_datetime(date_str):
    """解析时间，支持 datetime 对象和时间字符串"""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                return datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                logger.warning(f"无法解析时间字符串: {date_str}")
                return None


def _row_to_user(row: Dict) -> User:
    """将数据库行转换为 User 对象"""
    return User(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
        role=row.get("role", "user"),
        nickname=row.get("nickname") or "",
        phone=row.get("phone") or "",
        avatar=row.get("avatar") or "",
        status=row.get("status", "active"),
        created_at=parse_datetime(row.get("created_at")),
        updated_at=parse_datetime(row.get("updated_at")),
    )


class UserService:
    """用户服务 — 基于 MySQL 存储"""

    def __init__(self):
        self.mysql = get_mysql_client()
        self._table_inited = False
        if self.mysql.is_connected():
            self._init_user_table()
            self._table_inited = True

    def _ensure_mysql(self) -> bool:
        """确保 MySQL 可用，若首次失败则重试"""
        if self.mysql.is_connected():
            if not self._table_inited:
                self._init_user_table()
                self._table_inited = True
            return True
        return False

    def _init_user_table(self):
        """初始化用户表（MySQL）"""
        self.mysql.execute_update("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                email VARCHAR(128) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(16) DEFAULT 'user',
                nickname VARCHAR(64) DEFAULT '',
                phone VARCHAR(20) DEFAULT '',
                avatar VARCHAR(256) DEFAULT '',
                status VARCHAR(16) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_users_username (username),
                INDEX idx_users_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        logger.info("MySQL用户表初始化完成")

    def _hash_password(self, password: str) -> str:
        return hash_password(password)

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        nickname: str = "",
        phone: str = "",
        role: str = "user",
    ) -> tuple[Optional[User], Optional[str]]:
        """注册新用户"""
        if not self._ensure_mysql():
            return None, "数据库不可用"

        try:
            if self.get_user_by_username(username):
                return None, "用户名已被注册"
            if self.get_user_by_email(email):
                return None, "邮箱已被注册"

            password_hash = self._hash_password(password)
            now = datetime.now()

            result = self.mysql.execute_update(
                """INSERT INTO users
                   (username, email, password_hash, nickname, phone, role, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (username, email, password_hash, nickname, phone, role, now, now),
            )
            if result <= 0:
                return None, "注册失败"

            rows = self.mysql.execute_query(
                "SELECT LAST_INSERT_ID() as id"
            )
            if rows and rows[0].get("id"):
                user_id = rows[0]["id"]
                logger.info(f"用户注册成功: {username} (id={user_id})")
                return self.get_user_by_id(user_id), None

            logger.warning(f"无法获取新用户ID: {username}")
            return self.get_user_by_username(username), None

        except Exception as e:
            error_str = str(e).lower()
            if "duplicate" in error_str or "unique" in error_str:
                if "username" in error_str:
                    return None, "用户名已被注册"
                elif "email" in error_str:
                    return None, "邮箱已被注册"
                else:
                    return None, "用户名或邮箱已被注册"
            logger.error(f"用户注册失败: {e}", exc_info=True)
            return None, "注册失败"

    def login_user(self, username_or_email: str, password: str) -> Optional[User]:
        """用户登录"""
        if not self._ensure_mysql():
            return None

        try:
            user = self.get_user_by_username(username_or_email)
            if not user:
                user = self.get_user_by_email(username_or_email)

            if not user:
                logger.warning(f"用户不存在: {username_or_email}")
                return None

            if user.status != "active":
                logger.warning(f"用户已禁用: {username_or_email}")
                return None

            if not verify_password(password, user.password_hash):
                logger.warning(f"密码错误: {username_or_email}")
                return None

            logger.info(f"用户登录成功: {username_or_email}")
            return user

        except Exception as e:
            logger.error(f"用户登录失败: {e}", exc_info=True)
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """通过ID获取用户"""
        try:
            rows = self.mysql.execute_query(
                """SELECT id, username, email, password_hash, role, nickname,
                          phone, avatar, status, created_at, updated_at
                   FROM users WHERE id = %s""",
                (user_id,),
            )
            if rows:
                return _row_to_user(rows[0])
            return None
        except Exception as e:
            logger.error(f"获取用户失败(id={user_id}): {e}", exc_info=True)
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        try:
            rows = self.mysql.execute_query(
                """SELECT id, username, email, password_hash, role, nickname,
                          phone, avatar, status, created_at, updated_at
                   FROM users WHERE username = %s""",
                (username,),
            )
            if rows:
                return _row_to_user(rows[0])
            return None
        except Exception as e:
            logger.error(f"获取用户失败(username={username}): {e}", exc_info=True)
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        try:
            rows = self.mysql.execute_query(
                """SELECT id, username, email, password_hash, role, nickname,
                          phone, avatar, status, created_at, updated_at
                   FROM users WHERE email = %s""",
                (email,),
            )
            if rows:
                return _row_to_user(rows[0])
            return None
        except Exception as e:
            logger.error(f"获取用户失败(email={email}): {e}", exc_info=True)
            return None

    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        try:
            update_fields = []
            update_values = []

            field_map = {
                "username": "username = %s",
                "email": "email = %s",
                "password": "password_hash = %s",
                "nickname": "nickname = %s",
                "phone": "phone = %s",
                "avatar": "avatar = %s",
                "status": "status = %s",
                "role": "role = %s",
            }

            for key, clause in field_map.items():
                if key in kwargs:
                    update_fields.append(clause)
                    if key == "password":
                        update_values.append(self._hash_password(kwargs[key]))
                    else:
                        update_values.append(kwargs[key])

            if not update_fields:
                return False

            update_fields.append("updated_at = %s")
            update_values.append(datetime.now())
            update_values.append(user_id)

            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            result = self.mysql.execute_update(query, tuple(update_values))
            logger.info(f"用户更新成功: {user_id}")
            return result > 0

        except Exception as e:
            logger.error(f"更新用户失败: {e}", exc_info=True)
            return False

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        try:
            result = self.mysql.execute_update(
                "DELETE FROM users WHERE id = %s", (user_id,)
            )
            if result > 0:
                logger.info(f"用户删除成功: {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除用户失败: {e}", exc_info=True)
            return False

    def get_all_users(self, role: Optional[str] = None) -> list[User]:
        """获取所有用户"""
        try:
            if role:
                rows = self.mysql.execute_query(
                    """SELECT id, username, email, password_hash, role, nickname,
                              phone, avatar, status, created_at, updated_at
                       FROM users WHERE role = %s ORDER BY created_at DESC""",
                    (role,),
                )
            else:
                rows = self.mysql.execute_query(
                    """SELECT id, username, email, password_hash, role, nickname,
                              phone, avatar, status, created_at, updated_at
                       FROM users ORDER BY created_at DESC"""
                )

            return [_row_to_user(row) for row in (rows or [])]
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            return []

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            if not verify_password(old_password, user.password_hash):
                return False
            return self.update_user(user_id, password=new_password)
        except Exception as e:
            logger.error(f"修改密码失败: {e}", exc_info=True)
            return False


# 单例
_user_service = None


def get_user_service() -> UserService:
    """获取用户服务单例"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
