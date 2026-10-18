# 待隔离真实验收

本轮按用户要求只后台执行，没有打开真实学校页面、读取 Cookie/口令/令牌、接管鼠标键盘、切换窗口、安装或启动桌面候选。以下全部不是 PASS。用户现在无需采取动作；只有未来启动真实验收时才需要明确会话/机器授权。

1. **真实两学科：PENDING / UNVERIFIED。** 在授权用户已登录且主动打开的 Catalog 页面，先核对实际加载扩展的 manifest、worker、v9 revision 与候选哈希；人工启动两个已授权学科。记录页码、唯一课程数、每页来源、重复冲突、错误/限流、暂停/恢复/取消、popup 关闭、标签切换与真实 worker suspend/restart。必须证明已完成结果保留并与 checkpoint 对齐。不得自动登录或提交学校写入动作。
2. **116 学科：BLOCKED。** 编译常量仍 false；需真实两学科明确 PASS、原授权条件满足和单独解锁决定，绝不因合成测试自动开放。
3. **MyProgress / Degree Audit：UNVERIFIED。** 人工逐字段核对专业、degree、major、catalogYear、GPA、学分及课程行；保留来源位置和审核决定。检查 Notes/导航/公告/页脚、截断、重复与替换建议。结构通过不等于字段核实；摘要不自动创建官方 ProgramVersion。
4. **Catalog / Sections：UNVERIFIED。** 人工核对课程身份、学期/校园/班次、多 meeting、TBA/混合授课、来源日期/审核/apply；变更、过期、删除保持解释与阻断，不回退 mock。
5. **真实学业规划：BLOCKED/UNVERIFIED。** 先补接真实审核候选选择，再由学生/学校或顾问确认 ProgramVersion、规则、转学/替换关系与 GPA 标度；验证可行和不可行原因、重启读回、档案隔离。不能以当前 mock 方案当真实建议。
6. **Windows 安装态：UNVERIFIED。** 在隔离测试账户/虚拟机核对候选来源 SHA/版本/包 hash，执行空库建档、review/apply、关闭重启、配对发现、备份恢复、schema 1→2 升级与失败回滚、数据保留卸载契约。使用新建合成库，绝不复制/使用当前正式库或覆盖 0.1.5。签名/SmartScreen、干净 Windows、WebView2、不同用户均单独记录。
7. **原生 UX：UNVERIFIED。** 在上述隔离环境检查键盘焦点、读屏、窄窗口、多 DPI/缩放和导入窗口。headless DOM 检查不等于 Windows 桌面视觉验收。

资料：现有 `docs/CONTROLLED_STUDENT_BETA_PLAN.md`、`docs/LOCAL_DESKTOP_EXECUTION_PLAN.md` 与 Windows 验收脚本。仅在相应边界获得授权后执行；本轮不创建新批准流程或替用户确认事实。
