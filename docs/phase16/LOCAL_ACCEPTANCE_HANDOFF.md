# 下一阶段本地隔离验收

本轮未安装、覆盖或启动用户电脑上的软件，也未访问真实 SQLite。以下是后续独立本地任务的操作流程，不是已执行记录。

1. **隔离候选安装**：取本 Draft PR 最终源码对应 CI artifact；核对 manifest 的 `provenance.source_head_sha`、0.1.8 身份、包 SHA-256。`workflow_sha` / `build_commit` 可能是 GitHub 的 PR merge-ref SHA，不等于开发分支 SHA，也不表示已经合并 main。历史 0.1.8 安装包不含本轮改动，必须重建。使用独立 Windows VM/测试账户和新数据目录，不覆盖现有安装或正式数据库。没有匹配 artifact 时停止安装步骤并重建。
2. **原生 GUI**：核对启动、WebView2、本地 API 健康、键盘焦点/Tab、125%/150%/200% 缩放与窄窗口；记录截图时脱敏。浏览器 headless 成功不替代此项。
3. **学生建档**：从空合成库验证创建/切换/重启/删除隔离；随后只在明确授权的本地数据目录创建真实档案，确认非 Demo；无来源时应显示缺失说明。
4. **扩展配对**：核对安装版 manifest 0.1.8 和 revision v9；人工发起本地配对，检查来源域/本地地址及重启恢复。不导出 Cookie、Session、学校 Token、MFA 或密码。
5. **真实两学科受控验收**：学生自行登录且主动打开授权 Catalog 页面，仅人工启动两个已授权学科；核对页码、课程数、重复、限流、暂停/恢复/取消、popup 关闭与真实 worker 重启。保留成功结果与 checkpoint 对齐证据。不得自动登录、注册、退课、候补或高频轮询。
6. **MyProgress**：逐字段核对专业、学位、Catalog 年份、GPA、学分与课程行；审核来源位置、截断、重复/替代建议。先 Review 再显式 Apply，核对完成/在修/计划/未开始与异常；不得以网页结构校验代替事实确认。
7. **Catalog / Sections**：核对机构/校园、MATH*1044 等规范化、课程版本/标题、学期、CRN/非 CRN 身份、多 meeting、地点、线上/TBA、取消/变更。重复应用不新增重复课程/班次，不覆盖已确认历史；冲突应阻断并说明。
8. **真实审核与规划**：先补齐真实 ProgramVersion、持久化要求节点、学校规则来源与适用性审核。缺记录时保留阻断，不改标签伪造通过。核对每条要求的身份、来源、年份、匹配课程、应用学分、原因、状态；比较完成/在修/计划口径，复核最低成绩、重复、转学、替代与多要求组。检查资格的目标学期、长期计划先修顺序和开课待核实提示。
9. **真实排课**：选定真实学期和已应用课程，使用 REVIEWED_IMPORTED；核对班次/每条 meeting/冲突/偏好、来源版本/读取时间、取消/缺失/TBA 的解释。同输入重复运行排名应一致。座位仅来源读取参考，所有注册在学校门户手工进行。
10. **保存、重启、恢复**：保存两个计划、What-if 和课表，关闭重启读回；切换档案无交叉污染；Apply 后候选与分析自动失效；用隔离合成库执行备份/恢复/升级失败回滚。真实数据库升级单独授权和验证，不复制正式库到 GitHub。
11. **保持 116 锁定**：`CATALOG_FULL_CAPTURE_UNLOCKED = false`。真实两学科通过也不会自动解锁；本任务不修改该门禁。

每项记录 PASS / FAIL / BLOCKED / NOT_RUN、源码 SHA、artifact hash、环境、时间、脱敏证据与失败原因。真实验收门禁清单：REAL_2_SUBJECT_ACCEPTANCE、FULL_116_SUBJECT_BATCH、REAL_MYPROGRESS_ACCEPTANCE、REAL_CATALOG_ACCEPTANCE、REAL_SECTIONS_ACCEPTANCE、REAL_DEGREE_AUDIT、REAL_ELIGIBILITY、REAL_PLANNER、REAL_SCHEDULE_OPTIMIZER、WINDOWS_NATIVE_INSTALLATION、WINDOWS_NATIVE_GUI、REAL_DATABASE_UPGRADE。本轮这些均不是 PASS。
