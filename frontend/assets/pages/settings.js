import { getTheme, setTheme, toast } from "../app.js";
import { renderDisclaimerNotice } from "../disclaimer.js";

export async function render(root) {
  const cur = getTheme();
  root.innerHTML = `
    <h1 class="page-title">SETTINGS</h1>

    ${renderDisclaimerNotice()}

    <div class="card">
      <div class="field">
        <label>主题</label>
        <div class="btn-row">
          <button class="btn ${cur === 'light' ? '' : 'secondary'}" data-theme="light">PAPER &middot; 亮</button>
          <button class="btn ${cur === 'dark' ? '' : 'secondary'}" data-theme="dark">INK &middot; 暗</button>
        </div>
      </div>
      <div class="field">
        <label>关于</label>
        <div style="font-family:var(--font-mono); font-size:11.5px; letter-spacing:0.08em; color:var(--mute); line-height:1.9;">
          TISHINENG &middot; 0.2.0<br>
          STATION TSN-01<br>
          DATA &middot; 本程序所在目录（便携式）
        </div>
      </div>
      <div class="field">
        <label>仓库</label>
        <div class="repo-list">
          <a class="repo-link" href="https://github.com/cd233ljx/TiShiNengRunning" target="_blank" rel="noopener">
            <span class="repo-tag">FORK</span>
            <div class="repo-body">
              <span class="repo-url">github.com/cd233ljx/TiShiNengRunning</span>
              <span class="repo-desc">本程序所在仓库。在原作者基础上加了图形界面，方便非技术用户使用。</span>
            </div>
          </a>
          <a class="repo-link" href="https://github.com/dispose0335/TiShiNengRunning" target="_blank" rel="noopener">
            <span class="repo-tag">UPSTREAM</span>
            <div class="repo-body">
              <span class="repo-url">github.com/dispose0335/TiShiNengRunning</span>
              <span class="repo-desc">原作者仓库。命令行（TUI）版本，本程序的功能与逆向研究均来自此处。</span>
            </div>
          </a>
        </div>
      </div>
    </div>`;

  root.querySelectorAll("[data-theme]").forEach(b => {
    b.addEventListener("click", () => {
      setTheme(b.dataset.theme);
      toast("主题已切换", "success");
      render(document.getElementById("app"));
    });
  });
}
