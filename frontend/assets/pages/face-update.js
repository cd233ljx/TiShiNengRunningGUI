import { api, toast, friendlyError } from "../app.js";

export async function render(root) {
  let accounts = [];
  try { accounts = (await api("/api/accounts")).items; } catch (e) {
    root.innerHTML = `<div class="card"><h2>更新人脸图片</h2><div class="empty">${e.message}</div></div>`; return;
  }
  if (!accounts.length) {
    root.innerHTML = `<div class="card"><h2>更新人脸图片</h2><div class="empty">尚无账号，<a href="#/accounts">去添加</a></div></div>`; return;
  }

  root.innerHTML = `<div class="card">
    <h2>更新人脸图片</h2>
    <p class="subtitle">从服务器拉取最新人脸图，保存到本地 face_images/</p>
    <div class="field">
      <label>账号</label>
      <select id="acc" class="select">
        ${accounts.map(a => `<option value="${a.id}">${a.username} · ${a.school_name || ""}</option>`).join("")}
      </select>
    </div>
    <div class="btn-row">
      <button class="btn" id="go">开始更新</button>
    </div>
    <div id="result" style="margin-top:12px;"></div>
  </div>`;

  document.getElementById("go").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "更新中...";
    try {
      const r = await api("/api/face/update", {
        method: "POST",
        body: JSON.stringify({ account_id: Number(document.getElementById("acc").value) })
      });
      document.getElementById("result").innerHTML =
        `<span class="tag success">完成</span> 已加载 ${r.size} 字节`;
      toast("人脸图片已更新", "success");
    } catch (err) {
      toast(friendlyError(err.code, err.message), "error");
    } finally {
      e.target.disabled = false; e.target.textContent = "开始更新";
    }
  });
}
