# 下一轮源码交接

- 分支：`comprehensive-repair-20261018-safe-sync`（Owner 在命名冲突后明确授权的新发布分支）。这是独立根脱敏快照；原修复分支和完整历史保留在本机。最终远端 HEAD 以同步报告和 `git rev-parse HEAD` 为准。
- 起点：`066dd9c57294bec704df61ad2a5b1db3f5d03f08`。本报告由修复提交维护；最终交付提交另在交付记录中列出，避免自引用 SHA。
- 不覆盖原 main，不整合旧 PR #28。PR #87 的实现已包含在修复源码中；脱敏发布分支不继承原私密历史，不能按原提交祖先关系推断。
- 差异：见 FIXES_AND_IMPROVEMENTS 的 F01–F20 和 MODIFIED_FILES；所有新增样本均 synthetic/mock。
- 云端可继续：typed reviewed program/course/term candidates 接入真实档案 UI；扩充语义边界/跨来源冲突/重复及真实脱敏夹具；按输入身份扩展其他异步 UI 回归；Python 3.12 / PostgreSQL CI（本轮未跑）。不要重建已存在的诊断/备份/preflight 或重新实现 v9 checkpoint。
- 云端不可替代：用户已登录页面两学科验收、116 解锁授权、学校政策审核、原生桌面/安装/DPI/签名验收。

建议接续命令（实际本轮命令、工具版本、退出码见 TEST_EVIDENCE 和 CHECK_RESULTS）：`pnpm install --frozen-lockfile`、`pnpm test`、`pnpm lint`、`pnpm typecheck`、`pnpm format`、`pnpm build`、`pnpm openapi:check`、`pnpm exec playwright test`、`pnpm desktop:identity:check`。E2E 现在自己创建合成库；任何已有服务占用端口应失败，不得复用或终止用户服务。

本地忽略的构建包、浏览器、合成数据库、日志和 trace 不随源码提交。本次已获 Owner 明确授权，仅允许扫描通过后推送上述分支；全历史/文件审查证据见 `../github-safe-sync-20261018/SECURITY_REVIEW.md`。任何人工/真实验收结果都需单独登记来源，不能复用本报告的自动化 PASS。

修复源码提交：`7b0ea63e906409205f071b048fe29161f05f6e6a`。后续提交只补充文档、证据和生成目录忽略规则；包中产品源码仍对应该提交。交付 HEAD 由本报告所在分支 `git rev-parse HEAD` 取得，最终对话附完整值。后台打包应使用独立 venv 和本目录 BUILD_RUNTIME_VERSIONS.txt，对齐后先执行 `python -m pip check`，避免全局开发包污染。原始失败包保留，不能通过放宽 staging 禁止路径来修复。


成功构建环境的重建顺序（仓库根目录、后台 CLI；不同平台的 wheel/安装包结果不作为本次 byte parity）：

```powershell
python -m venv .cache/build-venv
.cache/build-venv/Scripts/python.exe -m pip install -r docs/comprehensive-repair-20261018/BUILD_RUNTIME_VERSIONS.txt
.cache/build-venv/Scripts/python.exe -m pip install --no-deps ./apps/api
.cache/build-venv/Scripts/python.exe -m pip check
$env:PATH = (Resolve-Path .cache/build-venv/Scripts).Path + ';' + $env:PATH
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) '.cache/pyinstaller-config'
$env:NEXT_TELEMETRY_DISABLED = '1'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/Build-Windows-Installer.ps1
```

本轮实际执行使用 `.cache/Build-IsolatedCandidate.ps1` 设置上述环境并调用同一构建脚本，外层期限 900s；成功包源 SHA 和 hash 见 WINDOWS_PACKAGE_EVIDENCE.json。不要执行安装程序来替代尚未获授权的真实安装验收。

公开测试记录中的 `<SOURCE_WORKTREE>`、`<ORIGINAL_CHECKOUT>`、`<USERPROFILE>` 和 `<PYTHON_3_14>` 是隐私占位符；原始命令、退出码和日志保留在本机。重建前选择 Python 3.14.3。
