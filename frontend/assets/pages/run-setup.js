import { api, toast, friendlyError, nav } from "../app.js";

const RUN_TYPES = [
  { key: "morning", label: "晨跑",   hint: "MORNING" },
  { key: "sun",     label: "阳光跑", hint: "DAYTIME" },
  { key: "freedom", label: "自由跑", hint: "ANYTIME" },
];

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; }
  catch (err) {
    root.innerHTML = `<h1 class="page-title">NEW RUN</h1>
      <div class="card"><div class="empty">加载账号失败：${err.message}</div></div>`;
    return;
  }
  if (!accounts.length) {
    root.innerHTML = `<h1 class="page-title">NEW RUN</h1>
      <div class="card"><div class="empty">尚未授权任何账号，<a href="#/accounts">去添加</a></div></div>`;
    return;
  }

  root.innerHTML = `
    <h1 class="page-title">NEW RUN</h1>
    <div class="card">
      <form id="run-form">
        <div class="field">
          <label>账号</label>
          <select id="acc" class="select">
            ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label>跑步类型</label>
          <div class="run-type-pick" id="run-types">
            ${RUN_TYPES.map(t => `
              <div class="pick" data-key="${t.key}">
                <div style="font-family:var(--font-display); font-size:18px; letter-spacing:0.05em; color:var(--ink);">${t.label}</div>
                <div style="margin-top:6px; font-family:var(--font-mono); font-size:10px; letter-spacing:0.18em; color:var(--mute);">${t.hint}</div>
              </div>`).join("")}
          </div>
        </div>
        <div class="field">
          <label>距离 (km)</label>
          <input id="dist" class="input" type="number" step="0.1" min="0.1" max="50" value="3.0">
        </div>
        <div class="btn-row">
          <button type="submit" class="btn" id="go">开始跑步</button>
        </div>
      </form>
    </div>`;

  let selectedType = "freedom";
  const picks = root.querySelectorAll(".run-type-pick .pick");
  function selectType(key) {
    selectedType = key;
    picks.forEach(p => p.classList.toggle("selected", p.dataset.key === key));
  }
  picks.forEach(p => p.addEventListener("click", () => selectType(p.dataset.key)));
  selectType("freedom");

  document.getElementById("run-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const account_id = Number(document.getElementById("acc").value);
    const distance_km = Number(document.getElementById("dist").value);
    if (!account_id || !(distance_km > 0)) { toast("参数无效", "error"); return; }

    try {
      const r = await api("/api/run/start", {
        method: "POST",
        body: JSON.stringify({ account_id, run_type: selectedType, distance_km }),
      });
      nav(`/run-active?task=${encodeURIComponent(r.task_id)}&km=${distance_km}`);
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    }
  });
}
