from .base import PlatformAdapter
from .mock_adapter import MockAdapter
from .taobao_adapter import TaobaoAdapter, create_taobao_adapter_from_env

_adapter: PlatformAdapter = None


def get_platform_adapter() -> PlatformAdapter:
    """获取当前平台适配器。优先淘宝，失败回退 Mock"""
    global _adapter
    if _adapter is None:
        taobao = create_taobao_adapter_from_env()
        _adapter = taobao if taobao and taobao.is_connected() else MockAdapter()
    return _adapter


def set_platform_adapter(adapter: PlatformAdapter):
    """运行时切换平台适配器"""
    global _adapter
    _adapter = adapter


__all__ = [
    "PlatformAdapter", "MockAdapter", "TaobaoAdapter",
    "get_platform_adapter", "set_platform_adapter",
    "create_taobao_adapter_from_env",
]
