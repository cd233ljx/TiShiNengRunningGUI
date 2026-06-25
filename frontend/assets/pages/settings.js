import { getTheme, setTheme, toast } from "../app.js";

export async function render(root) {
  const cur = getTheme();
  root.innerHTML = `
    <h1 class="page-title">SETTINGS</h1>

    <div class="notice">
      <div class="notice-header">DISCLAIMER &middot; 免责声明</div>
      <p>本程序为学习用途，仅用于研究体育数据接口的逆向工程。在你启动它之前，请逐条确认：</p>
      <ul>
        <li>使用本程序辅助完成校园体测，可能违反所在学校的学生守则或体育课程纪律</li>
        <li>由此产生的任何后果（账号封禁、课程处分、信用记录等）由使用者本人承担</li>
        <li>本程序的作者及贡献者不为任何使用行为承担法律、纪律或行政责任</li>
        <li>账号凭证、跑步记录、运行日志均存储在本地，不向第三方上传</li>
      </ul>
      <p class="footnote">继续使用本程序，视为已阅读并同意上述条款。</p>
    </div>

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
          TISHINENG &middot; 0.1.0<br>
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
