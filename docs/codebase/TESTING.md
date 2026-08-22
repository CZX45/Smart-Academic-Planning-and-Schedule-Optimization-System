# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary frameworks: pytest 9+, Vitest 4, Playwright 1.61, Rust/Cargo test.
- Assertions/mocking: native pytest assertions/fixtures, Vitest expect/mocks, Playwright locators/routes.
- Commands:

```bash
corepack pnpm test
cd apps/api && python -m pytest
corepack pnpm e2e
cargo test --manifest-path desktop-shell/src-tauri/Cargo.toml
```

### 2) Test Layout

- Backend: 38 files under `apps/api/tests/test_*.py` including models, services, APIs, migrations, runtime, security, backup/restore, diagnostics, and packaging.
- Web: co-located `apps/web/src/**/*.test.ts`; shared: `packages/shared/src/index.test.ts`.
- Extension: 25 files under `apps/extension/tests/` with synthetic HTML fixtures.
- Browser E2E: `tests/e2e/*.spec.ts`, configured by `playwright.config.ts`.

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | yes | parsers, rules, allocation, optimizer scoring, sanitization | Deterministic synthetic inputs |
| Integration | yes | FastAPI/SQLAlchemy, imports/reviews, migrations, local runtime | SQLite locally; PostgreSQL in CI |
| E2E | yes | browser workflows and installed Windows desktop | Packaged desktop is authoritative for Tauri/WebView/process proof |

### 4) Mocking and Isolation Strategy

- API/domain tests use isolated database sessions and synthetic fixtures.
- Playwright routes mock complete API responses for frontend-state tests; separate CI jobs exercise real API/server paths.
- Packaged E2E uses a fresh isolated `LOCALAPPDATA` tree and sanitized MyProgress fixture, not real student data.
- Common failure mode: cross-session UI state and packaged-process behavior can diverge from single-page source E2E.

### 5) Coverage and Quality Signals

- Coverage threshold: `[TODO]` no explicit numeric percentage is enforced.
- Current counts are determined by fresh command output, not historical phase claims.
- High-risk gates include OpenAPI drift, PostgreSQL migration/seed idempotency, local migrations, security wording/policies, installer artifact/lifecycle, and packaged desktop E2E.

### 6) Evidence

- `apps/api/pyproject.toml`
- `docs/TEST_STRATEGY.md`
- `.github/workflows/ci.yml`
- `.github/workflows/windows-installer-lifecycle.yml`
- `.github/workflows/windows-packaged-desktop-e2e.yml`
