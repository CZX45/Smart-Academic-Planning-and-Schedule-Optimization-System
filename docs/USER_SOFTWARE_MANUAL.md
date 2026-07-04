# User Software Manual

## English

### What This Software Is

Smart Academic Planner is a local academic planning and schedule optimization
tool. It helps you review mock or imported academic-planning data, preview
degree progress, test advisory plans, compare section-level schedules, and
stage Kean Student Portal academic data for manual review.

The software is advisory. Imported data is non-official until you review it,
and high-impact academic decisions should be confirmed with the school or an
advisor.

### Prerequisites

- Windows with PowerShell.
- Git.
- Node.js 24 or newer.
- Corepack and pnpm through Corepack.
- Python 3.12 or newer for backend checks outside Docker.
- Docker Desktop for the full local stack.
- Chrome or Edge for the browser extension.

Run the prerequisite checker:

```powershell
.\scripts\windows\Check-Prerequisites.ps1
```

### Start The Software On Windows

From the repository root:

```powershell
.\scripts\windows\Start-Smart-Academic-Planner.ps1
```

The script checks prerequisites, creates `.env` from `.env.example` when safe,
installs pnpm dependencies if needed, starts PostgreSQL/API/web services with
Docker Compose, runs migrations through the API container startup command, runs
development seed data, and prints the confirmed URLs.

### Local URLs

- Web app: <http://localhost:3000>
- API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- API readiness: <http://localhost:8000/ready>

### Stop The Software

```powershell
.\scripts\windows\Stop-Smart-Academic-Planner.ps1
```

This stops Docker Compose services and preserves the local PostgreSQL data
volume. To intentionally delete the local database volume, run the destructive
Docker command documented by the stop script.

### Use The Dashboard

Open <http://localhost:3000>, or set `LOCAL_WEB_PORT` before startup when using
another supported local port such as `3001`, `3010`, or `3011`. The dashboard
shows the current local API status, the API base URL, the current web origin,
the active import source state, and workflow cards for degree audit, data
import review, browser-extension import, section monitoring, schedule
optimization, and what-if planning.

Use the in-page workflow links to jump to:

- Data Import Preview for staging uploaded or extension-provided data.
- Data Review for Phase 7B manual review before internal application.
- Degree Progress for mock degree audit.
- Long-Term Academic Planner for course-level advisory planning.
- Semester Schedule Builder for section-level schedule optimization.
- Section Monitoring for advisory comparisons of user-triggered snapshots.

### Import Data

Browser-extension imports go into staging first. They are non-official and
require Phase 7B review before use inside planning workflows.

For local MyProgress testing, use **Load sanitized MyProgress sample** in Data
Import Preview. The sample is sanitized, local-only, not official school data,
and is not mixed with real portal data. If a saved usable Kean MyProgress
import already exists in the local database, the dashboard loads the latest
usable preview before showing demo/mock data.

### Build And Load The Browser Extension

Build the extension:

```powershell
corepack pnpm extension:package
```

The generated load-unpacked folder is:

```text
dist/extension-unpacked
```

Load it manually:

1. Open Chrome or Edge.
2. Go to `chrome://extensions` or `edge://extensions`.
3. Enable Developer Mode.
4. Click Load unpacked.
5. Select the generated extension build folder.

### Kean Manual Login And Import

Open the official Kean Student Portal:

```text
https://kean-ss.colleague.elluciancloud.com/Student
```

Log in manually. The extension does not log in for you and does not collect
your password.

To run a Kean academic import:

1. Start the local app.
2. Build and load the extension.
3. Open the Kean Student Portal and log in manually.
4. Navigate manually to a supported academic page.
5. Open the extension.
6. Click `Start Kean Academic Import` for guided import, or `Extract current
page` for a single page.
7. Verify detected page type, diagnostic mode, warnings, and preview rows.
8. Click `Confirm staging import`.
9. Review the imported data in the local app's Data Import Preview and Data
   Review panels.

### Planning And Scheduling Features

Use the planning features after reviewing the data source:

- Degree Progress explains requirement status and warnings.
- Explore Programs compares what-if program scenarios.
- Long-Term Academic Planner creates advisory course-level plans.
- Semester Schedule Builder optimizes section-level schedules from mock or
  reviewed data.
- Section Monitoring compares user-triggered non-official snapshots.

The academic-plan optimizer remains separate from the section-level schedule
optimizer.

### Smoke Tests

After starting the app and packaging the extension, run:

```powershell
corepack pnpm app:smoke
```

The smoke test checks the web app, API health, API docs, database readiness,
and extension package output.

### Troubleshooting

- If Docker Desktop is not running, start Docker Desktop and rerun
  `.\scripts\windows\Start-Smart-Academic-Planner.ps1`.
- If port 3000, 8000, or 5432 is already in use, stop the conflicting service
  or stop the existing local stack.
- If the API is not ready, run `docker compose logs api`.
- If the database is not ready, run `docker compose logs db`.
- If the extension build folder is missing, run `corepack pnpm
extension:package`.
- If Kean selectors do not match a real page, follow
  [Kean Portal Real-Page QA](KEAN_PORTAL_REAL_PAGE_QA.md) and update fake
  fixtures first.

### Safety And Non-Automation

This software has no credential collection, no cookie or session-token storage,
no SAML/MFA/CAPTCHA bypass, no portal form submission, no automatic
registration, no add/drop/swap automation, no waitlist automation, no
background polling, no seat reservation, no seat grabbing, no browser-store
publishing, and no hidden automation.

## 中文

### 这个软件是什么

Smart Academic Planner 是一个可以在本机运行的学业规划和课表优化工具。它可以帮助你查看
模拟或导入的学业规划数据，预览学位进度，生成建议性的长期选课计划，比较具体课程 section
的课表组合，并把 Kean Student Portal 中你手动打开的学业相关页面数据导入到本地待审核区。

这个软件只提供建议。导入的数据是 non-official，必须经过 Phase 7B manual review。重要学业
决定仍然需要向学校或 advisor 确认。

### 需要先安装什么

- Windows 和 PowerShell。
- Git。
- Node.js 24 或更新版本。
- Corepack，以及通过 Corepack 使用 pnpm。
- Python 3.12 或更新版本，用于 Docker 外的后端检查。
- Docker Desktop，用于完整本地运行。
- Chrome 或 Edge，用于加载浏览器扩展。

检查环境：

```powershell
.\scripts\windows\Check-Prerequisites.ps1
```

### 在 Windows 上启动软件

在项目根目录运行：

```powershell
.\scripts\windows\Start-Smart-Academic-Planner.ps1
```

脚本会检查环境，必要时从 `.env.example` 创建 `.env`，安装 pnpm 依赖，使用 Docker Compose
启动 PostgreSQL、API 和 web app，运行迁移和开发 seed，并打印本地访问地址。

### 打开哪个网址

- Web app: <http://localhost:3000> by default; set `LOCAL_WEB_PORT` to use
  `3001`, `3010`, or `3011`.
- API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- API readiness: <http://localhost:8000/ready>

### 如何停止

```powershell
.\scripts\windows\Stop-Smart-Academic-Planner.ps1
```

默认只停止服务，不删除本地 PostgreSQL 数据卷。只有在你明确想清空本地数据库时，才运行 stop
脚本中说明的 destructive reset 命令。

### 如何使用 dashboard

打开 <http://localhost:3000>。如果需要其他本地端口，可以在启动前设置
`LOCAL_WEB_PORT` 为 `3001`、`3010` 或 `3011`。页面会显示本地 API 状态、API base
URL、当前 web origin、当前 import source 状态，以及 degree audit、data import review、browser
extension import、section monitoring、schedule optimization、what-if planning 等工作流入口。

### 如何导入 Kean 数据

先构建扩展：

```powershell
corepack pnpm extension:package
```

生成的扩展目录是：

```text
dist/extension-unpacked
```

加载方法：

1. 打开 Chrome 或 Edge。
2. 进入 `chrome://extensions` 或 `edge://extensions`。
3. 打开 Developer Mode。
4. 点击 Load unpacked。
5. 选择生成的扩展目录。

然后打开：

```text
https://kean-ss.colleague.elluciancloud.com/Student
```

你需要自己手动登录。扩展不会替你登录，也不会收集密码。

导入步骤：

1. 启动本地 app。
2. 构建并加载扩展。
3. 手动登录 Kean Student Portal。
4. 手动打开支持的学业页面。
5. 打开扩展。
6. 点击 `Start Kean Academic Import` 或 `Extract current page`。
7. 检查 detected page type、diagnostic mode、warnings 和 preview。
8. 点击 `Confirm staging import`。
9. 回到本地 app，在 Data Import Preview 和 Data Review 中审核导入结果。

### 如何使用规划和排课功能

- Degree Progress 查看学位要求进度。
- Explore Programs 做 what-if program 比较。
- Long-Term Academic Planner 生成建议性的长期 course-level 计划。
- Semester Schedule Builder 做 section-level 课表优化。
- Section Monitoring 比较你手动触发的非官方 section snapshot。

### 运行 smoke test

启动 app 并打包扩展后运行：

```powershell
corepack pnpm app:smoke
```

### 安全边界

本软件 no credential collection、no cookie/session-token storage、no SAML/MFA/CAPTCHA
bypass、no portal form submission、no automatic registration、no add/drop/swap automation、
no waitlist automation、no background polling、no seat reservation、no seat grabbing、no
browser-store publishing、no hidden automation。
