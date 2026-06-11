"""
平台适配器基类 — 定义数据源标准接口

所有平台（淘宝、京东、自有数据库）都需实现此接口。
Service 层只依赖此接口，不关心数据来自哪里。
"""

from abc import ABC, abstractmethod
from typing import Any


class PlatformAdapter(ABC):
    """平台适配器抽象基类"""

    # ── 订单 ──

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """查询单个订单"""

    @abstractmethod
    async def get_user_orders(self, user_id: str) -> list[dict[str, Any]]:
        """查询用户订单列表"""

    @abstractmethod
    async def search_orders(self, keyword: str) -> list[dict[str, Any]]:
        """按关键词搜索订单"""

    @abstractmethod
    async def get_shipping_info(self, order_id: str) -> dict[str, Any] | None:
        """查询物流信息"""

    @abstractmethod
    async def get_order_count(self) -> int:
        """获取订单总数"""

    # ── 产品 ──

    @abstractmethod
    async def search_products(self, keyword: str) -> list[dict[str, Any]]:
        """搜索产品"""

    @abstractmethod
    async def get_product(self, product_id: str) -> dict[str, Any] | None:
        """获取产品详情"""

    @abstractmethod
    async def recommend_products(self, preference: str) -> list[dict[str, Any]]:
        """推荐产品"""

    # ── 状态 ──

    @abstractmethod
    def is_connected(self) -> bool:
        """数据源是否可用"""

    @property
    def platform_name(self) -> str:
        return self.__class__.__name__
