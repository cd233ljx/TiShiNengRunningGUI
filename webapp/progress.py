"""进度事件总线。

每个 task_id 维护一个订阅者列表（asyncio.Queue）。publish 向所有当前订阅者投递。

**终态事件缓存**：done / error / cancelled 会被记入 `_terminal`，之后才到的订阅者
立即收到该事件再退出 —— 解决"任务完成早于 WS 订阅时前端永久卡住"问题
（错误路径尤其容易触发，因为 startRunHandle 抛错速度通常 < WS 订阅延迟）。
非终态事件（running/refreshing 等）仍然无缓冲，订阅前发出的中间进度会丢。
"""
import asyncio
from collections import defaultdict
from typing import AsyncIterator, Dict, List

TERMINAL_PHASES = frozenset({"done", "error", "cancelled"})


class Bus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._terminal: Dict[str, dict] = {}

    async def publish(self, task_id: str, event: dict) -> None:
        """向 task_id 当前所有订阅者投递 event；终态事件会被缓存供后到订阅者 replay。"""
        if event.get("phase") in TERMINAL_PHASES:
            self._terminal[task_id] = event
        for q in list(self._subscribers.get(task_id, ())):
            await q.put(event)

    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """订阅 task_id 的事件流。如该 task 已 terminal，立即 yield 终态事件后退出。

        用法:
            async for evt in bus.subscribe("t-1"):
                ...
                if evt["phase"] in ("done","error","cancelled"): break
        """
        # 已结束的任务：直接 replay terminal event，不再排队等待
        cached = self._terminal.get(task_id)
        if cached is not None:
            yield cached
            return

        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(q)
        try:
            while True:
                evt = await q.get()
                yield evt
        finally:
            try:
                self._subscribers[task_id].remove(q)
            except ValueError:
                pass
            # 队列为空就清掉 key，避免内存累积
            if not self._subscribers.get(task_id):
                self._subscribers.pop(task_id, None)


# 全局单例（lifespan 会复用此实例；测试可以直接 new Bus()）
bus = Bus()
