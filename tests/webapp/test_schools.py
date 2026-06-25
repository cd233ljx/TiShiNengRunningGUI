"""学校列表/刷新端点测试。外部 HTTP 全 mock。"""
from unittest.mock import AsyncMock, patch

from tests.webapp.conftest import wait_for_task_done


def test_list_schools_empty(client, api_token):
    """没有学校时返回空数组。"""
    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_refresh_schools_calls_sdk_and_persists(client, api_token, monkeypatch):
    """触发刷新：mock 掉 SDK，等异步任务结束，确认学校落库。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "北京"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{
            "school_id": 101, "school_name": "测试大学",
            "school_url": "https://example.com", "openId": "open-1",
            "isOpenKeep": "1", "isOpenLive": "0", "isOpenEncry": "0",
            "sysType": "1", "schoolCode": "TEST101",
        }]
    })

    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        resp = client.post("/api/schools/refresh",
                           headers={"X-API-Token": api_token})
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        assert task_id

        done = wait_for_task_done(client, api_token, task_id)
        assert done["phase"] == "done", f"刷新失败 evt={done}"
        assert done["total"] >= 1

    # 再查列表
    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(s["school_name"] == "测试大学" for s in items)


def test_refresh_filters_demo_and_test(client, api_token):
    """名字含 demo/test 的学校应被过滤。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "X"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [
            {"school_id": 1, "school_name": "demo school", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C1"},
            {"school_id": 2, "school_name": "Test 学院", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C2"},
            {"school_id": 3, "school_name": "真实学校", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C3"},
        ]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        resp = client.post("/api/schools/refresh",
                           headers={"X-API-Token": api_token})
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        wait_for_task_done(client, api_token, task_id)

    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    items = resp.json()["items"]
    names = {s["school_name"] for s in items}
    assert "真实学校" in names
    assert "demo school" not in names
    assert "Test 学院" not in names


def test_refresh_emits_progress_events(client, api_token):
    """刷新过程中应至少推一个 refreshing 事件，再 done。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [
            {"province_id": "1", "province_name": "北京"},
            {"province_id": "2", "province_name": "上海"},
        ]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={"data": []})

    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        resp = client.post("/api/schools/refresh",
                           headers={"X-API-Token": api_token})
        task_id = resp.json()["task_id"]

        # 收集所有事件直到 done
        with client.websocket_connect(
                f"/ws/progress?task={task_id}&token={api_token}") as ws:
            phases = []
            for _ in range(50):
                evt = ws.receive_json()
                phases.append(evt)
                if evt["phase"] in ("done", "error"):
                    break

    refreshing = [p for p in phases if p["phase"] == "refreshing"]
    assert len(refreshing) >= 1, f"应至少推 1 个 refreshing 事件 phases={phases}"
    assert phases[-1]["phase"] == "done"
    # 进度字段齐全
    assert refreshing[0].get("province")
    assert refreshing[0].get("current") == 1
    assert refreshing[0].get("total") == 2
