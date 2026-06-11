"""
Agent 工具集 — 异步版本，匹配实际 Service API
"""

from langchain_core.tools import tool


@tool
async def query_order(order_id: str) -> str:
    """查询订单详情（含商品和物流）。当用户询问某个订单时使用。"""
    from ..services import OrderService
    service = OrderService()
    result = await service.get_order_details(order_id)
    return result or f"未找到订单 {order_id}"


@tool
async def list_user_orders(user_id: str = "") -> str:
    """查询用户的所有订单列表。当用户问"我的订单"时使用。"""
    from ..services import OrderService
    service = OrderService()
    orders = await service.get_user_orders(user_id or "user_001")
    if not orders:
        return "暂无订单记录"
    lines = ["您的订单:"]
    for o in orders[:10]:
        lines.append(
            f"  {o.get('order_id')} | {o.get('status')} | ¥{o.get('total_amount', 0)}"
        )
    return "\n".join(lines)


@tool
async def search_orders(keyword: str) -> str:
    """搜索订单。当用户用关键词查找订单时使用。"""
    from ..services import OrderService
    service = OrderService()
    results = await service.search_orders(keyword)
    if not results:
        return f"未找到包含'{keyword}'的订单"
    lines = [f"搜索'{keyword}':"]
    for o in results[:10]:
        lines.append(f"  {o.get('order_id')} | {o.get('status')}")
    return "\n".join(lines)


@tool
async def search_product(query: str) -> str:
    """搜索产品。当用户询问某类产品的价格、推荐时使用。"""
    from ..services import ProductService
    service = ProductService()
    results = await service.search_products(query)
    if not results:
        return f"未找到'{query}'相关产品"
    lines = [f"搜索'{query}':"]
    for p in results[:5]:
        lines.append(f"  {p.get('name')} | ¥{p.get('price', 0)} | {p.get('description', '')[:40]}")
    return "\n".join(lines)


@tool
async def get_product_detail(product_name: str) -> str:
    """获取产品详细信息。当用户询问某款具体产品的参数时使用。"""
    from ..services import ProductService
    service = ProductService()
    p = await service.get_product_details(product_name)
    return str(p) if p else f"未找到产品 {product_name}"


@tool
async def search_knowledge(query: str) -> str:
    """搜索知识库。当用户问退货政策、售后流程等通用问题时使用。"""
    from ..services import KnowledgeBase
    kb = KnowledgeBase()
    results = await kb.search(query)
    return "\n\n".join(results[:3]) if results else "知识库暂无相关信息"


ORDER_TOOLS = [query_order, list_user_orders, search_orders]
PRODUCT_TOOLS = [search_product, get_product_detail]
SERVICE_TOOLS = [search_knowledge]
