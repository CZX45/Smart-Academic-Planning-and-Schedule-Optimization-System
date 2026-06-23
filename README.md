# Smart Academic Planning and Schedule Optimization System

A full-stack, school-agnostic foundation for explainable academic planning, degree-progress analysis, and section-level schedule optimization.

Phase 3A adds a deterministic Degree Audit Core on top of the Phase 2A/2B academic data foundation. It creates auditable snapshots for one mock student and one program version, evaluates stored requirement trees, applies completed/in-progress/planned attempts plus approved transfer, waiver, and substitution records, and returns structured explanations and advisor warnings. It does **not** implement eligibility decisions, minor/major what-if, planning, scheduling, real school login, scraping, automatic registration, waitlist automation, or authoritative academic advice. Development seed data is mock-only and must not be presented as official school policy.

## Monorepo Layout

```text
apps/
  api/                 # FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Ruff, mypy
  web/                 # Next.js TypeScript app with API health status
packages/
  shared/              # Shared TypeScript schemas/client helpers and OpenAPI copy step
  fixtures/            # Development-only mock seed placeholders
  config/              # Reserved for shared config packages
infra/
  docker/              # Dockerfiles for local API/web containers
docs/                  # Product, architecture, data model, rules, roadmap, testing docs
tests/e2e/             # Playwright baseline tests
```

## Prerequisites

- Node.js 24+
- pnpm 10.28.1, normally via Corepack from `packageManager`
- Python 3.12+
- Docker with Docker Compose
- Access to the npm registry and Python package index

## Environment

Copy the example file before local development:

```bash
cp .env.example .env
```

`.env.example` contains only local development defaults. It must not contain real school accounts, school passwords, student records, or production secrets. The local `.env` file is ignored by Git.

Required local variables include:

- `DATABASE_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `CORS_ORIGINS`

## Install

```bash
corepack enable
pnpm install --frozen-lockfile
python -m pip install -e "apps/api[dev]"
```

## Local mixed development

After dependencies are installed, this command starts Docker PostgreSQL plus local FastAPI and local Next.js dev servers:

```bash
pnpm dev
```

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>
- Backend readiness: <http://localhost:8000/ready>
- PostgreSQL: `localhost:5432`

Stop the foreground `pnpm dev` process with Ctrl+C. Stop PostgreSQL with:

```bash
docker compose down
```

## Full Docker development

This command starts PostgreSQL, FastAPI, and Next.js in Docker. The API waits for the database health check and runs Alembic migrations before Uvicorn starts.

```bash
pnpm dev:docker
```

Use <http://localhost:3000> for the frontend. Stop containers with:

```bash
docker compose down
```

To intentionally delete the local development database volume:

```bash
docker compose down -v
```

## Database and seed

Start only PostgreSQL:

```bash
pnpm db:up
```

Run migrations:

```bash
pnpm migration
```

Check Alembic metadata drift:

```bash
pnpm migration:check
```

Run idempotent development seed data:

```bash
pnpm seed
```

## OpenAPI and shared API types

The FastAPI application is the OpenAPI source of truth. Generate the baseline contract artifact and copy it into the shared package with:

```bash
pnpm openapi:generate
```

Check generated OpenAPI artifacts for drift:

```bash
pnpm openapi:check
```

The initial shared package exposes typed health/readiness schemas and API helpers.

## Phase 2A academic domain API

The backend now exposes a read-only `/api/v1` academic catalog and mock student record API:

- `GET /api/v1/institutions`
- `GET /api/v1/programs`
- `GET /api/v1/programs/{program_version_id}`
- `GET /api/v1/programs/{program_version_id}/requirements`
- `GET /api/v1/courses`
- `GET /api/v1/courses/{course_id}`
- `GET /api/v1/students/{student_id}`
- `GET /api/v1/students/{student_id}/course-attempts`

Responses include source metadata and mock/official flags. These endpoints return stored catalog and student record data only; they do not return Degree Audit, eligibility, academic plan, schedule optimizer, or registration results.

## Phase 2B course rules and sections API

Phase 2B keeps `Course` and `Section` separate. A course can have historical or expected offering patterns, course-level rules, and concrete term sections. A section can have multiple meetings such as lecture and lab records. Course prerequisites, corequisites, restrictions, and permissions share a relational expression tree model, but Phase 2B stores and returns those trees only; it does not evaluate whether a student is eligible.

New read-only endpoints include:

- `GET /api/v1/terms/{term_id}/sections`
- `GET /api/v1/courses/{course_id}/sections`
- `GET /api/v1/sections/{section_id}`
- `GET /api/v1/sections/{section_id}/meetings`
- `GET /api/v1/courses/{course_id}/rules`
- `GET /api/v1/sections/{section_id}/rules`
- `GET /api/v1/rules/{rule_id}`
- `GET /api/v1/rules/{rule_id}/expression`
- `GET /api/v1/courses/{course_id}/offering-patterns`

Offering patterns are historical or predicted planning metadata, not a school promise that a course will be offered. Mock sections, meetings, offering patterns, and rules are explicitly tagged as `MOCK` and `is_official = false`.

## Phase 3A degree audit API

Phase 3A creates immutable-style audit snapshots under `/api/v1`. A snapshot records `engine_version`, `calculation_mode`, credit totals, per-requirement evaluations, applied course/exception records, and structured warnings.

New endpoints include:

- `POST /api/v1/degree-audits`
- `GET /api/v1/degree-audits/{audit_id}`
- `GET /api/v1/degree-audits/{audit_id}/requirements`
- `GET /api/v1/degree-audits/{audit_id}/warnings`
- `GET /api/v1/students/{student_id}/degree-audits`
- `GET /api/v1/students/{student_id}/degree-audits/latest`

`CURRENT` shows final completed and approved records as completed while still reporting in-progress/planned layers separately. `PROJECTED` can show in-progress and planned potential contributions without relabeling them as completed. GET endpoints never create snapshots.

The web app now opens to a read-only mock Degree Progress view with summary credits, warnings, and expandable requirement rows. It uses shared Zod schemas and does not reimplement audit rules in the frontend.

## Quality gates

Run the following before opening a pull request:

```bash
python -m ruff check apps/api
python -m ruff format --check apps/api
pnpm lint
pnpm typecheck
pnpm test
pnpm build
cd apps/api && python -m alembic upgrade head
cd apps/api && python -m mypy .
cd apps/api && python -m pytest
git diff --check
```

Playwright is configured with a baseline homepage test:

```bash
pnpm exec playwright install --with-deps
pnpm e2e
```

## Phase 2A, 2B, and 3A scope and data safety

Phase 2A is a domain-storage foundation. It models institutions, campuses, terms, academic programs, program versions, courses, course equivalencies, requirement trees, course options, mock student profiles, academic program declarations, course attempts, transfer credits, waivers, and substitutions.

Phase 2B adds `Section`, `SectionMeeting`, `CourseOfferingPattern`, `CourseRule`, and `CourseRuleExpression`. It models section snapshots and rule storage only; it does not monitor seats, store registration rosters, evaluate eligibility, or optimize schedules.

Phase 3A adds `DegreeAuditRun`, `RequirementEvaluation`, `AuditCourseApplication`, and `DegreeAuditWarning`. It evaluates a single `StudentProfile` against a single `ProgramVersion` and stores a snapshot. The baseline allocator is deterministic and explainable but intentionally not a global course-allocation optimizer.

All seed data is mock-only. Mock data is not official university policy, and students must confirm high-impact academic guidance with the school or an advisor.

The next planned implementation phase is Phase 3B What-if and advanced allocation. The project should not jump directly to eligibility, scheduling, OR-Tools, browser extension work, or registration behavior.

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)
