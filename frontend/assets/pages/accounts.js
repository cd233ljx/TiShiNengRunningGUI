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
