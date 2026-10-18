# CI 修复报告

## 原始故障

[原始 GitHub run 39101996989](https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/actions/runs/39101996989)：E2E 与 Docker Compose 成功，checks 在 `python -m mypy .` 失败：

```text
Error importing plugin "sqlalchemy.ext.mypy.plugin": No module named 'sqlalchemy.ext.mypy'
```

Runner 实际安装 SQLAlchemy 2.1.5、mypy 2.4.0、Python 3.12；原依赖下限未限制 SQLAlchemy 2.1，旧插件已不存在。源码已采用 `Mapped`、`mapped_column`、`DeclarativeBase`，不依赖旧式声明推断。

## 选择与验证

移除 SQLAlchemy 插件，保留 `strict = true`、Pydantic 插件与既有检查范围。单独在 2.1 下移除插件会暴露三个 Select 返回类型兼容错误；因此采用风险较小的 SQLAlchemy **2.0.51** 和原生类型方案，没有批量 ignore。mypy 固定 **2.4.0**，Ruff **0.14.8**，构建 setuptools **84.0.0**。负向 ORM 测试验证给 title 赋整数、UUID 字段赋字符串仍产生两个 assignment 错误。

`apps/api/requirements-ci.txt` 锁定运行时、开发与 PyInstaller 依赖，四个 CI 工作流、API Dockerfile、Windows runtime builder 共同使用。生成方式保存在锁文件首部，支持 Python 3.12/3.14 与平台 markers。更新依赖时必须重新生成、复跑矩阵、重新生成 OpenAPI。完整锁定不是软件供应链安全扫描。

已验证 Python 3.12.14 与 Python 3.14.8；mypy 配置目标语言仍为项目最低 3.12。新增 CI 双解释器矩阵。SQLite 全套 API tests 与 PostgreSQL 16 迁移/重复 seed/无漂移检查各自验证，不能把类型检查当数据库运行测试。

OpenAPI 的 Decimal 字段 schema 变更来自锁定的 Pydantic 2.14.1（移除旧正则描述），业务金额边界验证仍由现有 Pydantic/domain 测试覆盖。两份 OpenAPI 已同步生成。

Docker 受管网络使用可选 BuildKit CA secret，证书不写入镜像；Node 24 仅在提供该 secret 时启用环境代理。没有禁用 TLS 或改写代理凭证。Playwright 本地使用官方已安装 Chrome 155；CI 仍使用锁文件对应 Playwright 浏览器。受管网络拒绝下载 pinned Chromium 的结果保留为环境差异，不冒充本地 pinned-browser 测试。

最终门禁结果、提交与日志见 [TEST_MATRIX](TEST_MATRIX.md) 和 `evidence/delivery.json`。

## 修复后首轮 CI 的第二处故障

[run 39106070735](https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/actions/runs/39106070735) 的双 Python mypy、E2E 与 Docker 均 PASS；pytest 暴露既有 cleanup 测试依赖 checkout 不在 UserProfile 的假设。Ubuntu runner checkout 在 `/home/runner/work`，生产清理保护拒绝删除是正确行为。POSIX 测试改用系统临时目录，Windows 仍保留 checkout 临时目录以避免上一轮 system Temp 权限重试问题。保留全部原断言，另加主目录拒绝测试；生产清理脚本没有改动。

锁文件单独更新也会触发 Windows foundation/lifecycle 门禁（补齐 path filters）。
