export const DISCLAIMER_VERSION = "1";

export const PHONE_SESSION_WARNING = "最近一段时间内不要再次登录手机端";

export const DISCLAIMER_INTRO = "本程序为学习用途，仅用于研究体育数据接口的逆向工程。在你启动它之前，请逐条确认：";

export const DISCLAIMER_ITEMS = [
  "使用本程序辅助完成校园体测，可能违反所在学校的学生守则或体育课程纪律",
  "由此产生的任何后果（账号封禁、课程处分、信用记录等）由使用者本人承担",
  "本程序的作者及贡献者不为任何使用行为承担法律、纪律或行政责任",
  "账号凭证、跑步记录、运行日志均存储在本地，不向第三方上传"
];

export const DISCLAIMER_FOOTNOTE = "继续使用本程序，视为已阅读并同意上述条款。";

export function renderDisclaimerNotice(extraClass = "") {
  const itemsHtml = DISCLAIMER_ITEMS.map(item => `<li>${item}</li>`).join("");
  return `
    <div class="notice ${extraClass}">
      <div class="notice-header">DISCLAIMER &middot; 免责声明</div>
      <p>${DISCLAIMER_INTRO}</p>
      <ul>
        ${itemsHtml}
      </ul>
      <p class="footnote">${DISCLAIMER_FOOTNOTE}</p>
    </div>
  `;
}
