"""FastAPI 共享依赖。"""
from typing import AsyncGenerator

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


def require_token(
    request: Request,
    x_api_token: str | None = Header(default=None),
) -> None:
    """校验 X-API-Token 头与启动时生成的 token 匹配。"""
    expected = getattr(request.app.state, "api_token", None)
    if not expected:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"code": "NO_TOKEN_CONFIGURED", "msg": "服务未配置 token"})
    if x_api_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code": "BAD_TOKEN", "msg": "无效的访问凭证"})


def require_ws_token(token: str | None, expected: str | None) -> bool:
    """WebSocket 的 token 校验（不能用 Header 依赖，由路由手动调用）。"""
    return bool(expected) and token == expected


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """复用 database.get_db；这里转发以集中 import。"""
    from database import get_db as _get_db
    async for session in _get_db():
        yield session
