from typing import List, Dict, Optional
import uuid
from datetime import datetime, timedelta
import json

from ..utils import get_redis_client
from ..utils import get_mysql_client
from ..utils.logger import get_logger

logger = get_logger("conversation_service")


class ConversationService:
    """对话服务 - Redis(热缓存) + MySQL(长期存储)"""

    SESSION_PREFIX = "session:"
    MESSAGES_PREFIX = "messages:"
    SESSION_INDEX_KEY = "session_index"
    SESSION_EXPIRY = 24 * 60 * 60

    def __init__(self):
        self.redis = get_redis_client()
        self._redis_available = self.redis.get_connection() is not None

    def _get_session_key(self, session_id: str) -> str:
        return f"{self.SESSION_PREFIX}{session_id}"

    def _get_messages_key(self, session_id: str) -> str:
        return f"{self.MESSAGES_PREFIX}{session_id}"

    def _mysql(self):
        mysql = get_mysql_client()
        return mysql if mysql.is_connected() else None

    async def create_conversation(self, user_id: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        if self._redis_available:
            session_data = {"session_id": session_id, "user_id": user_id, "created_at": now, "updated_at": now}
            self.redis.set(self._get_session_key(session_id), session_data, expire=self.SESSION_EXPIRY)
            self.redis.get_connection().sadd(self.SESSION_INDEX_KEY, session_id)

        return session_id

    async def add_message(self, session_id: str, role: str, content: str, agent_name: Optional[str] = None) -> bool:
        if not self._redis_available:
            return False
        conn = self.redis.get_connection()
        if conn is None:
            return False
        if not self.redis.exists(self._get_session_key(session_id)):
            return False

        message = {"role": role, "content": content, "agent_name": agent_name, "created_at": datetime.now().isoformat()}
        conn.rpush(self._get_messages_key(session_id), json.dumps(message, ensure_ascii=False))

        session_key = self._get_session_key(session_id)
        session_data = self.redis.get(session_key)
        if session_data:
            session_data["updated_at"] = datetime.now().isoformat()
            self.redis.set(session_key, session_data, expire=self.SESSION_EXPIRY)

        conn.expire(self._get_messages_key(session_id), self.SESSION_EXPIRY)

        # 同步写入 MySQL 持久化
        self._save_to_mysql(session_id, role, content, agent_name)

        return True

    def _save_to_mysql(self, session_id: str, role: str, content: str, agent_name: Optional[str]):
        """写入 MySQL 作为长期持久化存储"""
        mysql = self._mysql()
        if mysql is None:
            return
        mysql.execute_update(
            "INSERT INTO conversation_messages (session_id, role, content, agent_name) VALUES (%s, %s, %s, %s)",
            (session_id, role, content, agent_name),
        )

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        # 优先走 Redis
        if self._redis_available:
            conn = self.redis.get_connection()
            if conn:
                messages_data = conn.lrange(self._get_messages_key(session_id), 0, -1)
                if messages_data:
                    messages = []
                    for msg_str in messages_data:
                        try:
                            messages.append(json.loads(msg_str))
                        except json.JSONDecodeError:
                            continue
                    return messages

        # Redis 无数据，从 MySQL 恢复
        return self._load_from_mysql(session_id)

    def _load_from_mysql(self, session_id: str) -> List[Dict[str, str]]:
        """从 MySQL 恢复历史消息"""
        mysql = self._mysql()
        if mysql is None:
            return []
        rows = mysql.execute_query(
            "SELECT role, content, agent_name, created_at FROM conversation_messages WHERE session_id = %s ORDER BY id ASC",
            (session_id,),
        )
        if not rows:
            return []
        messages = []
        for r in rows:
            messages.append({
                "role": r["role"],
                "content": r["content"],
                "agent_name": r.get("agent_name"),
                "created_at": r.get("created_at").isoformat() if hasattr(r.get("created_at"), "isoformat") else r.get("created_at"),
            })
        return messages

    async def get_conversation_info(self, session_id: str) -> Optional[Dict]:
        if self._redis_available:
            session_data = self.redis.get(self._get_session_key(session_id))
            if session_data is None:
                return None
            conn = self.redis.get_connection()
            message_count = conn.llen(self._get_messages_key(session_id)) if conn else 0
            return {
                "session_id": session_data.get("session_id", session_id),
                "user_id": session_data.get("user_id"),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at"),
                "message_count": message_count,
            }
        return None

    async def get_user_id(self, session_id: str) -> Optional[str]:
        if self._redis_available:
            session_data = self.redis.get(self._get_session_key(session_id))
            if session_data:
                return session_data.get("user_id")
        return None

    async def delete_conversation(self, session_id: str) -> bool:
        if self._redis_available:
            conn = self.redis.get_connection()
            if conn is None:
                return False
            conn.delete(self._get_session_key(session_id))
            conn.delete(self._get_messages_key(session_id))
            conn.srem(self.SESSION_INDEX_KEY, session_id)
        # 同时清除 MySQL 持久化数据
        mysql = self._mysql()
        if mysql:
            mysql.execute_update("DELETE FROM conversation_messages WHERE session_id = %s", (session_id,))
        return True

    async def clean_expired_sessions(self) -> int:
        if not self._redis_available:
            return 0
        conn = self.redis.get_connection()
        if conn is None:
            return 0
        session_ids = conn.smembers(self.SESSION_INDEX_KEY)
        expired_count = 0
        for session_id in session_ids:
            if not conn.exists(self._get_session_key(session_id)):
                conn.srem(self.SESSION_INDEX_KEY, session_id)
                expired_count += 1
        return expired_count

    def get_all_sessions(self) -> List[Dict]:
        if not self._redis_available:
            return []
        conn = self.redis.get_connection()
        if conn is None:
            return []
        sessions = []
        for sid in conn.smembers(self.SESSION_INDEX_KEY):
            data = self.redis.get(self._get_session_key(sid))
            if data:
                message_count = conn.llen(self._get_messages_key(sid))
                sessions.append({
                    "session_id": data.get("session_id", sid),
                    "user_id": data.get("user_id"),
                    "message_count": message_count,
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                })
        return sessions

    async def export_conversation(self, session_id: str) -> Optional[str]:
        session_data = self.redis.get(self._get_session_key(session_id)) if self._redis_available else None
        messages = await self.get_conversation_history(session_id)
        if not session_data and not messages:
            return None
        data = {
            "session_id": session_id,
            "user_id": session_data.get("user_id") if session_data else None,
            "created_at": session_data.get("created_at") if session_data else None,
            "updated_at": session_data.get("updated_at") if session_data else None,
            "messages": messages,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def get_session_count(self) -> int:
        if not self._redis_available:
            return 0
        conn = self.redis.get_connection()
        if conn is None:
            return 0
        return conn.scard(self.SESSION_INDEX_KEY)

    async def get_redis_status(self) -> Dict:
        if not self._redis_available:
            return {"available": False, "message": "Redis客户端未初始化"}
        try:
            conn = self.redis.get_connection()
            if conn and conn.ping():
                return {"available": True, "message": "Redis连接正常", "session_count": await self.get_session_count()}
            return {"available": False, "message": "Redis连接失败"}
        except Exception as e:
            return {"available": False, "message": f"Redis错误: {str(e)}"}
