"""进度事件总线契约：按 task_id 广播，多订阅者互不干扰。"""
import asyncio

import pytest

from webapp.progress import Bus


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
