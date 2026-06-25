"""TsnRunServer 进度回调契约测试。

保证两件事：
1. 不传 callback 时，新增的 _emit 方法是 no-op，不影响 CLI 行为。
2. 传 callback 时，按规格表的 phase 顺序回调。
"""
from unittest.mock import MagicMock

from tsnRunServer import TsnRunServer, TsnRunType


def test_emit_without_callback_is_noop():
    """不传 progress_callback 时，_emit 静默执行，不抛异常。"""
    server = TsnRunServer(accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom)
    # 不应抛任何异常
    server._emit("preparing", msg="加载账号...")
    server._emit("running", elapsed_s=10, total_s=900, distance_km=0.1)


def test_emit_with_callback_invokes_it():
    """传入 callback 时，_emit 把 phase 和额外字段作为 dict 传出去。"""
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )
    server._emit("preparing", msg="加载账号...")
    cb.assert_called_once_with({"phase": "preparing", "msg": "加载账号..."})


def test_emit_swallows_callback_exception():
    """callback 抛异常时，_emit 必须吞掉，不影响主流程。"""
    def boom(evt):
        raise RuntimeError("callback failed")

    server = TsnRunServer(
        accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom,
        progress_callback=boom,
    )
    # 不应抛异常
    server._emit("preparing", msg="test")


import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_start_run_emits_phase_sequence_private():
    """私版账号跑步：startRun 应按 preparing → path_gen → 完成前的阶段顺序 emit。"""
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=0.1, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )

    # 全 mock 掉外部依赖
    fake_account = MagicMock()
    fake_account.id = 1
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "TEST"
    fake_client.sportRecordSetting = AsyncMock(return_value={
        "freedom": 0, "sunRun": 0, "morningRun": 0,
    })
    fake_client.getSportSetting = AsyncMock(return_value={
        "identify": "id-1", "geofence": {}, "list": [],
        "totalRange": 0.05,
    })
    fake_client.getRunningStartTime = AsyncMock(return_value={"startTime": 1700000000000})

    async def fake_get_db():
        yield MagicMock()

    with patch("tsnRunServer.getTsnAccountByid", AsyncMock(return_value=fake_account)), \
         patch("tsnRunServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("tsnRunServer.get_db", fake_get_db), \
         patch.object(TsnRunServer, "queryPath", AsyncMock(return_value=[[100.0, 30.0], [100.001, 30.001]])), \
         patch.object(TsnRunServer, "uploadRunPath", AsyncMock(return_value=None)), \
         patch("tsnRunServer.genTiShiNengRunPathRepeat", return_value=([{"a":1,"o":2,"t":1700000000000}], [1], 100.0)), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):
        await server.startRun()

    phases = [call.args[0]["phase"] for call in cb.call_args_list]
    # 至少包含 preparing 和 path_gen；这两个是 startRun 起步与路径生成阶段的关键标记
    assert "preparing" in phases, f"phases={phases}"
    assert "path_gen" in phases, f"phases={phases}"
    # preparing 应早于 path_gen
    assert phases.index("preparing") < phases.index("path_gen")


@pytest.mark.asyncio
async def test_upload_run_path_heartbeats_running_events(monkeypatch):
    """uploadRunPath 在等待跑步真实结束期间，应周期性 emit running 事件。

    用 fake time.time 制造一个需要等待 ~6 秒的场景，2 秒心跳应至少触发 2~3 次。
    """
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=0.5, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )
    server.isPublic = False
    server.start_timestamp = 1_700_000_000_000  # 毫秒
    server.identify = "id-1"
    server.geofence = {}
    server.pointList = []
    server.isEndFace = 0
    server.exerciseSetting = {}
    server.endStride = 0
    server.limitSpeed = 0
    server.endLimitStepFrequency = 0

    # 模拟 path 让 endTime = start + 6 秒
    path = [{"longitude": 1.0, "latitude": 2.0, "time": 1_700_000_006_000}]

    # 把 tsnClient 全部 mock
    server.tsnClient = MagicMock()
    server.tsnClient.appAddSportRecord = AsyncMock(return_value={})
    server.tsnClient.sumSportRecord = AsyncMock(return_value={})
    server.tsnClient.appSportRecordList = AsyncMock(
        return_value={"data": [{"sportStatus": 1, "remark": ""}]}
    )

    # 让 time.time 返回 endTime - 6s（即剩余 6 秒）
    fake_now = [1_700_000_000.0]
    monkeypatch.setattr("tsnRunServer.time.time", lambda: fake_now[0])

    # 加速 sleep：每次 sleep 把 fake_now 推进对应秒数后立即返回
    async def fast_sleep(sec):
        fake_now[0] += sec
    monkeypatch.setattr("tsnRunServer.asyncio.sleep", fast_sleep)

    await server.uploadRunPath(path, stepNumbers=[10], sumDistance=500.0)

    phases = [c.args[0]["phase"] for c in cb.call_args_list]
    running_count = sum(1 for p in phases if p == "running")
    assert running_count >= 2, f"heartbeat 应至少触发 2 次，实际 {running_count}, phases={phases}"
    assert "uploading" in phases, f"上传阶段需 emit，phases={phases}"
