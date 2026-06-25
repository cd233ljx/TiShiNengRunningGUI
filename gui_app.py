"""TiShiNeng GUI 启动入口。

职责：
1. 解析数据根目录（冻结/开发双模式），通过环境变量把 DATABASE_URL 注入给 database.py
2. 生成一次性 API token，挑空闲端口
3. 后台线程启动 uvicorn 托管 FastAPI
4. 轮询 /api/bootstrap 确认后端就绪
5. PyWebView 打开主窗口，URL 带 ?t=<token>
6. 关窗口后让 uvicorn 优雅退出
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from loguru import logger

from webapp import paths
from webapp.server import create_app, generate_token, pick_free_port, run_server_in_thread


DEV_TOKEN = "dev-token"


def configure_runtime(dev: bool) -> tuple[str, int]:
    """设置环境与日志。返回 (token, port)。"""
    # 1. 数据根（paths.data_dir 自动判断冻结/开发）
    data_dir = paths.data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    # 2. DATABASE_URL — database.py 读 env，已支持
    db_path = paths.db_path()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    # 3. 让 TsnRunServer.getFaceImage 默认走 data_dir/face_images/
    #    通过把工作目录切到 data_dir 即可（getFaceImage 使用相对路径 "face_images"）
    os.chdir(data_dir)

    # 4. 日志 sink — 文件按天滚动
    logs = paths.logs_dir()
    logger.remove()
    logger.add(
        logs / "tishineng-{time:YYYY-MM-DD}.log",
        rotation="00:00", retention="7 days", encoding="utf-8",
        level="INFO",
    )
    if dev:
        logger.add(sys.stderr, level="DEBUG")

    token = DEV_TOKEN if dev else generate_token()
    port = pick_free_port()
    return token, port


def wait_for_backend(port: int, token: str, timeout: float = 5.0) -> bool:
    """轮询 /api/bootstrap 直到 200 或超时。"""
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/bootstrap"
    while time.time() < deadline:
        try:
            r = httpx.get(url, headers={"X-API-Token": token}, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def show_startup_error_dialog(message: str) -> None:
    """后端起不来时的兜底对话框。优先用 tkinter（系统自带），失败则 print。"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("TiShiNeng 启动失败", message)
        root.destroy()
    except Exception:
        print(f"[ERROR] {message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="开发模式：固定 token、启用 DevTools")
    args = parser.parse_args()

    token, port = configure_runtime(dev=args.dev)
    app = create_app(api_token=token)
    server = run_server_in_thread(app, port)

    if not server.wait_started(timeout=5.0):
        show_startup_error_dialog(f"后端线程未在 5 秒内启动。日志：{paths.logs_dir()}")
        return 2

    if not wait_for_backend(port, token, timeout=5.0):
        show_startup_error_dialog(f"无法连接后端 http://127.0.0.1:{port}。日志：{paths.logs_dir()}")
        server.stop()
        return 3

    # 启动 PyWebView 主窗口（阻塞主线程）
    try:
        import webview
        url = f"http://127.0.0.1:{port}/?t={token}"
        webview.create_window(
            title="TiShiNeng 模拟跑步",
            url=url,
            width=960, height=720, min_size=(720, 540),
        )
        webview.start(debug=args.dev)
    except Exception as e:
        logger.exception(e)
        show_startup_error_dialog(
            "WebView2 运行时未安装或加载失败。\n\n"
            "请安装 Microsoft Edge WebView2 Runtime：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            f"详细错误：{e}"
        )
        server.stop()
        return 4
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
