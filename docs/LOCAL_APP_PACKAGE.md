# Local App Package

Phase 11C turns the repository into local runnable software for Windows. The
package remains a developer/local-user package, not a hosted production release
and not a browser-store extension release.

## Package Contents

- `docker-compose.yml` for PostgreSQL, FastAPI, and Next.js local services.
- `scripts/windows/Start-Smart-Academic-Planner.ps1` for one-command startup.
- `scripts/windows/Stop-Smart-Academic-Planner.ps1` for clean shutdown.
- `scripts/windows/Check-Prerequisites.ps1` for local checks.
- `scripts/windows/Build-Browser-Extension.ps1` for extension packaging.
- `scripts/windows/Open-Local-App.ps1` for opening the local web app.
- `scripts/package-extension.mjs` for creating `dist/extension-unpacked`.
- `scripts/smoke-test-local.mjs` for local runtime checks.
- `apps/web` for the local web app.
- `apps/api` for the local API, migrations, and seed workflow.
- `apps/extension` for the read-only import assistant.
- `docs/USER_SOFTWARE_MANUAL.md` for user instructions.
- `docs/KEAN_PORTAL_REAL_PAGE_QA.md` for real-page QA.

## Prerequisites

- Windows with PowerShell.
- Git.
- Node.js 24 or newer.
- Corepack and pnpm through Corepack.
- Python 3.12 or newer for backend checks outside Docker.
- Docker Desktop.
- Chrome or Edge.

Check prerequisites:

```powershell
.\scripts\windows\Check-Prerequisites.ps1
```

## One-Click Start

```powershell
.\scripts\windows\Start-Smart-Academic-Planner.ps1
```

The start script:

- locates the repository root relative to the script path;
- checks Git, Node.js, Corepack, pnpm, Python, Docker, Docker daemon, ports, and
  environment files;
- creates `.env` from `.env.example` when `.env` is missing;
- installs pnpm dependencies when `node_modules` is missing;
- starts PostgreSQL, API, and web app services with Docker Compose;
- relies on the API container command to run Alembic migrations before Uvicorn;
- runs development seed data in the API container;
- waits for web/API URLs before printing success.

The local package uses `PRODUCT_MODE=LOCAL_DESKTOP`, `AUTH_MODE=local`, and
`API_HOST=127.0.0.1` by default. Local desktop mode is loopback-only and does
not require a bearer token. Docker is a separate explicit `PRODUCT_MODE=SERVER`
runtime with `AUTH_MODE=bearer`; the container may bind `0.0.0.0`, but the host
port is published on `127.0.0.1` by default. Pairing and complete localhost
webpage protection are not implemented yet.

## Stop Command

```powershell
.\scripts\windows\Stop-Smart-Academic-Planner.ps1
```

The stop script runs `docker compose down` and preserves the PostgreSQL volume.
The destructive reset command remains manual:

```powershell
docker compose down -v
```

## Expected Local URLs

- Web app: <http://localhost:3000>
- API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- API health: <http://localhost:8000/health>
- API readiness/database check: <http://localhost:8000/ready>

## Database Notes

The local database is PostgreSQL 16 through Docker Compose. `.env.example`
contains local development defaults only:

- `POSTGRES_USER=sapsos`
- `POSTGRES_PASSWORD=sapsos_dev_password`
- `POSTGRES_DB=sapsos`
- `DATABASE_URL=postgresql+psycopg://sapsos:sapsos_dev_password@localhost:5432/sapsos`
- `PRODUCT_MODE=LOCAL_DESKTOP`
- `AUTH_MODE=local`
- `API_HOST=127.0.0.1`
- `API_PORT=8000`

The stable application contracts are `APP_ID=com.sapsos.smart-academic-planner`
and `APP_DATA_DIR_NAME=SAPSOS`. The future Windows data root is
`%LOCALAPPDATA%\\SAPSOS\\`; this phase defines and tests the contract but does
not create the directory.

These are not school credentials and are not production secrets. Docker Compose
uses the `postgres_data` volume so local data survives normal stops.

## Browser Extension Package Workflow

Build the extension package:

```powershell
corepack pnpm extension:package
```

Or use the Windows wrapper:

```powershell
.\scripts\windows\Build-Browser-Extension.ps1
```

Generated load-unpacked folder:

```text
dist/extension-unpacked
```

Manual loading:

1. Open Chrome or Edge.
2. Go to `chrome://extensions` or `edge://extensions`.
3. Enable Developer Mode.
4. Click Load unpacked.
5. Select the generated extension build folder.

The workflow does not publish to Chrome Web Store or Edge Add-ons.

## Kean Import Workflow

1. Start the local app.
2. Build/load the browser extension.
3. Open:

   ```text
   https://kean-ss.colleague.elluciancloud.com/Student
   ```

4. Log in manually.
5. Open supported academic pages manually.
6. Use the extension to preview visible academic-planning data.
7. Confirm staging import only after preview.
8. Review imported data in the local app.
9. Complete Phase 7B manual review before applying internal planning records.

## Smoke Test

After the stack is running and the extension package exists:

```powershell
corepack pnpm app:smoke
```

The smoke test checks:

- web app reachability;
- API health;
- API docs;
- API readiness/database connection;
- extension package output.

It does not require Kean portal access or portal credentials.

## Troubleshooting

- Docker Desktop is required for the full local stack. If the prerequisite
  checker reports Docker daemon failure, start Docker Desktop and rerun the
  start script.
- If startup fails on ports 3000, 8000, or 5432, stop the conflicting local
  service or run the stop script for an existing SAPSOS stack.
- If the API fails readiness, inspect `docker compose logs api` and
  `docker compose logs db`.
- If `corepack pnpm extension:package` fails, run
  `corepack pnpm --filter @sapsos/extension test` and inspect TypeScript
  errors.
- If a Kean page is unsupported, follow
  [Kean Portal Real-Page QA](KEAN_PORTAL_REAL_PAGE_QA.md) and update fake
  fixtures before changing selectors.

## Known Limitations

- Docker Desktop is required for the full local stack.
- Real Kean routes/selectors may require manual verification.
- Imported data is non-official.
- Phase 7B review remains required.
- The extension does not log in for the user.
- The extension does not collect credentials.
- The extension has no automatic registration, no portal submission, no
  waitlist automation, no seat reservation, and no seat grabbing.
- There is no browser-store publishing workflow.
