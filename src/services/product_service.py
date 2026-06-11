from typing import Optional, Dict, List
import json
from ..utils import get_mysql_client
from ..utils.logger import get_logger

logger = get_logger("product_service")


class ProductService:
    """
    产品服务 - 管理产品数据和推荐

    功能：
    - 查询产品详细信息
    - 产品搜索和过滤
    - 产品推荐算法
    """

    def __init__(self):
        self.products = self._load_from_mysql() or self._load_mock_products()

    def _load_from_mysql(self) -> Optional[List[Dict]]:
        """从 MySQL 加载产品数据，表为空时返回 None"""
        try:
            mysql = get_mysql_client()
            if not mysql.is_connected():
                return None
            rows = mysql.execute_query(
                "SELECT id, name, description, price, stock, category, specifications FROM products ORDER BY id"
            )
            if not rows:
                return self._seed_mysql(mysql)
            products = []
            for r in rows:
                spec = r.get("specifications")
                products.append({
                    "id": r["id"],
                    "name": r["name"],
                    "description": r.get("description", ""),
                    "price": float(r["price"]),
                    "stock": r.get("stock", 0),
                    "category": r.get("category", ""),
                    "specifications": json.loads(spec) if isinstance(spec, str) else (spec or {}),
                })
            logger.info(f"从MySQL加载了{len(products)}个产品")
            return products
        except Exception as e:
            logger.warning(f"从MySQL加载产品失败: {e}")
            return None

    def _seed_mysql(self, mysql) -> Optional[List[Dict]]:
        """首次初始化时把模拟数据写入 MySQL"""
        mock = self._load_mock_products()
        for p in mock:
            mysql.execute_update(
                "INSERT IGNORE INTO products (id, name, description, price, stock, category, specifications) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (p["id"], p["name"], p["description"], p["price"], p["stock"], p["category"], json.dumps(p["specifications"], ensure_ascii=False)),
            )
        logger.info(f"已将{len(mock)}个模拟产品写入MySQL")
        return mock

    def _load_mock_products(self) -> List[Dict]:
        """加载模拟产品数据"""
        return [
            {
                "id": 1,
                "name": "智能手机Pro Max",
                "description": "6.7英寸超视网膜XDR显示屏，A17仿生芯片，三摄像头系统",
                "price": 8999,
                "stock": 150,
                "category": "电子产品",
                "specifications": {
                    "屏幕": "6.7英寸OLED",
                    "处理器": "A17仿生",
                    "内存": "8GB",
                    "存储": "256GB",
                    "电池": "4500mAh"
                }
            },
            {
                "id": 2,
                "name": "无线降噪耳机",
                "description": "主动降噪，30小时续航，舒适佩戴",
                "price": 1999,
                "stock": 300,
                "category": "电子产品",
                "specifications": {
                    "类型": "头戴式",
                    "降噪": "主动降噪",
                    "续航": "30小时",
                    "连接": "蓝牙5.0"
                }
            },
            {
                "id": 3,
                "name": "智能手表Series 8",
                "description": "健康监测，运动追踪，防水设计",
                "price": 3299,
                "stock": 200,
                "category": "电子产品",
                "specifications": {
                    "屏幕": "1.9英寸",
                    "防水": "IP68",
                    "续航": "18小时",
                    "传感器": "心率、血氧"
                }
            },
            {
                "id": 4,
                "name": "机械键盘RGB",
                "description": "青轴机械键盘，RGB背光，全键无冲",
                "price": 599,
                "stock": 500,
                "category": "电脑配件",
                "specifications": {
                    "轴体": "青轴",
                    "背光": "RGB",
                    "连接": "USB-C",
                    "尺寸": "标准104键"
                }
            },
            {
                "id": 5,
                "name": "无线游戏鼠标",
                "description": "16000DPI，可调节重量，RGB灯效",
                "price": 399,
                "stock": 450,
                "category": "电脑配件",
                "specifications": {
                    "DPI": "16000",
                    "按键": "7个",
                    "续航": "70小时",
                    "重量": "可调节"
                }
            }
        ]

    async def get_product_details(self, product_name: str) -> Optional[Dict]:
        """
        根据产品名称查询产品详情

        Args:
            product_name: 产品名称或关键词

        Returns:
            产品详情字典，如果未找到则返回None
        """
        for product in self.products:
            if product_name.lower() in product["name"].lower():
                return {
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"],
                    "price": product["price"],
                    "stock": product["stock"],
                    "category": product["category"],
                    "specifications": json.dumps(product["specifications"], ensure_ascii=False, indent=2)
                }
        return None

    async def search_products(self, keyword: str) -> List[Dict]:
        """
        搜索产品

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的产品列表
        """
        results = []
        for product in self.products:
            if (keyword.lower() in product["name"].lower() or
                keyword.lower() in product["description"].lower()):
                results.append({
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"],
                    "price": product["price"],
                    "stock": product["stock"]
                })
        return results

    async def recommend_products(self, product_id: int, limit: int = 3) -> List[Dict]:
        """
        推荐相关产品

        Args:
            product_id: 产品ID
            limit: 推荐数量限制

        Returns:
            推荐产品列表
        """
        current_product = None
        for product in self.products:
            if product["id"] == product_id:
                current_product = product
                break

        if not current_product:
            return []

        recommendations = []
        for product in self.products:
            if (product["category"] == current_product["category"] and
                product["id"] != product_id):
                recommendations.append({
                    "id": product["id"],
                    "name": product["name"],
                    "description": product["description"],
                    "price": product["price"]
                })
                if len(recommendations) >= limit:
                    break

        return recommendations

    def get_all_products(self) -> List[Dict]:
        """获取所有产品列表"""
        return self.products
