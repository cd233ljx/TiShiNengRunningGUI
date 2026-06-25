// 主页：六个入口卡片，对应 CLI 6 个菜单项。
export async function render(root) {
  root.innerHTML = `
    <div class="card">
      <h2>欢迎使用 TiShiNeng 模拟跑步</h2>
      <p class="subtitle">下面选择你要做的事</p>
      <div class="row" style="flex-wrap:wrap;">
        ${tile("🏃", "开始跑步", "#/run-setup")}
        ${tile("👤", "账号管理", "#/accounts")}
        ${tile("📐", "查询里程", "#/distance")}
        ${tile("🛣️", "爬取路径", "#/path-crawl")}
        ${tile("🖼️", "更新人脸", "#/face-update")}
        ${tile("⚙️", "设置",     "#/settings")}
      </div>
    </div>
  `;
}

function tile(emoji, label, href) {
  return `
    <a href="${href}" style="flex:1 1 30%; min-width:220px; text-decoration:none;">
      <div class="card" style="margin:0; text-align:center; cursor:pointer;">
        <div style="font-size:28px;">${emoji}</div>
        <div style="margin-top:8px; color: var(--text);">${label}</div>
      </div>
    </a>`;
}
