// 主页：LANE 调度台。6 个跑道卡片对应 CLI 6 个操作。
// 编号是位置标识（哪条跑道）而非顺序——用户可以跳着用。

export async function render(root) {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, "·");

  root.innerHTML = `
    <header class="board-header">
      <h1 class="board-title">OPERATIONS BOARD</h1>
      <div class="board-meta">SESSION · ${today}</div>
    </header>

    <div class="lane-grid">
      ${lane("01", "开始跑步", "记录一次模拟跑步",   "#/run-setup")}
      ${lane("02", "账号管理", "添加 / 删除已授权",   "#/accounts")}
      ${lane("03", "查询里程", "查看本账号累计跑量", "#/distance")}
      ${lane("04", "爬取路径", "抓取可复用历史路径", "#/path-crawl")}
      ${lane("05", "更新人脸", "重新拉取本账号人脸", "#/face-update")}
      ${lane("06", "设置",     "主题 · 版本",         "#/settings")}
    </div>

    <div class="footer-note">
      本程序仅供学习与研究使用 &middot; 使用风险自负 &middot;
      详见 <a href="#/docs">DOCS / 使用说明</a>
    </div>
  `;
}

function lane(num, title, desc, href) {
  return `
    <a class="lane-card" href="${href}">
      <span class="lane-num-label">LANE</span>
      <div class="lane-num">${num}</div>
      <h3>${title}</h3>
      <p>${desc}</p>
      <div class="lane-arrow">ENTER  &gt;</div>
    </a>`;
}
