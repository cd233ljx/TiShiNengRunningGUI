"""路径爬取（后台异步）。task_id 与跑步共用全局 Bus，前端订阅 /ws/progress 即可看到 crawling 事件。"""
import asyncio
import uuid
from typing import Dict

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel

from spiderServer import startSpider
from webapp.deps import require_token
from webapp.progress import bus

router = APIRouter(prefix="/api/spider", tags=["spider"],
                   dependencies=[Depends(require_token)])

_TASKS: Dict[str, asyncio.Task] = {}


class SpiderStartBody(BaseModel):
    account_id: int


@router.post("/start")
async def spider_start(body: SpiderStartBody) -> dict:
    task_id = uuid.uuid4().hex

    def _cb(evt: dict):
        loop = asyncio.get_event_loop()
        loop.create_task(bus.publish(task_id, evt))

    async def _do() -> None:
        try:
            await startSpider(body.account_id, progress_callback=_cb)
            await bus.publish(task_id, {"phase": "done"})
        except Exception as e:  # noqa: BLE001
            logger.exception(e)
            await bus.publish(task_id, {"phase": "error",
                                        "code": "UNKNOWN", "msg": str(e)})
        finally:
            _TASKS.pop(task_id, None)

    _TASKS[task_id] = asyncio.create_task(_do())
    return {"task_id": task_id}
