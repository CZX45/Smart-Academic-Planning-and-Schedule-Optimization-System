# Final Architecture Snapshot

This snapshot captures the Phase 10B handoff architecture at a concise level for
reviewers and future maintainers.

## Monorepo Layout

```text
apps/
  api/                 # FastAPI backend, domain services, migrations, tests
  extension/           # Manifest V3 local-development read-only import assistant
  web/                 # Next.js student/advisor review UI
packages/
  shared/              # Shared TypeScript schemas, API helpers, OpenAPI artifact
  fixtures/            # Mock/source-tagged fixture placeholders
  config/              # Shared config placeholder
infra/
  docker/              # Local Docker infrastructure helpers
docs/                  # Architecture, domain, release, safety, handoff docs
tests/e2e/             # Playwright baseline workflows
```

## API App Role

`apps/api` owns the domain model, Pydantic schemas, SQLAlchemy persistence,
Alembic migrations, OpenAPI generation, and pytest coverage. It exposes
read-oriented academic data endpoints plus snapshot-creating endpoints for
degree audit, what-if scenarios, eligibility, academic planning, schedule
optimization, data imports, data reviews, and section monitoring.

Core academic calculations belong in backend/domain modules and are covered by
deterministic tests. Mutating endpoints are scoped to internal planning and
staging records; they do not perform school-portal actions.

## Web App Role

`apps/web` renders the student/advisor-facing review surface. It calls typed API
helpers from `packages/shared`, displays snapshots and warnings, and keeps
manual next actions visible. UI components should render state and invoke typed
services; they should not reimplement audit, eligibility, planning, or schedule
optimizer logic.

## Browser Extension Role

`apps/extension` is a local-development Manifest V3 extension. It reads only the
active visible page after explicit user action, previews extracted rows, and
sends confirmed data to the backend as a non-official staging import. It does
not store credentials, inspect password fields, bypass school authentication,
submit forms, or run hidden automation.

Phase 11B adds a Kean Student Portal workflow under
`https://kean-ss.colleague.elluciancloud.com/Student/*`. Current-page import
uses the active tab, guided import requests the optional Kean host permission,
and extraction code still enforces the `/Student/` prefix plus configured
academic-planning page definitions.

## Shared Package Role

`packages/shared` contains TypeScript schemas, API helpers, and generated
OpenAPI artifacts used by frontend code and tests. OpenAPI generation keeps the
backend contract and shared client artifacts aligned.

## Database and Migrations Role

PostgreSQL is the target database. Alembic migrations in `apps/api` are the
reviewable record of schema changes. Phase 10B adds no schema changes and no
migrations.

## OpenAPI Role

FastAPI OpenAPI output is the source of truth for frontend/backend integration.
The expected workflow is:

```text
Backend schemas and routes -> OpenAPI artifact -> shared TypeScript artifact -> typed web usage.
```

`corepack pnpm openapi:generate` regenerates artifacts, and
`corepack pnpm openapi:check` verifies there is no drift.

## Test Layers

- Python unit/integration tests with pytest for API, domain logic, policies,
  imports, reviews, eligibility, planning, scheduling, monitoring, and docs.
- Ruff and mypy for Python linting/formatting/type checking.
- TypeScript tests for web, extension, and shared packages.
- Playwright e2e tests for baseline browser workflows.
- OpenAPI drift checks for generated API contracts.
- Release and safety policy tests for prohibited action names and misleading
  demo wording.

## Data Import Flow

```text
CSV/JSON upload or user-triggered extension import
  -> DataImportRun staging records with source metadata
  -> mapping candidates and warnings
  -> DataImportReviewSession
  -> dry run
  -> explicit apply of supported reviewed rows to internal planning records
```

Imported rows remain non-official unless a future reviewed workflow changes that
rule. Unsupported, ambiguous, rejected, deferred, or advisor-review rows are
skipped with reason codes and warnings.

Kean Student Portal imports are labeled `KEAN_STUDENT_PORTAL` in safe preview
metadata while preserving `source_type = BROWSER_EXTENSION`,
`is_official = false`, `official_application_ready = false`, and Phase 7B
review.

## Section Monitoring Flow

```text
Monitor target
  -> user-triggered section-search snapshot import
  -> snapshot comparison
  -> advisory alert
  -> user acknowledgement and manual portal review
```

Alerts are derived from imported snapshots and do not update canonical section,
seat, waitlist, schedule, student, or registration state.

## Schedule Optimization Flow

```text
Requested course set and constraints
  -> eligible candidate sections
  -> hard-constraint filtering
  -> preference scoring
  -> ranked schedule options
  -> conflicts, warnings, score explanations, and repair suggestions
```

Academic-plan optimization and semester section-schedule optimization remain
separate. Schedule options are advisory snapshots.

## Deployment-Readiness Notes

- Production deployment is not included in Phase 10B.
- Production use needs account/auth design, institutional data review, data
  deletion/export controls, observability planning, accessibility review, and
  deployment runbooks.
- Environment validation, CORS checks, security headers, OpenAPI checks, and
  migration checks are already part of the readiness path.
- Any browser-store packaging review must preserve the read-only import model
  and be explicitly approved before release work begins.
- Kean import support is local-development workflow support, not browser-store
  publication, official-source ingestion, account handling, polling, or
  enrollment automation.
