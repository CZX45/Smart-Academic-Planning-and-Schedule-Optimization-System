# Crystal / SAPSOS 当前唯一修复基线 — 2026-10-18

本报告取代旧报告中关于本轮工程状态的判断，不替代真实学校或安装态验收。目标为 Windows 单用户 LOCAL_DESKTOP；SQLite 资料留在本机。本轮不推进 SaaS。

| 对象 | 实际证据 |
|---|---|
| 隔离工作树 | `<SOURCE_WORKTREE>` |
| 本地分支 | `codex/comprehensive-repair-20261018` |
| 修复起点 | `066dd9c57294bec704df61ad2a5b1db3f5d03f08`，本地 release-convergence 历史分支；旧同名工作树目录不存在 |
| 原 <ORIGINAL_CHECKOUT> main | `bce82aea587017435b4ec7741d95e11bae138335`；两个已跟踪改动及原未跟踪文件保留 |
| 远端 main（本轮只读查询） | `8e055994e3e4435043c66e9362d9d0ede2365ec3` |
| PR #28 | `0fc2f0fbbae94d4439547a8d542d06e90e8956e3`，open/draft/unmerged；旧中文化分支，未整支合入 |
| PR #87 | `18515a26640309d3ff94ffedb31c5b554f6f5fa7`，open/draft/unmerged；已是本地修复起点祖先 |
| 历史差异 | origin/main 相对起点 1 个独有提交，起点 45 个独有提交；不以远端覆盖较新本地 |
| 起点版本漂移 | 扩展 0.1.7、桌面/API 0.1.6；身份校验确实失败 |
| 当前候选 | 0.1.8；版本与生成 OpenAPI 已收敛 |
| 正式安装 | 0.1.5；只读文件版本及 SHA 核对，无启动/覆盖/卸载 |
| 正式 SQLite | 只读 immutable + query_only 查询 schema 1；未读取学生业务行 |
| 候选 SQLite | schema 2；本次没有新增 schema 或迁移，也没有运行正式库迁移 |
| Catalog | 保留 `phase15b-main-world-checkpoint-v9`；`CATALOG_FULL_CAPTURE_UNLOCKED = false` |

最终提交与包来源记录见 [交接](NEXT_CLOUD_HANDOFF.md) 和 [发布门禁](RELEASE_READINESS.md)。源码起点与最终交付提交是不同身份。

本轮扫描 README、ROADMAP、ARCHITECTURE、DECISIONS、LOCAL_DESKTOP_EXECUTION_PLAN、CONTROLLED_STUDENT_BETA 系列、release-convergence 历史证据、七份 codebase 文档、相关源码和测试。已存在的 onboarding、持久化导入身份、reviewed rules/sections、备份恢复、诊断/preflight，以及 v9 MAIN-world ACK/checkpoint/分页修复均复用，没有重建。

当前完成 20 个修复/工程改进条目，见 [逐项清单](FIXES_AND_IMPROVEMENTS.md)。完整单元/集成 616 项、无头浏览器 58 项、Rust 25 项通过；数字不是业务完成率。真实学校和原生桌面验收仍未执行。真实学生前端的专业/课程/学期候选尚未接通审核数据，现已阻止误用 mock 候选；这项功能仍为 BLOCKED。

本轮所有新增学术样本均为 synthetic/mock；未导入新学校政策，未生成新的已审核 ProgramVersion。摘要语义筛选是防污染启发式（包括长度、导航词、GPA 可疑范围），不是任何学校的正式规则。特殊 GPA 标度、跨来源歧义及未审核政策必须继续人工审核。

更多证据：[功能矩阵](CAPABILITY_EVIDENCE_MATRIX.md)、[测试](TEST_EVIDENCE.md)、[真实验收待办](REAL_ACCEPTANCE_PENDING.md)。

最终包与保护证据：WINDOWS_PACKAGE_EVIDENCE.json、PACKAGE_EVIDENCE.json、PROTECTION_EVIDENCE.json。已生成未签名且未安装的 0.1.8 NSIS 候选，20 项修复的产品源码提交为 `7b0ea63e906409205f071b048fe29161f05f6e6a`。
