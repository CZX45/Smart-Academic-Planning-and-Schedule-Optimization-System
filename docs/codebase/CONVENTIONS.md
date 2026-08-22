# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Files | Python snake_case; TS feature names use kebab-case or descriptive lowercase | `schedule_optimizer/engine.py`, `course-state-workflow.ts` | `apps/api/app/services/`, `apps/web/src/lib/` |
| Functions/methods | Python snake_case; TS/Rust camel/snake per language | `initialize_database`, `fetchHealth` | `apps/api/app/db/bootstrap.py`, `packages/shared/src/index.ts` |
| Types/interfaces | PascalCase | `RuntimeManifest`, `DataImportPreviewState` | `apps/api/app/runtime/discovery.py`, `apps/web/src/app/page.tsx` |
| Constants/env vars | UPPER_SNAKE_CASE | `LOCAL_SCHEMA_VERSION`, `PRODUCT_MODE` | `apps/api/app/db/bootstrap.py`, `.env.example` |

### 2) Formatting and Linting

- Formatter: Ruff format for Python; Prettier for TypeScript/JSON/CSS; rustfmt for Rust.
- Linters: Ruff rules `E,F,I,UP,B`; ESLint strict TypeScript/Next core-web-vitals; Cargo clippy where invoked.
- Strictness: mypy strict; TypeScript `strict`, with `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` in extension/shared.
- Commands: `corepack pnpm format`, `corepack pnpm lint`, `python -m ruff check apps/api`, `python -m ruff format --check apps/api`, `cargo fmt --check`.

### 3) Import and Module Conventions

- Ruff enforces Python import ordering.
- Web uses `@/*` and `@sapsos/shared`; extension/shared use NodeNext and explicit `.js` runtime import style where required.
- Generated OpenAPI output is owned by the backend export and copied into the shared package; it is not edited manually.
- Private helpers generally use Python's leading underscore convention; TypeScript relies on module scope or class privacy rather than a repository-specific prefix.

### 4) Error and Logging Conventions

- API/domain layers return typed validation/errors and structured reason/warning records; high-risk uncertainty fails closed or requests manual/advisor review.
- Packaged scripts use `$ErrorActionPreference = "Stop"`, bounded waits, explicit assertions, and sanitized evidence.
- Logs must omit credentials, raw portal HTML, full student records, cookies, tokens, and other auth material.
- Python services use the standard `logging` module with module-named loggers where operational logging is needed. The Rust shell uses sanitized JSON diagnostic files plus narrowly scoped `eprintln!` startup failures; no third-party structured logging stack is configured.

### 5) Testing Conventions

- pytest modules are `apps/api/tests/test_*.py`; Vitest uses `*.test.ts`; Playwright uses `*.spec.ts`.
- Tests use synthetic/sanitized fixtures and SQLite isolation for domain behavior; PostgreSQL migration/seed behavior runs in CI.
- Coverage threshold: `[TODO]` no explicit numeric threshold is configured in current manifests.

### 6) Evidence

- `apps/api/pyproject.toml`
- `apps/web/eslint.config.mjs`
- `apps/extension/eslint.config.js`
- `apps/extension/tsconfig.json`
- `docs/TEST_STRATEGY.md`
