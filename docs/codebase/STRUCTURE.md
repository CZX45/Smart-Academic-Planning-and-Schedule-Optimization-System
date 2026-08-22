# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `apps/api/` | FastAPI boundary, domain services, persistence, migrations, packaging, pytest | `apps/api/app/main.py`, `apps/api/tests/` |
| `apps/web/` | Next.js UI and workflow state | `apps/web/src/app/page.tsx`, `apps/web/src/components/` |
| `apps/extension/` | Manifest V3 visible-page capture and local handoff | `apps/extension/manifest.json`, `apps/extension/src/` |
| `packages/shared/` | Typed schemas, API helpers, generated OpenAPI copy | `packages/shared/src/index.ts` |
| `desktop-shell/` | Tauri shell, desktop identity, retention and NSIS hooks | `desktop-shell/src-tauri/src/main.rs` |
| `scripts/windows/` | Build, validation, lifecycle, installed E2E, and local helpers | root `package.json` scripts |
| `tests/e2e/` | Browser workflow regression suite | `playwright.config.ts` |
| `docs/` | Product, architecture, domain, safety, release, and execution authority | `README.md`, `AGENTS.md` |

Hidden configuration is concentrated in `.github/` for CI and repository policy. `.cache/` and `.runtime/` are local ignored/task evidence areas, not product modules.

### 2) Entry Points

- Main API entry: `apps/api/app/main.py`; packaged process entry: `apps/api/app/run.py`.
- Web entry: `apps/web/src/app/page.tsx` through the Next.js app router.
- Desktop entry: `desktop-shell/src-tauri/src/main.rs`.
- Extension entry points: `apps/extension/src/popup/` and `apps/extension/src/background/service-worker.ts` configured by `apps/extension/manifest.json`.
- Secondary entry points: seed, OpenAPI export, migration contract, schema verifier, Windows build/lifecycle scripts.

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `apps/api/app/services/` | Audit, eligibility, planner, optimizer, import, review, backup/restore domain behavior | UI rendering and school record writes |
| `apps/api/app/api/` | FastAPI routing and validated request/response boundaries | Hidden academic policy or UI state |
| `apps/web/src/` | Typed calls, workflow state, rendering and user actions | Independent academic-rule evaluation |
| `apps/extension/src/` | User-triggered visible-page extraction and local API handoff | Credentials, background scraping, registration actions |
| `desktop-shell/src-tauri/` | Process ownership, migration preflight, runtime discovery and desktop lifecycle | Academic rule logic |

### 4) Naming and Organization Rules

- Python files/functions use `snake_case`; classes and Pydantic/SQLAlchemy types use `PascalCase`.
- TypeScript components/types use `PascalCase`; functions/variables use `camelCase`; test files use `.test.ts` and `.spec.ts`.
- Python is layer/feature hybrid; frontend workflow modules are feature-oriented.
- Web uses `@/*` and `@sapsos/shared` aliases; extension/shared use NodeNext imports.

### 5) Evidence

- `AGENTS.md`
- `apps/api/app/`
- `apps/web/tsconfig.json`
- `apps/extension/manifest.json`
- `playwright.config.ts`
