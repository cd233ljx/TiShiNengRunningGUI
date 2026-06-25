"""更新人脸：把现有 main.py update_face_images 的核心包成端点。"""
from unittest.mock import AsyncMock, patch

from tests.webapp.conftest import wait_for_task_done


def _seed_account(client, api_token):
    """同 test_run.py 的种子，复制以保持各测试文件自闭。"""
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 333, "school_name": "FaceX", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "F333"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        r = client.post("/api/schools/refresh", headers={"X-API-Token": api_token})
        wait_for_task_done(client, api_token, r.json()["task_id"])

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id="333:u", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return "333:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 333, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_face_update_success(client, api_token):
    account_id = _seed_account(client, api_token)
    with patch("webapp.routers.face.TsnRunServer.getFaceImage",
               new=AsyncMock(return_value=b"fake-image-bytes")), \
         patch("webapp.routers.face.getTsnClientById",
               new=AsyncMock(return_value=AsyncMock(isPublic=lambda: False))):
        resp = client.post("/api/face/update",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


def test_face_update_no_account_returns_404(client, api_token):
    resp = client.post("/api/face/update",
                       headers={"X-API-Token": api_token},
                       json={"account_id": 99999})
    assert resp.status_code == 404
    assert resp.json()["code"] == "ACCOUNT_NOT_FOUND"
    assert resp.json()["msg"] == "账号不存在"
