"""账号 CRUD + 授权端点测试。"""
from unittest.mock import AsyncMock, patch

from tests.webapp.conftest import wait_for_task_done


def _seed_school(client, api_token, monkeypatch):
    """辅助：插入一所测试学校。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "X"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 111, "school_name": "种子学校",
                  "school_url": "https://s.example.com", "openId": "o1",
                  "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "S111"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        r = client.post("/api/schools/refresh", headers={"X-API-Token": api_token})
        wait_for_task_done(client, api_token, r.json()["task_id"])


def test_list_accounts_empty(client, api_token):
    resp = client.get("/api/accounts", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_authorize_success(client, api_token, monkeypatch):
    _seed_school(client, api_token, monkeypatch)
    # mock 掉 tsnPasswordAuthServer
    async def fake_auth(school_id, username, password, session):
        # 模拟在 DB 里加一条账号
        from models import TsnAccount_Model
        acct = TsnAccount_Model(
            student_id="s1", user_id="111:u1", school_id=school_id,
            username=username, password=password,
            mobile_device_id="dev", access_token="tk",
            refresh_token="rt", expires_in=86399,
        )
        session.add(acct)
        await session.flush()
        return f"{school_id}:u1"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        resp = client.post("/api/accounts/authorize",
                           headers={"X-API-Token": api_token},
                           json={"school_id": 111, "username": "alice", "password": "pw"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "alice"
    assert body["school_id"] == 111


def test_authorize_wrong_password_returns_400(client, api_token, monkeypatch):
    _seed_school(client, api_token, monkeypatch)
    from TiShiNengError import TiShiNengError

    async def fake_auth(school_id, username, password, session):
        raise TiShiNengError("密码错误", code=10002)

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        resp = client.post("/api/accounts/authorize",
                           headers={"X-API-Token": api_token},
                           json={"school_id": 111, "username": "alice", "password": "bad"})

    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "10002"
    assert "密码" in body["msg"]


def test_delete_account(client, api_token, monkeypatch):
    """删除账号：先 seed 一条，然后 DELETE 应返回 200 并真正消失。"""
    _seed_school(client, api_token, monkeypatch)

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        acct = TsnAccount_Model(
            student_id="s", user_id="111:u2", school_id=school_id,
            username=username, password=password,
            mobile_device_id="d", access_token="tk",
            refresh_token="rt", expires_in=1,
        )
        session.add(acct)
        await session.flush()
        return f"{school_id}:u2"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 111, "username": "bob", "password": "pw"})
        account_id = r.json()["account_id"]

    # 删除
    resp = client.delete(f"/api/accounts/{account_id}",
                         headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    # 验证消失
    resp = client.get("/api/accounts", headers={"X-API-Token": api_token})
    assert all(a["id"] != account_id for a in resp.json()["items"])


def test_delete_nonexistent_returns_404(client, api_token):
    resp = client.delete("/api/accounts/99999",
                         headers={"X-API-Token": api_token})
    assert resp.status_code == 404
