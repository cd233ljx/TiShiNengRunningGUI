"""bootstrap 端点：token 校验最小用例。"""


def test_bootstrap_without_token_returns_401(client):
    resp = client.get("/api/bootstrap")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["code"] == "BAD_TOKEN"


def test_bootstrap_with_wrong_token_returns_401(client):
    resp = client.get("/api/bootstrap", headers={"X-API-Token": "wrong"})
    assert resp.status_code == 401


def test_bootstrap_with_correct_token_returns_200(client, api_token):
    resp = client.get("/api/bootstrap", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_root_serves_index_html(client, tmp_data_dir, monkeypatch):
    """根路径 / 应返回 frontend/index.html。"""
    # 简单造一个 index.html
    import webapp.paths as paths_mod
    frontend = paths_mod.project_root() / "frontend"
    # 测试环境用真实仓库的 frontend；若不存在则跳过
    if not (frontend / "index.html").exists():
        import pytest
        pytest.skip("frontend/index.html 尚未创建")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
