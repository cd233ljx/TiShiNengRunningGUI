import { api, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; }
  catch (e) {
    root.innerHTML = `<h1 class="page-title">DISTANCE INQUIRY</h1>
      <div class="card"><div class="empty">${e.message}</div></div>`;
    return;
  }
  if (!accounts.length) {
    root.innerHTML = `<h1 class="page-title">DISTANCE INQUIRY</h1>
      <div class="card"><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`;
    return;
  }

  root.innerHTML = `
    <h1 class="page-title">DISTANCE INQUIRY</h1>
    <div class="card">
      <div class="field"><label>账号</label>
        <select id="acc" class="select">
          ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
        </select>
      </div>
      <div class="btn-row"><button class="btn" id="go">查询</button></div>
      <div id="result" style="margin-top:28px;"></div>
    </div>`;

  document.getElementById("go").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "查询中";
    try {
      const r = await api("/api/distance/query", {
        method: "POST",
        body: JSON.stringify({ account_id: Number(document.getElementById("acc").value) })
      });
      document.getElementById("result").innerHTML = `
        <div class="stat-row">
          <span class="stat-big">${r.total_km.toFixed(2)}</span>
          <span class="stat-unit">KM</span>
        </div>
        <div class="stat-cap">${r.count} 条记录 · ${r.username} · ${r.school_name || ""}</div>`;
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    } finally {
      e.target.disabled = false; e.target.textContent = "查询";
    }
  });
}
