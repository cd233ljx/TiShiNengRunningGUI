"""GET /api/bootstrap — 前端启动握手，校验 token 有效。"""
from fastapi import APIRouter, Depends

from webapp.deps import require_token

router = APIRouter(prefix="/api", tags=["bootstrap"])

APP_VERSION = "0.1.0"


@router.get("/bootstrap", dependencies=[Depends(require_token)])
async def bootstrap() -> dict:
    return {"status": "ok", "version": APP_VERSION}
