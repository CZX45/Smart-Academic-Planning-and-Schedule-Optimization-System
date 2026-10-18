# Phase 16 云端交付报告

状态：CLOUD_DEVELOPMENT_COMPLETE（本轮面向已审核数据的云端开发门禁通过；不代表全部产品能力或真实学校、用户电脑验收完成）。

## 基线与提交

- 起点：`comprehensive-repair-20261018-safe-sync`，`4e037fe2ea436bb94bbd53b162dc58d27a8f85a7`。
- 开发分支：`codex-phase16-academic-workflow-stabilization-20261018`。
- 远端已有 `codex` 分支，斜杠分支名触发 Git directory/file conflict；保留该分支，使用连字符开发分支名。
- 产品身份仍为 SAPSOS Local Desktop **0.1.8**；本轮代码已在 Windows CI 重建并验证候选安装包，尚未签名或发布。
- 最终代码提交：`0547e861ea81cf004ca9c4bc1a050674f8007879`；四个工作流、八个 job 全部 PASS。后续交付提交仅更新本目录的文档与证据；其 HEAD/CI 由 Draft PR 检查页及最终回复记录。最终代码提交和文档提交以本目录 `evidence/delivery.json` 及 Draft PR 的提交链为准。文档不自引用其自身尚未生成的 Git SHA。
- 初始工作区是旧 main（0.1.5）；已明确识别差异，随后从指定安全提交创建分支。安全同步历史是独立根，不能与旧 main 直接比较，因此 Draft PR 目标为上述安全同步分支。
- main 保护值：`8e055994e3e4435043c66e9362d9d0ede2365ec3`；没有向 main 推送、合并、强推或删除分支。

## 实际修复

| ID | 根因与结果 | 可复现证据 |
|---|---|---|
| P16-01 | SQLAlchemy 2.1 删除旧 mypy 插件；改原生 ORM 类型并锁定已验证的 2.0.51，保留 strict 和 Pydantic 插件 | 双 Python mypy；错误 ORM 赋值必须报错 |
| P16-02 | CI/打包运行时依赖可随上游漂移；统一跨平台 constraints 与 Python 3.12/3.14 CI 矩阵 | requirements-ci.txt、四个工作流、Docker 和 Windows 打包 |
| P16-03 | 真实档案前端缺少候选；新增学生作用域只读 API，课程来自成功审核应用，专业来自精确有效规则，学期来自修读/课节证据 | test_phase16_workflow.py |
| P16-04 | 档案选择刷新丢失；普通浏览器按 API 地址保存已验证学生 ID；切换和 Apply 后重置分析状态 | student-selection tests、真实工作流 E2E |
| P16-05 | 真实工作流未接通；独立组件连接审核、资格、规划、What-if、真实课节优化与保存读回 | 63 项浏览器回归、已有 API/domain 套件 |
| P16-06 | 无快照真实档案可能读到 Mock 修读/转学/豁免/替代；真实档案统一排除这些记录 | 零 Mock 学分回归 |
| P16-07 | 规则元数据与 payload 可不一致或损坏；精确校验机构/专业/年份、确认状态，异常返回需要审核 | 篡改/损坏 payload 测试 |
| P16-08 | 缺规则、映射异常或不完整历史仍可能确定满足；真实审核 fail-closed，规划不消费需审核要求 | 真实正向闭环和冲突反例 |
| P16-09 | 重修/等价/替代的不同记录可重复花费学分；统一课程学分身份，排他要求组尊重分配器 | 重复、等价、跨组回归 |
| P16-10 | Reviewed rules 课程分隔符不能复用已有规范化；支持星号等明确代码格式 | FIN*300 / source-id 映射测试 |
| P16-11 | Planner 零学分 override 被默认值覆盖，真实学期/开课证据混用 Mock | 显式 None、来源过滤及既有边界测试 |
| P16-12 | 界面缺来源、方案比较和数据失效反馈；增加来源/学分口径、比较表、根因分组、历史审核提示 | 类型契约和浏览器回归 |
| P16-13 | Planner 曾在审核后重读旧课程池；现复用审核上下文与学分身份，不重新引入被排除课程 | reviewed planner 反例与零学分 advisory 回归 |
| P16-14 | GitHub Linux checkout 位于受保护主目录导致 cleanup 测试失败；仅调整 POSIX 测试目录并增加主目录拒绝断言 | 生产清理脚本未修改；Windows checkout 测试策略保留 |
| P16-15 | 真实 API 可解析 Mock 专业绑定/规则；统一 resolver 校验学生绑定来源、机构校园、规则来源类别，审核和资格共同使用 | 真实审核闭环、Mock 规则及绑定拒绝反例 |
| P16-16 | Windows 安装态 E2E 仍只接受 schema 1、构建硬编码 0.1.6；改读取产品 schema 常量和当前桌面身份，保持严格只读校验 | schema 2 正向、旧版/未来/重复/错名/缺文件拒绝测试 |
| P16-17 | 大型 DOM 重复检查祖先可见性耗尽采集预算；缓存仅限单次同步采集，保留隐藏/表单内容过滤 | 原大型夹具及跨采集可见性/隐私回归 |
| P16-18 | 桌面 API 每次启动动态分配端口，按完整地址保存的档案偏好无法跨重启恢复；桌面 loopback 偏好使用稳定范围，并验证返回档案名单，浏览器/远程 API 继续按完整地址隔离 | 双档案更换端口恢复、缺失档案拒绝、导航零写入回归 |

修改文件完整清单见 `evidence/modified-files.txt`；主要改动集中于 academic-workflow API/组件、reviewed rules、audit/planner、CI 依赖与 Windows 验证脚本。

上一轮 F01–F20 保留；扩展提取器仅增加单次同步采集内的祖先可见性缓存，采集预算、阻止元素规则、116 门禁和学校访问逻辑保持原约束。没有数据库 schema 变更，不需要新增迁移。

## 未完成与风险

- 普通用户尚无完整的 ProgramVersion/持久化 requirement-node 创建向导；当前选择器消费已存在并审核的记录。缺这些记录时明确阻断。Reviewed rules 的节点映射仍依赖既有持久化节点，不能把任意新学校规则自动变成完整培养方案。
- What-if 当前只使用学生已审核绑定方案，尚未提供未绑定替代专业的适用性审核与组合编辑器；保留原始主修/辅修关系。
- 真实课程来源/规则覆盖、学校重修政策、可重复获学分课程和复杂跨组规则需要学校确认；本轮去重采用保守的一身份一次计入，不宣称覆盖所有学校政策。
- 新组件的错误提示、核心操作为中文；已有后端解释仍有英文，未做全应用中文化重写。原生读屏、多 DPI、窄窗口视觉验收未运行。
- 正式安全插件工具在本会话不可调用，已完成手工变更审查与安全回归；不冒充插件扫描通过。
- Windows runner 门禁与真实 Windows GUI/真实数据库升级是不同证据。详见 TEST_MATRIX 与 LOCAL_ACCEPTANCE_HANDOFF。

## 交付与边界

测试结果见 [TEST_MATRIX](TEST_MATRIX.md)，学业能力见 [ACADEMIC_WORKFLOW_REPORT](ACADEMIC_WORKFLOW_REPORT.md)，安全复核见 [RELEASE_READINESS](RELEASE_READINESS.md)。所有新数据均为脱敏合成夹具；没有访问学生门户、真实 SQLite、学校凭证或用户安装目录。学校写入动作数 **0**，116 学科继续锁定。
