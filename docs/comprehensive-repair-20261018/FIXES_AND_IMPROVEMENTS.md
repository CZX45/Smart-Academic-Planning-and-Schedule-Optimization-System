# 修复与改进

共 20 项；每项依据当前源码和反例/检查，不把历史 v9 功能再计为新修复。所有学术回归数据均为合成。文件路径相对仓库根。

| ID | 当前根因与修改 | 主要文件 | 证据 |
|---|---|---|---|
| F01 | 标签边界吞入重复字段；冲突值未阻断；短导航词可成为 degree。重复同值去重、冲突留空并报告，紧邻冒号可解析 | extension/src/content/extractors.ts（位于 apps/） | summary-boundaries 4 个反例 |
| F02 | 非空摘要字段被标 high/无需审核。改 medium、requiresReview、UNREVIEWED 和文本 offset；结构通过上限不再 100% | 同上 | 字段 provenance 回归；offset 是捕获文本位置，非官方来源认证 |
| F03 | API 信任客户端已通过摘要；错误学位/专业/GPA 可绕过提取器。服务端剔除污染值、保留 rejectedSummaryFields、结构化错误并阻断 | apps/api/app/services/data_imports/{summary_quality,parsers}.py | 10 个 import-summary 测试 |
| F04 | NaN/Infinity/超界 confidence 导致异常或错误满分。非有限及超界值降为 0 | apps/api/app/services/data_imports/parsers.py | import-summary 测试 |
| F05 | FIN*3000 与空格/连字符不能统一。仅规范单课程分隔符，不猜测复合代码或等价关系 | apps/api/app/services/data_imports/normalizers.py | academic-value-boundaries |
| F06 | 数字 0 学分被当缺失，非有限数进入比较。保留明确 0，拒绝 NaN/Infinity | apps/api/app/services/course_state/engine.py | academic-value-boundaries |
| F07 | 空白成绩与最低成绩字符串造成错误判定。统一空白为缺失，缺最低成绩证据保持 UNKNOWN | apps/api/app/services/degree_audit/grade_policy.py | academic-value-boundaries |
| F08 | 重复 planned/retake 或完成+计划重复增加最低学分。每个课程身份最多计一次、完成覆盖未来潜在值 | apps/api/app/services/course_eligibility/engine.py | 两个重复学分反例 |
| F09 | is_online 被当成无时间，定时线上课绕过冲突/不可用日。仅真正 arranged/缺时间视为 floating | apps/api/app/services/schedule_optimizer/engine.py | overlap 和 excluded-day 两个反例 |
| F10 | Section credits=0 被 truthiness 替换为 Course 默认值。仅 None 才回退 | 同上 | 零学分方案实际包含班次的 RED/GREEN |
| F11 | 学生、API、候选或偏好切换后显示旧结果，旧异步响应可写入新状态。抽取带 generation 的局部 hook，按工作流身份和输入失效 | apps/web/src/lib/use-scoped-workflow-state.ts、course-state-workflow.ts、section-monitoring-workflow.ts、app/page.tsx | 学生切换、迟到响应、课表偏好 E2E |
| F12 | 真实档案 readiness 可启用硬编码 demo 候选。当前这些控件只允许明确 demo 学生，真实候选接入仍待开发 | apps/web/src/app/page.tsx | real readiness 不启用 mock 的 E2E |
| F13 | 自动验证文案混淆结构、值核实和审核应用。改为结构校验通过/待审核，保留精确 import-id 应用关联 | page.tsx、data-import-preview.ts | 标签单元测试及完整浏览器回归 |
| F14 | Windows cleanup 测试在系统 Temp 重试挂起；junction 中文输出在线程中误按 UTF-8 解码。使用工作树临时目录、30s 子进程期限及 bytes 输出 | tests/test_windows_installer_foundation.py、test_local_data_removal.py（位于 apps/api/） | 原超时栈、cleanup GREEN、线程警告设为错误仍通过 |
| F15 | E2E 入口复用服务且可默认连接正式库/继承 DATABASE_URL。改独立合成库、明确 mock seed、拒绝服务复用、独立 APPDATA、固定测试 API 身份、分层期限 | scripts/e2e-isolation.mjs、run-e2e.mjs、playwright.config.ts、package.json | 两个 Node 契约测试及 58 E2E |
| F16 | 旧摘要审核夹具返回两条 confirmed 却断言 0。改为 UNREVIEWED→实际点击两次确认→应用，保留原断言并增加 1/2 计数断言 | tests/e2e/home.spec.ts | 首轮 57/58；修复后 58/58 |
| F17 | 扩展、桌面、API 包身份不一致。统一 0.1.8，并同步配置/测试/锁文件本包记录 | desktop-shell/、五个包 manifest、API config、installer lifecycle | Validate-Desktop-Identity PASS |
| F18 | 既有 Prettier 基线漂移导致 format 失败。按仓库配置整理，未关闭格式校验 | Web/Extension/Shared 的格式差异 | pnpm format PASS；无内容差异的换行不计源码修复 |
| F19 | 后端已有 myprogress_remap_executed 但已提交 OpenAPI 缺失。重新生成两份契约 | apps/api/openapi.json、packages/shared/src/generated/openapi.json | 生成与提交后 openapi:check |
| F20 | 嵌套工作树 Next 推断到原仓库根；静态 out 未被忽略。明确 Turbopack root，并忽略本工作树生成 out | apps/web/next.config.ts、.gitignore | 干净生成缓存回归、production build |

未盲目拆分整页、未改变业务数据权限或迁移格式。除 F11 的小 hook，其他 UI 模块结构保持渐进调整。没有性能对照数据，因此不声称提速。完整改动文件列表在 `MODIFIED_FILES.txt`；代码行为变化与格式整理应分开审阅。
