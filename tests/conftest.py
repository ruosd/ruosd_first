import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mock_package(name):
    """递归创建 mock 模块，支持子包导入 (如 chromadb.config)"""
    parts = name.split(".")
    for i in range(len(parts)):
        parent = ".".join(parts[: i + 1])
        if parent not in sys.modules:
            sys.modules[parent] = MagicMock()


# 本地缺失的全部外部依赖
_missing = [
    "mysql",
    "mysql.connector",
    "slowapi",
    "slowapi.util",
    "slowapi.errors",
    "langchain",
    "langchain.schema",
    "langchain_openai",
    "langchain_community",
    "langgraph",
    "chromadb",
    "chromadb.config",
    "chromadb.api",
    "chromadb.utils",
    "ollama",
    "prometheus_fastapi_instrumentator",
    "prometheus_client",
    "celery",
    "pypdf",
    "pdfplumber",
    "python_docx",
    "tiktoken",
    "aiohttp",
    "redis",
]
for mod in _missing:
    _mock_package(mod)

# 为 slowapi.errors 补充 RateLimitExceeded
import types
if "slowapi.errors" in sys.modules:
    sys.modules["slowapi.errors"].RateLimitExceeded = type(
        "RateLimitExceeded", (Exception,), {}
    )

# 为 celery 补充 Celery 类
if "celery" in sys.modules:
    sys.modules["celery"].Celery = MagicMock()

import pytest


class FakeRedis:
    def __init__(self):
        self._data = {}

    def ping(self):
        return True

    def set(self, key, value, ex=None):
        self._data[key] = value
        return True

    def get(self, key):
        return self._data.get(key)

    def delete(self, key):
        return self._data.pop(key, None) is not None

    def exists(self, key):
        return key in self._data

    def expire(self, key, seconds):
        return key in self._data

    def hset(self, name, key, value):
        return 1

    def hget(self, name, key):
        return None

    def hgetall(self, name):
        return {}

    def sadd(self, key, value):
        return 1

    def smembers(self, key):
        return set()

    def setex(self, key, ttl, value):
        self._data[key] = value
        return True

    def close(self):
        pass

    def scan_iter(self, pattern=None):
        return iter([])


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    def fake_connect(self):
        self._connection = FakeRedis()

    def fake_get_connection(self):
        if not hasattr(self, "_connection") or self._connection is None:
            self._connection = FakeRedis()
        return self._connection

    monkeypatch.setattr(
        "src.utils.redis_client.RedisClient._connect",
        fake_connect,
    )
    monkeypatch.setattr(
        "src.utils.redis_client.RedisClient.get_connection",
        fake_get_connection,
    )


@pytest.fixture
def sample_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "test123456",
    }
