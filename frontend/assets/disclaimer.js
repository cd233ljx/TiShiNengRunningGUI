// 免责声明与使用前提醒的共享文案。
// 启动门禁、Settings、Docs 共用，避免三处文案漂移。

export const DISCLAIMER_VERSION = "1";

export const PHONE_SESSION_WARNING =
  "使用前请退出手机端体适能 / 官方 APP，并在最近一段时间内不要再次登录手机端，避免多端状态冲突或异常。";

export const DISCLAIMER_INTRO =
  "本程序为学习用途，仅用于研究体育数据接口的逆向工程。在你启动它之前，请逐条确认：";

export const DISCLAIMER_ITEMS = [
  "使用本程序辅助完成校园体测，可能违反所在学校的学生守则、体育课程纪律或平台规则",
  "由此产生的任何后果（账号异常、课程处分、信用记录等）由使用者本人承担",
  "本程序的作者及贡献者不为任何使用行为承担法律、纪律或行政责任",
  "账号凭证、跑步记录、运行日志均存储在本地，不主动向第三方上传",
];

export const DISCLAIMER_FOOTNOTE = "继续使用本程序，视为已阅读并同意上述条款。";

export function renderDisclaimerNotice(extraClass = "") {
  const cls = ["notice", extraClass].filter(Boolean).join(" ");
  return `
    <div class="${cls}">
      <div class="notice-header">DISCLAIMER &middot; 免责声明</div>
      <p class="phone-warning"><strong>使用前必读：</strong>${PHONE_SESSION_WARNING}</p>
      <p>${DISCLAIMER_INTRO}</p>
      <ul>
        ${DISCLAIMER_ITEMS.map(item => `<li>${item}</li>`).join("")}
      </ul>
      <p class="footnote">${DISCLAIMER_FOOTNOTE}</p>
    </div>`;
}
