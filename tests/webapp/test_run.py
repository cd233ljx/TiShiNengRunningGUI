"""跑步路由测试：start → 立即返回 task_id；cancel → 终止；WS 推送 done。"""
import json
import threading
from unittest.mock import AsyncMock, patch

from tests.webapp.conftest import wait_for_task_done


def _seed_account(client, api_token, monkeypatch):
    """种一个学校 + 一个账号，返回 account_id。"""
    from unittest.mock import AsyncMock as _AM
    fake_tsn = _AM()
    fake_tsn.findAllProvince = _AM(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake_tsn.listSchoolByProvinceId = _AM(return_value={
        "data": [{"school_id": 222, "school_name": "Run校", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "R222"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        r = client.post("/api/schools/refresh", headers={"X-API-Token": api_token})
        wait_for_task_done(client, api_token, r.json()["task_id"])

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(
            student_id="s", user_id="222:u", school_id=school_id,
            username=username, password=password, mobile_device_id="d",
            access_token="tk", refresh_token="rt", expires_in=1)
        session.add(a)
        await session.flush()
        return "222:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 222, "username": "runner", "password": "p"})
        return r.json()["account_id"]


def test_run_start_returns_task_id_immediately(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)

    # 让 TsnRunServer.startRunHandle 立刻返回 — 验证 start 端点不阻塞
    async def fake_start(self):
        return None

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=fake_start):
        resp = client.post("/api/run/start",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id, "run_type": "freedom",
                                 "distance_km": 0.5})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "task_id" in body
    assert len(body["task_id"]) > 0


def test_run_start_validates_run_type(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)
    resp = client.post("/api/run/start",
                       headers={"X-API-Token": api_token},
                       json={"account_id": account_id, "run_type": "invalid",
                             "distance_km": 0.5})
    assert resp.status_code == 422


def test_run_start_distance_must_be_positive(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)
    resp = client.post("/api/run/start",
                       headers={"X-API-Token": api_token},
                       json={"account_id": account_id, "run_type": "freedom",
                             "distance_km": -1.0})
    assert resp.status_code == 422


def test_run_cancel_terminates_task(client, api_token, monkeypatch):
    """start → cancel：取消应导致后台任务被 cancel。"""
    account_id = _seed_account(client, api_token, monkeypatch)
    started = threading.Event()
    cancelled = threading.Event()

    async def slow_run(self):
        try:
            started.set()
            import asyncio as _aio
            await _aio.sleep(60)
        except BaseException:
            cancelled.set()
            raise

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=slow_run):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        # 等待后台真的开始
        assert started.wait(2.0), "后台任务未启动"

        # 取消
        c = client.post("/api/run/cancel",
                        headers={"X-API-Token": api_token},
                        json={"task_id": task_id})
        assert c.status_code == 200

    # 等 cancel 落地
    assert cancelled.wait(2.0), "后台任务未收到 CancelledError"


def test_ws_progress_streams_events_until_done(client, api_token, monkeypatch):
    """WebSocket：start 后连上 /ws/progress?task=...，应收到 done 事件。"""
    account_id = _seed_account(client, api_token, monkeypatch)

    async def emitting_run(self):
        import asyncio as _aio
        await _aio.sleep(0.1)  # 让 WS 先订阅上
        self._emit("preparing", msg="x")
        self._emit("running", elapsed_s=1, total_s=1, distance_km=0.1)

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=emitting_run):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        with client.websocket_connect(
                f"/ws/progress?task={task_id}&token={api_token}") as ws:
            phases = []
            for _ in range(10):
                msg = ws.receive_text()
                evt = json.loads(msg)
                phases.append(evt["phase"])
                if evt["phase"] in ("done", "error", "cancelled"):
                    break
            assert "done" in phases or "error" in phases, f"phases={phases}"


def test_ws_progress_rejects_bad_token(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)

    async def _noop(self):
        return None

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=_noop):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        import pytest
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                    f"/ws/progress?task={task_id}&token=WRONG") as ws:
                ws.receive_text()
