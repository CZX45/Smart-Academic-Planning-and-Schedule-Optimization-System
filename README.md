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

- Node.js 24+ and pnpm 10+
- Python 3.12+
- Docker with Docker Compose

## Environment

Copy the example file before local development:

```bash
cp .env.example .env
```

`.env.example` contains only local development defaults. Do not commit real credentials or school secrets.

## One-command local startup

After dependencies are installed, this command starts PostgreSQL, the FastAPI backend, and the Next.js frontend:

```bash
pnpm dev
```

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>
- PostgreSQL: `localhost:5432`

## Setup and development commands

```bash
pnpm install
python -m pip install -e "apps/api[dev]"
pnpm db:up
pnpm db:migrate
pnpm seed:dev
pnpm dev
```

## OpenAPI and shared API types

The FastAPI application is the OpenAPI source of truth. Generate the baseline contract artifact and copy it into the shared package with:

```bash
pnpm openapi:generate
```

The initial shared package exposes a typed `HealthResponse` schema and `fetchHealth` helper.

## Quality gates

Run the following before opening a pull request:

```bash
pnpm lint
pnpm typecheck
pnpm test
cd apps/api && ruff format --check .
cd apps/api && alembic upgrade head
git diff --check
```

Playwright is configured with a baseline homepage test:

```bash
pnpm exec playwright test
```

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)
