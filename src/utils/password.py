"""
密码工具模块 — 统一密码哈希和验证

原理说明:
  bcrypt 是专门为密码存储设计的哈希算法，特点：
  1. 自动加盐 — 每次 hash 结果不同，即使相同密码
  2. 故意慢 — 12 轮迭代约需 0.3 秒，暴力破解成本极高
  3. 抗 GPU — 算法结构让 GPU 并行加速无效

使用方式:
  from src.utils.password import hash_password, verify_password

  hashed = hash_password("mypassword")    # 生成 bcrypt 哈希
  is_valid = verify_password("mypassword", hashed)  # 验证密码
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    对密码进行 bcrypt 哈希

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希字符串 (包含盐值)
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)  # 12 轮迭代，平衡安全性和性能
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码是否匹配哈希

    Args:
        password: 用户输入的明文密码
        hashed: 数据库中存储的 bcrypt 哈希

    Returns:
        是否匹配
    """
    password_bytes = password.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
