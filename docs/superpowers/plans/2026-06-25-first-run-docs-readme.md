# 首次免责声明、应用内 Docs 与 README 重写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为已发布的 GUI 增加首次免责声明门禁、应用内 `DOCS` 使用说明与首次 Docs 引导，并把仓库 README 重写为普通用户 + 开发者双层文档。

**Architecture:** 采用轻量前端体验层：前端 ES Module 统一维护免责声明文案，`app.js` 在路由渲染前执行 localStorage 版本门禁，Home 渲染后展示一次 Docs 引导；`#/docs` 是新的静态 SPA 页面。README 独立重写，不新增后端 API、数据库或打包流程。

**Tech Stack:** 原生 ES Module 前端、hash 路由、localStorage/sessionStorage、CSS（无构建工具）、pytest 静态契约测试、Markdown。

**对应规格：** `docs/superpowers/specs/2026-06-25-first-run-docs-readme-design.md`

---

## 文件结构（新建/修改一览）

| 类别 | 路径 | 责任 |
|---|---|---|
| 新增·前端 | `frontend/assets/disclaimer.js` | 免责声明版本、手机端登录提醒、免责声明条目、共享 HTML 渲染 helper |
| 新增·前端 | `frontend/assets/pages/docs.js` | 应用内产品使用说明书页面，路由 `#/docs` |
| 修改·前端 | `frontend/index.html` | 顶部导航新增 `DOCS` |
| 修改·前端 | `frontend/assets/app.js` | 注册 `#/docs`；启动时执行免责声明 gate；同意后进入 Home；首次显示 Docs 引导 |
| 修改·前端 | `frontend/assets/pages/settings.js` | 保留设置页免责声明，但复用 `disclaimer.js` 文案 |
| 修改·前端 | `frontend/assets/pages/home.js` | 页脚从 Settings 免责声明链接改为 Docs 使用说明入口 |
| 修改·前端 | `frontend/assets/app.css` | 新增 gate、引导弹窗、Docs 页面样式 |
| 修改·测试 | `tests/test_frontend_static.py` | 增加无构建前端的静态契约测试 |
| 修改·文档 | `README.md` | 完全重写为 GUI 用户优先 + 开发者说明 |

**边界：** 不新增后端 API，不改 `webapp/`、数据库、`gui_app.py`、CLI 或 PyInstaller 配置。

---

## Task 1: 写前端与 README 静态契约测试

**Files:**
- Modify: `tests/test_frontend_static.py`

- [ ] **Step 1: 在 `tests/test_frontend_static.py` 末尾追加失败测试**

追加以下测试函数，不删除现有两个测试：

```python

def test_docs_route_and_top_nav_are_registered():
    """DOCS must be reachable as an in-app route from the top navigation."""
    index = read_frontend("frontend/index.html")
    app = read_frontend("frontend/assets/app.js")

    assert '<a href="#/docs" data-nav>DOCS</a>' in index
    assert '"/docs":' in app
    assert 'import("./pages/docs.js")' in app


def test_disclaimer_gate_uses_versioned_local_storage_contract():
    """First-run disclaimer must block app rendering until current version is accepted."""
    app = read_frontend("frontend/assets/app.js")
    disclaimer = read_frontend("frontend/assets/disclaimer.js")

    assert 'DISCLAIMER_VERSION = "1"' in disclaimer
    assert 'ts_disclaimer_version' in app
    assert 'ts_disclaimer_accepted_at' in app
    assert 'renderDisclaimerGate' in app
    assert '我已阅读并同意' in app
    assert '暂不使用' in app


def test_docs_onboarding_emphasizes_phone_logout_warning():
    """The first-run Docs prompt must warn users not to log in on phone recently."""
    app = read_frontend("frontend/assets/app.js")
    docs = read_frontend("frontend/assets/pages/docs.js")
    readme = read_frontend("README.md")

    required = "最近一段时间内不要再次登录手机端"
    assert required in app
    assert required in docs
    assert required in readme
    assert "ts_docs_onboarding_seen" in app
    assert "打开 DOCS" in app


def test_settings_and_docs_reuse_shared_disclaimer_copy():
    """Disclaimer copy should live in one module and be reused by gate/settings/docs."""
    settings = read_frontend("frontend/assets/pages/settings.js")
    docs = read_frontend("frontend/assets/pages/docs.js")
    disclaimer = read_frontend("frontend/assets/disclaimer.js")

    assert 'from "../disclaimer.js"' in settings
    assert 'from "../disclaimer.js"' in docs
    assert "DISCLAIMER_ITEMS" in disclaimer
    assert "renderDisclaimerNotice" in disclaimer


def test_readme_is_gui_first_and_keeps_developer_commands():
    """README should be useful to GUI users first while retaining developer workflows."""
    readme = read_frontend("README.md")

    assert "GUI 快速开始" in readme
    assert "TiShiNeng.exe" in readme
    assert "DOCS" in readme
    assert "WebView2 Runtime" in readme
    assert "python gui_app.py --dev" in readme
    assert "python -m pytest tests/ -q" in readme
    assert "python -m PyInstaller tishineng.spec --clean --noconfirm" in readme
```

- [ ] **Step 2: 运行静态测试，确认失败**

Run:

```bash
cd F:/CODE/TiShiNengRunning
.venv/Scripts/python -m pytest tests/test_frontend_static.py -q
```

Expected: FAIL，至少包含以下原因之一：

- `frontend/assets/disclaimer.js` 不存在。
- `#/docs` 路由不存在。
- README 尚未包含 GUI 快速开始新结构。

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_frontend_static.py
git commit -m "test: 固化首次使用体验前端契约"
```

---

## Task 2: 新增共享免责声明模块并复用到 Settings

**Files:**
- Create: `frontend/assets/disclaimer.js`
- Modify: `frontend/assets/pages/settings.js`

- [ ] **Step 1: 创建 `frontend/assets/disclaimer.js`**

Create file with exactly this content:

```javascript
// 免责声明与使用前提醒的共享文案。
// 启动门禁、Settings、Docs 共用，避免三处文案漂移。

export const DISCLAIMER_VERSION = "1";

export const PHONE_SESSION_WARNING =
  "使用前请退出手机端体适能 / 官方 APP，并在最近一段时间内不要再次登录手机端，避免多端状态冲突或异常。";

export const DISCLAIMER_INTRO =
  "本程序为学习用途，仅用于研究体育数据接口的逆向工程。在你启动它之前，请逐条确认：";

export const DISCLAIMER_ITEMS = [
  "使用本程序辅助完成校园体测，可能违反所在学校的学生守则、体育课程纪律或平台规则",
  "由此产生的任何后果（账号异常、课程处分、信用记录等）由使用者本人承担",
  "本程序的作者及贡献者不为任何使用行为承担法律、纪律或行政责任",
  "账号凭证、跑步记录、运行日志均存储在本地，不主动向第三方上传",
];

export const DISCLAIMER_FOOTNOTE = "继续使用本程序，视为已阅读并同意上述条款。";

export function renderDisclaimerNotice(extraClass = "") {
  const cls = ["notice", extraClass].filter(Boolean).join(" ");
  return `
    <div class="${cls}">
      <div class="notice-header">DISCLAIMER &middot; 免责声明</div>
      <p class="phone-warning"><strong>使用前必读：</strong>${PHONE_SESSION_WARNING}</p>
      <p>${DISCLAIMER_INTRO}</p>
      <ul>
        ${DISCLAIMER_ITEMS.map(item => `<li>${item}</li>`).join("")}
      </ul>
      <p class="footnote">${DISCLAIMER_FOOTNOTE}</p>
    </div>`;
}
```

- [ ] **Step 2: Replace `frontend/assets/pages/settings.js` with shared disclaimer copy**

Replace the whole file with:

```javascript
import { getTheme, setTheme, toast } from "../app.js";
import { renderDisclaimerNotice } from "../disclaimer.js";

export async function render(root) {
  const cur = getTheme();
  root.innerHTML = `
    <h1 class="page-title">SETTINGS</h1>

    ${renderDisclaimerNotice()}

    <div class="card">
      <div class="field">
        <label>主题</label>
        <div class="btn-row">
          <button class="btn ${cur === 'light' ? '' : 'secondary'}" data-theme="light">PAPER &middot; 亮</button>
          <button class="btn ${cur === 'dark' ? '' : 'secondary'}" data-theme="dark">INK &middot; 暗</button>
        </div>
      </div>
      <div class="field">
        <label>关于</label>
        <div style="font-family:var(--font-mono); font-size:11.5px; letter-spacing:0.08em; color:var(--mute); line-height:1.9;">
          TISHINENG &middot; 0.1.0<br>
          STATION TSN-01<br>
          DATA &middot; 本程序所在目录（便携式）
        </div>
      </div>
      <div class="field">
        <label>仓库</label>
        <div class="repo-list">
          <a class="repo-link" href="https://github.com/cd233ljx/TiShiNengRunning" target="_blank" rel="noopener">
            <span class="repo-tag">FORK</span>
            <div class="repo-body">
              <span class="repo-url">github.com/cd233ljx/TiShiNengRunning</span>
              <span class="repo-desc">本程序所在仓库。在原作者基础上加了图形界面，方便非技术用户使用。</span>
            </div>
          </a>
          <a class="repo-link" href="https://github.com/dispose0335/TiShiNengRunning" target="_blank" rel="noopener">
            <span class="repo-tag">UPSTREAM</span>
            <div class="repo-body">
              <span class="repo-url">github.com/dispose0335/TiShiNengRunning</span>
              <span class="repo-desc">原作者仓库。命令行（TUI）版本，本程序的功能与逆向研究均来自此处。</span>
            </div>
          </a>
        </div>
      </div>
    </div>`;

  root.querySelectorAll("[data-theme]").forEach(b => {
    b.addEventListener("click", () => {
      setTheme(b.dataset.theme);
      toast("主题已切换", "success");
      render(document.getElementById("app"));
    });
  });
}
```

- [ ] **Step 3: Run targeted tests, expect partial failure remains**

Run:

```bash
.venv/Scripts/python -m pytest tests/test_frontend_static.py -q
```

Expected: still FAIL because `#/docs` route/page and README are not implemented yet, but failures about missing `frontend/assets/disclaimer.js` should be gone.

- [ ] **Step 4: Commit shared disclaimer module**

```bash
git add frontend/assets/disclaimer.js frontend/assets/pages/settings.js
git commit -m "feat(frontend): 统一免责声明文案"
```

---

## Task 3: 新增 DOCS 导航、路由、免责声明 gate 与首次引导

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/assets/app.js`
- Modify: `frontend/assets/pages/home.js`

- [ ] **Step 1: Modify top navigation in `frontend/index.html`**

Change the `<nav class="topnav">` block to include DOCS between ACCOUNTS and SETTINGS:

```html
    <nav class="topnav">
      <a href="#/home" data-nav>HOME</a>
      <a href="#/accounts" data-nav>ACCOUNTS</a>
      <a href="#/docs" data-nav>DOCS</a>
      <a href="#/settings" data-nav>SETTINGS</a>
    </nav>
```

- [ ] **Step 2: Replace `frontend/assets/app.js` with gate-aware router**

Replace the whole file with:

```javascript
// TiShiNeng GUI 前端入口。
// 责任：(1) 从 URL 取 token 存到 sessionStorage；(2) hash 路由；
// (3) 统一 api() / ws() 网络层；(4) 全局 toast；(5) 错误码 → 友好文案；
// (6) 首次免责声明门禁与 Docs 引导。

import {
  DISCLAIMER_VERSION,
  PHONE_SESSION_WARNING,
  renderDisclaimerNotice,
} from "./disclaimer.js";

const TOKEN_KEY = "ts_token";
const DISCLAIMER_VERSION_KEY = "ts_disclaimer_version";
const DISCLAIMER_ACCEPTED_AT_KEY = "ts_disclaimer_accepted_at";
const DOCS_ONBOARDING_SEEN_KEY = "ts_docs_onboarding_seen";

let memoryDisclaimerVersion = "";
let memoryDocsOnboardingSeen = false;
let pendingDocsOnboarding = false;

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
  return safeLocalGet("ts_theme") || "light";
}
export function setTheme(t) {
  safeLocalSet("ts_theme", t);
  document.documentElement.setAttribute("data-theme", t);
}
setTheme(getTheme());

// ============ localStorage 安全封装 ============
function safeLocalGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function safeLocalSet(key, value) {
  try { localStorage.setItem(key, value); return true; } catch { return false; }
}

function hasAcceptedDisclaimer() {
  return (safeLocalGet(DISCLAIMER_VERSION_KEY) || memoryDisclaimerVersion) === DISCLAIMER_VERSION;
}

function markDisclaimerAccepted() {
  memoryDisclaimerVersion = DISCLAIMER_VERSION;
  safeLocalSet(DISCLAIMER_VERSION_KEY, DISCLAIMER_VERSION);
  safeLocalSet(DISCLAIMER_ACCEPTED_AT_KEY, new Date().toISOString());
}

function hasSeenDocsOnboarding() {
  return safeLocalGet(DOCS_ONBOARDING_SEEN_KEY) === "true" || memoryDocsOnboardingSeen;
}

function markDocsOnboardingSeen() {
  memoryDocsOnboardingSeen = true;
  safeLocalSet(DOCS_ONBOARDING_SEEN_KEY, "true");
}

// ============ 路由 ============
const routes = {
  "/home":         () => import("./pages/home.js"),
  "/accounts":     () => import("./pages/accounts.js"),
  "/docs":         () => import("./pages/docs.js"),
  "/run-setup":    () => import("./pages/run-setup.js"),
  "/run-active":   () => import("./pages/run-active.js"),
  "/face-update":  () => import("./pages/face-update.js"),
  "/path-crawl":   () => import("./pages/path-crawl.js"),
  "/distance":     () => import("./pages/distance.js"),
  "/settings":     () => import("./pages/settings.js"),
};

async function render() {
  if (!hasAcceptedDisclaimer()) {
    renderDisclaimerGate();
    return;
  }

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

  maybeShowDocsOnboarding(path);
}

function renderDisclaimerGate() {
  const root = document.getElementById("app");
  document.querySelectorAll("[data-nav]").forEach(a => a.classList.remove("active"));
  root.innerHTML = `
    <section class="gate-shell" aria-labelledby="disclaimer-title">
      <div class="gate-card">
        <div class="gate-kicker">FIRST RUN CHECK</div>
        <h1 id="disclaimer-title" class="gate-title">使用前请确认免责声明</h1>
        ${renderDisclaimerNotice("gate-notice")}
        <div id="gate-exit-hint" class="gate-exit-hint" hidden>请直接关闭此窗口，或返回后点击同意继续。</div>
        <div class="btn-row gate-actions">
          <button class="btn" id="accept-disclaimer">我已阅读并同意</button>
          <button class="btn secondary" id="decline-disclaimer">暂不使用</button>
        </div>
      </div>
    </section>`;

  document.getElementById("accept-disclaimer").addEventListener("click", () => {
    markDisclaimerAccepted();
    pendingDocsOnboarding = !hasSeenDocsOnboarding();
    if (!location.hash) location.hash = "/home";
    render();
  });

  document.getElementById("decline-disclaimer").addEventListener("click", () => {
    try { window.close(); } catch (_) { /* ignore */ }
    const hint = document.getElementById("gate-exit-hint");
    if (hint) hint.hidden = false;
  });
}

function maybeShowDocsOnboarding(path) {
  if (path !== "/home") return;
  if (!pendingDocsOnboarding && hasSeenDocsOnboarding()) return;
  if (document.getElementById("docs-onboarding")) return;

  pendingDocsOnboarding = false;
  const overlay = document.createElement("div");
  overlay.className = "modal-backdrop";
  overlay.id = "docs-onboarding";
  overlay.innerHTML = `
    <div class="onboarding-card" role="dialog" aria-modal="true" aria-labelledby="docs-onboarding-title">
      <div class="notice-header">FIRST RUN GUIDE</div>
      <h2 id="docs-onboarding-title">先阅读 DOCS，再开始使用</h2>
      <p class="phone-warning"><strong>使用前必读：</strong>${PHONE_SESSION_WARNING}</p>
      <p>第一次使用建议先阅读产品说明书，了解学校刷新、账号授权、路径、人脸、里程与常见问题。</p>
      <div class="btn-row">
        <button class="btn" id="open-docs">打开 DOCS</button>
        <button class="btn secondary" id="skip-docs">稍后再说</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  document.getElementById("open-docs").addEventListener("click", () => {
    markDocsOnboardingSeen();
    overlay.remove();
    nav("/docs");
  });
  document.getElementById("skip-docs").addEventListener("click", () => {
    markDocsOnboardingSeen();
    overlay.remove();
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

// === 外链拦截 ============
// PyWebView 内点击 http(s) 链接默认会让 SPA 跳走。拦截这些点击，
// 尝试 window.open（pywebview 会在系统浏览器打开），失败则复制 URL 到剪贴板。
document.addEventListener("click", (e) => {
  const a = e.target.closest && e.target.closest("a[href]");
  if (!a) return;
  const href = a.getAttribute("href");
  if (!/^https?:\/\//i.test(href)) return;  // 内部 hash 链接放行
  e.preventDefault();
  let opened = null;
  try { opened = window.open(href, "_blank"); } catch (_) {}
  if (opened) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(href).then(
      () => toast("链接已复制：" + href, "success"),
      () => toast("无法打开外链，请手动复制", "error"),
    );
  } else {
    toast("无法打开外链，URL：" + href);
  }
});
```

- [ ] **Step 3: Modify Home footer in `frontend/assets/pages/home.js`**

Change the footer link to point users to Docs first:

```javascript
    <div class="footer-note">
      本程序仅供学习与研究使用 &middot; 使用风险自负 &middot;
      详见 <a href="#/docs">DOCS / 使用说明</a>
    </div>
```

- [ ] **Step 4: Run targeted tests, expect Docs page/CSS/README failures remain**

Run:

```bash
.venv/Scripts/python -m pytest tests/test_frontend_static.py -q
```

Expected: still FAIL because `frontend/assets/pages/docs.js` and README are not done yet. Route/nav/gate-related failures should be gone.

- [ ] **Step 5: Commit gate and route shell**

```bash
git add frontend/index.html frontend/assets/app.js frontend/assets/pages/home.js
git commit -m "feat(frontend): 增加首次免责声明门禁"
```

---

## Task 4: 新增应用内 Docs 页面与样式

**Files:**
- Create: `frontend/assets/pages/docs.js`
- Modify: `frontend/assets/app.css`

- [ ] **Step 1: Create `frontend/assets/pages/docs.js`**

Create file with exactly this content:

```javascript
import {
  PHONE_SESSION_WARNING,
  renderDisclaimerNotice,
} from "../disclaimer.js";

export async function render(root) {
  root.innerHTML = `
    <header class="board-header">
      <h1 class="board-title">DOCS</h1>
      <div class="board-meta">USER MANUAL · FIRST RUN</div>
    </header>

    <div class="docs-layout">
      <aside class="docs-toc" aria-label="Docs navigation">
        ${toc("before", "BEFORE YOU START")}
        ${toc("quick", "QUICK START")}
        ${toc("accounts", "ACCOUNTS")}
        ${toc("running", "RUNNING")}
        ${toc("paths", "PATHS")}
        ${toc("face", "FACE")}
        ${toc("distance", "DISTANCE")}
        ${toc("faq", "FAQ")}
        ${toc("disclaimer", "DISCLAIMER")}
      </aside>

      <article class="docs-body">
        <section id="before" class="docs-section docs-critical">
          <div class="notice-header">BEFORE YOU START · 使用前必读</div>
          <h2>先退出手机端，再使用本程序</h2>
          <p class="phone-warning"><strong>重要：</strong>${PHONE_SESSION_WARNING}</p>
          <ul>
            <li>操作期间不要多端同时在线，不要一边运行本程序一边打开官方 APP。</li>
            <li>不同学校规则不同，是否允许、是否会触发异常，请自行判断。</li>
            <li>如果你不确定后果，请停止使用本程序。</li>
          </ul>
        </section>

        <section id="quick" class="docs-section">
          <h2>第一次使用流程</h2>
          <ol>
            <li><strong>刷新学校列表：</strong>进入 ACCOUNTS，点击“刷新学校列表”，等待进度完成。</li>
            <li><strong>授权账号：</strong>搜索学校，填写用户名和密码，点击“授权”。</li>
            <li><strong>准备数据：</strong>如果需要复用历史路线，先进入“爬取路径”；如果提示需要人脸，先进入“更新人脸”。</li>
            <li><strong>开始跑步：</strong>进入“开始跑步”，选择账号、跑步类型和距离，确认后执行。</li>
            <li><strong>查看结果：</strong>任务完成后可进入“查询里程”查看累计跑量。</li>
          </ol>
        </section>

        <section id="accounts" class="docs-section">
          <h2>账号授权</h2>
          <p>授权前请确认手机端体适能 / 官方 APP 已退出，并在最近一段时间内不要再次登录手机端。</p>
          <ul>
            <li>学校列表来自接口刷新，首次刷新可能较慢。</li>
            <li>学校输入框支持按学校名称或代码筛选。</li>
            <li>账号凭证和授权结果保存在本地数据库，不主动上传到第三方。</li>
            <li>登录失败时，先检查学校是否选对、账号密码是否正确。</li>
          </ul>
        </section>

        <section id="running" class="docs-section">
          <h2>跑步任务</h2>
          <ul>
            <li><strong>晨跑：</strong>通常对应学校规定的晨跑任务。</li>
            <li><strong>阳光跑：</strong>通常对应日常阳光体育任务。</li>
            <li><strong>自由跑：</strong>通常用于自由运动记录，具体是否计入以学校规则为准。</li>
            <li>距离请按页面提示填写，不要填写明显异常的数据。</li>
            <li>任务执行期间不要重复点击开始，也不要在手机端同时登录。</li>
          </ul>
        </section>

        <section id="paths" class="docs-section">
          <h2>路径爬取</h2>
          <p>路径爬取会读取账号历史运动记录中的轨迹，供后续生成模拟路径时复用。</p>
          <ul>
            <li>如果账号没有历史记录，可能无法爬取到可用路径。</li>
            <li>路径数据保存在本地数据库。</li>
            <li>路径复用不代表一定安全或一定符合学校规则。</li>
          </ul>
        </section>

        <section id="face" class="docs-section">
          <h2>人脸图片</h2>
          <p>部分学校或任务可能要求人脸校验。本程序只能尝试拉取账号已有的人脸图片。</p>
          <ul>
            <li>如果提示账号没有人脸图片，请先在官方 APP 中按学校要求上传。</li>
            <li>人脸图片保存在本地 `face_images/` 目录。</li>
            <li>更新失败时，先确认账号授权是否仍有效。</li>
          </ul>
        </section>

        <section id="distance" class="docs-section">
          <h2>查询里程</h2>
          <p>查询里程用于查看账号当前累计跑量，适合任务后确认结果。</p>
          <ul>
            <li>查询失败时，先检查账号授权状态。</li>
            <li>不同学校统计口径可能不同，以学校平台显示为准。</li>
          </ul>
        </section>

        <section id="faq" class="docs-section">
          <h2>常见问题</h2>
          <dl class="faq-list">
            <dt>启动失败怎么办？</dt>
            <dd>查看程序同目录 `logs/` 下的日志文件；老版本 Windows 10 可能需要安装 Microsoft Edge WebView2 Runtime。</dd>
            <dt>刷新学校很慢怎么办？</dt>
            <dd>学校列表按省份拉取，首次刷新需要等待。页面会显示当前省份和进度。</dd>
            <dt>登录失败怎么办？</dt>
            <dd>确认学校、账号、密码是否正确，并确认手机端没有同时登录。</dd>
            <dt>外链打不开怎么办？</dt>
            <dd>应用会尝试用系统浏览器打开外链；失败时会复制链接，可手动粘贴到浏览器。</dd>
          </dl>
        </section>

        <section id="disclaimer" class="docs-section">
          ${renderDisclaimerNotice()}
        </section>
      </article>
    </div>`;
}

function toc(id, label) {
  return `<a href="#${id}">${label}</a>`;
}
```

- [ ] **Step 2: Append Docs/gate styles to `frontend/assets/app.css`**

Append this CSS to the end of the file:

```css

/* === First-run gate / modal ================================= */
.gate-shell {
  min-height: calc(100vh - 150px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.gate-card {
  width: min(760px, 100%);
  background: var(--paper-card);
  border: 1px solid var(--rule);
  border-left: 4px solid var(--track);
  padding: 28px 32px;
  border-radius: 2px;
}
.gate-kicker {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.2em;
  color: var(--track);
  margin-bottom: 8px;
}
.gate-title {
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: normal;
  letter-spacing: 0.045em;
  margin: 0 0 18px;
}
.gate-notice { margin-bottom: 18px; }
.gate-actions { justify-content: flex-start; }
.gate-exit-hint {
  margin: 10px 0 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--track);
  letter-spacing: 0.06em;
}
.phone-warning {
  border-left: 3px solid var(--mark);
  padding-left: 10px;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(15, 24, 32, 0.48);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.onboarding-card {
  width: min(560px, 100%);
  background: var(--paper-card);
  color: var(--ink);
  border: 1px solid var(--rule);
  border-left: 4px solid var(--mark);
  padding: 24px 28px;
  border-radius: 2px;
  box-shadow: 0 18px 60px rgba(0,0,0,0.24);
}
.onboarding-card h2 {
  margin: 0 0 10px;
  font-family: var(--font-body);
  font-size: 20px;
}
.onboarding-card p {
  margin: 0 0 14px;
  line-height: 1.7;
}

/* === Docs page =============================================== */
.docs-layout {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.docs-toc {
  position: sticky;
  top: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--rule);
  background: var(--paper-card);
}
.docs-toc a {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--mute);
  padding: 5px 6px;
  border-left: 2px solid transparent;
}
.docs-toc a:hover {
  color: var(--ink);
  border-left-color: var(--mark);
}
.docs-body {
  min-width: 0;
}
.docs-section {
  background: var(--paper-card);
  border: 1px solid var(--rule);
  padding: 22px 26px;
  margin-bottom: 14px;
  border-radius: 2px;
}
.docs-section h2 {
  margin: 0 0 10px;
  font-family: var(--font-body);
  font-size: 20px;
  color: var(--ink);
}
.docs-section p,
.docs-section li,
.docs-section dd {
  font-size: 13px;
  line-height: 1.75;
}
.docs-section ol,
.docs-section ul {
  margin: 8px 0 0;
  padding-left: 20px;
}
.docs-critical {
  border-left: 4px solid var(--track);
}
.faq-list {
  margin: 0;
}
.faq-list dt {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--ink);
  margin-top: 12px;
}
.faq-list dt:first-child { margin-top: 0; }
.faq-list dd {
  margin: 4px 0 0;
  color: var(--ink-soft);
}
@media (max-width: 760px) {
  .docs-layout { grid-template-columns: 1fr; }
  .docs-toc { position: static; }
}
```

- [ ] **Step 3: Run targeted tests, expect README failure remains**

Run:

```bash
.venv/Scripts/python -m pytest tests/test_frontend_static.py -q
```

Expected: still FAIL only on README-related assertions if README has not been rewritten yet.

- [ ] **Step 4: Commit Docs page and styles**

```bash
git add frontend/assets/pages/docs.js frontend/assets/app.css
git commit -m "feat(frontend): 新增应用内使用说明"
```

---

## Task 5: 重写 README 为 GUI 用户优先 + 开发者说明

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace `README.md`**

Replace the whole file with:

```markdown
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

进入 `ACCOUNTS`，点击“刷新学校列表”。首次刷新会遍历省份和学校，可能较慢，页面会显示当前省份和进度。

### 3. 授权账号

在 `ACCOUNTS` 中搜索学校，填写用户名和密码，点击“授权”。授权信息保存在本地数据库。

### 4. 准备路径和人脸

- 如果需要复用历史路线，进入“爬取路径”。
- 如果学校任务要求人脸，进入“更新人脸”。如果账号没有人脸图片，请先按学校要求在官方 APP 中上传。

### 5. 开始跑步

回到 `HOME`，进入“开始跑步”，选择账号、跑步类型和距离，确认后执行。任务执行期间不要再次登录手机端。

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
```

- [ ] **Step 2: Run targeted tests, expect pass**

Run:

```bash
.venv/Scripts/python -m pytest tests/test_frontend_static.py -q
```

Expected: PASS, for example:

```text
7 passed
```

The exact count may be higher if more static tests are added later; all tests in `tests/test_frontend_static.py` must pass.

- [ ] **Step 3: Commit README rewrite**

```bash
git add README.md
git commit -m "docs: 重写 GUI 使用说明 README"
```

---

## Task 6: 全量验证与手动体验检查

**Files:**
- No planned source edits. If a verification failure appears, fix it in the smallest relevant file and re-run the failed command before committing.

- [ ] **Step 1: Run full pytest suite**

Run:

```bash
cd F:/CODE/TiShiNengRunning
.venv/Scripts/python -m pytest tests/ -q
```

Expected: PASS. Baseline before this work was 43 tests; after Task 1, expect at least 48 tests. Exact count may vary, but there must be no failures.

- [ ] **Step 2: Start GUI dev mode for manual check**

Run:

```bash
.venv/Scripts/python gui_app.py --dev
```

Expected:

- Backend starts on `127.0.0.1:<port>`.
- PyWebView opens a window.
- If localStorage is already accepted from prior manual testing, clear site data in DevTools or open DevTools and run:

```javascript
localStorage.removeItem("ts_disclaimer_version");
localStorage.removeItem("ts_disclaimer_accepted_at");
localStorage.removeItem("ts_docs_onboarding_seen");
location.reload();
```

- [ ] **Step 3: Verify first-run gate manually**

Expected behavior:

1. App shows `使用前请确认免责声明` before Home content.
2. Top navigation is visible, but normal page content is blocked.
3. Disclaimer includes `使用前必读` and the phone warning.
4. Clicking `暂不使用` shows `请直接关闭此窗口，或返回后点击同意继续。` if the window cannot close.
5. Clicking `我已阅读并同意` enters Home.

- [ ] **Step 4: Verify Docs onboarding manually**

Expected behavior after accepting disclaimer:

1. A `FIRST RUN GUIDE` dialog appears on Home.
2. It includes `最近一段时间内不要再次登录手机端`.
3. `打开 DOCS` navigates to `#/docs`.
4. Reloading after that does not show the onboarding again.

- [ ] **Step 5: Verify Docs page and Settings manually**

Expected behavior:

1. Top nav shows `HOME · ACCOUNTS · DOCS · SETTINGS`.
2. `DOCS` active state works at `#/docs`.
3. Docs first section is `BEFORE YOU START · 使用前必读`.
4. Docs first section includes the phone warning.
5. Settings still shows the disclaimer card.

- [ ] **Step 6: Stop dev GUI**

Close the PyWebView window or interrupt the terminal with Ctrl+C.

- [ ] **Step 7: Review git diff**

Run:

```bash
git status --short
git diff --stat HEAD~5..HEAD
```

Expected:

- Only planned files changed.
- Untracked `.codegraph/` and release zip may still exist from the session baseline; do not add them.

- [ ] **Step 8: Final commit for verification fixes if needed**

If manual verification required fixes, commit them:

```bash
git add frontend/assets/disclaimer.js frontend/assets/pages/docs.js frontend/assets/pages/settings.js frontend/assets/pages/home.js frontend/assets/app.js frontend/assets/app.css frontend/index.html tests/test_frontend_static.py README.md
git commit -m "fix(frontend): 完善首次使用体验验证问题"
```

If no fixes were needed after Task 5, skip this commit.

---

## Self-review

### Spec coverage

- 初次进入弹出免责声明、同意后才能进入：Task 3 implements `renderDisclaimerGate`, versioned localStorage, route blocking.
- 设置页现有免责声明保留：Task 2 keeps Settings disclaimer and reuses shared copy.
- 右上角新增 Docs：Task 3 modifies `frontend/index.html` and route map.
- 初次进入引导点击 Docs：Task 3 implements `maybeShowDocsOnboarding`.
- 引导和 Docs 首屏强调最近不要手机登录：Task 3 onboarding, Task 4 Docs `before` section, Task 5 README.
- README 完全重写：Task 5.
- 错误处理和降级：Task 3 safe localStorage and window close fallback; existing route error handling preserved.
- 测试与验证：Task 1 static tests, Task 6 full pytest + manual checks.

### Placeholder scan

No TBD/TODO/placeholders are present. Code snippets include concrete file contents or exact replacement blocks. Commands include expected outcomes.

### Type and name consistency

- localStorage keys match spec and tests: `ts_disclaimer_version`, `ts_disclaimer_accepted_at`, `ts_docs_onboarding_seen`.
- Shared exports match imports: `DISCLAIMER_VERSION`, `PHONE_SESSION_WARNING`, `renderDisclaimerNotice`.
- Route path and page path match: `"/docs"` → `./pages/docs.js` → `frontend/assets/pages/docs.js`.
- Test strings match implementation snippets.
