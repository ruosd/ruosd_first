"""
测试数据填充脚本

用法:
  docker-compose exec web python scripts/seed_data.py
"""

import sys, os, time, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USERS = [
    {"username": "zhangsan", "email": "zhangsan@a.com", "password": "123456", "nickname": "张三", "phone": "13800001111"},
    {"username": "lisi", "email": "lisi@a.com", "password": "123456", "nickname": "李四", "phone": "13800002222"},
    {"username": "wangwu", "email": "wangwu@a.com", "password": "123456", "nickname": "王五", "phone": "13800003333"},
]

PRODUCTS = [
    (1, "iPhone 15 Pro Max", 9999),
    (2, "华为Mate 60 Pro", 6999),
    (3, "小米14 Pro", 4999),
    (4, "MacBook Air M2", 7999),
    (5, "联想ThinkPad X1", 9999),
    (6, "AirPods Pro 2", 1899),
    (7, "华为FreeBuds Pro 3", 1499),
    (8, "Apple Watch S9", 3199),
    (9, "格力空调 KFR-35GW", 3299),
    (10, "海尔冰箱 BCD-500", 4999),
]


def generate_orders():
    now = datetime.now()
    statuses = ["待付款", "待发货", "已发货", "已送达", "已完成", "退款中", "已退款"]
    companies = ["顺丰速运", "京东物流", "中通快递", "圆通速递", "韵达快递"]

    orders = []
    items = []
    trackings = []

    for i in range(1, 21):
        user = random.choice(USERS)
        product = random.choice(PRODUCTS)
        status = random.choice(statuses)
        qty = random.randint(1, 2)
        amount = product[2] * qty

        order_id = f"TEST{now.strftime('%Y%m%d')}{i:04d}"
        days_ago = random.randint(0, 30)
        created = now - timedelta(days=days_ago)

        orders.append((
            order_id, user["username"], status, amount,
            created.strftime("%Y-%m-%d %H:%M:%S"),
            created.strftime("%Y-%m-%d %H:%M:%S"),
        ))

        items.append((
            order_id, product[0], product[1], qty, product[2],
        ))

        if status in ("已发货", "已送达", "已完成"):
            comp = random.choice(companies)
            trackings.append((
                order_id,
                f"{comp[:2].upper()}{random.randint(10000000, 99999999)}",
                "已签收" if status in ("已送达", "已完成") else "运输中",
                random.choice(["上海转运中心", "北京分拨中心", "广州集散中心", "杭州中转部"]),
                (now + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ))

    return orders, items, trackings


def seed():
    print("=" * 50)
    print("  填充测试数据")
    print("=" * 50)

    # 1. 等待 MySQL 就绪
    print("\n[0/3] 等待 MySQL 就绪...")
    from src.utils.mysql_client import get_mysql_client
    for i in range(30):
        mysql = get_mysql_client()
        if mysql.is_connected():
            print("  ✅ MySQL 连接成功")
            break
        if i < 29:
            time.sleep(2)
    else:
        print("  ❌ MySQL 连接超时，退出")
        return

    # 2. 用户
    print("\n[1/3] 注册测试用户...")
    from src.services import get_user_service
    user_svc = get_user_service()
    for u in USERS:
        user, err = user_svc.register_user(u["username"], u["email"], u["password"], u["nickname"], u["phone"])
        if err:
            print(f"  ❌ {u['username']}: {err}")
        else:
            print(f"  ✅ {u['username']}")

    # 3. 产品
    print("\n[2/4] 同步产品数据...")
    from src.services import ProductService
    ps = ProductService()
    product_count = len(ps.get_all_products())
    print(f"  ✅ {product_count} 个产品已就绪")

    # 4. 订单
    print("\n[3/4] 生成订单...")
    from src.utils.mysql_client import get_mysql_client
    mysql = get_mysql_client()

    if mysql.is_connected():
        orders, items, trackings = generate_orders()

        count = 0
        for o in orders:
            mysql.execute_update(
                "INSERT IGNORE INTO orders (order_id, user_id, status, total_amount, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                o,
            )
            count += 1

        for it in items:
            mysql.execute_update(
                "INSERT IGNORE INTO order_items (order_id, product_id, product_name, quantity, price) VALUES (%s, %s, %s, %s, %s)",
                it,
            )

        for tr in trackings:
            mysql.execute_update(
                "INSERT IGNORE INTO tracking_info (order_id, tracking_number, status, location, estimated_delivery, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
                tr,
            )

        print(f"  ✅ {count} 条订单 + {len(items)} 条商品 + {len(trackings)} 条物流")
    else:
        print("  ⚠️  MySQL 不可用，跳过")

    # 4. 总结
    print(f"\n{'=' * 50}")
    print("  完成！")
    print(f"  - {product_count} 个产品")
    print(f"  测试账号: {USERS[0]['username']} / {USERS[0]['password']}")
    print(f"  管理员:   admin / admin123")
    print("=" * 50)


if __name__ == "__main__":
    seed()
