import { api, wsUrl, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; } catch (e) {
    root.innerHTML = `<h1 class="page-title">PATH CRAWL</h1>
      <div class="card"><div class="empty">${e.message}</div></div>`;
    return;
  }
  if (!accounts.length) {
    root.innerHTML = `<h1 class="page-title">PATH CRAWL</h1>
      <div class="card"><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`;
    return;
  }

  root.innerHTML = `
    <h1 class="page-title">PATH CRAWL</h1>
    <div class="card">
      <p class="subtitle">从所选账号的历史运动记录中提取路径，存到本地数据库供跑步复用</p>
      <div class="field"><label>账号</label>
        <select id="acc" class="select">
          ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
        </select>
      </div>
      <div class="btn-row">
        <button class="btn" id="go">开始爬取</button>
      </div>
      <div id="status" class="subtitle" style="margin-top:16px; font-family:var(--font-mono); font-size:11px; letter-spacing:0.1em;"></div>
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
