# 发布准备状态

**不满足正式发布条件。** 可以由本分支构建隔离候选用于下一阶段验收，但必须等待适用 CI，并核对源码 SHA/包 hash；不创建 Release、不合并、不安装到用户电脑。

产品版本仍为 0.1.8，本轮没有版本提升。上一轮 `7b0ea63...` 安装包是历史 artifact，不能证明本轮变更已打包；需重新运行 Windows 构建。安全同步基线 SHA 与历史产品 SHA 是不同证据链，不混用。

## 尚未关闭的门禁

- GitHub 全套适用 CI 结果见 TEST_MATRIX 与 delivery.json。
- 全部真实学校数据验收、原生 GUI、真实数据库升级仍待后续隔离任务。
- 完整 ProgramVersion/要求节点建模向导、未绑定替代专业 What-if 编辑仍未交付。
- 签名/SmartScreen、干净 Windows/WebView2、多 DPI/读屏没有新验收证据。
- 学校政策覆盖与可重复学分课程需人工确认；保守去重避免高估，但可能低估特殊学校政策允许的学分。

## 本轮手工安全复核

新候选接口只读，沿用既有 router 鉴权；新增反例证实无权限返回 404、不泄露学生存在性，合法授权为 200。查询要求学生自己的成功 application/review/import 链；Mock 档案返回空候选，真实机构/校园与来源边界保留。

前端仅保存学生 UUID 与 API 地址键，不保存学校凭证；来源证据按 React 文本渲染，未引入 HTML 注入。页面导航不写入，Review Apply 保持用户显式动作；迟到请求受 generation 隔离，计算按钮防重复提交。

规则 payload 不完整、源身份不一致或真实绑定/规则使用 Mock 来源时返回需审核，不将任意导入内容当已确认规则。新例外不会自动发布/注册/申请候补。Docker CA 只经 BuildKit secret 使用，未关闭证书验证或提交代理配置。未修改 extension 的学校请求实现、权限或 116 门禁。

检查范围为本分支相对指定基线的 diff、敏感字段与新增文件、授权/本地请求安全/配对/恢复测试。未发现新增敏感信息泄露；测试 token/数据库密码仅为既有合成 fixtures。正式 codex-security 工具在本会话不可调用，**未执行插件扫描，不将手工审查称为正式全库扫描**。依赖供应链全面审计与学校真实政策正确性不在该结论范围。

`MAIN_UNCHANGED=true`、`PROVIDER_ACTIONS_WRITTEN=0`、116 编译锁 false。Draft PR 保持 draft/unmerged。
