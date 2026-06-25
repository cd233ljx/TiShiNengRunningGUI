"""路径爬取路由测试。startSpider 已在 Phase 1 改为支持 callback；这里只需测端点能立即返回 task_id。"""
from unittest.mock import AsyncMock, patch

from tests.webapp.conftest import wait_for_task_done


def _seed_account(client, api_token):
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 444, "school_name": "Spider校", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "P444"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        r = client.post("/api/schools/refresh", headers={"X-API-Token": api_token})
        wait_for_task_done(client, api_token, r.json()["task_id"])

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id="444:u", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return "444:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 444, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_spider_start_returns_task_id(client, api_token):
    account_id = _seed_account(client, api_token)

    async def fake_spider(account_id, progress_callback=None):
        if progress_callback:
            progress_callback({"phase": "crawling", "current": 1})

    with patch("webapp.routers.spider.startSpider", new=fake_spider):
        resp = client.post("/api/spider/start",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    assert "task_id" in resp.json()
