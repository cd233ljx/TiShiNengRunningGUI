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
