# TiShiNengRunning · GUI 模拟跑步工具

> ⚠️ **免责声明 / 使用前必读**
>
> 本项目仅用于学习与研究体育数据接口、桌面 GUI 打包和本地自动化流程。使用本程序辅助完成校园体测或运动任务，可能违反所在学校的学生守则、体育课程纪律或平台规则。
>
> **使用前请退出手机端体适能 / 官方 APP，并在最近一段时间内不要再次登录手机端**，避免多端状态冲突或异常。由此产生的账号异常、课程处分、信用记录或其他后果，由使用者本人承担。作者及贡献者不对任何使用行为承担法律、纪律或行政责任。

TiShiNengRunning 是一个基于原命令行项目扩展的 Windows 桌面应用。它把学校刷新、账号授权、模拟跑步、路径爬取、人脸更新、里程查询等操作整合到 GUI 中，面向不熟悉命令行的用户。

- GUI：PyWebView + 本机 FastAPI + 原生前端页面
- CLI：保留原 `main.py` 命令行入口
- 数据：便携式本地存储，默认放在程序同目录

---

## GUI 快速开始（推荐）

1. 下载发布包中的 `TiShiNeng.exe`。
2. 将 `TiShiNeng.exe` 放到一个你能长期保留的目录。
3. 双击运行。
4. 首次进入时阅读并同意免责声明。
5. 按首次引导点击右上角 `DOCS`，先阅读应用内使用说明。
6. 使用前退出手机端体适能 / 官方 APP，并在最近一段时间内不要再次登录手机端。
7. 按以下顺序操作：
   - `ACCOUNTS` → 刷新学校列表
   - `ACCOUNTS` → 授权账号
   - 如需要：爬取路径 / 更新人脸
   - `HOME` → 开始跑步
   - 如需要：查询里程

> Windows 10 1809+ / Windows 11 通常自带 WebView2 Runtime。老版本 Windows 10 如无法启动窗口，请先安装 [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)。

---

## 第一次使用流程

### 1. 退出手机端

使用前请退出手机端体适能 / 官方 APP，并在最近一段时间内不要再次登录手机端。不要在运行本程序时同时打开官方 APP。

### 2. 刷新学校列表

进入 `ACCOUNTS`，点击"刷新学校列表"。首次刷新会遍历省份和学校，可能较慢，页面会显示当前省份和进度。

### 3. 授权账号

在 `ACCOUNTS` 中搜索学校，填写用户名和密码，点击"授权"。授权信息保存在本地数据库。

### 4. 准备路径和人脸

- 如果需要复用历史路线，进入"爬取路径"。
- 如果学校任务要求人脸，进入"更新人脸"。如果账号没有人脸图片，请先按学校要求在官方 APP 中上传。

### 5. 开始跑步

回到 `HOME`，进入"开始跑步"，选择账号、跑步类型和距离，确认后执行。任务执行期间不要再次登录手机端。

---

## 数据存放与隐私

GUI 版本按便携式应用处理数据：

| 路径 | 说明 |
|---|---|
| `tsn_data.db` | 本地 SQLite 数据库，保存学校、账号、路径等数据 |
| `face_images/` | 本地人脸图片缓存 |
| `logs/` | 启动和运行日志 |
| `config.json` | 前端/后端共享配置 |

冻结打包后，这些文件位于 `TiShiNeng.exe` 同目录；开发模式下位于项目根目录。程序不会主动把这些本地文件上传到第三方。

---

## 常见问题

### 启动失败怎么办？

查看 `logs/` 目录下的日志文件。老版本 Windows 10 可能需要安装 WebView2 Runtime。

### 学校刷新很慢怎么办？

首次刷新会按省份请求学校列表，请等待页面进度完成。网络异常或学校接口异常时，部分学校可能会被跳过。

### 登录失败怎么办？

确认学校是否选对、账号密码是否正确，并确认手机端没有同时登录体适能 / 官方 APP。

### 人脸为空怎么办？

本程序只能拉取账号已有的人脸图片。如果提示没有人脸图片，请先在官方 APP 中按学校要求上传。

### 外链打不开怎么办？

GUI 会尝试用系统浏览器打开外链；如果失败，会尝试复制链接到剪贴板，你可以手动粘贴到浏览器。

---

## 开发者说明

### 环境要求

- Python 3.10+
- Windows 10/11（GUI 打包目标）
- WebView2 Runtime（多数 Windows 11 已内置）

### 安装依赖

```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip install -r requirements-dev.txt
```

### 开发模式启动 GUI

```bash
python gui_app.py --dev
```

`--dev` 会启用开发模式，便于调试前端页面和本机后端。

### 启动 CLI

```bash
python main.py
```

CLI 入口仍保留，用于命令行场景和回归验证。

### 运行测试

```bash
python -m pytest tests/ -q
```

如使用项目虚拟环境：

```bash
.venv/Scripts/python -m pytest tests/ -q
```

### 打包

```bash
python -m PyInstaller tishineng.spec --clean --noconfirm
```

或运行一键校验脚本：

```bash
scripts/verify-build.bat
```

构建产物位于 `dist/`。当前 GUI 会把 `frontend/` 静态资源打入包中，冻结模式下从 PyInstaller `_MEIPASS` 读取。

---

## 架构概览

```text
TiShiNeng.exe / gui_app.py
├─ PyWebView 窗口（WebView2）
├─ uvicorn 后台线程
│  └─ FastAPI app: webapp/server.py
│     ├─ /api/bootstrap
│     ├─ /api/schools
│     ├─ /api/accounts
│     ├─ /api/run + /ws/progress
│     ├─ /api/face
│     ├─ /api/spider
│     └─ /api/distance
├─ frontend/
│  ├─ index.html
│  └─ assets/
│     ├─ app.js / app.css
│     └─ pages/*.js
└─ 原业务层
   ├─ main.py
   ├─ tsnClient.py
   ├─ tsnRunServer.py
   ├─ spiderServer.py
   └─ TiShiNengSdk*.py
```

核心思路：GUI 只包装本机后端和前端页面，跑步、路径、人脸、账号等业务逻辑复用原项目实现。

---

## 仓库来源

- Fork / GUI 版本：<https://github.com/cd233ljx/TiShiNengRunning>
- Upstream / 原命令行版本：<https://github.com/dispose0335/TiShiNengRunning>

当前 GUI 在原作者命令行版本基础上增加桌面应用、前端页面、WebSocket 进度和 PyInstaller 打包支持。

---

## 贡献与反馈

欢迎围绕以下方向提交反馈或改进：

- GUI 使用体验
- 打包和启动兼容性
- 文档和首次使用引导
- 测试覆盖和稳定性

如果仓库未声明许可证，请不要假设拥有额外授权；使用、分发和修改前请自行确认相关风险。
