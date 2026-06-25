import { api, wsUrl, toast, friendlyError, nav } from "../app.js";

const PHASE_LABELS = {
  preparing:  "加载账号",
  face_start: "人脸验证 · 开始",
  path_gen:   "生成跑步路径",
  running:    "跑步进行中",
  face_mid:   "人脸验证 · 中途",
  uploading:  "上传运动记录",
  face_end:   "人脸验证 · 结束",
};

export async function render(root, { task, km } = {}) {
  if (!task) {
    root.innerHTML = `<div class="card"><h2>运动中</h2><div class="empty">无效的任务</div></div>`;
    return;
  }
  const totalKm = Number(km || 0);

  root.innerHTML = `
    <header class="board-header">
      <h1 class="board-title">LANE · RUNNING</h1>
      <div class="board-meta">TASK · ${task.slice(0, 8).toUpperCase()}</div>
    </header>

    <div class="card">
      <div class="running-display">
        <div class="label">ELAPSED · 已用时间</div>
        <div class="big-time" id="elapsed">00:00</div>
      </div>

      <div class="progress"><span id="bar"></span></div>

      <div class="running-display">
        <div class="big-dist-frame">
          <div class="big-dist" id="dist-cur">0.00</div>
          <div class="unit">/ ${totalKm.toFixed(2)} KM</div>
        </div>
        <div class="label" style="margin-top:6px;">DISTANCE · 已跑距离</div>
      </div>

      <div class="phase-line">
        <span class="dot"></span>
        <span id="phase-text">连接中</span>
      </div>

      <div class="btn-row" style="justify-content:center; margin-top:28px;">
        <button class="btn secondary" id="cancel">取消任务</button>
      </div>
    </div>`;

  const $elapsed = root.querySelector("#elapsed");
  const $distCur = root.querySelector("#dist-cur");
  const $bar     = root.querySelector("#bar");
  const $phase   = root.querySelector("#phase-text");
  const $dot     = root.querySelector(".phase-line .dot");
  const $cancel  = document.getElementById("cancel");
  let terminalAction = null;

  $cancel.addEventListener("click", async () => {
    if (terminalAction) {
      terminalAction();
      return;
    }
    if (!window.confirm("确认取消当前跑步任务？")) return;
    try {
      await api("/api/run/cancel", {
        method: "POST",
        body: JSON.stringify({ task_id: task }),
      });
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    }
  });

  const ws = new WebSocket(wsUrl("/ws/progress", { task }));
  ws.onopen    = () => { $phase.textContent = "已连接"; };
  ws.onmessage = (ev) => {
    let evt;
    try { evt = JSON.parse(ev.data); } catch { return; }
    handleEvent(evt);
  };
  ws.onerror = () => { $phase.textContent = "连接异常"; };

  function handleEvent(evt) {
    const phase = evt.phase;
    if (phase === "running") {
      const pct = evt.total_s > 0 ? Math.min(100, (evt.elapsed_s / evt.total_s) * 100) : 0;
      $bar.style.width = pct.toFixed(1) + "%";
      $elapsed.textContent = fmt(evt.elapsed_s);
      $distCur.textContent = Number(evt.distance_km || 0).toFixed(2);
      $phase.textContent = "跑步进行中";
      return;
    }
    if (phase === "done") {
      $bar.style.width = "100%";
      $phase.innerHTML = `<span class="tag success">完成</span>`;
      $dot.style.animation = "none";
      $dot.style.background = "var(--lane)";
      setReturnHomeAction();
      setTimeout(() => nav("/home"), 3000);
      return;
    }
    if (phase === "error") {
      $phase.innerHTML = `<span class="tag danger">失败</span> ${friendlyError(evt.code, evt.msg)}`;
      $dot.style.animation = "none";
      $dot.style.background = "var(--track)";
      setReturnHomeAction();
      return;
    }
    if (phase === "cancelled") {
      $phase.innerHTML = `<span class="tag">已取消</span>`;
      $dot.style.animation = "none";
      $dot.style.background = "var(--mute)";
      setReturnHomeAction();
      return;
    }
    $phase.textContent = PHASE_LABELS[phase] || phase;
  }

  function setReturnHomeAction() {
    terminalAction = () => nav("/home");
    $cancel.textContent = "返回主页";
  }
}

function fmt(sec) {
  sec = Math.max(0, Math.floor(sec));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
