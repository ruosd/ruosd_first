"""
CI 兼容测试 — 可在本地和 CI 环境运行
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_python_syntax():
    """验证所有 Python 源码语法正确"""
    import ast

    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    errors = []
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, encoding="utf-8") as fh:
                        ast.parse(fh.read())
                except SyntaxError as e:
                    errors.append(f"{path}:{e.lineno} - {e.msg}")
    assert errors == [], f"Syntax errors found:\n" + "\n".join(errors)


def test_no_print_in_src():
    """验证 src/ 中无裸 print() 调用（应使用 logger）"""
    import re

    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    violations = []
    print_pattern = re.compile(r"\bprint\(")
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if print_pattern.search(line):
                            # 排除 logger.info/error 等正常调用行中的巧合匹配
                            if "logger." not in line and "def " not in line:
                                violations.append(f"{path}:{lineno}: {line.strip()}")
    assert violations == [], f"print() found:\n" + "\n".join(violations)


def test_models_import():
    """验证数据模型可独立导入"""
    from src.models.user import User
    from src.models.product import Product
    from src.models.order import Order

    u = User(id=1, username="test", email="t@t.com")
    assert u.username == "test"
    assert u.is_admin() is False

    admin = User(id=2, username="admin", email="a@t.com", role="admin")
    assert admin.is_admin() is True

    p = Product(id=1, name="Test", description="A test product", price=99.9, stock=10, category="test")
    assert p.name == "Test"

    from src.models.order import Order, OrderStatus
    o = Order(
        order_id="TEST001",
        user_id="user_001",
        status=OrderStatus.PENDING_PAYMENT,
        total_amount=99.9,
        items=[{"product_id": 1, "product_name": "Test", "quantity": 1, "price": 99.9}],
    )
    assert o.status == OrderStatus.PENDING_PAYMENT


def test_password_utils():
    """验证密码哈希和验证"""
    from src.utils.password import hash_password, verify_password

    pw = "test_password_123"
    hashed = hash_password(pw)

    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_requirements_file():
    """验证 requirements.txt 格式正确"""
    req_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
    with open(req_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    assert len(lines) > 0, "requirements.txt is empty"
    # 验证无重复包名
    from collections import Counter

    names = [l.split("==")[0].split(">=")[0].split("<=")[0].strip() for l in lines]
    duplicates = [n for n, c in Counter(names).items() if c > 1]
    assert duplicates == [], f"Duplicate packages: {duplicates}"


def test_env_example():
    """验证 .env.example 包含必要的配置项"""
    env_example = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    with open(env_example, encoding="utf-8") as f:
        content = f.read()

    required = [
        "JWT_SECRET_KEY",
        "ALIYUN_API_KEY",
        "REDIS_HOST",
        "MYSQL_HOST",
    ]
    for key in required:
        assert key in content, f"Missing {key} in .env.example"


def test_gitignore():
    """验证 .gitignore 包含关键排除项"""
    gitignore = os.path.join(os.path.dirname(__file__), "..", ".gitignore")
    with open(gitignore, encoding="utf-8") as f:
        content = f.read()

    required = [".env", "__pycache__", "node_modules", "data/"]
    for entry in required:
        assert entry in content, f"Missing {entry} in .gitignore"
