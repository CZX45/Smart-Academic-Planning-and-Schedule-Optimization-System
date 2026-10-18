# 候选与发布门禁

状态：**NOT_APPROVED / 真实发布验收未完成**。工程源码候选为 0.1.8，扩展 v9 修订保持不变。正式安装仍为 0.1.5、正式库 schema 1；本次没有运行安装、升级、卸载或正式数据迁移。

- Web/API/Extension 源码 production build：PASS。
- 扩展 unpacked 候选已生成到隔离工作树 `dist/extension-unpacked`；没有加载进用户浏览器。内容/来源哈希见 `PACKAGE_EVIDENCE.json`。
- Windows NSIS 构建：PASS，未签名、未安装；`<SOURCE_WORKTREE>\dist\windows-installer\SAPSOS-Local-Desktop-0.1.8-x64-setup.exe`（30442132 bytes）。SHA-256：`f8b6976a930dc40e3b8e56c789a2cb646e298eeab6036ef779b63005f164b240`；来源提交 `7b0ea63e906409205f071b048fe29161f05f6e6a`。NSIS transient-resource、staging 禁止路径、逐文件大小/hash 以及 artifact 校验均通过，见 WINDOWS_PACKAGE_EVIDENCE.json。
- 身份校验：0.1.8 在桌面、Rust、自有五包、API 与 OpenAPI 一致。
- 正式库及安装文件：`.cache/evidence/protected-baseline.json` 与 `PROTECTION_EVIDENCE.json` 的构建后复核记录 SHA、size、mtime。基线是在本轮早期合成测试之后采集，不伪称任务开始前快照；后续完整回归/构建均在其后。
- 本轮无远端 push/merge/tag/release。未使用真实学校规则补齐缺口。

发布前阻断：真实两学科、真实 MyProgress/Catalog/Sections/学业规则审核、真实候选 UI、原生安装生命周期/升级回滚、签名与干净 Windows 验收。自动化 PASS 不解除这些门禁。

解包 API 合成启动/空库建档/进程重启读回/schema 2 检查 PASS。它不是安装后的 Tauri/WebView2 或原生窗口验收。全局 Python 打包失败产物和日志均保留；最终成功包使用独立 venv 的 36 个测试版本依赖，未修改打包保护规则。
