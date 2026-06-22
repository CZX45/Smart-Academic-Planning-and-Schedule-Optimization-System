# Smart Academic Planning and Schedule Optimization System

A full-stack, school-agnostic foundation for explainable academic planning, degree-progress analysis, and section-level schedule optimization.

Phase 1 implements the runnable project infrastructure only. It does **not** implement real school login, scraping, automatic registration, waitlist automation, or authoritative academic advice. Development seed data is mock-only and must not be presented as official school policy.

## Phase 1 Monorepo Layout

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

## Phase 1 scope and data safety

Phase 1 is infrastructure only. It does not include real school login, SAML automation, portal scraping, automatic registration, add/drop/swap, waitlist automation, seat grabbing, graduation audit logic, or automatic schedule optimization.

All seed data is mock-only. Mock data is not official university policy, and students must confirm high-impact academic guidance with the school or an advisor.

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)
