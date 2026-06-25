"""学校列表/刷新端点测试。外部 HTTP 全 mock。"""
from unittest.mock import AsyncMock, patch


def test_list_schools_empty(client, api_token):
    """没有学校时返回空数组。"""
    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_refresh_schools_calls_sdk_and_persists(client, api_token, monkeypatch):
    """触发刷新：mock 掉 SDK，看到学校落库。"""
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
        body = resp.json()
        assert body["total"] >= 1

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

    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    items = resp.json()["items"]
    names = {s["school_name"] for s in items}
    assert "真实学校" in names
    assert "demo school" not in names
    assert "Test 学院" not in names
