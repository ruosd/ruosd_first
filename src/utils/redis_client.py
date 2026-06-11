import redis
from typing import Optional, Any, Dict, List
import json
from .settings import settings
from .logger import get_logger

logger = get_logger("redis_client")

class RedisClient:
    """Redis客户端封装类"""
    
    _instance: Optional['RedisClient'] = None
    _connection: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._connect()
    
    def _connect(self):
        """建立Redis连接"""
        try:
            self._connection = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self._connection.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._connection = None
    
    def get_connection(self) -> Optional[redis.Redis]:
        """获取Redis连接"""
        if self._connection is None:
            self._connect()
        return self._connection
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值（会自动序列化为JSON）
            expire: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        try:
            conn = self.get_connection()
            if conn:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                return conn.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis设置失败: {e}")
        return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取键值
        
        Args:
            key: 键名
            
        Returns:
            键对应的值
        """
        try:
            conn = self.get_connection()
            if conn:
                value = conn.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
        return None
    
    def delete(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键名
            
        Returns:
            是否删除成功
        """
        try:
            conn = self.get_connection()
            if conn:
                return conn.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")
        return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            
        Returns:
            键是否存在
        """
        try:
            conn = self.get_connection()
            if conn:
                return conn.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis检查失败: {e}")
        return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            seconds: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        try:
            conn = self.get_connection()
            if conn:
                return conn.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis设置过期时间失败: {e}")
        return False
    
    def hset(self, name: str, key: str, value: Any) -> bool:
        """
        设置哈希表字段
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值
            
        Returns:
            是否设置成功
        """
        try:
            conn = self.get_connection()
            if conn:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                return conn.hset(name, key, value) > 0
        except Exception as e:
            logger.error(f"Redis哈希设置失败: {e}")
        return False
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        """
        获取哈希表字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            字段值
        """
        try:
            conn = self.get_connection()
            if conn:
                value = conn.hget(name, key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
        except Exception as e:
            logger.error(f"Redis哈希获取失败: {e}")
        return None
    
    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取哈希表所有字段
        
        Args:
            name: 哈希表名
            
        Returns:
            所有字段和值的字典
        """
        try:
            conn = self.get_connection()
            if conn:
                data = conn.hgetall(name)
                result = {}
                for key, value in data.items():
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
                return result
        except Exception as e:
            logger.error(f"Redis哈希获取所有失败: {e}")
        return {}
    
    def close(self):
        """关闭Redis连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

def get_redis_client() -> RedisClient:
    """获取Redis客户端实例"""
    return RedisClient()