"""进度事件总线契约：按 task_id 广播，多订阅者互不干扰。"""
import asyncio

import pytest

from webapp.progress import Bus


async def collect_until_terminal(bus: Bus, task_id: str) -> list[dict]:
    received = []
    stream = bus.subscribe(task_id)
    try:
        async for evt in stream:
            received.append(evt)
            if evt["phase"] in ("done", "error", "cancelled"):
                break
    finally:
        await stream.aclose()
    return received


@pytest.mark.asyncio
async def test_publish_then_subscribe_delivers_event():
    """订阅者应能收到 publish 的事件。"""
    bus = Bus()
    received = []

    async def consume():
        async for evt in bus.subscribe("task-1"):
            received.append(evt)
            if evt.get("phase") == "done":
                break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)  # 给订阅初始化时间
    await bus.publish("task-1", {"phase": "running", "elapsed_s": 1})
    await bus.publish("task-1", {"phase": "done"})
    await asyncio.wait_for(consumer, timeout=2.0)

    assert received == [{"phase": "running", "elapsed_s": 1}, {"phase": "done"}]


@pytest.mark.asyncio
async def test_two_subscribers_each_receive_all_events():
    """同一 task 的多个订阅者各自收到全部事件。"""
    bus = Bus()
    a, b = [], []

    async def consume(sink):
        async for evt in bus.subscribe("task-x"):
            sink.append(evt)
            if evt.get("phase") == "done":
                break

    ta = asyncio.create_task(consume(a))
    tb = asyncio.create_task(consume(b))
    await asyncio.sleep(0.05)
    await bus.publish("task-x", {"phase": "running"})
    await bus.publish("task-x", {"phase": "done"})
    await asyncio.wait_for(asyncio.gather(ta, tb), timeout=2.0)

    assert a == [{"phase": "running"}, {"phase": "done"}]
    assert b == [{"phase": "running"}, {"phase": "done"}]


@pytest.mark.asyncio
async def test_isolation_between_task_ids():
    """task-1 的事件不会传给 task-2 的订阅者。"""
    bus = Bus()
    got = []

    async def consume():
        async for evt in bus.subscribe("task-2"):
            got.append(evt)
            if evt.get("phase") == "done":
                break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await bus.publish("task-1", {"phase": "running"})  # 不该被 task-2 听到
    await bus.publish("task-2", {"phase": "done"})
    await asyncio.wait_for(consumer, timeout=2.0)

    assert got == [{"phase": "done"}]


@pytest.mark.asyncio
async def test_subscribe_late_misses_earlier_events():
    """订阅者在 publish 之后才订阅 — 收不到历史事件（设计如此，无缓冲）。"""
    bus = Bus()
    await bus.publish("task-3", {"phase": "running"})

    async def consume():
        got = []
        async for evt in bus.subscribe("task-3"):
            got.append(evt)
            if evt.get("phase") == "done":
                break
        return got

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await bus.publish("task-3", {"phase": "done"})
    got = await asyncio.wait_for(consumer, timeout=2.0)
    assert got == [{"phase": "done"}]  # 没有 'running'


@pytest.mark.asyncio
async def test_subscribe_after_terminal_replays_it():
    """订阅在 terminal 事件之后才发起 — 立即收到 terminal event 然后退出。

    这是 P1 修复（避免前端永久卡住）的核心契约：错误路径下任务比 WS 订阅完成得快时，
    后到的订阅者必须仍然能拿到终态。
    """
    bus = Bus()
    # 任务很快完成（甚至在前端连上 WS 之前）
    await bus.publish("late", {"phase": "running"})            # 非终态，丢
    await bus.publish("late", {"phase": "error", "code": "X", "msg": "boom"})

    received = await collect_until_terminal(bus, "late")
    assert received == [{"phase": "error", "code": "X", "msg": "boom"}]


@pytest.mark.asyncio
async def test_terminal_done_also_replays():
    """phase=done 也走同一条缓存路径。"""
    bus = Bus()
    await bus.publish("d", {"phase": "done", "total": 42})

    received = await collect_until_terminal(bus, "d")
    assert received == [{"phase": "done", "total": 42}]


@pytest.mark.asyncio
async def test_terminal_cancelled_also_replays():
    """phase=cancelled 也走同一条缓存路径。"""
    bus = Bus()
    await bus.publish("c", {"phase": "cancelled"})

    received = await collect_until_terminal(bus, "c")
    assert received == [{"phase": "cancelled"}]


@pytest.mark.asyncio
async def test_non_terminal_event_is_not_cached():
    """非终态事件（如 running）不缓存：迟到订阅者仍然只能收到之后的事件。"""
    bus = Bus()
    await bus.publish("r", {"phase": "running", "elapsed_s": 1})  # 不缓存

    received = []

    async def consume():
        async for evt in bus.subscribe("r"):
            received.append(evt)
            if evt["phase"] == "done":
                break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await bus.publish("r", {"phase": "done"})
    await asyncio.wait_for(consumer, timeout=2.0)
    # 迟到订阅者看不到那个 "running"
    assert received == [{"phase": "done"}]
