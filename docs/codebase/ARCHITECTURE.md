# Architecture

## Core Sections (Required)

### 1) Architectural Style

- Primary style: local-first modular monorepo with a layered FastAPI backend, feature-oriented UI, and a supervised Tauri shell.
- Classification basis: routes delegate to typed service modules and persistence models; the UI uses shared typed clients; the desktop shell owns packaged runtime startup and shutdown.
- Primary constraints: deterministic/explainable academic outputs, explicit source provenance, and no school-record mutation or credential capture.

### 2) System Flow

```text
user-opened source or fixture -> staging import -> explicit review/apply -> source-tagged local state
-> audit/eligibility/planner/section optimizer -> persisted explainable snapshot -> UI
```

1. The extension or Web UI sends an explicitly confirmed local import through shared API helpers.
2. FastAPI validates and stores staging records, mapping candidates, provenance, and warnings.
3. Explicit review/apply materializes supported non-official course or section state.
4. Domain services calculate deterministic audit, eligibility, planning, or schedule snapshots.
5. The Web UI renders results, assumptions, warnings, source labels, and manual next actions.
6. In LOCAL_DESKTOP, Tauri supervises the packaged API and SQLite lifecycle.

Initialization is explicit: the FastAPI lifespan initializes the selected database before serving; packaged startup acquires a single-owner lock, resolves resources and database state, applies approved restore/migration handling, starts the API, validates runtime identity/readiness, and only then exposes the desktop UI. FastAPI `Depends(...)` provides request-scoped sessions/security context; there is no general dependency-injection container.

No queue, background worker service, or event bus exists. Section-monitoring behavior is request-driven and persisted rather than owned by a continuously polling daemon.

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| Tauri shell | Local process identity, preflight/migration, runtime bridge, shutdown | Academic semantics | `desktop-shell/src-tauri/src/main.rs` |
| FastAPI/API | Validation, auth/local request boundary, HTTP schemas | UI-only state | `apps/api/app/main.py`, `apps/api/app/api/` |
| Domain services | Audit, allocation, rules, planning, optimizer, import/review behavior | Portal actions | `apps/api/app/services/` |
| Persistence | PostgreSQL/SQLite sessions, models, Alembic and local migrations | Frontend behavior | `apps/api/app/db/`, `apps/api/alembic/` |
| Web/extension | User review, explicit actions, visible-page capture | Rule-engine decisions | `apps/web/src/`, `apps/extension/src/` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| Persisted snapshot | audit, scenarios, planner, optimizer, monitoring | Repeatable results and traceability |
| Expression/rule tree | degree requirements and eligibility | Composable, explainable policy evaluation |
| Staging-review-apply | MyProgress, catalog/rules, sections | Fail-closed data quality and provenance |
| Dual runtime adapter | config/database/startup | Keep LOCAL_DESKTOP isolated from SERVER auth/data behavior |
| Fail-closed identity check | Tauri process and installer scripts | Avoid trusting unrelated processes or artifacts |

### 5) Known Architectural Risks

- `apps/web/src/app/page.tsx` and `apps/api/app/api/v1/academic.py` are very large, high-churn integration surfaces; small state changes can affect multiple workflows.
- LOCAL_DESKTOP schema bootstrap/migrations are intentionally separate from PostgreSQL Alembic; their compatibility and upgrade policies must stay synchronized.
- The target architecture is school-agnostic, but current real-page extraction and reviewed fixtures prioritize Kean/WKU; those mappings must remain source-tagged rather than enter generic algorithms.

### 6) Evidence

- `docs/ARCHITECTURE.md`
- `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`
- `apps/api/app/services/`
- `desktop-shell/src-tauri/src/main.rs`
- `apps/web/src/app/page.tsx`
