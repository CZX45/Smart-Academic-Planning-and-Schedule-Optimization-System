# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type (API/DB/Queue/etc) | Purpose | Auth model | Criticality | Evidence |
|--------|---------------------------|---------|------------|-------------|----------|
| Local FastAPI | Loopback HTTP | Web, extension and Tauri local application boundary | Local origin/pairing credential in LOCAL_DESKTOP | high | `apps/api/app/main.py`, `apps/api/app/security/local_request.py` |
| PostgreSQL | Database | SERVER and CI persistence | Database URL; SERVER bearer boundary | high | `docker-compose.yml`, `.github/workflows/ci.yml` |
| SQLite | Embedded database | LOCAL_DESKTOP per-user persistence | Local filesystem/process boundary | high | `apps/api/app/db/bootstrap.py` |
| Kean Student Portal | User-opened webpage | Optional visible-page academic capture | User manually authenticates; extension receives no credential | high | `apps/extension/manifest.json`, `apps/extension/src/shared/kean.ts` |
| WebView2 | Desktop runtime | Render packaged static Next.js UI | OS/Tauri local application | high | `desktop-shell/src-tauri/tauri.conf.json` |

No message queue, external telemetry, analytics, automatic crash upload, or cloud database integration is present in the current product path.

No API gateway or service mesh sits between the desktop/web clients and FastAPI. Browser `fetch` calls target the configured local/API base URL; the extension's only institution-specific remote access is the already-open Kean portal page rather than a credentialed backend API call.

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| PostgreSQL | SERVER canonical relational store | SQLAlchemy + Alembic | Migration and authorization correctness | `apps/api/alembic/`, `apps/api/app/db/session.py` |
| SQLite `%LOCALAPPDATA%/SAPSOS/sapsos.db` | LOCAL_DESKTOP student data | SQLAlchemy + local bootstrap/migrations | Upgrade, backup/restore, and atomicity | `apps/api/app/db/`, `desktop-shell/data-retention-contract.json` |
| Browser extension storage | Local pairing/config state | Chrome MV3 storage | Credential-like local pairing data must not become portal auth | `apps/extension/manifest.json`, pairing modules |

### 3) Secrets and Credentials Handling

- Credential sources: `.env` for development/server configuration; browser pairing uses a local credential distinct from portal auth.
- Hardcoding checks: `.env` is ignored; `.env.example` contains development-only values; security tests prohibit school credentials and broad extension behavior.
- Rotation/lifecycle: local pairing session/revoke endpoints exist; production institutional credential lifecycle is not implemented because the app does not collect portal credentials.

### 4) Reliability and Failure Behavior

- Packaged startup, readiness, shutdown and UI operations use bounded waits and explicit failure evidence.
- Shared API helpers and UI workflows use bounded request timeouts.
- There is no circuit breaker; local failure surfaces as typed offline/failed/schema-error states.

### 5) Observability for Integrations

- Local diagnostics are read-only, allowlisted, sanitized, and manually exported.
- Runtime manifests and process-identity evidence support packaged troubleshooting.
- Gap: no external monitoring/metrics service by design; participant evidence is manual and sanitized.

### 6) Evidence

- `.env.example`
- `apps/api/app/security/local_request.py`
- `apps/api/app/services/diagnostics/`
- `apps/extension/manifest.json`
- `docs/SECURITY_AND_PRIVACY.md`
