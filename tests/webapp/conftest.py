"""webapp 测试公共 fixture：TestClient、临时数据目录。"""
import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import webapp.paths as paths_mod


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """每个测试一个干净的数据目录。

    注意：database.py 在 import 时已根据 DATABASE_URL 创建了模块级 engine，
    后续 setenv 无法替换该 engine；因此每个测试只能 drop_all + create_all
    复用共享 engine 来真正隔离数据。
    """
    paths_mod.set_data_dir(tmp_path)
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'tsn_data.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # 真清空共享 engine 上的全部数据
    from database import Base, engine
    import models  # noqa: F401 - 确保所有 ORM 模型注册到 Base.metadata

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())

    yield tmp_path
    paths_mod.set_data_dir(None)


@pytest.fixture
def api_token() -> str:
    return "test-token-12345"


@pytest.fixture
def client(tmp_data_dir, api_token):
    """构建 FastAPI TestClient，注入固定 token。"""
    from webapp.server import create_app
    app = create_app(api_token=api_token)
    with TestClient(app) as c:
        yield c
