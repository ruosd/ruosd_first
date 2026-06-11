"""
Mock 平台适配器 — 包装自有数据库（当前默认数据源）

将现有 OrderService 和 ProductService 的方法映射到 PlatformAdapter 接口。
后续接入淘宝时，只需替换为 TaobaoAdapter，Service 层代码不变。
"""

from typing import Optional, List, Dict, Any
from .base import PlatformAdapter


class MockAdapter(PlatformAdapter):
    """自有数据库适配器 — 当前系统默认数据源"""

    def __init__(self):
        self._order_service = None
        self._product_service = None
        self._connected = True

    @property
    def platform_name(self) -> str:
        return "mock"

    # ── 懒加载 Service（避免循环导入）──

    def _get_order_service(self):
        if self._order_service is None:
            from ..services import OrderService
            self._order_service = OrderService()
        return self._order_service

    def _get_product_service(self):
        if self._product_service is None:
            from ..services import ProductService
            self._product_service = ProductService()
        return self._product_service

    # ── 订单 ──

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        svc = self._get_order_service()
        result = await svc.get_order_details(order_id)
        if result:
            return {"order_id": order_id, "detail": result}
        return None

    async def get_user_orders(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._get_order_service().get_user_orders(user_id)

    async def search_orders(self, keyword: str) -> List[Dict[str, Any]]:
        return await self._get_order_service().search_orders(keyword)

    async def get_shipping_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        result = await self._get_order_service().get_order_details(order_id)
        if result:
            return {"order_id": order_id, "shipping": result}
        return None

    async def get_order_count(self) -> int:
        return await self._get_order_service().get_order_count()

    # ── 产品 ──

    async def search_products(self, keyword: str) -> List[Dict[str, Any]]:
        return await self._get_product_service().search_products(keyword)

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_product_service().get_product_details(product_id)

    async def recommend_products(self, preference: str) -> List[Dict[str, Any]]:
        # Mock 适配器：简单用 preference 做关键词搜索
        return await self._get_product_service().search_products(preference)

    # ── 状态 ──

    def is_connected(self) -> bool:
        return self._connected
