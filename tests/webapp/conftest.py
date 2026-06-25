"""webapp 测试公共 fixture：TestClient、临时数据目录。"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import webapp.paths as paths_mod


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """每个测试一个干净的数据目录。"""
    paths_mod.set_data_dir(tmp_path)
    # 强制 database.py 用临时 SQLite
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'tsn_data.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
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
