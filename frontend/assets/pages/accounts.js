import { api, wsUrl, toast, friendlyError } from "../app.js";

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
        <div id="refresh-progress" class="subtitle" style="margin-top:10px; display:none;"></div>
      </form>
    </div>`;

  await reloadAccounts();
  await loadSchools();

  document.getElementById("refresh-schools").addEventListener("click", async (e) => {
    const btn = e.target;
    btn.disabled = true; btn.textContent = "启动中...";
    try {
      const r = await api("/api/schools/refresh", { method: "POST" });
      streamRefreshProgress(r.task_id, btn);
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
      btn.disabled = false; btn.textContent = "刷新学校列表";
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

function streamRefreshProgress(taskId, btn) {
  const hint = document.getElementById("refresh-progress");
  hint.style.display = "block";
  hint.textContent = "等待服务器响应...";

  const reset = () => {
    btn.disabled = false;
    btn.textContent = "刷新学校列表";
  };

  const ws = new WebSocket(wsUrl("/ws/progress", { task: taskId }));
  ws.onmessage = (ev) => {
    let evt;
    try { evt = JSON.parse(ev.data); } catch { return; }
    if (evt.phase === "refreshing") {
      const total = evt.total ?? "?";
      const cur = evt.current ?? "?";
      const province = evt.province || "";
      const added = evt.schools_added ?? 0;
      btn.textContent = `刷新中 ${cur}/${total}...`;
      hint.textContent = `正在加载省份「${province}」，已收录 ${added} 所学校...`;
    } else if (evt.phase === "done") {
      const skipped = evt.skipped ?? 0;
      toast(`已更新 ${evt.total} 所学校${skipped ? `（跳过 ${skipped}）` : ""}`, "success");
      hint.style.display = "none";
      reset();
      loadSchools();
    } else if (evt.phase === "error") {
      toast(friendlyError(evt.code, evt.msg), "error");
      hint.textContent = `失败：${friendlyError(evt.code, evt.msg)}`;
      reset();
    }
  };
  ws.onerror = () => {
    toast("进度连接异常", "error");
    hint.style.display = "none";
    reset();
  };
}
