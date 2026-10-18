# 功能证据矩阵

PASS 仅对该列证据范围有效；UNVERIFIED 表示本轮未执行真实验收；BLOCKED 表示依赖缺口或授权边界；FAIL 是已观察失败，修复前记录保留在测试索引。

| 能力 | 代码 | 自动化 | 真实验收 | 限制/下一步 |
|---|---|---|---|---|
| MyProgress summary/rows/provenance/异常 | PASS（定向增强） | PASS：扩展/API/85 行合成 E2E | UNVERIFIED | 新页面结构、截断定位和特殊 GPA 标度仍须源复核 |
| Catalog/Sections 提取、分类与 review/apply | PASS（复用+回归） | PASS | UNVERIFIED | 不把自由文本升格官方规则 |
| v9 两学科串行、分页、ACK、checkpoint | PASS（既有代码） | PASS：controller/runner/lifecycle/DOM fixtures | UNVERIFIED：PENDING | 合成 worker restart 不等于真实浏览器 suspend |
| pause/resume/cancel、错误、重复、限流、保留成功结果 | PASS（既有代码） | PASS：现有扩展套件 | UNVERIFIED | 真页面/权限/浏览器重新加载待隔离会话 |
| 116 学科全量 | BLOCKED：编译门禁 false | PASS：保护仍在 | BLOCKED | 真实两学科 PASS 也不是自动解锁授权 |
| Course identity/state/零学分/缺成绩/重复 | PASS（定向增强） | PASS：domain + reviewed import | UNVERIFIED | 跨来源相似性不会自动成为等价课程 |
| Requirement/degree audit/reviewed ProgramVersion | PASS（既有引擎） | PASS：规则/缺失/冲突/审核测试 | UNVERIFIED | 没有已审核真实规则仍 UNKNOWN |
| Eligibility/Academic Planner/What-if 后端 | PASS（定向修复+复用） | PASS：合成 API/domain | UNVERIFIED | 不宣称全部学校政策已覆盖 |
| 实际 Sections/来源漂移/计划保存 | PASS（既有实现） | PASS：reviewed-section/持久化测试 | UNVERIFIED | 原生安装重启和真实来源时效未验收 |
| 线上定时/零学分/多 meeting 排课 | PASS（定向修复） | PASS | UNVERIFIED | TBA/未知继续警告，不伪造时间 |
| UI 学生与计算输入隔离 | PASS | PASS：headless E2E | UNVERIFIED | 原生 WebView/DPI 未测试 |
| 真实档案前端候选选择 | BLOCKED（未接通） | PASS：拒绝 mock 混入 | BLOCKED | 云端可补 typed reviewed candidate API/UI |
| 中文分组/错误指导/状态卡片 | UNVERIFIED：本轮仅定向修复 | PASS：已有 UI tests | UNVERIFIED | 本轮未重做共同根因分组、无屏幕阅读器验收 |
| 空库建档/身份/备份恢复/迁移回滚 | PASS（已有能力） | PASS：临时 SQLite/文件 | UNVERIFIED | 未接触正式 schema 1 库 |
| 诊断/startup preflight/清理保护 | PASS（既有能力+测试修复） | PASS：合成契约 | UNVERIFIED | 未启动现有 0.1.5 |
| 源码构建/扩展包一致性 | PASS | PASS | UNVERIFIED：扩展未加载 | 包校验不是浏览器加载证明 |
| Windows 新安装包 | 见 RELEASE_READINESS | 构建结果单列 | UNVERIFIED | 未执行安装/升级/卸载 |

未全面改造的体验项目没有计入本轮 20 项；任何未覆盖项目均不得用于发布批准。
