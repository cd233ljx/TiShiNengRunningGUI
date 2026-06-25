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
