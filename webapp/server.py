"""FastAPI app 工厂 + uvicorn 启动控制。

create_app(api_token, ...) 返回带依赖、路由、静态资源挂载的 FastAPI 实例。
run_server_in_thread(...) 起后台线程跑 uvicorn，供 gui_app.py 调用。
"""
from __future__ import annotations

import asyncio
import contextlib
import secrets
import socket
import threading
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from webapp import paths
from webapp.progress import bus
from webapp.routers import bootstrap


def create_app(api_token: str) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        from database import init_db
        await init_db()
        logger.info("FastAPI lifespan: database initialized")
        yield
        logger.info("FastAPI lifespan: shutting down")

    app = FastAPI(title="TiShiNeng GUI", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.api_token = api_token
    app.state.bus = bus

    # 路由（后续阶段持续追加）
    app.include_router(bootstrap.router)
    from webapp.routers import schools
    app.include_router(schools.router)
    from webapp.routers import accounts
    app.include_router(accounts.router)
    from webapp.routers import run as run_router
    app.include_router(run_router.router)
    app.include_router(run_router._ws_router)
    from webapp.routers import face
    app.include_router(face.router)
    from webapp.routers import spider
    app.include_router(spider.router)
    from webapp.routers import distance
    app.include_router(distance.router)

    # 全局异常 → 统一 {code, msg}
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from TiShiNengError import TiShiNengError

    @app.exception_handler(TiShiNengError)
    async def _on_tsn_error(_req, exc: TiShiNengError):
        return JSONResponse(status_code=400,
                            content={"code": str(exc.code), "msg": exc.message})

    @app.exception_handler(HTTPException)
    async def _on_http_exc(_req, exc: HTTPException):
        # detail 已是 {code, msg} 时直接用
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code,
                            content={"code": "HTTP_ERROR", "msg": str(exc.detail)})

    @app.exception_handler(RequestValidationError)
    async def _on_validation(_req, exc: RequestValidationError):
        return JSONResponse(status_code=422,
                            content={"code": "VALIDATION_ERROR",
                                     "msg": "参数校验失败", "errors": exc.errors()})

    @app.exception_handler(Exception)
    async def _on_exception(_req, exc):
        from TiShiNengError import TiShiNengError
        if isinstance(exc, TiShiNengError):
            return JSONResponse(status_code=400,
                                content={"code": str(exc.code), "msg": exc.message})
        logger.exception(exc)
        return JSONResponse(status_code=500,
                            content={"code": "UNKNOWN", "msg": str(exc)})

    # 前端静态资源
    fdir = paths.frontend_dir()
    if (fdir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(fdir / "assets")), name="assets")
    if (fdir / "icons").is_dir():
        app.mount("/icons", StaticFiles(directory=str(fdir / "icons")), name="icons")

    @app.get("/", include_in_schema=False)
    async def _index():
        idx = fdir / "index.html"
        if not idx.exists():
            return JSONResponse(status_code=503, content={"code": "NO_FRONTEND", "msg": "前端资源缺失"})
        return FileResponse(str(idx))

    return app


def pick_free_port() -> int:
    """绑定 127.0.0.1:0 拿到操作系统分配的空闲端口。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def generate_token() -> str:
    return secrets.token_urlsafe(32)


class ServerThread(threading.Thread):
    """守护线程跑 uvicorn。expose stop() / wait_started()。"""

    def __init__(self, app: FastAPI, host: str, port: int):
        super().__init__(daemon=True, name="uvicorn-thread")
        self.app = app
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._started = threading.Event()

    def run(self) -> None:
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,
            lifespan="on",
            log_config=None,
        )
        self._server = uvicorn.Server(config)

        async def _serve():
            self._started.set()
            await self._server.serve()

        try:
            asyncio.run(_serve())
        except Exception:
            logger.exception("uvicorn server crashed")

    def wait_started(self, timeout: float = 5.0) -> bool:
        return self._started.wait(timeout)

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True


def run_server_in_thread(app: FastAPI, port: int) -> ServerThread:
    t = ServerThread(app=app, host="127.0.0.1", port=port)
    t.start()
    return t
