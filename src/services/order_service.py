from typing import Optional, Dict, List
from datetime import datetime, timedelta
import random

from ..utils import get_mysql_client
from ..utils.logger import get_logger

logger = get_logger("order_service")


class OrderService:
    """
    订单服务 - 管理订单数据和状态
    
    功能：
    - 查询订单详情和状态
    - 订单搜索和过滤
    - 物流信息查询
    
    使用MySQL数据库存储订单信息
    """

    def __init__(self):
        self.mysql = get_mysql_client()
        self._mysql_available = self.mysql.is_connected()
        
        if self._mysql_available:
            logger.info("订单服务: 使用MySQL数据库")
            # 初始化测试数据
            self._init_test_data()
        else:
            logger.warning("订单服务: MySQL不可用，使用模拟数据")
            self.orders = self._load_mock_orders()

    def _load_mock_orders(self) -> List[Dict]:
        """加载模拟订单数据（MySQL不可用时使用）"""
        base_time = datetime.now()
        return [
            {
                "order_id": "202401150001",
                "user_id": "user_001",
                "status": "待发货",
                "total_amount": 8999.00,
                "created_at": (base_time - timedelta(days=2)).isoformat(),
                "items": [
                    {"product_id": 1, "product_name": "智能手机Pro Max", "quantity": 1, "price": 8999.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011500001",
                    "status": "待发货",
                    "location": "仓库准备中",
                    "estimated_delivery": "预计3-5个工作日"
                }
            },
            {
                "order_id": "202401140002",
                "user_id": "user_001",
                "status": "已发货",
                "total_amount": 2398.00,
                "created_at": (base_time - timedelta(days=3)).isoformat(),
                "items": [
                    {"product_id": 2, "product_name": "无线降噪耳机", "quantity": 1, "price": 1999.00},
                    {"product_id": 5, "product_name": "无线游戏鼠标", "quantity": 1, "price": 399.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011400002",
                    "status": "运输中",
                    "location": "上海市浦东新区转运中心",
                    "estimated_delivery": "2024-01-17"
                }
            },
            {
                "order_id": "202401130003",
                "user_id": "user_002",
                "status": "已完成",
                "total_amount": 3299.00,
                "created_at": (base_time - timedelta(days=10)).isoformat(),
                "items": [
                    {"product_id": 3, "product_name": "智能手表Series 8", "quantity": 1, "price": 3299.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011300003",
                    "status": "已签收",
                    "location": "北京市朝阳区",
                    "estimated_delivery": "已送达"
                }
            },
            {
                "order_id": "202401120004",
                "user_id": "user_001",
                "status": "待付款",
                "total_amount": 599.00,
                "created_at": (base_time - timedelta(days=1)).isoformat(),
                "items": [
                    {"product_id": 4, "product_name": "机械键盘RGB", "quantity": 1, "price": 599.00}
                ],
                "tracking_info": None
            }
        ]

    def _init_test_data(self):
        """初始化测试数据到MySQL"""
        test_orders = [
            {
                "order_id": "202401150001",
                "user_id": "user_001",
                "status": "待发货",
                "total_amount": 8999.00,
                "created_at": datetime.now() - timedelta(days=2),
                "items": [
                    {"product_id": 1, "product_name": "智能手机Pro Max", "quantity": 1, "price": 8999.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011500001",
                    "status": "待发货",
                    "location": "仓库准备中",
                    "estimated_delivery": "2024-01-20"
                }
            },
            {
                "order_id": "202401140002",
                "user_id": "user_001",
                "status": "已发货",
                "total_amount": 2398.00,
                "created_at": datetime.now() - timedelta(days=3),
                "items": [
                    {"product_id": 2, "product_name": "无线降噪耳机", "quantity": 1, "price": 1999.00},
                    {"product_id": 5, "product_name": "无线游戏鼠标", "quantity": 1, "price": 399.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011400002",
                    "status": "运输中",
                    "location": "上海市浦东新区转运中心",
                    "estimated_delivery": "2024-01-17"
                }
            },
            {
                "order_id": "202401130003",
                "user_id": "user_002",
                "status": "已完成",
                "total_amount": 3299.00,
                "created_at": datetime.now() - timedelta(days=10),
                "items": [
                    {"product_id": 3, "product_name": "智能手表Series 8", "quantity": 1, "price": 3299.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011300003",
                    "status": "已签收",
                    "location": "北京市朝阳区",
                    "estimated_delivery": "2024-01-15"
                }
            },
            {
                "order_id": "202401120004",
                "user_id": "user_001",
                "status": "待付款",
                "total_amount": 599.00,
                "created_at": datetime.now() - timedelta(days=1),
                "items": [
                    {"product_id": 4, "product_name": "机械键盘RGB", "quantity": 1, "price": 599.00}
                ],
                "tracking_info": None
            },
            # ========== 新增订单 ==========
            {
                "order_id": "202401110005",
                "user_id": "user_002",
                "status": "已完成",
                "total_amount": 1299.00,
                "created_at": datetime.now() - timedelta(days=15),
                "items": [
                    {"product_id": 6, "product_name": "平板电脑Air", "quantity": 1, "price": 1299.00}
                ],
                "tracking_info": {
                    "tracking_number": "JD2024011100005",
                    "status": "已签收",
                    "location": "广州市天河区",
                    "estimated_delivery": "2024-01-14"
                }
            },
            {
                "order_id": "202401100006",
                "user_id": "user_003",
                "status": "已发货",
                "total_amount": 4599.00,
                "created_at": datetime.now() - timedelta(days=5),
                "items": [
                    {"product_id": 7, "product_name": "笔记本电脑Pro", "quantity": 1, "price": 4599.00}
                ],
                "tracking_info": {
                    "tracking_number": "YT2024011000006",
                    "status": "运输中",
                    "location": "杭州市西湖区转运中心",
                    "estimated_delivery": "2024-01-18"
                }
            },
            {
                "order_id": "202401090007",
                "user_id": "user_003",
                "status": "待发货",
                "total_amount": 899.00,
                "created_at": datetime.now() - timedelta(days=2),
                "items": [
                    {"product_id": 8, "product_name": "蓝牙音箱Mini", "quantity": 1, "price": 299.00},
                    {"product_id": 9, "product_name": "USB-C扩展坞", "quantity": 1, "price": 600.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024010900007",
                    "status": "待发货",
                    "location": "深圳仓库",
                    "estimated_delivery": "预计3-5个工作日"
                }
            },
            {
                "order_id": "202401080008",
                "user_id": "user_004",
                "status": "已取消",
                "total_amount": 1999.00,
                "created_at": datetime.now() - timedelta(days=8),
                "items": [
                    {"product_id": 10, "product_name": "无线充电器套装", "quantity": 2, "price": 999.50}
                ],
                "tracking_info": None
            },
            {
                "order_id": "202401070009",
                "user_id": "user_004",
                "status": "已完成",
                "total_amount": 5999.00,
                "created_at": datetime.now() - timedelta(days=20),
                "items": [
                    {"product_id": 11, "product_name": "曲面显示器27寸", "quantity": 1, "price": 3999.00},
                    {"product_id": 12, "product_name": "人体工学椅", "quantity": 1, "price": 2000.00}
                ],
                "tracking_info": {
                    "tracking_number": "EMS2024010700009",
                    "status": "已签收",
                    "location": "成都市武侯区",
                    "estimated_delivery": "2024-01-10"
                }
            },
            {
                "order_id": "202401060010",
                "user_id": "user_005",
                "status": "待付款",
                "total_amount": 799.00,
                "created_at": datetime.now() - timedelta(days=1),
                "items": [
                    {"product_id": 13, "product_name": "游戏手柄Pro", "quantity": 1, "price": 499.00},
                    {"product_id": 14, "product_name": "耳机支架", "quantity": 1, "price": 300.00}
                ],
                "tracking_info": None
            },
            {
                "order_id": "202401050011",
                "user_id": "user_005",
                "status": "已发货",
                "total_amount": 1599.00,
                "created_at": datetime.now() - timedelta(days=4),
                "items": [
                    {"product_id": 15, "product_name": "电子书阅读器", "quantity": 1, "price": 1599.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024010500011",
                    "status": "派送中",
                    "location": "南京市玄武区",
                    "estimated_delivery": "2024-01-16"
                }
            },
            {
                "order_id": "202401040012",
                "user_id": "user_006",
                "status": "待发货",
                "total_amount": 2999.00,
                "created_at": datetime.now() - timedelta(days=2),
                "items": [
                    {"product_id": 16, "product_name": "智能投影仪", "quantity": 1, "price": 2999.00}
                ],
                "tracking_info": {
                    "tracking_number": "JD2024010400012",
                    "status": "待发货",
                    "location": "武汉仓库",
                    "estimated_delivery": "预计2-3个工作日"
                }
            },
            {
                "order_id": "202401030013",
                "user_id": "user_006",
                "status": "已完成",
                "total_amount": 459.00,
                "created_at": datetime.now() - timedelta(days=12),
                "items": [
                    {"product_id": 17, "product_name": "便携充电宝20000mAh", "quantity": 1, "price": 199.00},
                    {"product_id": 18, "product_name": "手机壳套装", "quantity": 1, "price": 260.00}
                ],
                "tracking_info": {
                    "tracking_number": "YT2024010300013",
                    "status": "已签收",
                    "location": "西安市雁塔区",
                    "estimated_delivery": "2024-01-06"
                }
            },
            {
                "order_id": "202401020014",
                "user_id": "user_007",
                "status": "已取消",
                "total_amount": 6999.00,
                "created_at": datetime.now() - timedelta(days=18),
                "items": [
                    {"product_id": 19, "product_name": "游戏主机X", "quantity": 1, "price": 6999.00}
                ],
                "tracking_info": None
            },
            {
                "order_id": "202401010015",
                "user_id": "user_007",
                "status": "已完成",
                "total_amount": 899.00,
                "created_at": datetime.now() - timedelta(days=25),
                "items": [
                    {"product_id": 20, "product_name": "网络摄像头", "quantity": 1, "price": 899.00}
                ],
                "tracking_info": {
                    "tracking_number": "EMS2024010100015",
                    "status": "已签收",
                    "location": "青岛市市南区",
                    "estimated_delivery": "2024-01-04"
                }
            },
            {
                "order_id": "202401160016",
                "user_id": "user_001",
                "status": "待付款",
                "total_amount": 12999.00,
                "created_at": datetime.now() - timedelta(hours=5),
                "items": [
                    {"product_id": 21, "product_name": "MacBook Pro 14寸", "quantity": 1, "price": 12999.00}
                ],
                "tracking_info": None
            },
            {
                "order_id": "202401170017",
                "user_id": "user_002",
                "status": "已发货",
                "total_amount": 159.00,
                "created_at": datetime.now() - timedelta(days=1),
                "items": [
                    {"product_id": 22, "product_name": "数据线套装", "quantity": 1, "price": 59.00},
                    {"product_id": 23, "product_name": "手机贴膜", "quantity": 2, "price": 50.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024011700017",
                    "status": "运输中",
                    "location": "重庆市渝北区",
                    "estimated_delivery": "2024-01-19"
                }
            },
            {
                "order_id": "202401180018",
                "user_id": "user_003",
                "status": "待发货",
                "total_amount": 3499.00,
                "created_at": datetime.now() - timedelta(days=1),
                "items": [
                    {"product_id": 24, "product_name": "无线吸尘器", "quantity": 1, "price": 3499.00}
                ],
                "tracking_info": {
                    "tracking_number": "JD2024011800018",
                    "status": "待发货",
                    "location": "苏州仓库",
                    "estimated_delivery": "预计2-3个工作日"
                }
            },
            {
                "order_id": "202401190019",
                "user_id": "user_008",
                "status": "已完成",
                "total_amount": 299.00,
                "created_at": datetime.now() - timedelta(days=7),
                "items": [
                    {"product_id": 25, "product_name": "便携蓝牙鼠标", "quantity": 1, "price": 299.00}
                ],
                "tracking_info": {
                    "tracking_number": "YT2024011900019",
                    "status": "已签收",
                    "location": "天津市和平区",
                    "estimated_delivery": "2024-01-14"
                }
            },
            {
                "order_id": "202401200020",
                "user_id": "user_008",
                "status": "已发货",
                "total_amount": 4599.00,
                "created_at": datetime.now() - timedelta(days=3),
                "items": [
                    {"product_id": 26, "product_name": "智能门锁", "quantity": 1, "price": 2999.00},
                    {"product_id": 27, "product_name": "智能门铃", "quantity": 1, "price": 1600.00}
                ],
                "tracking_info": {
                    "tracking_number": "SF2024012000020",
                    "status": "派送中",
                    "location": "郑州市金水区",
                    "estimated_delivery": "2024-01-18"
                }
            }
        ]

        for order in test_orders:
            # 检查订单是否已存在
            query = "SELECT COUNT(*) as count FROM orders WHERE order_id = %s"
            result = self.mysql.execute_query(query, (order["order_id"],))
            
            if result and result[0]["count"] == 0:
                # 插入订单
                now = datetime.now()
                insert_order = """
                INSERT INTO orders (order_id, user_id, status, total_amount, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                self.mysql.execute_update(insert_order, (
                    order["order_id"],
                    order["user_id"],
                    order["status"],
                    order["total_amount"],
                    order["created_at"],
                    now
                ))

                # 插入订单项
                for item in order["items"]:
                    insert_item = """
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    self.mysql.execute_update(insert_item, (
                        order["order_id"],
                        item["product_id"],
                        item["product_name"],
                        item["quantity"],
                        item["price"]
                    ))

                # 插入物流信息
                if order["tracking_info"]:
                    insert_tracking = """
                    INSERT INTO tracking_info (order_id, tracking_number, status, location, estimated_delivery, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    self.mysql.execute_update(insert_tracking, (
                        order["order_id"],
                        order["tracking_info"]["tracking_number"],
                        order["tracking_info"]["status"],
                        order["tracking_info"]["location"],
                        order["tracking_info"]["estimated_delivery"],
                        now
                    ))

        logger.info("测试数据初始化完成")

    async def get_order_details(self, order_id: str) -> Optional[str]:
        """
        根据订单号查询订单详情
        
        Args:
            order_id: 订单号
            
        Returns:
            订单详情字符串，如果未找到则返回None（表示订单不存在）
        """
        if self._mysql_available:
            return await self._get_order_details_mysql(order_id)
        else:
            return await self._get_order_details_mock(order_id)

    async def _get_order_details_mysql(self, order_id: str) -> Optional[str]:
        """从MySQL查询订单详情"""
        # 查询订单基本信息
        order_query = """
        SELECT * FROM orders WHERE order_id = %s
        """
        order_result = self.mysql.execute_query(order_query, (order_id,))
        
        if not order_result:
            # 订单不存在，返回None表示订单不存在
            return None

        order = order_result[0]

        # 查询订单项
        items_query = """
        SELECT * FROM order_items WHERE order_id = %s
        """
        items_result = self.mysql.execute_query(items_query, (order_id,))
        
        items_info = "\n".join([
            f"- {item['product_name']} x{item['quantity']} = ¥{item['price']}"
            for item in items_result
        ])

        # 查询物流信息
        tracking_query = """
        SELECT * FROM tracking_info WHERE order_id = %s
        """
        tracking_result = self.mysql.execute_query(tracking_query, (order_id,))
        
        tracking_info = "暂无物流信息"
        if tracking_result:
            tracking = tracking_result[0]
            estimated_delivery = tracking['estimated_delivery']
            if estimated_delivery:
                estimated_delivery = estimated_delivery.strftime('%Y-%m-%d')
            else:
                estimated_delivery = "暂无"
            
            tracking_info = f"""
物流单号：{tracking['tracking_number']}
物流状态：{tracking['status']}
当前位置：{tracking['location']}
预计送达：{estimated_delivery}
"""

        return f"""
订单号：{order['order_id']}
订单状态：{order['status']}
订单金额：¥{order['total_amount']:.2f}
下单时间：{order['created_at'].strftime('%Y-%m-%d %H:%M:%S')}

商品清单：
{items_info}

物流信息：
{tracking_info}
"""

    async def _get_order_details_mock(self, order_id: str) -> Optional[str]:
        """从模拟数据查询订单详情（MySQL不可用时使用）"""
        for order in self.orders:
            if order["order_id"] == order_id:
                items_info = "\n".join([
                    f"- {item['product_name']} x{item['quantity']} = ¥{item['price']}"
                    for item in order["items"]
                ])

                tracking_info = "暂无物流信息"
                if order["tracking_info"]:
                    tracking_info = f"""
物流单号：{order['tracking_info']['tracking_number']}
物流状态：{order['tracking_info']['status']}
当前位置：{order['tracking_info']['location']}
预计送达：{order['tracking_info']['estimated_delivery']}
"""

                return f"""
订单号：{order['order_id']}
订单状态：{order['status']}
订单金额：¥{order['total_amount']:.2f}
下单时间：{order['created_at']}

商品清单：
{items_info}

物流信息：
{tracking_info}
"""
        # 订单不存在
        return None

    async def get_order_count(self) -> int:
        """
        获取订单总数（用于验证MySQL连接）
        
        Returns:
            订单总数
        """
        if self._mysql_available:
            query = "SELECT COUNT(*) as count FROM orders"
            result = self.mysql.execute_query(query)
            if result:
                return result[0]["count"]
            return 0
        else:
            return len(self.orders)

    async def get_user_orders(self, user_id: str) -> List[Dict]:
        """
        查询用户的所有订单
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户订单列表
        """
        if self._mysql_available:
            query = """
            SELECT order_id, status, total_amount, created_at 
            FROM orders 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            """
            result = self.mysql.execute_query(query, (user_id,))
            return result if result else []
        else:
            return [
                {
                    "order_id": order["order_id"],
                    "status": order["status"],
                    "total_amount": order["total_amount"],
                    "created_at": order["created_at"]
                }
                for order in self.orders if order["user_id"] == user_id
            ]

    async def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单号
            new_status: 新状态
            
        Returns:
            更新是否成功
        """
        if self._mysql_available:
            query = """
            UPDATE orders 
            SET status = %s, updated_at = %s 
            WHERE order_id = %s
            """
            row_count = self.mysql.execute_update(query, (new_status, datetime.now(), order_id))
            return row_count > 0
        else:
            for order in self.orders:
                if order["order_id"] == order_id:
                    order["status"] = new_status
                    return True
            return False

    async def search_orders(self, keyword: str) -> List[Dict]:
        """
        搜索订单
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的订单列表
        """
        if self._mysql_available:
            query = """
            SELECT o.order_id, o.status, o.total_amount, o.created_at
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.order_id LIKE %s OR o.status LIKE %s OR oi.product_name LIKE %s
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
            """
            pattern = f"%{keyword}%"
            result = self.mysql.execute_query(query, (pattern, pattern, pattern))
            return result if result else []
        else:
            results = []
            for order in self.orders:
                if (keyword in order["order_id"] or
                    keyword in order["status"] or
                    any(keyword in item["product_name"] for item in order["items"])):
                    results.append({
                        "order_id": order["order_id"],
                        "status": order["status"],
                        "total_amount": order["total_amount"],
                        "created_at": order["created_at"]
                    })
            return results

    def is_mysql_available(self) -> bool:
        """检查MySQL是否可用"""
        return self._mysql_available