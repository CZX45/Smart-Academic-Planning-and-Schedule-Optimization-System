# Technology Stack

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary languages | Python, TypeScript/React, Rust, PowerShell | `apps/api/pyproject.toml`, `apps/web/package.json`, `desktop-shell/src-tauri/Cargo.toml`, `scripts/windows/` |
| Runtime + version | Python >=3.12; Node.js 24 in regular CI (22 in packaged E2E); Rust stable | `apps/api/pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/windows-packaged-desktop-e2e.yml` |
| Package manager | pnpm 10.28.1 and pip/setuptools; Cargo for Rust | `package.json`, `apps/api/pyproject.toml`, `desktop-shell/src-tauri/Cargo.toml` |
| Module/build system | pnpm workspace/Turborepo, setuptools, Cargo/Tauri 2, PyInstaller, NSIS | `pnpm-workspace.yaml`, `turbo.json`, `apps/api/pyproject.toml`, `scripts/windows/Build-Windows-Installer.ps1` |

### 2) Production Frameworks and Dependencies

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| FastAPI | >=0.125.0 | Typed local/server HTTP API | `apps/api/pyproject.toml` |
| SQLAlchemy | >=2.0.45 | PostgreSQL and SQLite persistence | `apps/api/pyproject.toml`, `apps/api/app/db/session.py` |
| Pydantic Settings | >=2.12.0 | Runtime configuration validation | `apps/api/pyproject.toml`, `apps/api/app/config.py` |
| Next.js / React | ^16.1.0 / ^19.2.3 | Student-facing static WebView UI and development web app | `apps/web/package.json` |
| Tauri | 2.x | Windows desktop shell and packaged lifecycle owner | `desktop-shell/src-tauri/Cargo.toml`, `desktop-shell/src-tauri/tauri.conf.json` |
| PostgreSQL / SQLite | PostgreSQL 16 in CI; Python SQLite locally | SERVER data store and LOCAL_DESKTOP embedded data store | `.github/workflows/ci.yml`, `apps/api/app/db/bootstrap.py` |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| pytest / Vitest / Playwright / Cargo test | Unit, integration, browser E2E, and Rust tests | `apps/api/pyproject.toml`, workspace package manifests, `playwright.config.ts` |
| Ruff / mypy | Python lint, format, and strict typing | `apps/api/pyproject.toml` |
| ESLint / Prettier / TypeScript | TypeScript lint, format, and strict type checking | package manifests and `eslint.config.*` / `tsconfig.json` files |
| PyInstaller 6.19.0 / Tauri CLI 2.11.4 | Windows FastAPI and NSIS packaging | `apps/api/packaging/requirements.txt`, Windows workflows |

Container development uses `python:3.12-slim` for the API, `node:24-alpine` for the web app, and `postgres:16-alpine` for the database. There is no single production container image for the Windows desktop path.

### 4) Key Commands

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm build
corepack pnpm test
corepack pnpm lint
corepack pnpm typecheck
cd apps/api && python -m pytest
pwsh -NoProfile -File scripts/windows/Build-Windows-Installer.ps1
```

### 5) Environment and Config

- Config sources: `.env.example`, `apps/api/app/config.py`, `desktop-shell/desktop-identity.json`, `desktop-shell/src-tauri/tauri.conf.json`.
- Required env vars: `PRODUCT_MODE`, `AUTH_MODE`, `ENVIRONMENT`, `DATABASE_URL`, `API_HOST`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL`.
- Runtime constraints: LOCAL_DESKTOP is loopback-only and SQLite-backed; SERVER is explicit, bearer-authenticated, and PostgreSQL-backed.
- Version pinning: Node/pnpm are exact in the root manifest/workflows; Python declares `>=3.12` and images/CI pin the 3.12 line, but no repository file pins an exact Python patch version (`[TODO]` if reproducible patch-level Python is required).

### 6) Evidence

- `package.json`
- `apps/api/pyproject.toml`
- `desktop-shell/src-tauri/Cargo.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/windows-packaged-desktop-e2e.yml`
- `infra/docker/api.Dockerfile`
- `infra/docker/web.Dockerfile`
- `docker-compose.yml`
