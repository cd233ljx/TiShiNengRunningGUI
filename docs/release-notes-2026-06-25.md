# 2026-06-25 GUI 打包分支收尾记录

分支：`feat/gui-and-packaging`

## 已完成范围

- 新增 PyWebView GUI 入口 `gui_app.py`，后端由同进程后台线程运行 FastAPI / uvicorn。
- 新增 PyInstaller onefile 打包配置：`tishineng.spec`、`version_info.txt`、`icon.ico`。
- 新增构建校验脚本 `scripts/verify-build.bat`：先跑测试，再构建 `dist\TiShiNeng.exe`。
- 新增打包冒烟清单 `docs/packaging-smoke.md`。
- 更新 README 的 GUI 使用、源码构建、开发模式和启动排障说明。
- 修复进度总线终态 replay，避免任务比 WebSocket 订阅更快结束时前端永久卡住。
- 修复前端学校选项渲染，避免把远程学校名称插入 `innerHTML`。
- 修复跑步终态按钮处理，避免取消 handler 与返回主页 handler 同时残留。
- 修复 Windows 代理环境下的本机启动探测和学校刷新可选查询问题。
- 冻结后启动失败提示改为 Windows 原生对话框，避免打包 tkinter/Tcl runtime。

## 发布前验证

推荐在发布前执行：

```bat
scripts\verify-build.bat
```

成功标准：

- `pytest tests\ -q` 通过。
- PyInstaller 构建通过。
- `dist\TiShiNeng.exe` 生成。

随后按 `docs\packaging-smoke.md` 手动完成 GUI 冒烟测试。

## 不纳入 Git 的产物

- `dist/`、`build/`：PyInstaller 临时/输出目录。
- `release/`：本地发布拷贝目录。
- `.codegraph/`：本地代码索引目录。
- `tsn_data.db`、`logs/`、`face_images/`：运行时便携数据。
