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
