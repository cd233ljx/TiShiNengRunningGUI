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
