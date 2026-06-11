from typing import Any, Optional

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool, PoolError

from ..utils.logger import get_logger
from ..utils.settings import settings

logger = get_logger("mysql_client")


class MySQLClient:
    """MySQL数据库客户端封装类（连接池）"""

    _instance: Optional['MySQLClient'] = None
    _pool: MySQLConnectionPool | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._init_pool()

    def _init_pool(self):
        """初始化连接池并建表"""
        try:
            logger.debug(f"创建MySQL连接池: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
            self._pool = MySQLConnectionPool(
                pool_name="dskf_pool",
                pool_size=5,
                pool_reset_session=True,
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DB,
                charset='utf8mb4',
            )
            logger.info("MySQL连接池已创建 (pool_size=5)")
            # 用第一个连接自动建表
            conn = self._pool.get_connection()
            try:
                self._create_tables(conn)
            finally:
                conn.close()
        except Error as e:
            logger.error(f"MySQL连接池创建失败: {e}")
            self._pool = None

    def get_connection(self) -> mysql.connector.MySQLConnection | None:
        """从连接池获取连接"""
        if self._pool is None:
            self._init_pool()
        if self._pool is None:
            return None
        try:
            return self._pool.get_connection()
        except PoolError as e:
            logger.error(f"连接池耗尽: {e}")
            return None

    def is_connected(self) -> bool:
        """检查MySQL是否可用"""
        conn = self.get_connection()
        if conn:
            try:
                return conn.is_connected()
            finally:
                conn.close()
        return False

    def _create_tables(self, conn):
        """创建订单相关表"""
        cursor = conn.cursor()

        create_orders_table = """
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(32) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        create_order_items_table = """
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(32) NOT NULL,
            product_id INT NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            INDEX idx_order_id (order_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        create_tracking_info_table = """
        CREATE TABLE IF NOT EXISTS tracking_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(32) UNIQUE NOT NULL,
            tracking_number VARCHAR(64) NOT NULL,
            status VARCHAR(64) NOT NULL,
            location VARCHAR(255),
            estimated_delivery DATE,
            updated_at DATETIME NOT NULL,
            INDEX idx_order_id (order_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        create_products_table = """
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            stock INT DEFAULT 0,
            category VARCHAR(64),
            specifications JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        create_messages_table = """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            agent_name VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session_id (session_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        create_metrics_table = """
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(32) NOT NULL,
            agent_name VARCHAR(64),
            event_data JSON,
            latency_ms INT,
            success BOOLEAN DEFAULT TRUE,
            session_id VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_event_type (event_type),
            INDEX idx_agent_name (agent_name),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        try:
            cursor.execute(create_orders_table)
            cursor.execute(create_order_items_table)
            cursor.execute(create_tracking_info_table)
            cursor.execute(create_products_table)
            cursor.execute(create_messages_table)
            cursor.execute(create_metrics_table)
            conn.commit()
            logger.info("MySQL表创建成功")
        except Error as e:
            logger.error(f"创建表失败: {e}")
        finally:
            cursor.close()

    def execute_query(self, query: str, params: tuple | None = None) -> list[dict[str, Any]] | None:
        """执行查询并返回结果"""
        conn = self.get_connection()
        if conn is None:
            return None

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Error as e:
            logger.error(f"查询执行失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def execute_update(self, query: str, params: tuple | None = None) -> int:
        """执行更新操作并返回受影响的行数"""
        conn = self.get_connection()
        if conn is None:
            return 0

        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Error as e:
            logger.error(f"更新执行失败: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()

    def close(self):
        """关闭连接池（清空所有连接）"""
        self._pool = None
        logger.info("MySQL连接池已释放")


def get_mysql_client() -> MySQLClient:
    """获取MySQL客户端实例"""
    return MySQLClient()
