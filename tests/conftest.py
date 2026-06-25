"""pytest 共享配置。开启 asyncio 自动模式，集中管理事件循环作用域。"""
import pytest


# 让 pytest-asyncio 自动识别 async 测试，无需每个用例标 @pytest.mark.asyncio
def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("asyncio"):
            continue
        if item.function.__code__.co_flags & 0x100:  # CO_COROUTINE
            item.add_marker(pytest.mark.asyncio)
