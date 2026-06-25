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
