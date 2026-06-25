"""里程查询：复用 main.py:495-650 的查询逻辑，但拍平成单端点。"""
from unittest.mock import AsyncMock, MagicMock, patch


def _seed_account(client, api_token, sys_type="2", school_id=555, school_name="Dist校"):
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": school_id, "school_name": school_name, "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": sys_type, "schoolCode": f"D{school_id}"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id=f"{school_id}:{username}", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return f"{school_id}:{username}"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": school_id, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_distance_query_public(client, api_token):
    account_id = _seed_account(client, api_token)
    fake_client = MagicMock()
    fake_client.isPublic.return_value = True
    fake_client.sumExerciseRecord = AsyncMock(return_value={
        "sportRange": "12.34", "sportTimes": "5"
    })
    with patch("webapp.routers.distance.getTsnClientById",
               new=AsyncMock(return_value=fake_client)):
        resp = client.post("/api/distance/query",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_km"] == 12.34
    assert body["count"] == 5
    assert body["school_name"] == "Dist校"
    assert body["username"] == "u"
    fake_client.sumExerciseRecord.assert_awaited_once()


def test_distance_query_private(client, api_token):
    account_id = _seed_account(client, api_token, sys_type="1", school_id=556, school_name="Private校")
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.sumSportRecord = AsyncMock(return_value={
        "sportRange": "7.89", "sportTimes": "3"
    })
    with patch("webapp.routers.distance.getTsnClientById",
               new=AsyncMock(return_value=fake_client)):
        resp = client.post("/api/distance/query",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_km"] == 7.89
    assert body["count"] == 3
    fake_client.sumSportRecord.assert_awaited_once()


def test_distance_query_missing_account_returns_404(client, api_token):
    resp = client.post("/api/distance/query",
                       headers={"X-API-Token": api_token},
                       json={"account_id": 99999})
    assert resp.status_code == 404
    assert resp.json() == {"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"}
