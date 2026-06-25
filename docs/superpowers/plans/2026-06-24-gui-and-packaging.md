# GUI 化与单 exe 打包 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有命令行 TiShiNeng 程序包装为面向非技术学生的 PyWebView 桌面应用，并打包为单一 `TiShiNeng.exe`。

**Architecture:** 单进程多线程：主线程跑 PyWebView（系统 WebView2 渲染 HTML 前端），后台线程跑 uvicorn 托管的 FastAPI；前端通过 HTTP/WS 调用本机后端；后端复用现有 `TsnRunServer` / `spiderServer` / `tsnClient`，仅以非侵入式 `progress_callback` 暴露进度。数据布局便携式（exe 同目录）。

**Tech Stack:** Python 3.10+、FastAPI、uvicorn、pywebview (WebView2)、SQLAlchemy/aiosqlite (既有)、loguru (既有)、原生 ES Module 前端 (无构建工具)、PyInstaller (--onefile)、pytest + pytest-asyncio。

**对应规格：** `docs/superpowers/specs/2026-06-24-gui-and-packaging-design.md`
**实施分支：** `feat/gui-and-packaging`（已创建）

---

## 文件结构（新建/修改一览）

| 类别 | 路径 | 责任 |
|---|---|---|
| 新增·入口 | `gui_app.py` | PyWebView 启动器，设置数据路径、起 uvicorn 后台线程 |
| 新增·后端 | `webapp/__init__.py` | 包标识 |
| 新增·后端 | `webapp/paths.py` | 数据目录 / 前端资源路径解析（兼容 PyInstaller） |
| 新增·后端 | `webapp/progress.py` | 进度事件总线（asyncio.Queue 广播） |
| 新增·后端 | `webapp/deps.py` | 公共依赖：token 校验、DB session 注入 |
| 新增·后端 | `webapp/server.py` | FastAPI app 工厂 + uvicorn 启动器 + token/端口管理 |
| 新增·后端 | `webapp/routers/__init__.py` | 包标识 |
| 新增·后端 | `webapp/routers/bootstrap.py` | `GET /api/bootstrap` |
| 新增·后端 | `webapp/routers/schools.py` | `GET /api/schools`、`POST /api/schools/refresh` |
| 新增·后端 | `webapp/routers/accounts.py` | 账号 CRUD + 授权 |
| 新增·后端 | `webapp/routers/run.py` | 跑步 start/cancel + WebSocket 进度 |
| 新增·后端 | `webapp/routers/face.py` | 更新人脸图片 |
| 新增·后端 | `webapp/routers/spider.py` | 启动路径爬取 |
| 新增·后端 | `webapp/routers/distance.py` | 查询里程 |
| 新增·前端 | `frontend/index.html` | SPA 入口 |
| 新增·前端 | `frontend/assets/app.css` | 主题 CSS（亮/暗变量） |
| 新增·前端 | `frontend/assets/app.js` | hash 路由 + `api()` + WS + toast |
| 新增·前端 | `frontend/assets/pages/home.js` | 主菜单页 |
| 新增·前端 | `frontend/assets/pages/accounts.js` | 账号列表 / 新增 / 删除 |
| 新增·前端 | `frontend/assets/pages/run-setup.js` | 跑步设置表单 |
| 新增·前端 | `frontend/assets/pages/run-active.js` | 跑步进行中（WS） |
| 新增·前端 | `frontend/assets/pages/face-update.js` | 更新人脸 |
| 新增·前端 | `frontend/assets/pages/path-crawl.js` | 路径爬取 |
| 新增·前端 | `frontend/assets/pages/distance.js` | 里程查询 |
| 新增·前端 | `frontend/assets/pages/settings.js` | 主题切换 + DEBUG 切换 |
| 新增·打包 | `packaging/tishineng.spec` | PyInstaller spec |
| 新增·打包 | `packaging/version_info.txt` | Windows 版本元数据 |
| 新增·脚本 | `scripts/verify-build.bat` | 本地一键校验 |
| 新增·测试 | `tests/conftest.py` | 共享 fixture |
| 新增·测试 | `tests/test_run_server_progress.py` | 进度回调契约 |
| 新增·测试 | `tests/webapp/conftest.py` | TestClient fixture |
| 新增·测试 | `tests/webapp/test_bootstrap.py` | token 验证 |
| 新增·测试 | `tests/webapp/test_progress_bus.py` | 广播 / 退订 |
| 新增·测试 | `tests/webapp/test_accounts.py` | 授权 / 删除 |
| 新增·测试 | `tests/webapp/test_run.py` | start / cancel / WS |
| 新增·文档 | `docs/packaging-smoke.md` | 打包冒烟清单 |
| 修改 | `tsnRunServer.py` | `__init__` 加 `progress_callback`、新增 `_emit`、`startRun` 各阶段 emit、`uploadRunPath` 心跳循环 |
| 修改 | `spiderServer.py` | `startSpider` 增 `progress_callback`，每条记录 emit |
| 修改 | `requirements.txt` | 新增 fastapi/uvicorn/pywebview/pydantic |
| 修改 | `.gitignore` | `.venv/`、`dist/`、`build/`、`logs/`、`config.json`、`tsn_data.db` |
| 新增 | `requirements-dev.txt` | pyinstaller/pytest/pytest-asyncio/pytest-mock |

**说明：** 现有 `database.py`、`models.py`、SDK 三层、加密工具、`services/*`、`tsnClient.py`、`main.py` 一律不动。

---

## Phase 0 · 准备：分支、虚拟环境、依赖

### Task 0.1: 验证分支与环境

**Files:** 无（只读检查）

- [ ] **Step 1: 确认在正确分支**

```bash
cd F:/CODE/TiShiNengRunning
git status
git branch --show-current
```

Expected: 当前分支为 `feat/gui-and-packaging`，工作区干净（或仅有规格文档）。

- [ ] **Step 2: 确认 Python 版本 ≥ 3.10**

```bash
python --version
```

Expected: `Python 3.10.x` 或更高。3.10 是 PyWebView 5.x 与 SQLAlchemy 2.0 的最低要求。

- [ ] **Step 3: 确认仓库根没有遗留 `.venv`/`venv`**

```bash
ls -d .venv venv 2>/dev/null || echo "no venv"
```

Expected: `no venv`（如果已有 venv，跳过 0.2 的创建步骤，但仍执行升级 pip 与安装依赖）。

---

### Task 0.2: 创建虚拟环境并更新 `.gitignore`

**Files:**
- Create: `.venv/`（由命令生成）
- Modify: `.gitignore`

- [ ] **Step 1: 创建 venv**

```bash
cd F:/CODE/TiShiNengRunning
python -m venv .venv
```

Expected: 生成 `.venv/Scripts/python.exe`。

- [ ] **Step 2: 升级 pip**

```bash
.venv/Scripts/python -m pip install --upgrade pip
```

Expected: 输出 `Successfully installed pip-<version>`。

- [ ] **Step 3: 检查/创建 `.gitignore`**

如果 `.gitignore` 已存在，读出当前内容；若没有则创建。最终至少包含下列条目（已有的不重复）：

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Build artifacts
dist/
build/
*.spec.bak

# App runtime data (portable layout)
tsn_data.db
tsn_data.db-journal
face_images/
logs/
config.json

# IDE
.vscode/
.idea/

# Brainstorming
.superpowers/
```

写入或合并完毕。

- [ ] **Step 4: 提交 `.gitignore`**

```bash
git add .gitignore
git commit -m "chore: 完善 .gitignore（venv/打包产物/便携数据）"
```

---

### Task 0.3: 写入 requirements 文件

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`

- [ ] **Step 1: 检查现有 `requirements.txt`**

```bash
cat requirements.txt
```

> 现有文件用 UTF-16 编码（每个字符前有空字节），需重写为 UTF-8。

- [ ] **Step 2: 重写 `requirements.txt`（UTF-8）**

完整内容：

```
aiosqlite==0.21.0
geopy==2.4.1
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
loguru==0.7.3
numpy==2.3.4
pillow==12.0.0
pycryptodome==3.23.0
requests==2.32.5
rsa==4.9.1
shapely==2.1.2
SQLAlchemy==2.0.44
typing_extensions==4.15.0
urllib3==2.5.0
fastapi==0.115.0
uvicorn==0.32.0
pywebview==5.3.2
pydantic==2.9.2
```

写入时使用 UTF-8 无 BOM。

- [ ] **Step 3: 新建 `requirements-dev.txt`**

```
pyinstaller==6.10.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 4: 安装依赖**

```bash
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip install -r requirements-dev.txt
```

Expected: 两条命令各自以 `Successfully installed ...` 结束，无 ERROR。

- [ ] **Step 5: 验证关键依赖可导入**

```bash
.venv/Scripts/python -c "import fastapi, uvicorn, webview, pydantic, pytest, PyInstaller; print('OK')"
```

Expected: 输出 `OK`。

- [ ] **Step 6: 提交**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "chore: 新增 GUI/打包/测试依赖"
```

---

## Phase 1 · 后端进度 hook（非侵入式）

> 这一阶段的核心目标：**让 `TsnRunServer` / `startSpider` 能向外发进度事件，但 CLI 路径 `main.py` 行为 100% 不变**。

### Task 1.1: 给 TsnRunServer 添加 `progress_callback` + `_emit`（TDD）

**Files:**
- Modify: `tsnRunServer.py:42-69`（`__init__`）、新增 `_emit` 方法
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_run_server_progress.py`

- [ ] **Step 1: 创建 `tests/__init__.py`（空文件）**

```python
```

- [ ] **Step 2: 创建 `tests/conftest.py`**

```python
"""pytest 共享配置。开启 asyncio 自动模式，集中管理事件循环作用域。"""
import pytest


# 让 pytest-asyncio 自动识别 async 测试，无需每个用例标 @pytest.mark.asyncio
def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("asyncio"):
            continue
        if item.function.__code__.co_flags & 0x100:  # CO_COROUTINE
            item.add_marker(pytest.mark.asyncio)
```

并在仓库根（与 `tests/` 平级）创建/追加 `pytest.ini`：

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: 写第一个失败测试 — 默认无 callback 时 `_emit` 不抛错**

`tests/test_run_server_progress.py`：

```python
"""TsnRunServer 进度回调契约测试。

保证两件事：
1. 不传 callback 时，新增的 _emit 方法是 no-op，不影响 CLI 行为。
2. 传 callback 时，按规格表的 phase 顺序回调。
"""
from unittest.mock import MagicMock

from tsnRunServer import TsnRunServer, TsnRunType


def test_emit_without_callback_is_noop():
    """不传 progress_callback 时，_emit 静默执行，不抛异常。"""
    server = TsnRunServer(accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom)
    # 不应抛任何异常
    server._emit("preparing", msg="加载账号...")
    server._emit("running", elapsed_s=10, total_s=900, distance_km=0.1)


def test_emit_with_callback_invokes_it():
    """传入 callback 时，_emit 把 phase 和额外字段作为 dict 传出去。"""
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )
    server._emit("preparing", msg="加载账号...")
    cb.assert_called_once_with({"phase": "preparing", "msg": "加载账号..."})


def test_emit_swallows_callback_exception():
    """callback 抛异常时，_emit 必须吞掉，不影响主流程。"""
    def boom(evt):
        raise RuntimeError("callback failed")

    server = TsnRunServer(
        accountId=1, runKiloMeter=3.0, logRunType=TsnRunType.freedom,
        progress_callback=boom,
    )
    # 不应抛异常
    server._emit("preparing", msg="test")
```

- [ ] **Step 4: 运行测试确认失败**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py -v
```

Expected: 3 个测试都失败，原因是 `TsnRunServer.__init__` 不接受 `progress_callback`，也没有 `_emit` 方法。

- [ ] **Step 5: 实现 `__init__` 接收 callback + 新增 `_emit`**

修改 `tsnRunServer.py`。在文件顶部 import 区追加：

```python
from typing import Callable, Optional
```

修改 `TsnRunServer.__init__` 签名为：

```python
    def __init__(self, accountId: int, runKiloMeter: float, logRunType: TsnRunType,
                 progress_callback: Optional[Callable[[dict], None]] = None):
        self.accountId = accountId
        self.runKiloMeter = runKiloMeter
        self.logRunType = logRunType

        self.accountModel: TsnAccount_Model | None = None
        self.tsnClient = None
        self.identify = None
        self.start_timestamp = None
        self.exerciseSetting = None
        self.geofence = None
        self.endStride = None
        self.limitSpeed = None
        self.endLimitStepFrequency = None
        self.pointList = None
        self.isMongoPath = True
        self.isPublic = False
        self.isFaceStatus = 1
        self.planUseTime = None

        self.needRunKm = None

        self.isStartFace = 0
        self.isEndFace = 0
        self.isMidwayFace = 0
        self.middleFaces = []
        self.startLongitude = 0
        self.startLatitude = 0

        self._progress_callback = progress_callback
```

并在 `__init__` 与 `publicRunTypeConvert` 之间插入：

```python
    def _emit(self, phase: str, **kw) -> None:
        """向外推送一次进度事件。回调缺失或抛异常时静默，绝不影响主流程。"""
        if self._progress_callback is None:
            return
        try:
            self._progress_callback({"phase": phase, **kw})
        except Exception:  # noqa: BLE001 — 故意吞掉，回调失败不能影响跑步
            logger.warning("progress_callback raised; ignored")
```

- [ ] **Step 6: 运行测试通过**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py -v
```

Expected: 3 个用例全部 PASS。

- [ ] **Step 7: 确认 CLI 零回归（不传 callback 仍能实例化）**

```bash
.venv/Scripts/python -c "from tsnRunServer import TsnRunServer, TsnRunType; s = TsnRunServer(1, 3.0, TsnRunType.freedom); print('OK')"
```

Expected: 输出 `OK`。

- [ ] **Step 8: 提交**

```bash
git add tsnRunServer.py tests/__init__.py tests/conftest.py tests/test_run_server_progress.py pytest.ini
git commit -m "feat(run-server): 添加可选 progress_callback 与 _emit（非侵入）"
```

---

### Task 1.2: 在 `startRun` 各阶段插入 emit 调用（TDD）

**Files:**
- Modify: `tsnRunServer.py`（`startRun` 方法中插入 `self._emit(...)`）
- Modify: `tests/test_run_server_progress.py`（追加测试）

- [ ] **Step 1: 写失败测试 — 校验 phase 序列**

在 `tests/test_run_server_progress.py` 末尾追加：

```python
import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_start_run_emits_phase_sequence_private():
    """私版账号跑步：startRun 应按 preparing → path_gen → 完成前的阶段顺序 emit。"""
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=0.1, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )

    # 全 mock 掉外部依赖
    fake_account = MagicMock()
    fake_account.id = 1
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "TEST"
    fake_client.sportRecordSetting = AsyncMock(return_value={
        "freedom": 0, "sunRun": 0, "morningRun": 0,
    })
    fake_client.getSportSetting = AsyncMock(return_value={
        "identify": "id-1", "geofence": {}, "list": [],
        "totalRange": 0.05,
    })
    fake_client.getRunningStartTime = AsyncMock(return_value={"startTime": 1700000000000})

    async def fake_get_db():
        yield MagicMock()

    with patch("tsnRunServer.getTsnAccountByid", AsyncMock(return_value=fake_account)), \
         patch("tsnRunServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("tsnRunServer.get_db", fake_get_db), \
         patch.object(TsnRunServer, "queryPath", AsyncMock(return_value=[[100.0, 30.0], [100.001, 30.001]])), \
         patch.object(TsnRunServer, "uploadRunPath", AsyncMock(return_value=None)), \
         patch("tsnRunServer.genTiShiNengRunPathRepeat", return_value=([{"a":1,"o":2,"t":1700000000000}], [1], 100.0)), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):
        await server.startRun()

    phases = [call.args[0]["phase"] for call in cb.call_args_list]
    # 至少包含 preparing 和 path_gen；这两个是 startRun 起步与路径生成阶段的关键标记
    assert "preparing" in phases, f"phases={phases}"
    assert "path_gen" in phases, f"phases={phases}"
    # preparing 应早于 path_gen
    assert phases.index("preparing") < phases.index("path_gen")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py::test_start_run_emits_phase_sequence_private -v
```

Expected: FAIL，断言 `"preparing" in phases` 失败。

- [ ] **Step 3: 在 startRun 中插入 emit**

修改 `tsnRunServer.py` 的 `startRun` 方法。**不改任何已有代码**，仅插入 3 处 `self._emit(...)`。用 Edit 工具按下面三个精确替换：

**插入点 1（startRun 第一行）：** 把

```python
    async def startRun(self):
        async for newDb in get_db():
```

替换为

```python
    async def startRun(self):
        self._emit("preparing", msg="加载账号信息...")
        async for newDb in get_db():
```

**插入点 2（queryPath 调用前）：** 把

```python
        runLinePath = await self.queryPath()
        startPoint = runLinePath[0]
```

替换为

```python
        self._emit("path_gen", msg="生成跑步路径...")
        runLinePath = await self.queryPath()
        startPoint = runLinePath[0]
```

**插入点 3（开始人脸识别前）：** 把

```python
        if self.isStartFace == 1:
            logger.info('开始人脸识别')
```

替换为

```python
        if self.isStartFace == 1:
            self._emit("face_start", msg="开始人脸验证...")
            logger.info('开始人脸识别')
```

- [ ] **Step 4: 运行测试通过**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py -v
```

Expected: 全部 PASS（4 个测试）。

- [ ] **Step 5: CLI 烟雾验证（实例化 + import 不出错）**

```bash
.venv/Scripts/python -c "from main import TsnCliManager; print('OK')"
```

Expected: 输出 `OK`。

- [ ] **Step 6: 提交**

```bash
git add tsnRunServer.py tests/test_run_server_progress.py
git commit -m "feat(run-server): startRun 各阶段 emit 进度事件"
```

---

### Task 1.3: 改造 `uploadRunPath` — 固定 sleep 换为 2 秒心跳循环（TDD）

**Files:**
- Modify: `tsnRunServer.py`（`uploadRunPath`，原 `tsnRunServer.py:292-411`）
- Modify: `tests/test_run_server_progress.py`

- [ ] **Step 1: 写失败测试 — 心跳循环至少发出一次 `running` 事件**

`tests/test_run_server_progress.py` 末尾追加：

```python
@pytest.mark.asyncio
async def test_upload_run_path_heartbeats_running_events(monkeypatch):
    """uploadRunPath 在等待跑步真实结束期间，应周期性 emit running 事件。

    用 fake time.time 制造一个需要等待 ~6 秒的场景，2 秒心跳应至少触发 2~3 次。
    """
    cb = MagicMock()
    server = TsnRunServer(
        accountId=1, runKiloMeter=0.5, logRunType=TsnRunType.freedom,
        progress_callback=cb,
    )
    server.isPublic = False
    server.start_timestamp = 1_700_000_000_000  # 毫秒
    server.identify = "id-1"
    server.geofence = {}
    server.pointList = []
    server.isEndFace = 0
    server.exerciseSetting = {}
    server.endStride = 0
    server.limitSpeed = 0
    server.endLimitStepFrequency = 0

    # 模拟 path 让 endTime = start + 6 秒
    path = [{"longitude": 1.0, "latitude": 2.0, "time": 1_700_000_006_000}]

    # 把 tsnClient 全部 mock
    server.tsnClient = MagicMock()
    server.tsnClient.appAddSportRecord = AsyncMock(return_value={})
    server.tsnClient.sumSportRecord = AsyncMock(return_value={})
    server.tsnClient.appSportRecordList = AsyncMock(
        return_value={"data": [{"sportStatus": 1, "remark": ""}]}
    )

    # 让 time.time 返回 endTime - 6s（即剩余 6 秒）
    fake_now = [1_700_000_000.0]
    monkeypatch.setattr("tsnRunServer.time.time", lambda: fake_now[0])

    # 加速 sleep：每次 sleep 把 fake_now 推进对应秒数后立即返回
    async def fast_sleep(sec):
        fake_now[0] += sec
    monkeypatch.setattr("tsnRunServer.asyncio.sleep", fast_sleep)

    await server.uploadRunPath(path, stepNumbers=[10], sumDistance=500.0)

    phases = [c.args[0]["phase"] for c in cb.call_args_list]
    running_count = sum(1 for p in phases if p == "running")
    assert running_count >= 2, f"heartbeat 应至少触发 2 次，实际 {running_count}, phases={phases}"
    assert "uploading" in phases, f"上传阶段需 emit，phases={phases}"
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py::test_upload_run_path_heartbeats_running_events -v
```

Expected: FAIL（当前 uploadRunPath 一次性 sleep，不发心跳）。

- [ ] **Step 3: 改造 `uploadRunPath`**

把 `tsnRunServer.py:312-328` 的固定 sleep 块替换。原代码：

```python
        sleepTime = int(endTime) / 1000 - time.time()
        taskList = []
        logger.info(f'等待{sleepTime}秒')
        taskList.append(asyncio.sleep(sleepTime))
        middleFacePoints = []
        logger.info(middleFacePoints)
        for middleFaceItem in middleFacePoints:
            if sleepTime > 0:
                middleUsedTime = int(middleFaceItem['timestamp']) / 1000 - time.time()
                if middleUsedTime < 0:
                    middleUsedTime = 0
            else:
                middleUsedTime = 0
            latitude = middleFaceItem['latitude']
            longitude = middleFaceItem['longitude']
            coordinates = f"{latitude},{longitude}"
            taskList.append(self.uploadFace(coordinates=coordinates, sleep=middleUsedTime, faceType=2))
        await asyncio.gather(*taskList)
```

改为：

```python
        sleepTime = int(endTime) / 1000 - time.time()
        logger.info(f'等待{sleepTime}秒')

        # 中途人脸任务保持原行为（当前 middleFacePoints 总是空，但保留扩展点）
        middleFacePoints = []
        logger.info(middleFacePoints)
        midface_tasks = []
        for middleFaceItem in middleFacePoints:
            if sleepTime > 0:
                middleUsedTime = int(middleFaceItem['timestamp']) / 1000 - time.time()
                if middleUsedTime < 0:
                    middleUsedTime = 0
            else:
                middleUsedTime = 0
            latitude = middleFaceItem['latitude']
            longitude = middleFaceItem['longitude']
            coordinates = f"{latitude},{longitude}"
            midface_tasks.append(self.uploadFace(coordinates=coordinates, sleep=middleUsedTime, faceType=2))

        # 2 秒心跳循环替换一次性 sleep —— 既能 emit 进度，又能响应 task.cancel()
        if sleepTime > 0:
            total = sleepTime
            elapsed = 0.0
            while elapsed < total:
                tick = min(2.0, total - elapsed)
                # emit 当前进度（distance 估算：按比例线性推进）
                progress_ratio = elapsed / total if total > 0 else 1.0
                self._emit(
                    "running",
                    elapsed_s=int(elapsed),
                    total_s=int(total),
                    distance_km=round(sumDistance / 1000 * progress_ratio, 3),
                )
                await asyncio.sleep(tick)
                elapsed += tick

        # 心跳结束后并行执行中途人脸（保持原顺序：先等待，再人脸）
        if midface_tasks:
            await asyncio.gather(*midface_tasks)
```

接着在原 `logger.info('上传跑步数据')` 这一行（`tsnRunServer.py:347`）之前插入：

```python
        self._emit("uploading", msg="上传运动记录...")
```

如果 `self.isEndFace == 1` 块存在，在 `logger.info('结束跑人脸识别')` 之前插入：

```python
            self._emit("face_end", msg="结束人脸验证...")
```

**不要修改其他业务逻辑** —— 仅做上述插入与 sleep 块替换。

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/test_run_server_progress.py -v
```

Expected: 全部 5 个用例 PASS。

- [ ] **Step 5: 提交**

```bash
git add tsnRunServer.py tests/test_run_server_progress.py
git commit -m "feat(run-server): uploadRunPath 用 2 秒心跳循环 + uploading/face_end 进度"
```

---

### Task 1.4: `spiderServer.startSpider` 添加 `progress_callback`

**Files:**
- Modify: `spiderServer.py:106`（`startSpider` 签名 + 内部 emit）
- Create: `tests/test_spider_progress.py`

- [ ] **Step 1: 写失败测试**

`tests/test_spider_progress.py`：

```python
"""startSpider 进度回调契约测试。"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import spiderServer


@pytest.mark.asyncio
async def test_start_spider_no_callback_still_works():
    """不传 callback 时行为不变（兼容 CLI 调用）。"""
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "T"
    fake_client.appSportRecordList = AsyncMock(return_value={"data": []})

    async def fake_get_db():
        yield MagicMock()

    with patch("spiderServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("spiderServer.get_db", fake_get_db):
        # 不抛异常即通过
        await spiderServer.startSpider(accountId=1)


@pytest.mark.asyncio
async def test_start_spider_emits_progress_when_callback_given():
    """传 callback 时，应在抓到记录后 emit 至少一次 'crawling' 事件。"""
    cb = MagicMock()
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "T"
    # 第一页一条 sportStatus==1 的记录；第二页空 → 跳出
    fake_client.appSportRecordList = AsyncMock(side_effect=[
        {"data": [{"id": "rec-1", "sportStatus": 1}]},
        {"data": []},
    ])
    fake_client.getSportRecordId = AsyncMock(return_value={
        "sportStatus": 1, "stepNumbers": [600], "id": "rec-1",
    })

    async def fake_get_db():
        yield MagicMock()

    with patch("spiderServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("spiderServer.get_db", fake_get_db), \
         patch("spiderServer.processRawAndAddDateBase", AsyncMock(return_value=None)):
        await spiderServer.startSpider(accountId=1, progress_callback=cb)

    phases = [c.args[0]["phase"] for c in cb.call_args_list]
    assert "crawling" in phases, f"phases={phases}"
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/test_spider_progress.py -v
```

Expected: 第二个用例 FAIL（`progress_callback` 参数不被接受）。

- [ ] **Step 3: 修改 `spiderServer.startSpider`**

把 `spiderServer.py:106` 的签名和函数体改为：

```python
from typing import Callable, Optional


async def startSpider(accountId: int,
                      progress_callback: Optional[Callable[[dict], None]] = None) -> None:
    def _emit(phase: str, **kw):
        if progress_callback is None:
            return
        try:
            progress_callback({"phase": phase, **kw})
        except Exception:  # noqa: BLE001
            logger.warning("progress_callback raised; ignored")

    tsnClient: TiShiNengPrivate | TiShiNengSdkPublic | None = None
    async for newDb in get_db():
        tsnClient = await getTsnClientById(accountId, newDb)

    _emit("preparing", msg="加载账号客户端...")

    if tsnClient.isPublic():
        baseRecord = await tsnClient.listExerciseRecord(1, '', 1)
        dates = baseRecord['dates']
        total_records_seen = 0
        for date in dates:
            recodeIdList = []
            for pageIndex in range(1, 10):
                recodeList = await tsnClient.listExerciseRecord(1, date['date'], pageIndex)
                breakFlag = False
                for i in recodeList['records']:
                    if i['id'] in recodeIdList:
                        breakFlag = True
                        break
                    else:
                        recodeIdList.append(i['id'])
                if breakFlag:
                    break
            logger.info(recodeIdList)
            for i in recodeIdList:
                rawRecord = await tsnClient.getExerciseRecord(i)
                if rawRecord['sportType'] != '0' and int(rawRecord['step']) >= 500:
                    logger.info(f" {tsnClient.schoolCode} {rawRecord}")
                    await processRawAndAddDateBase(tsnClient.schoolCode, rawRecord)
                    total_records_seen += 1
                    _emit("crawling", current=total_records_seen)
    else:
        recodeIdList = []
        for pageIndex in range(1, 10):
            resp = await tsnClient.appSportRecordList(2, pageIndex, 10)
            if 'data' not in resp:
                break
            breakFlag = False
            for data in resp['data']:
                if data['sportStatus'] != 1:
                    continue
                if data['id'] in recodeIdList:
                    breakFlag = True
                    break
                else:
                    recodeIdList.append(data['id'])
            if breakFlag:
                break
        for idx, i in enumerate(recodeIdList, 1):
            rawRecord = await tsnClient.getSportRecordId(i)
            if int(rawRecord['sportStatus']) == 1 and sum(rawRecord['stepNumbers']) >= 500:
                await processRawAndAddDateBase(tsnClient.schoolCode, rawRecord, isPublic=False)
                _emit("crawling", current=idx, total=len(recodeIdList))

    _emit("done")
```

> 注意：保留所有原始判断（`>= 500`、`sportType != '0'`、breakFlag 等），只是包裹与追加 emit。

- [ ] **Step 4: 测试通过**

```bash
.venv/Scripts/python -m pytest tests/test_spider_progress.py -v
```

Expected: 全部 PASS。

- [ ] **Step 5: 回归 — 现有 main.py 调用方式仍兼容**

```bash
.venv/Scripts/python -c "from spiderServer import startSpider; import inspect; sig = inspect.signature(startSpider); assert 'accountId' in sig.parameters; assert sig.parameters['progress_callback'].default is None; print('OK')"
```

Expected: 输出 `OK`。

- [ ] **Step 6: 提交**

```bash
git add spiderServer.py tests/test_spider_progress.py
git commit -m "feat(spider): startSpider 增加可选 progress_callback"
```

---

## Phase 2 · webapp 骨架（路径、总线、token、server）

### Task 2.1: 路径解析模块 `webapp/paths.py`

**Files:**
- Create: `webapp/__init__.py`
- Create: `webapp/paths.py`
- Create: `tests/webapp/__init__.py`
- Create: `tests/webapp/test_paths.py`

- [ ] **Step 1: 写失败测试**

`tests/webapp/__init__.py`：（空）

```python
```

`tests/webapp/test_paths.py`：

```python
"""路径解析模块测试。"""
import sys
from pathlib import Path

import webapp.paths as paths_mod


def test_data_dir_dev_uses_cwd_parent_of_paths(tmp_path, monkeypatch):
    """开发模式（非冻结）下 data_dir 应等于项目根。"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(paths_mod, "_OVERRIDE_DATA_DIR", None, raising=False)
    d = paths_mod.data_dir()
    # 项目根至少应是 webapp 目录的父目录
    assert (d / "webapp").is_dir() or d.is_dir()


def test_data_dir_frozen_uses_executable_dir(tmp_path, monkeypatch):
    """冻结模式（PyInstaller）下 data_dir 应等于 sys.executable 同目录。"""
    fake_exe = tmp_path / "TiShiNeng.exe"
    fake_exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(paths_mod, "_OVERRIDE_DATA_DIR", None, raising=False)
    assert paths_mod.data_dir() == tmp_path


def test_set_data_dir_override(tmp_path):
    """允许测试/外部代码通过 set_data_dir 覆盖（测试隔离用）。"""
    paths_mod.set_data_dir(tmp_path)
    try:
        assert paths_mod.data_dir() == tmp_path
        assert paths_mod.face_images_dir() == tmp_path / "face_images"
        assert paths_mod.logs_dir() == tmp_path / "logs"
        # 自动 mkdir
        assert paths_mod.face_images_dir().is_dir()
        assert paths_mod.logs_dir().is_dir()
    finally:
        paths_mod.set_data_dir(None)


def test_frontend_dir_dev(monkeypatch):
    """开发模式下 frontend_dir 是仓库内的 frontend/。"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    fd = paths_mod.frontend_dir()
    assert fd.name == "frontend"


def test_frontend_dir_frozen_uses_meipass(tmp_path, monkeypatch):
    """冻结模式下 frontend_dir 来自 sys._MEIPASS。"""
    meipass = tmp_path / "_MEI123"
    (meipass / "frontend").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert paths_mod.frontend_dir() == meipass / "frontend"
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_paths.py -v
```

Expected: 5 个用例 FAIL（模块尚不存在）。

- [ ] **Step 3: 创建 `webapp/__init__.py`（空标识）**

```python
```

- [ ] **Step 4: 创建 `webapp/paths.py`**

```python
"""数据/资源路径解析。

便携式布局：所有可写数据放在 exe 同目录（冻结模式）或项目根（开发模式）。
前端静态资源在冻结模式下从 PyInstaller `_MEIPASS` 临时解压目录读取。
"""
import sys
from pathlib import Path
from typing import Optional

_OVERRIDE_DATA_DIR: Optional[Path] = None


def set_data_dir(path: Optional[Path]) -> None:
    """测试或外部代码用：临时覆盖 data_dir 返回值。传 None 复位。"""
    global _OVERRIDE_DATA_DIR
    _OVERRIDE_DATA_DIR = path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """开发模式下的仓库根目录 = paths.py 文件向上两级（webapp/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """可写数据根目录。冻结 → exe 同目录；开发 → 项目根。"""
    if _OVERRIDE_DATA_DIR is not None:
        return _OVERRIDE_DATA_DIR
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return project_root()


def db_path() -> Path:
    """SQLite 文件路径。"""
    return data_dir() / "tsn_data.db"


def face_images_dir() -> Path:
    """人脸图片目录，自动创建。"""
    p = data_dir() / "face_images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """日志目录，自动创建。"""
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    """前端/后端共享的 config.json。"""
    return data_dir() / "config.json"


def frontend_dir() -> Path:
    """前端静态资源目录。冻结 → _MEIPASS/frontend；开发 → 项目根/frontend。"""
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "frontend"
    return project_root() / "frontend"
```

- [ ] **Step 5: 测试通过**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_paths.py -v
```

Expected: 5 个用例 PASS。

- [ ] **Step 6: 提交**

```bash
git add webapp/__init__.py webapp/paths.py tests/webapp/__init__.py tests/webapp/test_paths.py
git commit -m "feat(webapp): paths.py 数据/前端路径解析（冻结/开发双模式）"
```

---

### Task 2.2: 进度事件总线 `webapp/progress.py`

**Files:**
- Create: `webapp/progress.py`
- Create: `tests/webapp/test_progress_bus.py`

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_progress_bus.py`：

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_progress_bus.py -v
```

Expected: 4 个用例 FAIL（`webapp.progress` 不存在）。

- [ ] **Step 3: 创建 `webapp/progress.py`**

```python
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
```

- [ ] **Step 4: 测试通过**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_progress_bus.py -v
```

Expected: 4 个 PASS。

- [ ] **Step 5: 提交**

```bash
git add webapp/progress.py tests/webapp/test_progress_bus.py
git commit -m "feat(webapp): progress.Bus 事件总线（按 task_id 广播）"
```

---

### Task 2.3: token 校验依赖 `webapp/deps.py`

**Files:**
- Create: `webapp/deps.py`
- Create: `tests/webapp/conftest.py`

- [ ] **Step 1: 创建 `tests/webapp/conftest.py`**

```python
"""webapp 测试公共 fixture：TestClient、临时数据目录。"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import webapp.paths as paths_mod


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """每个测试一个干净的数据目录。"""
    paths_mod.set_data_dir(tmp_path)
    # 强制 database.py 用临时 SQLite
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'tsn_data.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    yield tmp_path
    paths_mod.set_data_dir(None)


@pytest.fixture
def api_token() -> str:
    return "test-token-12345"


@pytest.fixture
def client(tmp_data_dir, api_token):
    """构建 FastAPI TestClient，注入固定 token。"""
    from webapp.server import create_app
    app = create_app(api_token=api_token)
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 2: 创建 `webapp/deps.py`**

```python
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
```

- [ ] **Step 3: 提交（测试在 2.4 完成）**

```bash
git add webapp/deps.py tests/webapp/conftest.py
git commit -m "feat(webapp): deps 依赖（token 校验 / DB session）"
```

---

### Task 2.4: FastAPI app 工厂 + uvicorn 启动器 `webapp/server.py`

**Files:**
- Create: `webapp/server.py`
- Create: `webapp/routers/__init__.py`
- Create: `webapp/routers/bootstrap.py`
- Create: `tests/webapp/test_bootstrap.py`

- [ ] **Step 1: 写失败测试 — `/api/bootstrap` 行为**

`tests/webapp/test_bootstrap.py`：

```python
"""bootstrap 端点：token 校验最小用例。"""


def test_bootstrap_without_token_returns_401(client):
    resp = client.get("/api/bootstrap")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["code"] == "BAD_TOKEN"


def test_bootstrap_with_wrong_token_returns_401(client):
    resp = client.get("/api/bootstrap", headers={"X-API-Token": "wrong"})
    assert resp.status_code == 401


def test_bootstrap_with_correct_token_returns_200(client, api_token):
    resp = client.get("/api/bootstrap", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_root_serves_index_html(client, tmp_data_dir, monkeypatch):
    """根路径 / 应返回 frontend/index.html。"""
    # 简单造一个 index.html
    import webapp.paths as paths_mod
    frontend = paths_mod.project_root() / "frontend"
    # 测试环境用真实仓库的 frontend；若不存在则跳过
    if not (frontend / "index.html").exists():
        import pytest
        pytest.skip("frontend/index.html 尚未创建")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
```

- [ ] **Step 2: 创建 `webapp/routers/__init__.py`（空）**

```python
```

- [ ] **Step 3: 创建 `webapp/routers/bootstrap.py`**

```python
"""GET /api/bootstrap — 前端启动握手，校验 token 有效。"""
from fastapi import APIRouter, Depends

from webapp.deps import require_token

router = APIRouter(prefix="/api", tags=["bootstrap"])

APP_VERSION = "0.1.0"


@router.get("/bootstrap", dependencies=[Depends(require_token)])
async def bootstrap() -> dict:
    return {"status": "ok", "version": APP_VERSION}
```

- [ ] **Step 4: 创建 `webapp/server.py`**

```python
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

    # 全局异常 → 统一 {code, msg}
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
        config = uvicorn.Config(self.app, host=self.host, port=self.port,
                                log_level="info", access_log=False, lifespan="on")
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
```

- [ ] **Step 5: 创建最小的 `frontend/index.html` 占位（让根路由能返回 200）**

```html
<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>TiShiNeng</title></head>
<body><div id="app">加载中...</div></body></html>
```

- [ ] **Step 6: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_bootstrap.py -v
```

Expected: 4 个用例 PASS。

- [ ] **Step 7: 提交**

```bash
git add webapp/server.py webapp/routers/__init__.py webapp/routers/bootstrap.py tests/webapp/test_bootstrap.py frontend/index.html
git commit -m "feat(webapp): FastAPI app 工厂 + uvicorn 线程启动 + bootstrap 路由"
```

---

## Phase 3 · 学校 / 账号路由

### Task 3.1: 学校路由 `webapp/routers/schools.py`

**Files:**
- Create: `webapp/routers/schools.py`
- Create: `tests/webapp/test_schools.py`
- Modify: `webapp/server.py`（include_router）

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_schools.py`：

```python
"""学校列表/刷新端点测试。外部 HTTP 全 mock。"""
from unittest.mock import AsyncMock, patch


def test_list_schools_empty(client, api_token):
    """没有学校时返回空数组。"""
    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_refresh_schools_calls_sdk_and_persists(client, api_token, monkeypatch):
    """触发刷新：mock 掉 SDK，看到学校落库。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "北京"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{
            "school_id": 101, "school_name": "测试大学",
            "school_url": "https://example.com", "openId": "open-1",
            "isOpenKeep": "1", "isOpenLive": "0", "isOpenEncry": "0",
            "sysType": "1", "schoolCode": "TEST101",
        }]
    })

    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        resp = client.post("/api/schools/refresh",
                           headers={"X-API-Token": api_token})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    # 再查列表
    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(s["school_name"] == "测试大学" for s in items)


def test_refresh_filters_demo_and_test(client, api_token):
    """名字含 demo/test 的学校应被过滤。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "X"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [
            {"school_id": 1, "school_name": "demo school", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C1"},
            {"school_id": 2, "school_name": "Test 学院", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C2"},
            {"school_id": 3, "school_name": "真实学校", "school_url": "u",
             "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
             "sysType": "1", "schoolCode": "C3"},
        ]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        resp = client.post("/api/schools/refresh",
                           headers={"X-API-Token": api_token})
        assert resp.status_code == 200

    resp = client.get("/api/schools", headers={"X-API-Token": api_token})
    items = resp.json()["items"]
    names = {s["school_name"] for s in items}
    assert "真实学校" in names
    assert "demo school" not in names
    assert "Test 学院" not in names
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_schools.py -v
```

Expected: 全部 FAIL（路由未注册）。

- [ ] **Step 3: 创建 `webapp/routers/schools.py`**

```python
"""学校列表与刷新。

GET  /api/schools           — 返回当前数据库中的学校
POST /api/schools/refresh   — 调用 SDK 重新拉取并落库
"""
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from TiShiNengSdkPrivate import TiShiNengPrivate
from models import TsnSchool_Model
from services.tsnSchool.tsnSchoolDao import addOrUpdateSchool
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/schools", tags=["schools"], dependencies=[Depends(require_token)])


def _make_client() -> TiShiNengPrivate:
    """构造一个匿名 SDK 客户端用于查询省份/学校列表。可被测试 patch。"""
    return TiShiNengPrivate(1, 1, '', False, str(uuid.uuid4()), 'Xiaomi', '25053RT47C', "")


def _get_school_info(school_code: str) -> Optional[dict]:
    """对公版学校请求内网 URL。失败返回 None。"""
    try:
        url = f"https://h.tsnkj.com/upms/sysSchool/getSchoolInfo?schoolCode={school_code}"
        resp = httpx.get(url, headers={"User-Agent": "okhttp/4.9.0"}, timeout=10.0)
        return resp.json().get("data")
    except Exception as e:
        logger.debug(f"_get_school_info failed for {school_code}: {e}")
        return None


@router.get("")
async def list_schools(db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnSchool_Model).order_by(TsnSchool_Model.school_name)
    result = await db.execute(stmt)
    items = []
    for s in result.scalars().all():
        items.append({
            "school_id": s.school_id,
            "school_name": s.school_name,
            "sys_type": s.sys_type,  # 1 私版, 2 公版
            "school_code": s.school_code,
        })
    return {"items": items}


@router.post("/refresh")
async def refresh_schools(db: AsyncSession = Depends(get_db)) -> dict:
    tsn = _make_client()
    resp = await tsn.findAllProvince()
    if not resp or 'data' not in resp:
        return {"total": 0, "msg": "未获取到省份列表"}

    total = 0
    for province in resp['data']:
        plist = await tsn.listSchoolByProvinceId(province['province_id'])
        if not plist or 'data' not in plist:
            continue
        for school in plist['data']:
            name = school['school_name']
            if 'demo' in name.lower() or 'test' in name.lower():
                continue
            lan_url = None
            if school['sysType'] == '2':
                info = _get_school_info(school['schoolCode'])
                if info and info.get("url"):
                    lan_url = f"https://{info['url']}"
            await addOrUpdateSchool(
                school['school_id'], school['school_name'], school['school_url'],
                lan_url, school['openId'],
                school['isOpenKeep'] == '1',
                school['isOpenLive'] == '1',
                school['isOpenEncry'] == '1',
                int(school['sysType']), school['schoolCode'], db,
            )
            total += 1
    return {"total": total}
```

- [ ] **Step 4: 在 `webapp/server.py` 注册路由**

修改 `create_app` 中的 `app.include_router(bootstrap.router)` 下一行追加：

```python
    from webapp.routers import schools
    app.include_router(schools.router)
```

- [ ] **Step 5: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_schools.py -v
```

Expected: 3 个 PASS。

- [ ] **Step 6: 提交**

```bash
git add webapp/routers/schools.py webapp/server.py tests/webapp/test_schools.py
git commit -m "feat(webapp): /api/schools 列表与刷新"
```

---

### Task 3.2: 账号路由 `webapp/routers/accounts.py`

**Files:**
- Create: `webapp/routers/accounts.py`
- Create: `tests/webapp/test_accounts.py`
- Modify: `webapp/server.py`（include_router）

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_accounts.py`：

```python
"""账号 CRUD + 授权端点测试。"""
from unittest.mock import AsyncMock, patch


def _seed_school(client, api_token, monkeypatch):
    """辅助：插入一所测试学校。"""
    fake_tsn = AsyncMock()
    fake_tsn.findAllProvince = AsyncMock(return_value={
        "data": [{"province_id": "1", "province_name": "X"}]
    })
    fake_tsn.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 111, "school_name": "种子学校",
                  "school_url": "https://s.example.com", "openId": "o1",
                  "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "S111"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})


def test_list_accounts_empty(client, api_token):
    resp = client.get("/api/accounts", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_authorize_success(client, api_token, monkeypatch):
    _seed_school(client, api_token, monkeypatch)
    # mock 掉 tsnPasswordAuthServer
    async def fake_auth(school_id, username, password, session):
        # 模拟在 DB 里加一条账号
        from models import TsnAccount_Model
        acct = TsnAccount_Model(
            student_id="s1", user_id="111:u1", school_id=school_id,
            username=username, password=password,
            mobile_device_id="dev", access_token="tk",
            refresh_token="rt", expires_in=86399,
        )
        session.add(acct)
        await session.flush()
        return f"{school_id}:u1"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        resp = client.post("/api/accounts/authorize",
                           headers={"X-API-Token": api_token},
                           json={"school_id": 111, "username": "alice", "password": "pw"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "alice"
    assert body["school_id"] == 111


def test_authorize_wrong_password_returns_400(client, api_token, monkeypatch):
    _seed_school(client, api_token, monkeypatch)
    from TiShiNengError import TiShiNengError

    async def fake_auth(school_id, username, password, session):
        raise TiShiNengError("密码错误", code=10002)

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        resp = client.post("/api/accounts/authorize",
                           headers={"X-API-Token": api_token},
                           json={"school_id": 111, "username": "alice", "password": "bad"})

    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "10002"
    assert "密码" in body["msg"]


def test_delete_account(client, api_token, monkeypatch):
    """删除账号：先 seed 一条，然后 DELETE 应返回 200 并真正消失。"""
    _seed_school(client, api_token, monkeypatch)

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        acct = TsnAccount_Model(
            student_id="s", user_id="111:u2", school_id=school_id,
            username=username, password=password,
            mobile_device_id="d", access_token="tk",
            refresh_token="rt", expires_in=1,
        )
        session.add(acct)
        await session.flush()
        return f"{school_id}:u2"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 111, "username": "bob", "password": "pw"})
        account_id = r.json()["account_id"]

    # 删除
    resp = client.delete(f"/api/accounts/{account_id}",
                         headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    # 验证消失
    resp = client.get("/api/accounts", headers={"X-API-Token": api_token})
    assert all(a["id"] != account_id for a in resp.json()["items"])


def test_delete_nonexistent_returns_404(client, api_token):
    resp = client.delete("/api/accounts/99999",
                         headers={"X-API-Token": api_token})
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_accounts.py -v
```

Expected: 全 FAIL（路由未实现）。

- [ ] **Step 3: 创建 `webapp/routers/accounts.py`**

```python
"""账号 CRUD + 授权。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import tsnPasswordAuthServer
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/accounts", tags=["accounts"],
                   dependencies=[Depends(require_token)])


class AuthorizeBody(BaseModel):
    school_id: int = Field(..., description="学校 ID（来自 /api/schools）")
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


def _serialize(acct: TsnAccount_Model) -> dict:
    return {
        "id": acct.id,
        "username": acct.username,
        "school_id": acct.school_id,
        "school_name": acct.school.school_name if acct.school else None,
        "sys_type": acct.school.sys_type if acct.school else None,
    }


@router.get("")
async def list_accounts(db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnAccount_Model).options(selectinload(TsnAccount_Model.school))
    result = await db.execute(stmt)
    items = [_serialize(a) for a in result.scalars().all()]
    return {"items": items}


@router.post("/authorize")
async def authorize(body: AuthorizeBody, db: AsyncSession = Depends(get_db)) -> dict:
    # 失败由全局异常处理器返回 {code, msg}
    uid = await tsnPasswordAuthServer(body.school_id, body.username, body.password, db)
    # 取回刚刚保存的账号
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.username == body.username,
                   TsnAccount_Model.school_id == body.school_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=500,
                            detail={"code": "POST_AUTH_LOOKUP_FAILED",
                                    "msg": f"授权成功但未找到账号记录(uid={uid})"})
    return {"account_id": acct.id, **_serialize(acct)}


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnAccount_Model).where(TsnAccount_Model.id == account_id)
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})
    await db.execute(delete(TsnAccount_Model).where(TsnAccount_Model.id == account_id))
    await db.flush()
    return {"deleted": True}
```

- [ ] **Step 4: 在 `server.py` 注册**

`create_app` 内追加：

```python
    from webapp.routers import accounts
    app.include_router(accounts.router)
```

- [ ] **Step 5: 调整全局异常处理 — 让 `HTTPException(detail={...})` 直接透传 detail 作为响应体**

修改 `webapp/server.py` 的 `_on_exception`，**在它前面**追加专门的 HTTPException 处理：

```python
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

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
```

- [ ] **Step 6: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/webapp/ -v
```

Expected: bootstrap + schools + accounts + paths + progress_bus 全部 PASS（约 18 个用例）。

> ⚠️ 测试若因 `body["detail"]["code"]` 形态变化（exception handler 改造后变成顶层 `code`）失败，**修改 `test_bootstrap.py`** 中 `body["detail"]["code"]` 为 `body["code"]`，并把 401 用例 assert 同步调整。

- [ ] **Step 7: 提交**

```bash
git add webapp/routers/accounts.py webapp/server.py tests/webapp/test_accounts.py tests/webapp/test_bootstrap.py
git commit -m "feat(webapp): /api/accounts CRUD + 授权 + 统一错误响应"
```

---

## Phase 4 · 跑步 / 人脸 / 爬虫 / 里程 路由

### Task 4.1: 跑步路由 + WebSocket `webapp/routers/run.py`

**Files:**
- Create: `webapp/routers/run.py`
- Create: `tests/webapp/test_run.py`
- Modify: `webapp/server.py`（include_router）

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_run.py`：

```python
"""跑步路由测试：start → 立即返回 task_id；cancel → 终止；WS 推送 done。"""
import json
import threading
from unittest.mock import AsyncMock, patch


def _seed_account(client, api_token, monkeypatch):
    """种一个学校 + 一个账号，返回 account_id。"""
    from unittest.mock import AsyncMock as _AM
    fake_tsn = _AM()
    fake_tsn.findAllProvince = _AM(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake_tsn.listSchoolByProvinceId = _AM(return_value={
        "data": [{"school_id": 222, "school_name": "Run校", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "R222"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake_tsn):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(
            student_id="s", user_id="222:u", school_id=school_id,
            username=username, password=password, mobile_device_id="d",
            access_token="tk", refresh_token="rt", expires_in=1)
        session.add(a)
        await session.flush()
        return "222:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 222, "username": "runner", "password": "p"})
        return r.json()["account_id"]


def test_run_start_returns_task_id_immediately(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)

    # 让 TsnRunServer.startRunHandle 立刻返回 — 验证 start 端点不阻塞
    async def fake_start(self):
        return None

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=fake_start):
        resp = client.post("/api/run/start",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id, "run_type": "freedom",
                                 "distance_km": 0.5})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "task_id" in body
    assert len(body["task_id"]) > 0


def test_run_start_validates_run_type(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)
    resp = client.post("/api/run/start",
                       headers={"X-API-Token": api_token},
                       json={"account_id": account_id, "run_type": "invalid",
                             "distance_km": 0.5})
    assert resp.status_code == 422


def test_run_start_distance_must_be_positive(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)
    resp = client.post("/api/run/start",
                       headers={"X-API-Token": api_token},
                       json={"account_id": account_id, "run_type": "freedom",
                             "distance_km": -1.0})
    assert resp.status_code == 422


def test_run_cancel_terminates_task(client, api_token, monkeypatch):
    """start → cancel：取消应导致后台任务被 cancel。"""
    account_id = _seed_account(client, api_token, monkeypatch)
    started = threading.Event()
    cancelled = threading.Event()

    async def slow_run(self):
        try:
            started.set()
            import asyncio as _aio
            await _aio.sleep(60)
        except BaseException:
            cancelled.set()
            raise

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=slow_run):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        # 等待后台真的开始
        assert started.wait(2.0), "后台任务未启动"

        # 取消
        c = client.post("/api/run/cancel",
                        headers={"X-API-Token": api_token},
                        json={"task_id": task_id})
        assert c.status_code == 200

    # 等 cancel 落地
    assert cancelled.wait(2.0), "后台任务未收到 CancelledError"


def test_ws_progress_streams_events_until_done(client, api_token, monkeypatch):
    """WebSocket：start 后连上 /ws/progress?task=...，应收到 done 事件。"""
    account_id = _seed_account(client, api_token, monkeypatch)

    async def emitting_run(self):
        # 通过 _emit 推几个事件
        self._emit("preparing", msg="x")
        self._emit("running", elapsed_s=1, total_s=1, distance_km=0.1)

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=emitting_run):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        with client.websocket_connect(
                f"/ws/progress?task={task_id}&token={api_token}") as ws:
            phases = []
            for _ in range(10):
                msg = ws.receive_text()
                evt = json.loads(msg)
                phases.append(evt["phase"])
                if evt["phase"] in ("done", "error", "cancelled"):
                    break
            assert "done" in phases or "error" in phases, f"phases={phases}"


def test_ws_progress_rejects_bad_token(client, api_token, monkeypatch):
    account_id = _seed_account(client, api_token, monkeypatch)

    async def _noop(self):
        return None

    with patch("webapp.routers.run.TsnRunServer.startRunHandle", new=_noop):
        r = client.post("/api/run/start",
                        headers={"X-API-Token": api_token},
                        json={"account_id": account_id, "run_type": "freedom",
                              "distance_km": 0.5})
        task_id = r.json()["task_id"]

        import pytest
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                    f"/ws/progress?task={task_id}&token=WRONG") as ws:
                ws.receive_text()
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_run.py -v
```

Expected: 全 FAIL（路由不存在）。

- [ ] **Step 3: 创建 `webapp/routers/run.py`**

```python
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
```

- [ ] **Step 4: 在 `webapp/server.py` 注册**

`create_app` 内追加：

```python
    from webapp.routers import run as run_router
    app.include_router(run_router.router)
    app.include_router(run_router._ws_router)
```

- [ ] **Step 5: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_run.py -v
```

Expected: 6 个 PASS。

> 若 `test_ws_progress_streams_events_until_done` 不稳定（事件时序竞争），可在测试里在 connect 之前 `await asyncio.sleep(0)` —— 但 TestClient 不暴露事件循环。当前测试设计：start 注册任务时已经 `create_task`，但 `_do_run` 一开始可能比 ws connect 早完成（emitting_run 内只 emit 两次然后退出 → `bus.publish('done')`）。 由于 Bus 无历史缓冲，WS 必须先订阅再 publish。修复方法：在 emitting_run 里加一个让步 `await asyncio.sleep(0.05)`，让 WS 有机会订阅。如测试失败请按此调整：

```python
async def emitting_run(self):
    import asyncio as _aio
    await _aio.sleep(0.1)  # 让 WS 先订阅上
    self._emit("preparing", msg="x")
    self._emit("running", elapsed_s=1, total_s=1, distance_km=0.1)
```

- [ ] **Step 6: 提交**

```bash
git add webapp/routers/run.py webapp/server.py tests/webapp/test_run.py
git commit -m "feat(webapp): /api/run start/cancel + /ws/progress WebSocket"
```

---

### Task 4.2: 更新人脸路由 `webapp/routers/face.py`

**Files:**
- Create: `webapp/routers/face.py`
- Create: `tests/webapp/test_face.py`
- Modify: `webapp/server.py`

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_face.py`：

```python
"""更新人脸：把现有 main.py update_face_images 的核心包成端点。"""
from unittest.mock import AsyncMock, patch


def _seed_account(client, api_token):
    """同 test_run.py 的种子，复制以保持各测试文件自闭。"""
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 333, "school_name": "FaceX", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "F333"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id="333:u", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return "333:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 333, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_face_update_success(client, api_token):
    account_id = _seed_account(client, api_token)
    with patch("webapp.routers.face.TsnRunServer.getFaceImage",
               new=AsyncMock(return_value=b"fake-image-bytes")), \
         patch("webapp.routers.face.getTsnClientById",
               new=AsyncMock(return_value=AsyncMock(isPublic=lambda: False))):
        resp = client.post("/api/face/update",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


def test_face_update_no_account_returns_404(client, api_token):
    resp = client.post("/api/face/update",
                       headers={"X-API-Token": api_token},
                       json={"account_id": 99999})
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_face.py -v
```

Expected: 2 FAIL。

- [ ] **Step 3: 创建 `webapp/routers/face.py`**

```python
"""更新人脸图片端点。复用 TsnRunServer.getFaceImage（会自动下载并落盘）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import getTsnClientById
from tsnRunServer import TsnRunServer, TsnRunType
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/face", tags=["face"],
                   dependencies=[Depends(require_token)])


class FaceUpdateBody(BaseModel):
    account_id: int


@router.post("/update")
async def face_update(body: FaceUpdateBody, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.id == body.account_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})

    server = TsnRunServer(accountId=body.account_id, runKiloMeter=1.0,
                          logRunType=TsnRunType.freedom)
    server.accountModel = acct
    server.tsnClient = await getTsnClientById(acct.id, db)
    server.isPublic = server.tsnClient.isPublic()

    image_bytes = await server.getFaceImage()
    return {"updated": bool(image_bytes), "size": len(image_bytes) if image_bytes else 0}
```

- [ ] **Step 4: 在 `server.py` 注册**

`create_app` 内追加：

```python
    from webapp.routers import face
    app.include_router(face.router)
```

- [ ] **Step 5: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_face.py -v
```

Expected: 2 PASS。

- [ ] **Step 6: 提交**

```bash
git add webapp/routers/face.py webapp/server.py tests/webapp/test_face.py
git commit -m "feat(webapp): /api/face/update 更新人脸图片"
```

---

### Task 4.3: 路径爬取路由 `webapp/routers/spider.py`

**Files:**
- Create: `webapp/routers/spider.py`
- Create: `tests/webapp/test_spider_route.py`
- Modify: `webapp/server.py`

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_spider_route.py`：

```python
"""路径爬取路由测试。startSpider 已在 Phase 1 改为支持 callback；这里只需测端点能立即返回 task_id。"""
import threading
from unittest.mock import AsyncMock, patch


def _seed_account(client, api_token):
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 444, "school_name": "Spider校", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "1", "schoolCode": "P444"}]
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id="444:u", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return "444:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 444, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_spider_start_returns_task_id(client, api_token):
    account_id = _seed_account(client, api_token)

    async def fake_spider(account_id, progress_callback=None):
        if progress_callback:
            progress_callback({"phase": "crawling", "current": 1})

    with patch("webapp.routers.spider.startSpider", new=fake_spider):
        resp = client.post("/api/spider/start",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    assert "task_id" in resp.json()
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_spider_route.py -v
```

Expected: FAIL。

- [ ] **Step 3: 创建 `webapp/routers/spider.py`**

```python
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
```

- [ ] **Step 4: 注册到 server**

```python
    from webapp.routers import spider
    app.include_router(spider.router)
```

- [ ] **Step 5: 测试通过 + 提交**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_spider_route.py -v
git add webapp/routers/spider.py webapp/server.py tests/webapp/test_spider_route.py
git commit -m "feat(webapp): /api/spider/start 路径爬取（异步 + 进度复用 Bus）"
```

---

### Task 4.4: 里程查询路由 `webapp/routers/distance.py`

**Files:**
- Create: `webapp/routers/distance.py`
- Create: `tests/webapp/test_distance.py`
- Modify: `webapp/server.py`

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_distance.py`：

```python
"""里程查询：复用 main.py:495-650 的查询逻辑，但拍平成单端点。"""
from unittest.mock import AsyncMock, MagicMock, patch


def _seed_account(client, api_token):
    fake = AsyncMock()
    fake.findAllProvince = AsyncMock(return_value={"data": [{"province_id": "1", "province_name": "X"}]})
    fake.listSchoolByProvinceId = AsyncMock(return_value={
        "data": [{"school_id": 555, "school_name": "Dist校", "school_url": "u",
                  "openId": "o", "isOpenKeep": "0", "isOpenLive": "0", "isOpenEncry": "0",
                  "sysType": "2", "schoolCode": "D555"}]  # 公版
    })
    with patch("webapp.routers.schools._make_client", return_value=fake):
        client.post("/api/schools/refresh", headers={"X-API-Token": api_token})

    async def fake_auth(school_id, username, password, session):
        from models import TsnAccount_Model
        a = TsnAccount_Model(student_id="s", user_id="555:u", school_id=school_id,
                             username=username, password=password, mobile_device_id="d",
                             access_token="t", refresh_token="r", expires_in=1)
        session.add(a)
        await session.flush()
        return "555:u"

    with patch("webapp.routers.accounts.tsnPasswordAuthServer", new=fake_auth):
        r = client.post("/api/accounts/authorize",
                        headers={"X-API-Token": api_token},
                        json={"school_id": 555, "username": "u", "password": "p"})
        return r.json()["account_id"]


def test_distance_query_public(client, api_token):
    account_id = _seed_account(client, api_token)
    fake_client = MagicMock()
    fake_client.isPublic.return_value = True
    fake_client.sumExerciseRecord = AsyncMock(return_value={
        "sportRange": "12.34", "sportTimes": "5"
    })
    with patch("webapp.routers.distance.getTsnClientById",
               new=AsyncMock(return_value=fake_client)):
        resp = client.post("/api/distance/query",
                           headers={"X-API-Token": api_token},
                           json={"account_id": account_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_km"] == 12.34
    assert body["count"] == 5
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_distance.py -v
```

Expected: FAIL。

- [ ] **Step 3: 创建 `webapp/routers/distance.py`**

```python
"""里程查询。简化 main.py 中的实现：先取 sumExerciseRecord/sumSportRecord 汇总；若拿不到，再翻页累加。"""
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import getTsnClientById
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/distance", tags=["distance"],
                   dependencies=[Depends(require_token)])


class DistanceBody(BaseModel):
    account_id: int


@router.post("/query")
async def distance_query(body: DistanceBody, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.id == body.account_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})

    tsn = await getTsnClientById(body.account_id, db)
    total_km = 0.0
    count = 0
    try:
        if tsn.isPublic():
            summary = await tsn.sumExerciseRecord()
        else:
            summary = await tsn.sumSportRecord()
        if summary and "sportRange" in summary:
            total_km = float(summary["sportRange"])
            count = int(summary.get("sportTimes", 0) or 0)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"距离汇总失败，将返回 0: {e}")
    return {
        "total_km": round(total_km, 2),
        "count": count,
        "school_name": acct.school.school_name if acct.school else None,
        "username": acct.username,
    }
```

- [ ] **Step 4: 注册路由**

`create_app` 内追加：

```python
    from webapp.routers import distance
    app.include_router(distance.router)
```

- [ ] **Step 5: 测试 + 提交**

```bash
.venv/Scripts/python -m pytest tests/webapp/ -v
```

Expected: 全部 webapp 测试通过（约 25+ 用例）。

```bash
git add webapp/routers/distance.py webapp/server.py tests/webapp/test_distance.py
git commit -m "feat(webapp): /api/distance/query 里程查询"
```

---

### Task 4.5: webapp 整体回归 + CLI 零回归核查

**Files:** 无（验证）

- [ ] **Step 1: 全套测试**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 全 PASS（含 Phase 1 进度回调测试、webapp/* 全部）。

- [ ] **Step 2: 启动 dev 服务器手动验证 bootstrap**

```bash
# 临时设个 token 跑 dev 模式
.venv/Scripts/python -c "
import threading, time
from webapp.server import create_app, run_server_in_thread, pick_free_port
app = create_app(api_token='dev-token')
port = pick_free_port()
t = run_server_in_thread(app, port)
t.wait_started()
time.sleep(0.5)
import httpx
r = httpx.get(f'http://127.0.0.1:{port}/api/bootstrap', headers={'X-API-Token':'dev-token'})
print(r.status_code, r.json())
t.stop()
"
```

Expected: `200 {'status': 'ok', 'version': '0.1.0'}`

- [ ] **Step 3: CLI 仍可运行（不真正执行业务，只确认 import 通顺）**

```bash
.venv/Scripts/python -c "from main import main, TsnCliManager; print('CLI imports OK')"
```

Expected: `CLI imports OK`。

---

## Phase 5 · 前端骨架（HTML + CSS + 路由/网络层）

> 不引入构建工具。原生 ES Module + hash 路由。每个 JS 文件保持职责单一。

### Task 5.1: `frontend/index.html`

**Files:**
- Modify: `frontend/index.html`（覆盖 Phase 2 的占位）

- [ ] **Step 1: 完整内容**

```html
<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TiShiNeng 模拟跑步</title>
  <link rel="stylesheet" href="/assets/app.css">
</head>
<body>
  <header class="topbar">
    <div class="brand">TiShiNeng · 模拟跑步</div>
    <nav class="topnav">
      <a href="#/home" data-nav>主页</a>
      <a href="#/accounts" data-nav>账号</a>
      <a href="#/settings" data-nav>设置</a>
    </nav>
  </header>
  <main id="app" class="container">
    <div class="loading">加载中...</div>
  </main>
  <div id="toast" class="toast hidden"></div>

  <script type="module" src="/assets/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/index.html
git commit -m "feat(frontend): index.html 骨架与导航"
```

---

### Task 5.2: 主题与基础样式 `frontend/assets/app.css`

**Files:**
- Create: `frontend/assets/app.css`

- [ ] **Step 1: 完整内容**

```css
/* TiShiNeng GUI — 极简轻量主题，使用 CSS 变量做亮/暗切换。 */

:root {
  --bg: #f7f8fb;
  --surface: #ffffff;
  --border: #e6e8ee;
  --text: #1f2330;
  --text-mute: #6b7280;
  --primary: #3b5bff;
  --primary-soft: #eef2ff;
  --danger: #dc2626;
  --success: #16a34a;
  --warning: #d97706;
  --shadow: 0 4px 16px rgba(0,0,0,.06);
  --radius: 12px;
  font-family: system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

html[data-theme="dark"] {
  --bg: #14161d;
  --surface: #1c1f2a;
  --border: #2a2e3a;
  --text: #e8eaf2;
  --text-mute: #9aa1b1;
  --primary: #6a85ff;
  --primary-soft: #232a4a;
  --shadow: 0 4px 16px rgba(0,0,0,.4);
}

* { box-sizing: border-box; }
body { margin:0; background: var(--bg); color: var(--text); }
a { color: var(--primary); text-decoration: none; }

.topbar {
  display:flex; align-items:center; justify-content:space-between;
  padding: 12px 20px; background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.brand { font-weight: 600; }
.topnav a { padding: 6px 12px; margin-left: 4px; border-radius: 8px; color: var(--text-mute); }
.topnav a.active { background: var(--primary-soft); color: var(--primary); }

.container { max-width: 880px; margin: 0 auto; padding: 24px 20px; }

.card { background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); margin-bottom: 16px; }
.card h2 { margin: 0 0 12px 0; font-size: 18px; }
.card .subtitle { color: var(--text-mute); font-size: 13px; margin: 4px 0 16px 0; }

.btn { background: var(--primary); color: #fff; border:none;
       padding: 10px 16px; border-radius: 10px; cursor: pointer; font-size: 14px; }
.btn:hover { filter: brightness(1.05); }
.btn.secondary { background: var(--surface); color: var(--text); border:1px solid var(--border); }
.btn.danger { background: var(--danger); }
.btn:disabled { opacity:.55; cursor: not-allowed; }
.btn-row { display:flex; gap: 8px; flex-wrap: wrap; }

.input, .select {
  width: 100%; padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text);
  font-size: 14px;
}
.field { margin-bottom: 12px; }
.field label { display:block; font-size:12px; color: var(--text-mute); margin-bottom: 4px; }

.row { display:flex; gap: 8px; }
.row > * { flex: 1; }

.list { list-style: none; padding: 0; margin: 0; }
.list-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 8px;
}

.run-type-pick { display:flex; gap:8px; }
.run-type-pick .pick {
  flex:1; padding:14px 10px; border:1px solid var(--border); border-radius: 12px;
  text-align:center; cursor:pointer; font-size: 13px;
}
.run-type-pick .pick.selected { border-color: var(--primary); color: var(--primary); background: var(--primary-soft); font-weight: 600; }

.progress { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin: 12px 0; }
.progress > span { display:block; height:100%; background: var(--primary); width: 0%; transition: width .3s ease; }

.tag { display:inline-block; padding: 2px 8px; border-radius: 10px;
       font-size: 11px; background: var(--primary-soft); color: var(--primary); }
.tag.success { background: rgba(22,163,74,.15); color: var(--success); }
.tag.danger  { background: rgba(220,38,38,.15);  color: var(--danger); }

.toast {
  position: fixed; left: 50%; bottom: 32px; transform: translateX(-50%);
  background: var(--surface); border: 1px solid var(--border); color: var(--text);
  padding: 10px 16px; border-radius: 10px; box-shadow: var(--shadow);
  z-index: 9999; max-width: 80%;
}
.toast.hidden { display:none; }
.toast.error { border-color: var(--danger); color: var(--danger); }
.toast.success { border-color: var(--success); color: var(--success); }

.loading { color: var(--text-mute); padding: 40px; text-align:center; }
.empty { color: var(--text-mute); padding: 24px; text-align:center; font-size: 14px; }

dialog { border:none; border-radius: var(--radius); padding: 0; background: var(--surface); color: var(--text); }
dialog::backdrop { background: rgba(0,0,0,.4); }
dialog .dlg-body { padding: 20px; }
dialog .dlg-actions { display:flex; gap:8px; justify-content:flex-end; padding: 12px 20px; border-top: 1px solid var(--border); }
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/app.css
git commit -m "feat(frontend): 主题 CSS（亮/暗变量 + 基础组件）"
```

---

### Task 5.3: 路由 + 网络层 + toast `frontend/assets/app.js`

**Files:**
- Create: `frontend/assets/app.js`

- [ ] **Step 1: 完整内容**

```javascript
// TiShiNeng GUI 前端入口。
// 责任：(1) 从 URL 取 token 存到 sessionStorage；(2) hash 路由；
// (3) 统一 api() / ws() 网络层；(4) 全局 toast；(5) 错误码 → 友好文案。

const TOKEN_KEY = "ts_token";

// ============ token 引导 ============
(function bootstrapToken() {
  const params = new URLSearchParams(location.search);
  const t = params.get("t");
  if (t) {
    sessionStorage.setItem(TOKEN_KEY, t);
    history.replaceState({}, "", location.pathname + location.hash);
  }
})();

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

// ============ 错误码 → 中文 ============
export const ERROR_MESSAGES = {
  AUTH_FAILED: "用户名或密码错误",
  ACCOUNT_NOT_FOUND: "账号不存在",
  TASK_NOT_FOUND: "任务不存在或已结束",
  NO_FRONTEND: "前端资源缺失",
  BAD_TOKEN: "访问凭证无效，请重启程序",
  VALIDATION_ERROR: "输入有误，请检查",
  UNKNOWN: "操作失败，请稍后重试",
  // 业务异常码（来自 TiShiNengError.code）
  "10002": "密码错误",
  "20001": "获取人脸列表失败",
  "20002": "该账号没有人脸图片，请先在 APP 中上传",
  "20003": "人脸图片下载失败",
  "200000": "操作失败",
};

export function friendlyError(code, fallback) {
  return ERROR_MESSAGES[code] || fallback || "操作失败";
}

// ============ HTTP ============
export class ApiError extends Error {
  constructor(code, msg, status) {
    super(msg); this.code = code; this.status = status;
  }
}

export async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", "X-API-Token": getToken(), ...(opts.headers || {}) };
  const resp = await fetch(path, { ...opts, headers });
  let body = null;
  try { body = await resp.json(); } catch { /* ignore */ }
  if (!resp.ok) {
    const code = (body && body.code) || "UNKNOWN";
    const msg = (body && body.msg) || resp.statusText;
    throw new ApiError(code, msg, resp.status);
  }
  return body;
}

export function wsUrl(path, params = {}) {
  const sp = new URLSearchParams({ ...params, token: getToken() });
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}${path}?${sp.toString()}`;
}

// ============ toast ============
let toastTimer = null;
export function toast(msg, kind = "") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = `toast ${kind}`.trim();
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 3500);
}

// ============ 主题 ============
export function getTheme() {
  return localStorage.getItem("ts_theme") || "light";
}
export function setTheme(t) {
  localStorage.setItem("ts_theme", t);
  document.documentElement.setAttribute("data-theme", t);
}
setTheme(getTheme());

// ============ 路由 ============
const routes = {
  "/home":         () => import("./pages/home.js"),
  "/accounts":     () => import("./pages/accounts.js"),
  "/run-setup":    () => import("./pages/run-setup.js"),
  "/run-active":   () => import("./pages/run-active.js"),
  "/face-update":  () => import("./pages/face-update.js"),
  "/path-crawl":   () => import("./pages/path-crawl.js"),
  "/distance":     () => import("./pages/distance.js"),
  "/settings":     () => import("./pages/settings.js"),
};

async function render() {
  const hash = location.hash.replace(/^#/, "") || "/home";
  const [path, query] = hash.split("?");
  const loader = routes[path] || routes["/home"];
  const root = document.getElementById("app");
  root.innerHTML = '<div class="loading">加载中...</div>';

  try {
    const mod = await loader();
    const params = Object.fromEntries(new URLSearchParams(query || ""));
    await mod.render(root, params);
  } catch (e) {
    console.error(e);
    root.innerHTML = `<div class="card"><h2>页面加载失败</h2><p>${e.message}</p></div>`;
  }

  document.querySelectorAll("[data-nav]").forEach(a => {
    const target = a.getAttribute("href").replace(/^#/, "");
    a.classList.toggle("active", target === path);
  });
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", () => {
  if (!location.hash) location.hash = "/home";
  render();
});

// 让页面模块也能调用导航
export function nav(path) {
  location.hash = path.startsWith("#") ? path : `#${path}`;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/app.js
git commit -m "feat(frontend): 路由 + 网络层 + toast + 主题"
```

---

## Phase 6 · 前端页面（一页一文件）

### Task 6.1: 主页 `pages/home.js`

**Files:**
- Create: `frontend/assets/pages/home.js`

- [ ] **Step 1: 完整内容**

```javascript
// 主页：六个入口卡片，对应 CLI 6 个菜单项。
export async function render(root) {
  root.innerHTML = `
    <div class="card">
      <h2>欢迎使用 TiShiNeng 模拟跑步</h2>
      <p class="subtitle">下面选择你要做的事</p>
      <div class="row" style="flex-wrap:wrap;">
        ${tile("🏃", "开始跑步", "#/run-setup")}
        ${tile("👤", "账号管理", "#/accounts")}
        ${tile("📐", "查询里程", "#/distance")}
        ${tile("🛣️", "爬取路径", "#/path-crawl")}
        ${tile("🖼️", "更新人脸", "#/face-update")}
        ${tile("⚙️", "设置",     "#/settings")}
      </div>
    </div>
  `;
}

function tile(emoji, label, href) {
  return `
    <a href="${href}" style="flex:1 1 30%; min-width:220px; text-decoration:none;">
      <div class="card" style="margin:0; text-align:center; cursor:pointer;">
        <div style="font-size:28px;">${emoji}</div>
        <div style="margin-top:8px; color: var(--text);">${label}</div>
      </div>
    </a>`;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/pages/home.js
git commit -m "feat(frontend): 主页 6 项入口"
```

---

### Task 6.2: 账号页 `pages/accounts.js`

**Files:**
- Create: `frontend/assets/pages/accounts.js`

- [ ] **Step 1: 完整内容**

```javascript
import { api, toast, friendlyError } from "../app.js";

export async function render(root) {
  root.innerHTML = `<div class="card"><h2>账号管理</h2><div id="accounts-list" class="loading">加载中...</div></div>
    <div class="card">
      <h2>添加新账号</h2>
      <form id="auth-form">
        <div class="field">
          <label>学校</label>
          <select id="school-select" class="select"><option value="">先点 "刷新学校列表"</option></select>
        </div>
        <div class="field">
          <label>用户名</label>
          <input id="username" class="input" autocomplete="username">
        </div>
        <div class="field">
          <label>密码</label>
          <input id="password" class="input" type="password" autocomplete="current-password">
        </div>
        <div class="btn-row">
          <button type="button" class="btn secondary" id="refresh-schools">刷新学校列表</button>
          <button type="submit" class="btn">授权</button>
        </div>
      </form>
    </div>`;

  await reloadAccounts();
  await loadSchools();

  document.getElementById("refresh-schools").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "刷新中...";
    try {
      const r = await api("/api/schools/refresh", { method: "POST" });
      toast(`已更新 ${r.total} 所学校`, "success");
      await loadSchools();
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    } finally {
      e.target.disabled = false; e.target.textContent = "刷新学校列表";
    }
  });

  document.getElementById("auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const school_id = Number(document.getElementById("school-select").value);
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    if (!school_id || !username || !password) {
      toast("请填写完整", "error"); return;
    }
    try {
      const r = await api("/api/accounts/authorize", {
        method: "POST", body: JSON.stringify({ school_id, username, password })
      });
      toast(`授权成功：${r.username}`, "success");
      document.getElementById("password").value = "";
      await reloadAccounts();
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    }
  });
}

async function loadSchools() {
  const sel = document.getElementById("school-select");
  try {
    const r = await api("/api/schools");
    if (!r.items.length) {
      sel.innerHTML = '<option value="">尚无学校 — 请先刷新</option>'; return;
    }
    sel.innerHTML = '<option value="">请选择学校</option>' +
      r.items.map(s => `<option value="${s.school_id}">${s.school_name} (${s.sys_type === 2 ? '公版' : '私版'})</option>`).join("");
  } catch (err) {
    sel.innerHTML = `<option value="">加载失败: ${err.message}</option>`;
  }
}

async function reloadAccounts() {
  const wrap = document.getElementById("accounts-list");
  try {
    const r = await api("/api/accounts");
    if (!r.items.length) {
      wrap.innerHTML = '<div class="empty">尚无账号，请在下方添加</div>'; return;
    }
    wrap.innerHTML = `<ul class="list">${r.items.map(renderAccount).join("")}</ul>`;
    wrap.querySelectorAll("[data-del]").forEach(btn => {
      btn.addEventListener("click", () => confirmDelete(Number(btn.dataset.del), btn.dataset.label));
    });
  } catch (err) {
    wrap.innerHTML = `<div class="empty">加载失败：${err.message}</div>`;
  }
}

function renderAccount(a) {
  const tag = a.sys_type === 2 ? '<span class="tag">公版</span>' : '<span class="tag">私版</span>';
  return `<li class="list-item">
    <div>
      <div><strong>${a.username}</strong> &nbsp; ${tag}</div>
      <div style="color:var(--text-mute); font-size:12px;">${a.school_name || ""}</div>
    </div>
    <button class="btn danger" data-del="${a.id}" data-label="${a.username}">删除</button>
  </li>`;
}

async function confirmDelete(id, label) {
  if (!window.confirm(`确认删除账号「${label}」？\n本地数据库记录将永久删除（远端账号不受影响）。`)) return;
  try {
    await api(`/api/accounts/${id}`, { method: "DELETE" });
    toast("已删除", "success");
    await reloadAccounts();
  } catch (err) {
    toast(friendlyError(err.code, err.message), "error");
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/pages/accounts.js
git commit -m "feat(frontend): 账号页（列表/授权/删除二次确认）"
```

---

### Task 6.3: 跑步设置页 `pages/run-setup.js`

**Files:**
- Create: `frontend/assets/pages/run-setup.js`

- [ ] **Step 1: 完整内容**

```javascript
import { api, toast, friendlyError, nav } from "../app.js";

const RUN_TYPES = [
  { key: "morning", label: "晨跑", icon: "🌅" },
  { key: "sun",     label: "阳光跑", icon: "☀️" },
  { key: "freedom", label: "自由跑", icon: "🏃" },
];

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; }
  catch (err) {
    root.innerHTML = `<div class="card"><h2>开始跑步</h2><div class="empty">加载账号失败：${err.message}</div></div>`;
    return;
  }
  if (!accounts.length) {
    root.innerHTML = `<div class="card"><h2>开始跑步</h2>
      <div class="empty">尚未授权任何账号，<a href="#/accounts">去添加 →</a></div></div>`;
    return;
  }

  root.innerHTML = `
    <div class="card">
      <h2>开始跑步</h2>
      <form id="run-form">
        <div class="field">
          <label>账号</label>
          <select id="acc" class="select">
            ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>跑步类型</label>
          <div class="run-type-pick" id="run-types">
            ${RUN_TYPES.map(t => `<div class="pick" data-key="${t.key}">${t.icon}<br>${t.label}</div>`).join("")}
          </div>
        </div>
        <div class="field">
          <label>距离 (km)</label>
          <input id="dist" class="input" type="number" step="0.1" min="0.1" max="50" value="3.0">
        </div>
        <div class="btn-row">
          <button type="submit" class="btn" id="go">开始跑步</button>
        </div>
      </form>
    </div>`;

  let selectedType = "freedom";
  const picks = root.querySelectorAll(".run-type-pick .pick");
  function selectType(key) {
    selectedType = key;
    picks.forEach(p => p.classList.toggle("selected", p.dataset.key === key));
  }
  picks.forEach(p => p.addEventListener("click", () => selectType(p.dataset.key)));
  selectType("freedom");

  document.getElementById("run-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const account_id = Number(document.getElementById("acc").value);
    const distance_km = Number(document.getElementById("dist").value);
    if (!account_id || !(distance_km > 0)) { toast("参数无效", "error"); return; }

    try {
      const r = await api("/api/run/start", {
        method: "POST",
        body: JSON.stringify({ account_id, run_type: selectedType, distance_km }),
      });
      nav(`/run-active?task=${encodeURIComponent(r.task_id)}&km=${distance_km}`);
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    }
  });
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/pages/run-setup.js
git commit -m "feat(frontend): 跑步设置页"
```

---

### Task 6.4: 跑步进行中页 `pages/run-active.js`

**Files:**
- Create: `frontend/assets/pages/run-active.js`

- [ ] **Step 1: 完整内容**

```javascript
import { api, wsUrl, toast, friendlyError, nav } from "../app.js";

const PHASE_LABELS = {
  preparing: "加载账号...",
  face_start: "开始人脸验证...",
  path_gen: "生成跑步路径...",
  running: "跑步中...",
  face_mid: "中途人脸验证...",
  uploading: "上传运动记录...",
  face_end: "结束人脸验证...",
};

export async function render(root, { task, km } = {}) {
  if (!task) {
    root.innerHTML = `<div class="card"><h2>运动中</h2><div class="empty">无效的任务</div></div>`;
    return;
  }
  const totalKm = Number(km || 0);

  root.innerHTML = `
    <div class="card" id="run-card">
      <h2>运动中</h2>
      <div class="subtitle" id="status">连接中...</div>
      <div class="progress"><span id="bar"></span></div>
      <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-mute);">
        <span id="elapsed">已用时间 00:00</span>
        <span id="dist">0.00 / ${totalKm.toFixed(2)} km</span>
      </div>
      <div class="btn-row" style="margin-top:14px;">
        <button class="btn secondary" id="cancel">取消</button>
      </div>
    </div>`;

  const $status = root.querySelector("#status");
  const $bar = root.querySelector("#bar");
  const $elapsed = root.querySelector("#elapsed");
  const $dist = root.querySelector("#dist");

  let cancelled = false;

  document.getElementById("cancel").addEventListener("click", async () => {
    if (!window.confirm("确认取消当前跑步任务？")) return;
    cancelled = true;
    try { await api("/api/run/cancel", { method: "POST", body: JSON.stringify({ task_id: task }) }); }
    catch (err) { toast(friendlyError(err.code, err.message), "error"); }
  });

  const ws = new WebSocket(wsUrl("/ws/progress", { task }));
  ws.onopen = () => { $status.textContent = "已连接，等待开始..."; };
  ws.onmessage = (ev) => {
    let evt;
    try { evt = JSON.parse(ev.data); } catch { return; }
    handleEvent(evt);
  };
  ws.onerror = () => { $status.textContent = "连接异常"; };
  ws.onclose = () => { /* terminal events already render UI */ };

  function handleEvent(evt) {
    const phase = evt.phase;
    if (phase === "running") {
      const pct = evt.total_s > 0 ? Math.min(100, (evt.elapsed_s / evt.total_s) * 100) : 0;
      $bar.style.width = pct.toFixed(1) + "%";
      $elapsed.textContent = "已用时间 " + fmt(evt.elapsed_s);
      const d = Number(evt.distance_km || 0);
      $dist.textContent = `${d.toFixed(2)} / ${totalKm.toFixed(2)} km`;
      $status.textContent = "跑步中...";
      return;
    }
    if (phase === "done") {
      $bar.style.width = "100%";
      $status.innerHTML = `<span class="tag success">完成</span> &nbsp; 任务已完成`;
      setTimeout(() => nav("/home"), 3000);
      return;
    }
    if (phase === "error") {
      $status.innerHTML = `<span class="tag danger">失败</span> &nbsp; ${friendlyError(evt.code, evt.msg)}
        <div style="font-size:11px; color:var(--text-mute); margin-top:6px;">错误码: ${evt.code || "UNKNOWN"}</div>`;
      document.getElementById("cancel").textContent = "返回";
      document.getElementById("cancel").onclick = () => nav("/home");
      return;
    }
    if (phase === "cancelled") {
      $status.innerHTML = `<span class="tag">已取消</span>`;
      document.getElementById("cancel").textContent = "返回";
      document.getElementById("cancel").onclick = () => nav("/home");
      return;
    }
    // 其它阶段（preparing/path_gen/face_*/uploading）— 显示文案
    $status.textContent = PHASE_LABELS[phase] || phase;
  }
}

function fmt(sec) {
  sec = Math.max(0, Math.floor(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/assets/pages/run-active.js
git commit -m "feat(frontend): 跑步进行中页（WS 进度 + 取消）"
```

---

### Task 6.5: 其余页面 `face-update / path-crawl / distance / settings`

**Files:**
- Create: `frontend/assets/pages/face-update.js`
- Create: `frontend/assets/pages/path-crawl.js`
- Create: `frontend/assets/pages/distance.js`
- Create: `frontend/assets/pages/settings.js`

- [ ] **Step 1: `face-update.js`**

```javascript
import { api, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; } catch (e) {
    root.innerHTML = `<div class="card"><h2>更新人脸图片</h2><div class="empty">${e.message}</div></div>`; return;
  }
  if (!accounts.length) {
    root.innerHTML = `<div class="card"><h2>更新人脸图片</h2><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`; return;
  }

  root.innerHTML = `<div class="card">
    <h2>更新人脸图片</h2>
    <p class="subtitle">从服务器拉取最新人脸图，保存到本地 face_images/</p>
    <div class="field">
      <label>账号</label>
      <select id="acc" class="select">
        ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
      </select>
    </div>
    <div class="btn-row">
      <button class="btn" id="go">开始更新</button>
    </div>
    <div id="result" style="margin-top:12px;"></div>
  </div>`;

  document.getElementById("go").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "更新中...";
    try {
      const r = await api("/api/face/update", {
        method: "POST",
        body: JSON.stringify({ account_id: Number(document.getElementById("acc").value) })
      });
      document.getElementById("result").innerHTML =
        `<span class="tag success">完成</span> 已加载 ${r.size} 字节`;
      toast("人脸图片已更新", "success");
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    } finally {
      e.target.disabled = false; e.target.textContent = "开始更新";
    }
  });
}
```

- [ ] **Step 2: `path-crawl.js`**

```javascript
import { api, wsUrl, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; } catch (e) {
    root.innerHTML = `<div class="card"><h2>爬取路径数据</h2><div class="empty">${e.message}</div></div>`; return;
  }
  if (!accounts.length) {
    root.innerHTML = `<div class="card"><h2>爬取路径数据</h2><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`; return;
  }

  root.innerHTML = `<div class="card">
    <h2>爬取路径数据</h2>
    <p class="subtitle">从所选账号的历史运动记录中提取路径，存到本地数据库供跑步复用</p>
    <div class="field"><label>账号</label>
      <select id="acc" class="select">
        ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
      </select>
    </div>
    <div class="btn-row">
      <button class="btn" id="go">开始爬取</button>
    </div>
    <div id="status" class="subtitle" style="margin-top:12px;"></div>
  </div>`;

  document.getElementById("go").addEventListener("click", async (e) => {
    e.target.disabled = true;
    document.getElementById("status").textContent = "启动中...";
    try {
      const r = await api("/api/spider/start", {
        method: "POST",
        body: JSON.stringify({ account_id: Number(document.getElementById("acc").value) })
      });
      streamProgress(r.task_id);
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
      e.target.disabled = false;
    }
  });

  function streamProgress(task_id) {
    const $status = document.getElementById("status");
    const $go = document.getElementById("go");
    const ws = new WebSocket(wsUrl("/ws/progress", { task: task_id }));
    ws.onmessage = ev => {
      const evt = JSON.parse(ev.data);
      if (evt.phase === "crawling") $status.textContent = `已抓取 ${evt.current || 0} 条记录`;
      else if (evt.phase === "preparing") $status.textContent = "加载账号客户端...";
      else if (evt.phase === "done") {
        $status.innerHTML = `<span class="tag success">完成</span>`;
        $go.disabled = false;
      } else if (evt.phase === "error") {
        $status.innerHTML = `<span class="tag danger">失败</span> ${friendlyError(evt.code, evt.msg)}`;
        $go.disabled = false;
      }
    };
    ws.onclose = () => { $go.disabled = false; };
  }
}
```

- [ ] **Step 3: `distance.js`**

```javascript
import { api, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; } catch (e) {
    root.innerHTML = `<div class="card"><h2>查询里程</h2><div class="empty">${e.message}</div></div>`; return;
  }
  if (!accounts.length) {
    root.innerHTML = `<div class="card"><h2>查询里程</h2><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`; return;
  }

  root.innerHTML = `<div class="card">
    <h2>查询里程</h2>
    <div class="field"><label>账号</label>
      <select id="acc" class="select">
        ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
      </select>
    </div>
    <div class="btn-row"><button class="btn" id="go">查询</button></div>
    <div id="result" style="margin-top:14px;"></div>
  </div>`;

  document.getElementById("go").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "查询中...";
    try {
      const r = await api("/api/distance/query", {
        method: "POST",
        body: JSON.stringify({ account_id: Number(document.getElementById("acc").value) })
      });
      document.getElementById("result").innerHTML = `
        <div style="font-size:24px; font-weight:700; color:var(--primary);">${r.total_km.toFixed(2)} km</div>
        <div style="color:var(--text-mute); font-size:13px;">${r.count} 条记录 · ${r.username} · ${r.school_name || ""}</div>`;
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    } finally {
      e.target.disabled = false; e.target.textContent = "查询";
    }
  });
}
```

- [ ] **Step 4: `settings.js`**

```javascript
import { getTheme, setTheme, toast } from "../app.js";

export async function render(root) {
  const cur = getTheme();
  root.innerHTML = `<div class="card">
    <h2>设置</h2>
    <div class="field">
      <label>主题</label>
      <div class="row" style="max-width:280px;">
        <button class="btn ${cur === 'light' ? '' : 'secondary'}" data-theme="light">亮色</button>
        <button class="btn ${cur === 'dark' ? '' : 'secondary'}" data-theme="dark">暗色</button>
      </div>
    </div>
    <div class="field">
      <label>关于</label>
      <div style="color:var(--text-mute); font-size:13px;">
        TiShiNeng GUI · 0.1.0<br>
        数据目录: 本程序所在目录 (便携式)
      </div>
    </div>
  </div>`;

  root.querySelectorAll("[data-theme]").forEach(b => {
    b.addEventListener("click", () => {
      setTheme(b.dataset.theme);
      toast("主题已切换", "success");
      // 重新渲染以更新按钮高亮
      render(document.getElementById("app"));
    });
  });
}
```

- [ ] **Step 5: 提交**

```bash
git add frontend/assets/pages/face-update.js \
       frontend/assets/pages/path-crawl.js \
       frontend/assets/pages/distance.js \
       frontend/assets/pages/settings.js
git commit -m "feat(frontend): 人脸/爬取/里程/设置 四个页面"
```

---

## Phase 7 · GUI 入口 `gui_app.py`

### Task 7.1: 启动器：路径设置 → uvicorn 后台 → PyWebView 主窗口

**Files:**
- Create: `gui_app.py`

- [ ] **Step 1: 完整内容**

```python
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
```

- [ ] **Step 2: 开发模式手动验证（无需真正登录账号）**

```bash
.venv/Scripts/python gui_app.py --dev
```

Expected: 弹出窗口，显示「TiShiNeng · 模拟跑步」与 6 个入口卡片。点击「账号」可看到空列表与「刷新学校列表」按钮（点击它会发起外部 HTTP，可能失败，这是正常的 — 仅验证 GUI 通联）。关闭窗口后命令退出码为 0。

- [ ] **Step 3: 提交**

```bash
git add gui_app.py
git commit -m "feat(gui-app): PyWebView 入口（路径/日志/后台 uvicorn/主窗口）"
```

---

## Phase 8 · 配置持久化（可选轻量化）

### Task 8.1: `config.json` 读写

**Files:**
- Modify: `webapp/paths.py`（追加 `load_config` / `save_config`）
- Create: `tests/webapp/test_config.py`

> 配置当前仅前端用 localStorage 持久化主题。`config.json` 留作扩展点（DEBUG 切换等），先做一个简单读写以应对未来需求，但不强行接到前端。

- [ ] **Step 1: 写失败测试**

`tests/webapp/test_config.py`：

```python
"""config.json 简单读写测试。"""
from webapp import paths


def test_save_then_load(tmp_path):
    paths.set_data_dir(tmp_path)
    try:
        paths.save_config({"theme": "dark", "debug": True})
        cfg = paths.load_config()
        assert cfg == {"theme": "dark", "debug": True}
    finally:
        paths.set_data_dir(None)


def test_load_missing_returns_empty(tmp_path):
    paths.set_data_dir(tmp_path)
    try:
        assert paths.load_config() == {}
    finally:
        paths.set_data_dir(None)
```

- [ ] **Step 2: 运行确认失败**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_config.py -v
```

Expected: 2 FAIL（函数不存在）。

- [ ] **Step 3: 在 `webapp/paths.py` 末尾追加**

```python
import json


def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: dict) -> None:
    config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 测试通过 + 提交**

```bash
.venv/Scripts/python -m pytest tests/webapp/test_config.py -v
git add webapp/paths.py tests/webapp/test_config.py
git commit -m "feat(webapp): config.json 读写工具"
```

---

## Phase 9 · 打包（PyInstaller --onefile）

### Task 9.1: 编写 PyInstaller spec + 版本信息

**Files:**
- Create: `packaging/__init__.py`（占位空）
- Create: `packaging/tishineng.spec`
- Create: `packaging/version_info.txt`
- Create: `packaging/.gitkeep`（确保目录入 git，即使 spec 后改名）

> 图标 `packaging/icon.ico` 是可选的；若用户没有提供，spec 内 `icon=` 留空字符串。

- [ ] **Step 1: 创建 `packaging/__init__.py`**

```python
```

- [ ] **Step 2: 创建 `packaging/version_info.txt`**

PyInstaller 用的 Windows VERSIONINFO 资源：

```
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(0, 1, 0, 0),
    prodvers=(0, 1, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'TiShiNeng Open Source'),
         StringStruct(u'FileDescription', u'TiShiNeng GUI 模拟跑步'),
         StringStruct(u'FileVersion', u'0.1.0'),
         StringStruct(u'InternalName', u'TiShiNeng'),
         StringStruct(u'OriginalFilename', u'TiShiNeng.exe'),
         StringStruct(u'ProductName', u'TiShiNeng'),
         StringStruct(u'ProductVersion', u'0.1.0')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
```

- [ ] **Step 3: 创建 `packaging/tishineng.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for TiShiNeng GUI.
# 运行: .venv\Scripts\python -m PyInstaller packaging/tishineng.spec --clean --noconfirm
import os
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).resolve().parent  # 项目根

ICON_PATH = str(ROOT / "packaging" / "icon.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = None  # 可选

a = Analysis(
    [str(ROOT / "gui_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "frontend"), "frontend"),
    ],
    hiddenimports=[
        "aiosqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "test", "tests", "PySide6", "PyQt5", "PyQt6", "numpy.testing"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TiShiNeng",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 窗口程序
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
    version=str(ROOT / "packaging" / "version_info.txt"),
)
```

> `EXE(...)` 把所有数据包进自身，相当于 onefile 模式。

- [ ] **Step 4: 执行打包**

```bash
.venv/Scripts/python -m PyInstaller packaging/tishineng.spec --clean --noconfirm
```

Expected:
- 末尾出现 `Building EXE from EXE-00.toc completed successfully.`
- `dist/TiShiNeng.exe` 生成，体积 ~30-60 MB

- [ ] **Step 5: 运行打包产物**

```bash
./dist/TiShiNeng.exe
```

Expected: 5-10 秒内（首次解压慢）弹出主窗口，界面与开发模式一致。日志写在 `dist/logs/`，数据库会在 `dist/tsn_data.db`。

- [ ] **Step 6: 提交**

```bash
git add packaging/
git commit -m "build: PyInstaller spec + Windows version info"
```

---

### Task 9.2: 构建验证脚本

**Files:**
- Create: `scripts/verify-build.bat`

- [ ] **Step 1: 完整内容**

```bat
@echo off
setlocal

cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  echo [ERROR] .venv not found. 请先 python -m venv .venv 并安装依赖。
  exit /b 1
)

call .venv\Scripts\activate.bat

echo === pytest ===
python -m pytest tests/ -q
if errorlevel 1 (
  echo [ERROR] tests failed
  exit /b 2
)

echo === PyInstaller ===
python -m PyInstaller packaging\tishineng.spec --clean --noconfirm
if errorlevel 1 (
  echo [ERROR] PyInstaller failed
  exit /b 3
)

if not exist dist\TiShiNeng.exe (
  echo [ERROR] dist\TiShiNeng.exe missing
  exit /b 4
)

echo.
echo === Build OK ===
echo Run dist\TiShiNeng.exe and follow docs\packaging-smoke.md
endlocal
```

- [ ] **Step 2: 验证脚本可运行**

```bash
./scripts/verify-build.bat
```

Expected: pytest + PyInstaller 两阶段都过，末尾打印 `=== Build OK ===`。

- [ ] **Step 3: 提交**

```bash
git add scripts/verify-build.bat
git commit -m "build: scripts/verify-build.bat 一键校验"
```

---

## Phase 10 · 文档与冒烟

### Task 10.1: 打包冒烟 checklist

**Files:**
- Create: `docs/packaging-smoke.md`

- [ ] **Step 1: 完整内容**

```markdown
# TiShiNeng 打包冒烟测试清单

> 每次发布前在 Windows 11 上手动跑完。打包产物：`dist/TiShiNeng.exe`。

## 基础启动

- [ ] 双击 `TiShiNeng.exe`，首次启动 ≤ 10 秒（PyInstaller onefile 需解压到临时目录）
- [ ] 主窗口出现，标题为「TiShiNeng 模拟跑步」，主页显示 6 个入口卡片
- [ ] 无任何控制台窗口闪现
- [ ] 在 exe 同目录下出现 `logs/tishineng-YYYY-MM-DD.log`，写入了 `FastAPI lifespan: database initialized`
- [ ] 出现 `tsn_data.db` 文件

## 主题

- [ ] 进入「设置」点「暗色」 → 全部界面变暗
- [ ] 关闭主窗口 → 重新双击 → 仍为暗色（localStorage 持久化）

## 学校 / 账号

- [ ] 进入「账号管理」→ 点「刷新学校列表」→ 看到 toast 「已更新 N 所学校」
- [ ] 学校下拉列表能展开并搜索
- [ ] 输入错误密码授权 → 弹出错误 toast，内容包含「密码」字样
- [ ] 输入正确密码授权 → toast 显示「授权成功」，列表新增
- [ ] 点击账号的「删除」→ 弹出 confirm，取消则保留
- [ ] 再次点删除 → 确认 → 账号消失

## 跑步主流程

- [ ] 进入「开始跑步」→ 选账号 → 选「自由跑」（高亮）→ 输入 0.5
- [ ] 点「开始跑步」→ 跳转到运动中页面
- [ ] 状态文字按顺序经过：连接中 → 加载账号 → 生成跑步路径 → 跑步中
- [ ] 进度条与「已用时间」「距离」每 2 秒刷新
- [ ] 跑步完成 → 「完成」标签 → 3 秒后自动回主页

## 跑步取消

- [ ] 再次开始跑步（0.5km）
- [ ] 跑步中点「取消」→ confirm → 显示「已取消」标签
- [ ] 通过 Windows 任务管理器看到 `TiShiNeng.exe` 关闭后无残留 python 进程

## 其它功能

- [ ] 「更新人脸图片」选择账号 → 看到「人脸图片已更新」toast 与字节数
- [ ] 「爬取路径数据」启动后状态显示「已抓取 N 条记录」
- [ ] 「查询里程」显示 km 数字与记录数

## 便携性

- [ ] 关闭 exe，把整个 `dist/` 目录（含 exe、logs、tsn_data.db、face_images）拷到另一台无 Python 的 Win11 机器
- [ ] 在新机器双击 exe，能直接看到原账号列表（数据库随行）
```

- [ ] **Step 2: 提交**

```bash
git add docs/packaging-smoke.md
git commit -m "docs: 打包冒烟 checklist"
```

---

### Task 10.2: 更新 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 在 `## 使用指南` 前插入一节「GUI 版本」**

通过 Edit 工具，把 `README.md` 中 `## 使用指南` 这一行替换为：

```markdown
## GUI 版本（推荐）

面向非技术学生，提供桌面应用：

### 下载使用

1. 下载 `TiShiNeng.exe`（构建产物，位于 `dist/`）
2. 放到任意目录，双击运行
3. 首次启动会在同目录生成 `tsn_data.db`、`logs/`、`face_images/`（便携式）
4. **Windows 10 1809+ / Windows 11** 自带 WebView2 Runtime；
   老版本 Windows 10 需先装 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)

### 从源码构建

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
.venv\Scripts\python -m PyInstaller packaging/tishineng.spec --clean --noconfirm
# 产物: dist\TiShiNeng.exe
```

或一键校验：

```bash
scripts\verify-build.bat
```

### 开发模式

```bash
.venv\Scripts\python gui_app.py --dev
```

`--dev` 启用 DevTools、固定 token。

---

## 使用指南
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: README 增加 GUI 版本说明"
```

---

## 最终验收

### Task 99.1: 全套验证

- [ ] **Step 1: 全部测试**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 所有用例（progress 回调、bootstrap、schools、accounts、run、face、spider、distance、paths、progress_bus、config）通过。

- [ ] **Step 2: CLI 零回归**

```bash
.venv/Scripts/python -c "import main; from main import TsnCliManager; print('CLI OK')"
```

Expected: `CLI OK`。

- [ ] **Step 3: GUI 开发模式启动验证**

```bash
.venv/Scripts/python gui_app.py --dev
```

Expected: 主窗口正常弹出，控制台无未处理异常。

- [ ] **Step 4: 一键构建**

```bash
./scripts/verify-build.bat
```

Expected: 末尾 `=== Build OK ===`。

- [ ] **Step 5: 双击 dist\TiShiNeng.exe + 完成冒烟清单**

参照 `docs/packaging-smoke.md` 逐项打勾。

- [ ] **Step 6: 推送分支**

```bash
git push origin feat/gui-and-packaging
```

---

## 索引：失败时的回退点

| 现象 | 排查方向 |
|---|---|
| `pytest tests/` 在 Phase 1 测试就失败 | 检查 `tsnRunServer._emit` 实现，确认 `progress_callback` 默认 None 时 noop |
| Phase 2 `test_bootstrap` 401 失败 | 检查 `webapp/server.py` 是否正确设 `app.state.api_token` |
| Phase 4 WebSocket 测试不稳定 | `emitting_run` 加 `await asyncio.sleep(0.1)`，让 WS 先订阅 |
| `gui_app.py` 弹「无法连接后端」 | 看 `logs/`；常见原因：DATABASE_URL 设置后 path 含反斜杠转义错误 |
| PyInstaller 跑完 exe 启动后白屏 | 检查 `frontend/` 是否在 `datas` 中、`_MEIPASS` 路径在 `paths.frontend_dir()` 中是否正确 |
| 打包后报 `ModuleNotFoundError: uvicorn.protocols.*` | 把缺失模块加入 spec 的 `hiddenimports` |
| 老版 Win10 启动报 WebView2 错误 | README 给的 Microsoft 安装链接装一遍 |
