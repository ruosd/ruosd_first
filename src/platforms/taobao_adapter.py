"""
淘宝平台适配器（骨架）

使用方式:
  1. 在 .env 中配置 TAOBAO_APP_KEY / TAOBAO_APP_SECRET
  2. from src.platforms import set_platform_adapter
  3. set_platform_adapter(TaobaoAdapter())
  4. 重启服务 → 所有订单查询自动走淘宝 API

依赖: pip install top-sdk（淘宝开放平台 Python SDK）
"""

from typing import Any

from .base import PlatformAdapter


class TaobaoAdapter(PlatformAdapter):
    """淘宝开放平台适配器"""

    def __init__(self, app_key: str = "", app_secret: str = "", session_key: str = ""):
        self.app_key = app_key
        self.app_secret = app_secret
        self.session_key = session_key  # 淘宝 OAuth 授权后的 session
        self._connected = False
        self._client = None

        if app_key and app_secret:
            self._init_client()

    def _init_client(self):
        """初始化淘宝 SDK 客户端"""
        try:
            # import top.api  # 需要 pip install top-sdk
            self._connected = True
        except ImportError:
            self._connected = False

    @property
    def platform_name(self) -> str:
        return "taobao"

    # ── 订单 ──

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        """
        调用 taobao.trade.fullinfo.get
        文档: https://open.taobao.com/api.htm?apiId=54
        """
        if not self._connected:
            return None

        # TODO: 真实实现
        # req = top.api.TradeFullinfoGetRequest()
        # req.set_tid(order_id)
        # req.set_fields("tid,status,payment,total_fee,receiver_name,...")
        # resp = self._client.execute(req, self.session_key)
        # return self._parse_order(resp)
        raise NotImplementedError("需要配置淘宝 API 密钥并安装 top-sdk")

    async def get_user_orders(self, user_id: str) -> list[dict[str, Any]]:
        """
        调用 taobao.trades.sold.get
        文档: https://open.taobao.com/api.htm?apiId=46
        """
        # TODO: 真实实现
        raise NotImplementedError

    async def search_orders(self, keyword: str) -> list[dict[str, Any]]:
        # TODO: 调用 taobao.trades.sold.get + keyword filter
        raise NotImplementedError

    async def get_shipping_info(self, order_id: str) -> dict[str, Any] | None:
        """
        调用 taobao.logistics.trace.search
        文档: https://open.taobao.com/api.htm?apiId=254
        """
        # TODO: 真实实现
        raise NotImplementedError

    async def get_order_count(self) -> int:
        # TODO: 调用 taobao.trades.sold.get + 计数
        return 0

    # ── 产品 ──

    async def search_products(self, keyword: str) -> list[dict[str, Any]]:
        """
        调用 taobao.items.onsale.get
        文档: https://open.taobao.com/api.htm?apiId=18
        """
        # TODO: 真实实现
        raise NotImplementedError

    async def get_product(self, product_id: str) -> dict[str, Any] | None:
        """
        调用 taobao.item.get
        文档: https://open.taobao.com/api.htm?apiId=20
        """
        # TODO: 真实实现
        raise NotImplementedError

    async def recommend_products(self, preference: str) -> list[dict[str, Any]]:
        return await self.search_products(preference)

    # ── 状态 ──

    def is_connected(self) -> bool:
        return self._connected


# ── 环境变量加载 ──

def create_taobao_adapter_from_env() -> TaobaoAdapter | None:
    """从环境变量创建淘宝适配器"""
    import os

    app_key = os.getenv("TAOBAO_APP_KEY", "")
    app_secret = os.getenv("TAOBAO_APP_SECRET", "")
    session_key = os.getenv("TAOBAO_SESSION_KEY", "")

    if not app_key or not app_secret:
        return None

    return TaobaoAdapter(app_key, app_secret, session_key)
