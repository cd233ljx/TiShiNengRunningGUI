# GUI 化与单 exe 打包 — 设计规格

> 日期：2026-06-24
> 状态：待审阅
> 项目：TiShiNengRunning

## 1 · 目标与约束

把现有命令行程序 (`main.py`) 包装成面向 **非技术学生** 的桌面应用，并打包为 **单一 `TiShiNeng.exe`**，做到「下载 → 双击 → 输入账号 → 跑步」。

### 1.1 范围确认

| 维度 | 决定 |
|---|---|
| 目标用户 | 非技术学生（隐藏「学校代码 / sysType / 公版私版」等术语） |
| 目标平台 | Windows only（10 1809+ / 11） |
| GUI 技术栈 | PyWebView + HTML/CSS/原生 JS（系统 WebView2） |
| 后端通信 | **内置 FastAPI + WebView 加载本地端口**，跑步进度走 WebSocket |
| 功能覆盖 | 全部 6 项 CLI 功能 + 首次启动向导 |
| 跑步进行中 | 独立「运动中」页面，实时进度条 + 阶段状态 + 取消按钮 |
| 账号删除 | 二次确认 |
| 交付形态 | PyInstaller `--onefile` 单 exe |
| 数据存放 | exe 同目录（**便携式**） |
| 主题 | 亮 / 暗手动切换，本地持久化 |

### 1.2 非目标（YAGNI）

- 跨平台（macOS / Linux）
- 商业级签名与公证
- 在线自动更新
- 多账号并行跑步
- Web 远程访问（仅本地 127.0.0.1）
- 前端构建工具链（Node / Vite / React 等）

## 2 · 整体架构

```
┌─────────────────────────────────────────────────────┐
│                  TiShiNeng.exe                      │
│                                                     │
│   ┌─────────────────────────────────────────────┐   │
│   │   PyWebView 主窗口 (WebView2)                │   │
│   │     ↓ HTTP / WS                              │   │
│   │   http://127.0.0.1:<random-port>             │   │
│   └─────────────────────────────────────────────┘   │
│                       ↑                              │
│                       │ 同进程内访问                  │
│   ┌─────────────────────────────────────────────┐   │
│   │   FastAPI (uvicorn 后台线程)                  │   │
│   │   ├─ /api/bootstrap       (GET)              │   │
│   │   ├─ /api/schools         (REST)             │   │
│   │   ├─ /api/accounts        (REST)             │   │
│   │   ├─ /api/run/start       (POST)             │   │
│   │   ├─ /api/run/cancel      (POST)             │   │
│   │   ├─ /api/spider/start    (POST)             │   │
│   │   ├─ /api/face/update     (POST)             │   │
│   │   ├─ /api/distance/query  (POST)             │   │
│   │   └─ /ws/progress         (WebSocket)        │   │
│   └─────────────────────────────────────────────┘   │
│                       ↓                              │
│   ┌─────────────────────────────────────────────┐   │
│   │   Service 层 (复用现有代码)                   │   │
│   │   ├─ tsnRunServer.TsnRunServer                │   │
│   │   ├─ spiderServer.startSpider                 │   │
│   │   ├─ tsnClient.getClient / getTsnClientById   │   │
│   │   └─ services/*                               │   │
│   └─────────────────────────────────────────────┘   │
│                       ↓                              │
│   ┌─────────────────────────────────────────────┐   │
│   │   SQLite (tsn_data.db) + face_images/        │   │
│   │   均位于 exe 同目录                           │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 2.1 关键技术决策

1. **单进程多线程**：主线程跑 PyWebView（PyWebView 要求主线程驱动）；后台线程跑 uvicorn（单一 asyncio 事件循环）。跨线程提交协程用 `asyncio.run_coroutine_threadsafe()`。
2. **端口随机化**：启动时 `socket.bind(('127.0.0.1', 0))` 拿空闲端口；只绑 127.0.0.1，避免对外暴露。
3. **CSRF / 防误访问**：启动时 `secrets.token_urlsafe(32)` 生成一次性 token；启动 URL 带 `?t=<token>`，前端读到后存 `sessionStorage` 并清掉 URL；后续所有 fetch 注入 `X-API-Token` 头，WebSocket 用 `?token=<token>` 查询参数。每次启动新 token，进程结束即失效。
4. **路径定位**：用 `getattr(sys, 'frozen', False)` + `sys.executable` 检测 PyInstaller 环境；数据根 = `Path(sys.executable).parent`（打包态）或项目根（开发态）。前端静态资源用 `sys._MEIPASS` 定位。
5. **数据布局**（便携式）：
   - exe 同目录：`tsn_data.db` / `face_images/` / `logs/` / `config.json`
   - 整个文件夹拷贝即可迁移

## 3 · 目录结构

```
TiShiNengRunning/
├── main.py                       # CLI（保留，零回归）
├── gui_app.py                    # ★ 新增：GUI 入口（被打包成 exe）
│
├── webapp/                       # ★ 新增：FastAPI 应用
│   ├── __init__.py
│   ├── server.py                 # uvicorn 启动 + 端口/token 管理 + lifespan
│   ├── deps.py                   # 公共依赖（DB session、token 校验）
│   ├── progress.py               # 进度事件总线（asyncio.Queue 广播）
│   ├── paths.py                  # 数据/前端资源路径解析
│   └── routers/
│       ├── bootstrap.py          # GET /api/bootstrap
│       ├── schools.py            # GET /api/schools, POST /api/schools/refresh
│       ├── accounts.py           # CRUD 账号 + 授权
│       ├── run.py                # POST /api/run/start, /cancel, WS /ws/progress
│       ├── face.py               # POST /api/face/update
│       ├── spider.py             # POST /api/spider/start
│       └── distance.py           # POST /api/distance/query
│
├── frontend/                     # ★ 新增：前端静态资源（FastAPI 挂载 / PyInstaller 打入）
│   ├── index.html
│   ├── assets/
│   │   ├── app.css               # 亮/暗主题 CSS 变量
│   │   ├── app.js                # 路由 + fetch 包装 + WS 客户端
│   │   └── pages/
│   │       ├── home.js
│   │       ├── accounts.js
│   │       ├── run-setup.js
│   │       ├── run-active.js
│   │       ├── path-crawl.js
│   │       ├── face-update.js
│   │       ├── distance.js
│   │       └── settings.js
│   └── icons/                    # SVG 图标
│
├── packaging/                    # ★ 新增：打包资源
│   ├── tishineng.spec            # PyInstaller spec
│   ├── icon.ico
│   └── version_info.txt
│
├── tests/                        # ★ 新增：单元测试
│   ├── conftest.py
│   ├── webapp/
│   │   ├── test_bootstrap.py
│   │   ├── test_accounts.py
│   │   ├── test_run.py
│   │   └── test_progress_bus.py
│   └── test_run_server_progress.py
│
├── scripts/
│   └── verify-build.bat          # ★ 新增：本地构建验证
│
├── tsnRunServer.py               # ◯ 改动：增加可选 progress_callback 参数
├── spiderServer.py               # ◯ 改动：增加可选 progress_callback 参数
├── services/                     # 既有
├── TiShiNengSdk*.py              # 既有，不动
├── tsnClient.py                  # 既有，不动
├── database.py                   # 既有，不动（现有代码已支持 DATABASE_URL 环境变量）
├── models.py                     # 既有
├── requirements.txt              # ◯ 改动：新增运行时依赖
├── requirements-dev.txt          # ★ 新增：开发期依赖
└── docs/superpowers/specs/
    └── 2026-06-24-gui-and-packaging-design.md   # 本文档
```

### 3.1 模块划分原则

- 每个 `routers/*.py` 对应一个功能页 → 控制在 100 行内
- 每个 `frontend/assets/pages/*.js` 对应一个前端页面 → 一页一文件
- 现有 SDK 三层（Base/Private/Public）、加密工具、`models.py` 完全不动
- `tsnRunServer.py` / `spiderServer.py` 仅加非侵入式 hook（默认 None，CLI 行为零变化）

## 4 · 关键数据流

### 4.1 启动序列

```
gui_app.py 主线程
  │
  ├─ 1. 解析数据根目录 (sys.executable 同目录 / 或项目根)
  ├─ 2. 设置 DATABASE_URL 环境变量 → 数据根/tsn_data.db
  ├─ 3. 设置 FACE_IMAGES_DIR 环境变量 → 数据根/face_images/
  ├─ 4. 生成 API_TOKEN (secrets.token_urlsafe(32))
  ├─ 5. socket bind(127.0.0.1, 0) 取空闲 PORT
  ├─ 6. 后台线程 uvicorn.run(app, host=127.0.0.1, port=PORT)
  │     │
  │     └─→ FastAPI lifespan:
  │           ├─ await init_db()
  │           └─ 初始化 progress.Bus
  │
  ├─ 7. 轮询 GET /api/bootstrap 直到 200（最多 5s）
  └─ 8. webview.create_window(
            title="TiShiNeng 模拟跑步",
            url=f"http://127.0.0.1:{PORT}/?t={API_TOKEN}",
            width=960, height=720)
        webview.start()
```

启动期失败兜底：5 秒内 `/api/bootstrap` 不通 → 弹原生对话框「后端启动失败，详见 logs/，是否打开日志目录？」，不进入主窗口。

### 4.2 跑步进行时（最关键链路）

```
[前端 run-setup.js]
  用户点「开始跑步」
  │
  ├─ POST /api/run/start  { account_id, run_type, distance_km }
  │   │
  │   [routers/run.py]
  │   │  ├─ 生成 task_id = uuid4()
  │   │  ├─ asyncio.create_task( _do_run(task_id, ...) )
  │   │  └─ 立即 return { task_id }
  │   │
  │   └─ _do_run 内部:
  │        run_server = TsnRunServer(
  │            ...,
  │            progress_callback=lambda evt: Bus.publish(task_id, evt))
  │        try:
  │            await run_server.startRunHandle()
  │            Bus.publish(task_id, {"phase":"done"})
  │        except TiShiNengError as e:
  │            Bus.publish(task_id, {"phase":"error", "code": e.code, "msg": str(e)})
  │        except Exception as e:
  │            logger.exception(e)
  │            Bus.publish(task_id, {"phase":"error", "code":"UNKNOWN", "msg": str(e)})
  │
  └─ 跳转 /#/run/active?task=<task_id>
       │
       [前端 run-active.js]
       │
       └─ new WebSocket("ws://127.0.0.1:PORT/ws/progress?task=<id>&token=<t>")
           ↓
           服务端 ws_endpoint:
             async for evt in Bus.subscribe(task_id):
                 await ws.send_json(evt)
                 if evt["phase"] in ("done", "error", "cancelled"): break
           ↓
           前端 onmessage:
             更新进度条 / 已用时间 / 状态文字
             phase === "done"      → 显示完成卡，停留 3s 回主页
             phase === "error"     → 显示错误卡 + [返回] [重试]
             phase === "cancelled" → 显示「已取消」+ [返回]
```

#### 4.2.1 进度事件契约

| phase | 何时触发 | 额外字段 |
|---|---|---|
| `preparing` | 加载账号 / 客户端 | `msg` |
| `face_start` | 开始人脸验证（公版） | `msg` |
| `path_gen` | 生成跑步路径 | `msg` |
| `running` | 跑步循环中（每 2 秒 1 次） | `elapsed_s`, `total_s`, `distance_km` |
| `face_mid` | 中途人脸 | `msg` |
| `uploading` | 上传运动记录 | `msg` |
| `face_end` | 结束人脸 | `msg` |
| `done` | 全流程完成 | `result`（可选） |
| `error` | 任意异常 | `code`, `msg` |
| `cancelled` | 用户点取消 | — |

#### 4.2.2 心跳来源

现有 `tsnRunServer.uploadRunPath` 内 `taskList.append(asyncio.sleep(sleepTime))` 把跑步真实时长「卡」掉。改造为每 2 秒一次的循环，每次循环：

1. 调用 `self._emit("running", elapsed_s=..., total_s=..., distance_km=...)`
2. `await asyncio.sleep(min(2, remaining))`
3. 检查 `asyncio.CancelledError`（用户取消时由 `task.cancel()` 触发）

`_emit` 内部：

```python
def _emit(self, phase: str, **kw):
    if self._progress_callback is not None:
        try:
            self._progress_callback({"phase": phase, **kw})
        except Exception:
            logger.warning("progress callback raised, ignored")
```

回调失败不影响主流程。

### 4.3 账号授权（典型 REST 链路）

```
[前端 accounts.js]
  填表 → 提交
  │
  POST /api/accounts/authorize { school_id, username, password }
  │
  [routers/accounts.py]
  │  ├─ Pydantic 校验
  │  ├─ school = await get_school_by_id(school_id, db)
  │  ├─ try:
  │  │     uid = await tsnPasswordAuthServer(school, username, password)
  │  │  except TiShiNengError as e:
  │  │     return JSONResponse(status_code=400,
  │  │                         content={"code": e.code, "msg": str(e)})
  │  └─ 成功 → return { account_id, username, school_name }
```

错误统一格式 `{"code": "...", "msg": "..."}`；前端有错误码 → 友好文案映射表。

### 4.4 端口 / token 接入点

前端入口 `index.html` 加载后：

```js
const params = new URLSearchParams(location.search);
sessionStorage.setItem("token", params.get("t"));
history.replaceState({}, "", location.pathname);  // 清掉 URL 中的 token
```

随后所有请求经统一 `api()` 包装注入 `X-API-Token`。

## 5 · 错误处理与日志

### 5.1 错误分类

| 类别 | 来源 | 用户看到 | 日志级别 |
|---|---|---|---|
| 业务异常 | `TiShiNengError` | 友好中文 + 操作建议 | INFO |
| 网络异常 | `httpx.*` | 「网络异常，请稍后重试」+ 重试按钮 | WARNING |
| 认证失效 | 401/403 | 自动 refresh，失败提示「请重新授权」 | WARNING |
| 参数校验失败 | Pydantic | 表单内联红字，定位字段 | DEBUG |
| 未预期异常 | `Exception` | 通用提示 + 「查看日志」按钮 | ERROR + traceback |

### 5.2 前端错误处理

```js
async function api(path, opts={}) {
  const resp = await fetch(path, { ...opts,
    headers: { ...opts.headers,
      'X-API-Token': sessionStorage.getItem('token'),
      'Content-Type':'application/json' }
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({code:'UNKNOWN', msg:'未知错误'}));
    throw new ApiError(err.code, err.msg, resp.status);
  }
  return resp.json();
}
// 调用方
try { await api('/api/run/start', {method:'POST', body: JSON.stringify(...)}); }
catch (e) { toast.error(ERROR_MESSAGES[e.code] ?? e.msg); }
```

`ERROR_MESSAGES` 维护在 `frontend/assets/app.js`，前后端同步新增。

### 5.3 跑步任务失败

后台任务抛出任何异常 → `Bus.publish` 推 `phase:error` → 前端「运动中」页停掉心跳，渲染错误卡（标题 / 友好描述 / 错误码小字 / [返回] [重试]）。

「取消」→ `POST /api/run/cancel` → 服务端持有 task 引用，调用 `task.cancel()` → 协程抛 `CancelledError` → `Bus.publish` 推 `cancelled`。

### 5.4 日志

- 复用 `loguru`，新增 file sink：`logs/tishineng-YYYY-MM-DD.log`（按天滚动，保留 7 天）
- 路径在 exe 同目录
- 打包模式禁用 stdout sink（窗口程序无控制台）
- 默认 INFO；设置页可切换 DEBUG（写入 `config.json`，下次启动生效）

## 6 · 测试策略

### 6.1 后端单元测试（`tests/webapp/`）

pytest + httpx.AsyncClient。外部 HTTP / SDK 全部 monkeypatch mock 掉。

| 测试文件 | 关注点 |
|---|---|
| `test_bootstrap.py` | token 校验：无 token / 错 token / 对 token |
| `test_accounts.py` | 授权成功、密码错→ 400、删除二次确认参数 |
| `test_run.py` | start 立即返回 task_id；cancel 真正终止 task |
| `test_progress_bus.py` | 多订阅者广播；订阅者断开不影响他人 |

### 6.2 进度回调契约测试（`tests/test_run_server_progress.py`）

`TsnRunServer` 关键改动，必须保证：

1. **CLI 路径（不传 callback）行为 100% 不变** — mock SDK 后跑一遍 startRunHandle，对比 CLI 既有日志输出
2. **传入 callback 后按表 emit phase 序列** — 用 `MagicMock` 收集，断言序列

### 6.3 手动冒烟（`docs/packaging-smoke.md`）

打包后必跑 checklist：

- [ ] 双击 exe，主窗口 ≤ 5s 出现
- [ ] 设置 → 切暗色 → 重启，主题保持
- [ ] 用错密码授权 → 看到「用户名或密码错误」
- [ ] 0.5 km 短跑 → 运动中页面进度递增 → 完成
- [ ] 「取消」能真正中断（运动中页面 + 任务管理器双重确认）
- [ ] 关窗口后无残留 python 进程
- [ ] 把整个 dist 目录拷到无 Python 的机器，双击仍能跑

### 6.4 不做

- 前端 JS 单元测试（量小，冒烟覆盖）
- Playwright / Cypress（构建链路太重）
- 打包脚本本身的自动化测试

## 7 · 开发与打包工作流

### 7.1 虚拟环境（约定 `.venv/`）

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`.venv/` 加入 `.gitignore`。

### 7.2 依赖

`requirements.txt`（运行时新增）：

```
fastapi==0.115.0
uvicorn==0.32.0
pywebview==5.3.2
pydantic==2.9.2
```

`requirements-dev.txt`（开发期新增）：

```
pyinstaller==6.10.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

> 版本号为初始建议，实施时可按 PyPI 当前稳定版调整。

### 7.3 开发期运行（全部走 `.venv`）

```bash
# 模式一：GUI 模式（与生产一致）
.venv\Scripts\python gui_app.py

# 模式二：仅后端 + 浏览器调试
.venv\Scripts\python -m uvicorn webapp.server:app --reload --port 8000
# 浏览器开 http://127.0.0.1:8000/?t=dev-token

# 模式三：CLI 兼容
.venv\Scripts\python main.py
```

`gui_app.py --dev` 开启 PyWebView DevTools 并使用固定 token `dev-token`。

### 7.4 测试

```bash
.venv\Scripts\python -m pytest tests/ -v
```

### 7.5 打包

```bash
.venv\Scripts\python -m PyInstaller packaging/tishineng.spec --clean --noconfirm
# 产物: dist\TiShiNeng.exe（onefile 模式）
```

`packaging/tishineng.spec` 关键配置：

```python
a = Analysis(
    ['..\\gui_app.py'],
    pathex=['..'],
    datas=[
        ('..\\frontend', 'frontend'),
    ],
    hiddenimports=[
        'aiosqlite', 'sqlalchemy.dialects.sqlite.aiosqlite',
        'uvicorn.logging', 'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
    ],
    excludes=['tkinter', 'PySide6', 'PyQt5', 'PyQt6', 'numpy.testing'],
)
exe = EXE(
    pyz, a.scripts,
    name='TiShiNeng',
    icon='icon.ico',
    console=False,
    onefile=True,
    version='version_info.txt',
)
```

**陷阱预防：**

- uvicorn 的隐式导入必须列入 `hiddenimports`，否则 onefile exe 起不来
- `frontend/` 通过 `datas` 进包，运行时用 `sys._MEIPASS` 定位
- 数据库、人脸目录、日志、配置 **均不进包**，用 `Path(sys.executable).parent` 定位
- WebView2 Runtime 不打包（Win10 1809+ / Win11 内置；老 Win10 在 README 说明需安装 Microsoft Edge WebView2 Runtime）

### 7.6 验证脚本

`scripts/verify-build.bat`：

```bat
@echo off
call .venv\Scripts\activate
python -m pytest tests/ -q || exit /b 1
python -m PyInstaller packaging/tishineng.spec --clean --noconfirm || exit /b 1
echo Build OK. Now run dist\TiShiNeng.exe and follow docs\packaging-smoke.md
```

## 8 · 对现有代码的改动清单

| 文件 | 改动 |
|---|---|
| `tsnRunServer.py` | `__init__` 增加 `progress_callback: Callable[[dict], None] \| None = None`；新增 `_emit(phase, **kw)`；在 startRunHandle 全流程关键位置插入 `_emit` 调用；`uploadRunPath` 内的固定 `asyncio.sleep` 替换为 2 秒心跳循环 |
| `spiderServer.py` | `startSpider` 增加可选 `progress_callback`，在抓取每条记录后 emit `{"phase":"crawling", "current":i, "total":n}` |
| `database.py` | **不动**。现有代码已是 `os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./tsn_data.db")`；`gui_app.py` 启动时通过 `os.environ` 注入正确路径即可；`main.py` 走默认值兜底 |
| `requirements.txt` | 新增 fastapi / uvicorn / pywebview / pydantic |
| `.gitignore` | 新增 `.venv/`、`dist/`、`build/`、`*.spec.bak` |

其他文件均为新增。

## 9 · 风险与缓解

| 风险 | 缓解 |
|---|---|
| 老版 Win10 无 WebView2 Runtime | README 提供官方安装链接；`gui_app.py` 启动时 `webview.start()` 抛错可弹窗指引 |
| onefile 启动慢（3–8s 解压到临时目录） | 文档说明这是首次启动行为；接受不优化 |
| uvicorn 隐式导入遗漏 → 打包后报 ModuleNotFoundError | 已在 `hiddenimports` 列出常见项；冒烟测试覆盖 |
| 长跑步任务在主线程跨线程取消复杂 | 通过 asyncio.Task 引用 + `task.cancel()`，`CancelledError` 被 SDK 内部 try 拦截需检查 |
| token 泄露（URL 进入历史） | 前端立即 `history.replaceState` 清掉；token 每次启动重新生成 |
| 杀毒软件误报 onefile exe | 文档说明；后续可考虑代码签名（非本期范围） |

## 10 · 验收条件

- [ ] `.venv\Scripts\python -m pytest tests/ -v` 全绿
- [ ] `.venv\Scripts\python main.py` 仍能完整跑通（零回归）
- [ ] `scripts/verify-build.bat` 一次执行成功，产出 `dist/TiShiNeng.exe`
- [ ] 完成 `docs/packaging-smoke.md` 中全部冒烟项
- [ ] 拷贝到无 Python 的 Win11 机器双击可运行
