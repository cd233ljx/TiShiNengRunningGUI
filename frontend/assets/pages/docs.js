import {
  PHONE_SESSION_WARNING,
  renderDisclaimerNotice,
} from "../disclaimer.js";

export async function render(root) {
  root.innerHTML = `
    <header class="board-header">
      <h1 class="board-title">DOCS</h1>
      <div class="board-meta">USER MANUAL · FIRST RUN</div>
    </header>

    <div class="docs-layout">
      <aside class="docs-toc" aria-label="Docs navigation">
        ${toc("before", "BEFORE YOU START")}
        ${toc("quick", "QUICK START")}
        ${toc("accounts", "ACCOUNTS")}
        ${toc("running", "RUNNING")}
        ${toc("paths", "PATHS")}
        ${toc("face", "FACE")}
        ${toc("distance", "DISTANCE")}
        ${toc("faq", "FAQ")}
        ${toc("disclaimer", "DISCLAIMER")}
      </aside>

      <article class="docs-body">
        <section id="before" class="docs-section docs-critical">
          <div class="notice-header">BEFORE YOU START · 使用前必读</div>
          <h2>先退出手机端，再使用本程序</h2>
          <p class="phone-warning"><strong>重要：</strong>${PHONE_SESSION_WARNING}</p>
          <ul>
            <li>操作期间不要多端同时在线，不要一边运行本程序一边打开官方 APP。</li>
            <li>不同学校规则不同，是否允许、是否会触发异常，请自行判断。</li>
            <li>如果你不确定后果，请停止使用本程序。</li>
          </ul>
        </section>

        <section id="quick" class="docs-section">
          <h2>第一次使用流程</h2>
          <ol>
            <li><strong>刷新学校列表：</strong>进入 ACCOUNTS，点击“刷新学校列表”，等待进度完成。</li>
            <li><strong>授权账号：</strong>搜索学校，填写用户名和密码，点击“授权”。</li>
            <li><strong>准备数据：</strong>如果需要复用历史路线，先进入“爬取路径”；如果提示需要人脸，先进入“更新人脸”。</li>
            <li><strong>开始跑步：</strong>进入“开始跑步”，选择账号、跑步类型和距离，确认后执行。</li>
            <li><strong>查看结果：</strong>任务完成后可进入“查询里程”查看累计跑量。</li>
          </ol>
        </section>

        <section id="accounts" class="docs-section">
          <h2>账号授权</h2>
          <p>授权前请确认手机端体适能 / 官方 APP 已退出，并在最近一段时间内不要再次登录手机端。</p>
          <ul>
            <li>学校列表来自接口刷新，首次刷新可能较慢。</li>
            <li>学校输入框支持按学校名称或代码筛选。</li>
            <li>账号凭证和授权结果保存在本地数据库，不主动上传到第三方。</li>
            <li>登录失败时，先检查学校是否选对、账号密码是否正确。</li>
          </ul>
        </section>

        <section id="running" class="docs-section">
          <h2>跑步任务</h2>
          <ul>
            <li><strong>晨跑：</strong>通常对应学校规定的晨跑任务。</li>
            <li><strong>阳光跑：</strong>通常对应日常阳光体育任务。</li>
            <li><strong>自由跑：</strong>通常用于自由运动记录，具体是否计入以学校规则为准。</li>
            <li>距离请按页面提示填写，不要填写明显异常的数据。</li>
            <li>任务执行期间不要重复点击开始，也不要在手机端同时登录。</li>
          </ul>
        </section>

        <section id="paths" class="docs-section">
          <h2>路径爬取</h2>
          <p>路径爬取会读取账号历史运动记录中的轨迹，供后续生成模拟路径时复用。</p>
          <ul>
            <li>如果账号没有历史记录，可能无法爬取到可用路径。</li>
            <li>路径数据保存在本地数据库。</li>
            <li>路径复用不代表一定安全或一定符合学校规则。</li>
          </ul>
        </section>

        <section id="face" class="docs-section">
          <h2>人脸图片</h2>
          <p>部分学校或任务可能要求人脸校验。本程序只能尝试拉取账号已有的人脸图片。</p>
          <ul>
            <li>如果提示账号没有人脸图片，请先在官方 APP 中按学校要求上传。</li>
            <li>人脸图片保存在本地 \`face_images/\` 目录。</li>
            <li>更新失败时，先确认账号授权是否仍有效。</li>
          </ul>
        </section>

        <section id="distance" class="docs-section">
          <h2>查询里程</h2>
          <p>查询里程用于查看账号当前累计跑量，适合任务后确认结果。</p>
          <ul>
            <li>查询失败时，先检查账号授权状态。</li>
            <li>不同学校统计口径可能不同，以学校平台显示为准。</li>
          </ul>
        </section>

        <section id="faq" class="docs-section">
          <h2>常见问题</h2>
          <dl class="faq-list">
            <dt>启动失败怎么办？</dt>
            <dd>查看程序同目录 \`logs/\` 下的日志文件；老版本 Windows 10 可能需要安装 Microsoft Edge WebView2 Runtime。</dd>
            <dt>刷新学校很慢怎么办？</dt>
            <dd>学校列表按省份拉取，首次刷新需要等待。页面会显示当前省份和进度。</dd>
            <dt>登录失败怎么办？</dt>
            <dd>确认学校、账号、密码是否正确，并确认手机端没有同时登录。</dd>
            <dt>外链打不开怎么办？</dt>
            <dd>应用会尝试用系统浏览器打开外链；失败时会复制链接，可手动粘贴到浏览器。</dd>
          </dl>
        </section>

        <section id="disclaimer" class="docs-section">
          ${renderDisclaimerNotice()}
        </section>
      </article>
    </div>`;
}

function toc(id, label) {
  return `<a href="#${id}">${label}</a>`;
}
