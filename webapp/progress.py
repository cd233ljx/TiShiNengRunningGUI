"""进度事件总线。

每个 task_id 维护一个订阅者列表（asyncio.Queue）。publish 向所有当前订阅者投递。
无历史缓冲 —— 跑步任务期间订阅一次即可，断开重连会丢中间事件（前端通过 task 完成态自我恢复）。
"""
import asyncio
from collections import defaultdict
from typing import AsyncIterator, Dict, List


class Bus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    async def publish(self, task_id: str, event: dict) -> None:
        """向 task_id 当前所有订阅者投递 event。无订阅者时静默丢弃。"""
        for q in list(self._subscribers.get(task_id, ())):
            await q.put(event)

    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """订阅 task_id 的事件流。终结事件（done/error/cancelled）由调用方判断后 break。

        用法:
            async for evt in bus.subscribe("t-1"):
                ...
                if evt["phase"] in ("done","error","cancelled"): break
        """
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
