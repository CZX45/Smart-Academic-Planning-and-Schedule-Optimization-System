# 测试证据 — 2026-10-18

范围：Windows 后台、合成/内存/临时 SQLite、脱敏夹具和 headless Chromium。没有真实学校页面或原生桌面验收。全部记录命令、cwd、deadline、exit code、timed_out 和原日志 SHA；详见 CHECK_RESULTS.json。原日志保留于隔离工作树 `.cache/evidence/`，失败 trace 位于 `.cache/e2e/`，不会丢弃失败记录。

运行工具：Python `<PYTHON_3_14>` 3.14.3；Node 24.13.1；pnpm 10.28.1 使用本机缓存入口 `node <USERPROFILE>/AppData/Local/node/corepack/v1/pnpm/10.28.1/bin/pnpm.cjs`。以下 pnpm 均指该入口；外层统一由 `.cache/run_check.py --name NAME --timeout SECONDS -- COMMAND` 限时/记录。设置工作树 TEMP/TMP 和 COREPACK_HOME；测试 Python PATH 选择 3.14，未修改系统默认 Python。E2E 设置 task-local PLAYWRIGHT_BROWSERS_PATH 及 PLAYWRIGHT_WEB_PORT=3320。

| 检查（精确子命令） | 证据名称 | 结果 | 外层期限 |
|---|---|---|---|
| pnpm test | full-unit-final | PASS：Python 352、extension 173、shared 66、web 23、Node isolation 2，共 616；0 skipped | 600s |
| node node_modules/@playwright/test/cli.js test | full-e2e-final | PASS：58；包含 85 行真实路径 API + 合成输入、v9 DOM、键盘导航、四项状态隔离反例 | 660s（内部 600s） |
| pnpm lint | final-lint-clean | PASS：Ruff/ESLint，无新增 warning | 180s |
| pnpm typecheck | final-types-clean | PASS：严格 TS、mypy 159 文件 | 180s |
| pnpm format | final-format | PASS：Prettier、Ruff 159 文件 | 180s |
| pnpm build | final-build | PASS：compileall、tsc、Next 静态输出 | 300s |
| pnpm openapi:generate | openapi-generation | PASS：补回已实现 remap 字段；提交后另外运行 openapi:check | 60s |
| powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/Validate-Desktop-Identity.ps1 | desktop-identity-final | PASS：0.1.8 | 30s |
| pnpm extension:package | extension-package | PASS：unpacked 候选 | 90s |
| python -m pytest tests/test_local_data_removal.py -k reparse -W error::pytest.PytestUnhandledThreadExceptionWarning -q（cwd apps/api） | junction-warning-regression | PASS：1，无线程异常；其余 6 deselected 为该定向测试，不是完整套件跳过 | 45s |

本轮实际失败与处理：原 format/identity 失败已修复；summary、import quality、academic values、repeated credits、online conflict、zero section、student/real/schedule scope 的 RED/GREEN 均保留。初始 API TestClient 在沙箱 Windows socketpair 阻塞，同一合成测试移至后台批准执行后通过；未降低业务校验。系统 Temp 的 cleanup 挂起以栈定位并修复。Next root 变更后的旧生成缓存导致 manifest 错误，旧缓存移入本工作树证据目录，清洁生成后通过。新增 E2E API 最初未设置预期 API_PORT，安全边界拒绝并最终 429；补齐测试配置，未关闭本地请求认证。完整 E2E 首轮 57/58，旧 review fixture 自相矛盾已改成实际两次确认，最后 58/58。类型检查 bytes 插值警告修为显式 repr。

最终 pytest 仍有一条现有 FastAPI/Starlette httpx 弃用提示；未换依赖来掩盖。没有失败/跳过被删除。性能没有同口径对照，不作提速结论。真实 GUI、当前正式安装生命周期、学校规则正确性、Python 3.12 和 PostgreSQL 服务回归均 UNVERIFIED/NOT_RUN；不是本轮合成 PASS 的外推。

安装包构建、Rust 与提交后检查在本报告后续交付记录中追加实际结果。


补充构建证据：首轮全局 Python 打包被 staging 禁止测试文件检查拦截，失败产物保留于 `.cache/failed-global-packaging/`。改用独立 venv；初次安装解析到了未测试的新依赖，因此按 `BUILD_RUNTIME_VERSIONS.txt` 的 36 个实际测试版本对齐。依赖检查发现 colorama/greenlet 缺失，补齐后 pip check 通过。期间一次尝试以缺 greenlet metadata 退出 1，日志保留；没有终止其他进程或放宽过滤规则。第二轮最小环境通过 staging 内容检查，解包 API 的合成空库/建档/重启/schema 检查通过。最终 NSIS/Rust 结果在交付记录追加。

`cargo fmt --manifest-path desktop-shell/src-tauri/Cargo.toml -- --check`：PASS；`pnpm openapi:check` 提交后 PASS。7 份 codebase 文档已逐项复核结构、证据指向和未验证边界。最初保护比较器遇到 PowerShell JSON 日期自动类型转换，字符串比较误报；逐字段原始 JSON 复核确认 SHA/size/UTC 时间均相同，最终以原始字符串比较。


最终追加：`cargo test --release --locked --manifest-path desktop-shell/src-tauri/Cargo.toml` 在 600s 外层期限内 PASS，25 passed / 0 failed / 0 ignored。全套计数为 616 单元/集成 + 58 headless E2E + 25 Rust = **699 个测试**，另有独立 packaged API smoke（5 项断言，不混入测试数量）。最终 Windows NSIS build 272.6s、退出 0；包校验已在构建脚本中执行，资源契约和逐文件 hash 均通过。

包来源为 `7b0ea63e906409205f071b048fe29161f05f6e6a`；交付后续仅文档/证据和生成目录忽略规则。`git diff --exit-code 7b0ea63e906409205f071b048fe29161f05f6e6a -- apps desktop-shell packages scripts tests playwright.config.ts package.json` PASS，证明产品源码无后续漂移。保护文件在全部构建之后再次核对 PASS，见 PROTECTION_EVIDENCE.json。NSIS 安装、原生 GUI、真实浏览器扩展加载、真实学校数据仍未执行。
