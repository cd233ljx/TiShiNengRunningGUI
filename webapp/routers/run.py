"""跑步任务编排路由。

POST /api/run/start    — 立即返回 task_id，后台跑 TsnRunServer
POST /api/run/cancel   — 终止指定 task_id 的后台任务
WS   /ws/progress      — 推送进度事件，task_id + token 通过 query 传
"""
import asyncio
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from loguru import logger
from pydantic import BaseModel, Field
from typing_extensions import Literal

from TiShiNengError import TiShiNengError
from tsnRunServer import TsnRunServer, TsnRunType
from webapp.deps import require_token, require_ws_token
from webapp.progress import bus

router = APIRouter(prefix="/api/run", tags=["run"], dependencies=[Depends(require_token)])

_ws_router = APIRouter()  # 不附 require_token，因为 WS 不走 Header

# 全局 task 注册表：task_id -> asyncio.Task
_TASKS: Dict[str, asyncio.Task] = {}

RUN_TYPE_MAP = {
    "morning": TsnRunType.morningRun,
    "sun": TsnRunType.sumRun,
    "freedom": TsnRunType.freedom,
}


class RunStartBody(BaseModel):
    account_id: int
    run_type: Literal["morning", "sun", "freedom"]
    distance_km: float = Field(..., gt=0, le=50)


class RunCancelBody(BaseModel):
    task_id: str


@router.post("/start")
async def run_start(body: RunStartBody) -> dict:
    task_id = uuid.uuid4().hex
    run_type = RUN_TYPE_MAP[body.run_type]

    def _cb(evt: dict) -> None:
        # 同步 callback 内安排异步 publish。bus.publish 是 async，需 schedule 到当前 loop。
        loop = asyncio.get_event_loop()
        loop.create_task(bus.publish(task_id, evt))

    async def _do_run() -> None:
        try:
            server = TsnRunServer(
                accountId=body.account_id,
                runKiloMeter=body.distance_km,
                logRunType=run_type,
                progress_callback=_cb,
            )
            await server.startRunHandle()
            await bus.publish(task_id, {"phase": "done"})
        except asyncio.CancelledError:
            await bus.publish(task_id, {"phase": "cancelled"})
            raise
        except TiShiNengError as e:
            await bus.publish(task_id, {"phase": "error",
                                        "code": str(e.code), "msg": e.message})
        except Exception as e:  # noqa: BLE001
            logger.exception(e)
            await bus.publish(task_id, {"phase": "error",
                                        "code": "UNKNOWN", "msg": str(e)})
        finally:
            _TASKS.pop(task_id, None)

    task = asyncio.create_task(_do_run())
    _TASKS[task_id] = task
    return {"task_id": task_id}


@router.post("/cancel")
async def run_cancel(body: RunCancelBody) -> dict:
    task = _TASKS.get(body.task_id)
    if task is None or task.done():
        raise HTTPException(status_code=404,
                            detail={"code": "TASK_NOT_FOUND",
                                    "msg": "任务不存在或已结束"})
    task.cancel()
    return {"cancelled": True}


@_ws_router.websocket("/ws/progress")
async def ws_progress(websocket: WebSocket,
                      task: Optional[str] = None,
                      token: Optional[str] = None) -> None:
    expected = getattr(websocket.app.state, "api_token", None)
    if not require_ws_token(token, expected):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not task:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        async for evt in bus.subscribe(task):
            await websocket.send_json(evt)
            if evt.get("phase") in ("done", "error", "cancelled"):
                break
    except WebSocketDisconnect:
        logger.info(f"ws disconnected for task={task}")
    except Exception as e:  # noqa: BLE001
        logger.exception(e)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
