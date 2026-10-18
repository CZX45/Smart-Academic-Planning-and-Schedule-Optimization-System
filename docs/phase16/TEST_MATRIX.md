# 测试矩阵

最终状态与日志索引持续更新至交付提交。环境：Linux x86_64；Python 3.12.14 / 3.14.8；Node 24；pnpm 10.28.1；PostgreSQL 16；PowerShell 7.5.4（仅便携测试工具）；Chrome 155。所有数据库与测试档案为临时合成数据。

| 门禁 / 命令 | 数量 | 状态 | 证据/说明 |
|---|---:|---|---|
| `pnpm test`（含 pytest / Vitest / Node） | 626 PASS / 15 SKIP | PASS | unit-final.log；API Windows 专属项单列跳过 |
| `pnpm e2e` | 62 | PASS | e2e-final.log；58 既有 + 4 新增 |
| `pnpm lint` | 全包 | PASS | lint-final.log（含 Ruff、ESLint） |
| `pnpm typecheck` | 全包 | PASS | typecheck-final.log（含 strict mypy、TypeScript） |
| Python 3.14 `python -m mypy .` | 164 文件 | PASS | mypy314-final.log |
| `pnpm format` | 全包 | PASS | format-check-final.log（Ruff/Prettier） |
| `pnpm build` | 全包 | PASS | build-final.log |
| `pnpm openapi:check` | 两份契约 | PASS | openapi-check.log；生成后无漂移 |
| `alembic upgrade head` + seed 两次 + `alembic check` | PostgreSQL 16 | PASS | 独立合成数据库，当前迁移 20260824_0021 |
| Docker Compose build/up/health/ready/web/seed×2 | 3 容器 | PASS | 独立 project phase16-ci；mock-institution 计数为 1 |
| Windows installer foundation / lifecycle / packaged E2E | GitHub Windows runners | PASS | ea32a38；三个工作流均成功，见 ci-final.json |
| Rust desktop tests | 25 | PASS on Windows CI / NOT_RUN locally | ea32a38 foundation；实际执行名称见 rust-test-names.log |
| 原生 Windows GUI / 真库升级 / 学校真实数据 | 不计入自动化数量 | NOT_RUN | 见本地交接；不以 Ubuntu PASS 替代 |
| 手工安全差异审查与安全 API 回归 | 变更范围 | PASS | RELEASE_READINESS；正式插件不可调用 |

## 新增测试名称

Python：`test_candidates_require_apply_and_remain_student_scoped`；`test_mock_profile_and_mock_program_never_become_real_candidates`；`test_reviewed_sections_supply_real_terms_and_cancelled_sections_are_explained`；`test_program_requires_exact_active_reviewed_rules`；`test_rule_payload_catalog_tampering_is_not_active`；`test_real_audit_without_complete_history_or_reviewed_rules_requires_review`；`test_reviewed_course_reference_normalizes_asterisk`；`test_repeated_attempts_cannot_satisfy_two_exclusive_requirements`；`test_equivalent_courses_share_one_credit_identity`；`test_credit_group_cannot_count_a_course_reserved_by_another_requirement`；`test_invalid_rule_payload_requires_review_instead_of_crashing`；`test_real_planner_does_not_treat_mock_sections_as_offering_evidence`；`test_real_review_apply_candidates_and_audit_round_trip`；`test_native_orm_typing_rejects_invalid_column_values`；`test_academic_workflow_candidates_obey_student_authorization`。

Web 单元：student-selection 中的持久化/API 地址隔离和不可用 storage 两项。

E2E：`snapshot visibility cache is per capture and never exposes blocked content`；`real workflow submits scoped reviewed identities and never writes on navigation`；`real profile selection survives reload and clears the previous course`；`apply invalidates real candidates and ignores a stale response`。

原 699 = 616 单元/集成 + 58 E2E + 25 Rust。新增 23 API + 2 Web + 4 E2E = 29，测试库存 728；不能把库存或重复运行算成实际通过。Linux 的 Windows 平台 skip 与 Rust 未运行必须单独列出。

## 失败与修复记录

- 初次 API 回归两项缺 PowerShell 工具，便携 PowerShell 安装后通过；默认受管网络阻断 TestClient 所需本地 socket，授权网络环境重跑。
- 新 E2E 首轮缺 profile 契约字段，及标签定位不准确、StrictMode 重复 GET 假设；修复夹具/定位/竞态测试后 61/61。两项旧 UI 测试改为检查替代后的真实按钮，并增加无 Mock 断言，没有删除测试或关闭检查。
- 新授权测试实际遵循已有隐藏资源存在性的 404，已明确断言 `not_found` 与允许访问的 200；未放宽鉴权。
- Docker 初次 Corepack 未使用代理；仅在可选 CA secret 存在时采用环境代理，保留 TLS 后通过。
- 格式门禁初次发现新增代码未格式化，已使用包内 Prettier 修正。

本地实际合计 **688 PASS、15 Windows 平台 SKIP、25 Rust NOT_RUN locally / PASS in Windows CI**；不重复累计定向或重跑测试。API 360 PASS / 15 SKIP（375），扩展 173、Shared 66、Web 25、Node 2，E2E 62。日志文件与 SHA-256 见 `evidence/log-index.json`。

15 项跳过原因见 `evidence/pytest-earlier-skip-reasons.log`（较早执行的原始原因；最终相同 15 项跳过见 unit-final.log），包括 Windows junction、Windows PowerShell/VC runtime、进程检查和安装 payload；没有删除或新增 skip。完整 pytest nodeid 库存见 `evidence/pytest-inventory.log`。

补充测试：`test_planner_consumes_reviewed_options_and_preserves_zero_credit_override`、`test_safe_build_cleanup_keeps_user_profile_protected`。GitHub 首轮 cleanup 失败原因与修复见 CI_REPAIR_REPORT；未放宽生产删除保护。

新增 schema 验证器 6 项：当前唯一标记通过；旧版、未来版、错名、重复标记拒绝；缺文件不创建数据库。所有现有文件验证前后 SHA-256 不变。详见 `test_packaged_schema_verifier.py` 与 packaged-schema.log。

本地 Chrome 155 曾连续三次暴露 table-heavy DOM 的摘要为空（60/61），单 worker 仍可复现。直接探针确认重复的祖先可见性计算耗时 1,068 ms，触发原有 1,000 ms 预算；增加单次同步采集缓存后为 139 ms，返回 5,282 字符且 bounded=false。原断言、预算和节点/文本上限未修改。新增测试核实隐藏/表单内容排除以及下一次采集重新读取可见性；最终完整回归与失败样本分别归档。此耗时为单个合成夹具的观测，不是通用性能承诺。

另一次 61/62 失败来自测试夹具把超时通知与搜索点击写入同一变量。现独立记录事件，保留原提交结果断言，并新增 PREPARATION_VERIFIED → 唯一 SEARCH_SUBMITTED 顺序断言，以及超时后点击证据仍保留的验证；未改生产搜索流程或放宽超时。见 e2e-checkpoint-fixture-failure.log 与 checkpoint-focused.log。

完整名称索引：Python 375 项见 pytest-inventory.log；TypeScript 264 项见 typescript-test-names.json；Node 2 项见 unit-final.log；E2E 62 项见 e2e-final.log；Rust 25 项见 rust-test-names.log。名称索引由 collect/list 或实际执行日志生成，不作为重复测试通过次数。Windows foundation 另执行 preflight 3、runtime payload 9、VC runtime 7 项，均与既有库存重叠，不累加为新增测试。

最终代码提交 `ea32a382c6ad1bf328e670f555fb1d97ad839935` 的四个 GitHub 工作流、八个 job 全部 PASS，完整步骤快照见 evidence/ci-final.json。后续文档提交的 CI 以 Draft PR 最终 HEAD 检查为准，不能以较早失败运行或重复次数替代当前结果。
