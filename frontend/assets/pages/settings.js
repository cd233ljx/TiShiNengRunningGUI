import { getTheme, setTheme, toast } from "../app.js";

export async function render(root) {
  const cur = getTheme();
  root.innerHTML = `<div class="card">
    <h2>设置</h2>
    <div class="field">
      <label>主题</label>
      <div class="row" style="max-width:280px;">
        <button class="btn ${cur === 'light' ? '' : 'secondary'}" data-theme="light">亮色</button>
        <button class="btn ${cur === 'dark' ? '' : 'secondary'}" data-theme="dark">暗色</button>
      </div>
    </div>
    <div class="field">
      <label>关于</label>
      <div style="color:var(--text-mute); font-size:13px;">
        TiShiNeng GUI · 0.1.0<br>
        数据目录: 本程序所在目录 (便携式)
      </div>
    </div>
  </div>`;

  root.querySelectorAll("[data-theme]").forEach(b => {
    b.addEventListener("click", () => {
      setTheme(b.dataset.theme);
      toast("主题已切换", "success");
      // 重新渲染以更新按钮高亮
      render(document.getElementById("app"));
    });
  });
}
