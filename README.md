# Smart Academic Planning and Schedule Optimization System

A full-stack, school-agnostic foundation for explainable academic planning, degree-progress analysis, and section-level schedule optimization.

Phase 7A adds a read-only Data Import Preview foundation on top of Degree Audit, What-if Scenarios, Course Eligibility, the Long-Term Academic Planner, and the Semester Schedule Optimizer. It parses small mock or student-provided CSV/JSON academic data into staging tables, proposes mapping candidates, emits validation warnings, and renders a preview panel. It does **not** apply imported rows to official domain tables, create registrations, add/drop/swap courses, join waitlists, poll seats, run OR-Tools, scrape portals, bypass school authentication, or provide authoritative academic advice. Development seed data is mock-only and must not be presented as official school policy.

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

## Phase 3B what-if scenario API

Phase 3B creates scenario snapshots under `/api/v1/academic-scenarios`. Scenarios store hypothetical program combinations, per-program Phase 3A audit runs, global course allocations, warnings, and comparison summaries. Scenario creation never changes declared academic programs.

New endpoints include:

- `POST /api/v1/academic-scenarios`
- `GET /api/v1/academic-scenarios/{scenario_id}`
- `GET /api/v1/academic-scenarios/{scenario_id}/programs`
- `GET /api/v1/academic-scenarios/{scenario_id}/audits`
- `GET /api/v1/academic-scenarios/{scenario_id}/allocations`
- `GET /api/v1/academic-scenarios/{scenario_id}/warnings`
- `GET /api/v1/academic-scenarios/{scenario_id}/comparison`
- `GET /api/v1/students/{student_id}/academic-scenarios`
- `POST /api/v1/academic-scenarios/compare`

Program combination rules are directional. Shared credits require both requirement-level overlap permission and a matching directional combination rule. Shared credits can satisfy more than one requirement, but total earned credits are counted once. Estimated additional credits are labeled as estimates and do not predict graduation timing.

The web app includes an Explore Programs / What-if Analysis panel for mock candidate programs, scenario summaries, allocation rows, warnings, and saved-scenario comparison.

## Phase 4 course eligibility API

Phase 4 creates eligibility check snapshots under `/api/v1/eligibility-checks`. The engine evaluates stored mock course-level and section-level rule expression trees against a mock student record. Section availability is returned separately from academic eligibility so closed or waitlisted seats do not silently change prerequisite/restriction outcomes.

New endpoints include:

- `POST /api/v1/eligibility-checks`
- `POST /api/v1/eligibility-checks/batch`
- `GET /api/v1/eligibility-checks/{eligibility_check_id}`
- `GET /api/v1/eligibility-checks/{eligibility_check_id}/rules`
- `GET /api/v1/eligibility-checks/{eligibility_check_id}/warnings`
- `GET /api/v1/students/{student_id}/eligibility-checks`

Eligibility modes are `CURRENT`, `PROJECTED`, and `REGISTRATION`. Results can be `ELIGIBLE`, `CONDITIONALLY_ELIGIBLE`, `NOT_ELIGIBLE`, `PERMISSION_REQUIRED`, or `MANUAL_REVIEW_REQUIRED`. Responses include rule-level and expression-level explanations, structured reasons, warnings, corequisite summaries, and optional section availability.

The web app includes a Course Eligibility panel for mock course checks, expression evidence, warnings, offline/failure/schema-error states, and saved eligibility history.

## Phase 5A long-term academic planner API

Phase 5A creates academic plan snapshots under `/api/v1/academic-plans`. The planner evaluates remaining mock requirements, prerequisite/corequisite ordering, target terms, per-term credit limits, and stored offering-pattern assumptions. It stores generated terms, planned courses, requirement coverage, and warnings as reviewable snapshots.

New endpoints include:

- `POST /api/v1/academic-plans`
- `POST /api/v1/academic-plans/compare`
- `GET /api/v1/academic-plans/{plan_id}`
- `GET /api/v1/academic-plans/{plan_id}/terms`
- `GET /api/v1/academic-plans/{plan_id}/courses`
- `GET /api/v1/academic-plans/{plan_id}/warnings`
- `GET /api/v1/students/{student_id}/academic-plans`

Planning modes are `CURRENT_PROGRAM` and `WHAT_IF_SCENARIO`. A plan can complete with warnings when requirements are broad, a course lacks an offering pattern, a term falls below the requested minimum credits, or the horizon/credit limits prevent placement. Phase 5A deliberately remains course-level: it does not select sections, calculate weekly schedule conflicts, poll seat counts, or perform registration actions.

The web app includes a Long-Term Academic Planner panel for current-program and what-if mock plans, credit-limit controls, term-by-term output, requirement coverage, warnings, saved-plan comparison, and offline/failure/schema-error states.

## Phase 6B semester schedule optimizer API

Phase 6B creates semester schedule snapshots under `/api/v1/schedule-optimizations`. The optimizer evaluates concrete mock sections for one term, applies hard constraints such as time overlap, unavailable blocks, excluded days, required/excluded sections, modality filters, eligibility blocks, and credit limits, then ranks bounded options with deterministic preference scoring.

New endpoints include:

- `POST /api/v1/schedule-optimizations`
- `POST /api/v1/schedule-optimizations/compare`
- `GET /api/v1/schedule-optimizations/{run_id}`
- `GET /api/v1/schedule-optimizations/{run_id}/options`
- `GET /api/v1/schedule-optimizations/{run_id}/conflicts`
- `GET /api/v1/schedule-optimizations/{run_id}/warnings`
- `GET /api/v1/students/{student_id}/schedule-optimizations`

Planning modes are `FROM_DEGREE_AUDIT`, `FROM_LONG_TERM_PLAN`, and `CUSTOM_COURSE_SET`. Phase 6B is intentionally bounded and synchronous: it does not use OR-Tools, does not monitor seats, and does not perform registration, add/drop/swap, waitlist, or portal automation. Mock, inferred, or ambiguous schedule results require advisor or school confirmation for high-impact decisions.

Phase 6B preference inputs include normalized preference weights, per-course priority weights, per-section priority weights, no-gap, morning, afternoon, compactness, class-day, modality, early-start, and late-end preferences. Responses include a `score_breakdown`, `score_explanation`, `diversity_rank`, `difference_summary`, hard-constraint summaries, soft-preference summaries, and repair suggestions for infeasible or partial schedules.

The web app includes a Semester Schedule Builder panel for mock course sets, no-Friday and unavailable-time constraints, pinned/excluded section choices, online/compact/fewer-day/no-gap/morning/afternoon preferences, high-diversity ranking, partial-option controls, ranked option output, score breakdowns, repair suggestions, conflicts, warnings, saved-schedule comparison, and offline/failure/schema-error states.

## Phase 7A read-only data import preview API

Phase 7A creates staging-only import previews under `/api/v1/data-imports`. Imports are bounded, synchronous, mock or student-provided, and metadata-only for file storage. The service parses CSV or JSON content, normalizes generic course-code fields, stores raw normalized payload snippets in `imported_records`, creates mapping candidates, emits warnings, and returns preview disclaimers.

Supported endpoint family:

- `POST /api/v1/data-imports`
- `GET /api/v1/data-imports/{run_id}`
- `GET /api/v1/data-imports/{run_id}/records`
- `GET /api/v1/data-imports/{run_id}/mapping-candidates`
- `GET /api/v1/data-imports/{run_id}/warnings`
- `GET /api/v1/data-imports/{run_id}/preview`
- `POST /api/v1/data-imports/{run_id}/validate`
- `GET /api/v1/students/{student_id}/data-imports`

Import types include unofficial transcript CSV, degree audit JSON, catalog CSV, section schedule CSV, and generic CSV/JSON. Phase 7A intentionally keeps `official_application_ready = false`; it never writes imported records into `student_course_attempts`, `courses`, `sections`, requirement tables, registration state, seat counts, or waitlists. The web app includes a Data Import Preview panel with required non-official and advisor-confirmation disclaimers.

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

## Phase 2A through 6B scope and data safety

Phase 2A is a domain-storage foundation. It models institutions, campuses, terms, academic programs, program versions, courses, course equivalencies, requirement trees, course options, mock student profiles, academic program declarations, course attempts, transfer credits, waivers, and substitutions.

Phase 2B adds `Section`, `SectionMeeting`, `CourseOfferingPattern`, `CourseRule`, and `CourseRuleExpression`. It models section snapshots and rule storage only; it does not monitor seats, store registration rosters, evaluate eligibility, or optimize schedules.

Phase 3A adds `DegreeAuditRun`, `RequirementEvaluation`, `AuditCourseApplication`, and `DegreeAuditWarning`. It evaluates a single `StudentProfile` against a single `ProgramVersion` and stores a snapshot. The baseline allocator is deterministic and explainable but intentionally not a global course-allocation optimizer.

Phase 3B adds `AcademicPlanScenario`, `ScenarioProgram`, `ProgramCombinationRule`, `ScenarioProgramAudit`, `ScenarioCourseAllocation`, `ScenarioComparisonSnapshot`, and `ScenarioWarning`. It compares hypothetical program combinations without changing official student declarations.

Phase 4 adds `EligibilityCheckRun`, `RuleEvaluation`, `RuleExpressionEvaluation`, and `EligibilityWarning`. It snapshots mock course eligibility checks without changing `StudentAcademicProgram`, `StudentCourseAttempt`, section, or registration records.

Phase 5A adds `AcademicPlanRun`, `AcademicPlanTerm`, `AcademicPlanCourse`, `AcademicPlanRequirementCoverage`, and `AcademicPlanWarning`. It snapshots mock long-term course plans without changing official student declarations, course attempts, sections, section meetings, or registration records.

Phase 6A adds `ScheduleOptimizationRun`, `ScheduleConstraintSet`, `ScheduleOption`, `ScheduleOptionSection`, `ScheduleConflict`, and `ScheduleWarning`. Phase 6B extends those snapshots with advanced preference fields, score components, diversity metadata, and `ScheduleRepairSuggestion`. It snapshots mock single-term section schedules without changing official student declarations, course attempts, sections, section meetings, seat records, waitlists, or registration records.

Phase 7A adds `DataImportRun`, `DataImportFile`, `ImportedRecord`, `ImportMappingCandidate`, `ImportValidationWarning`, and `ImportPreviewSummary`. These tables are import staging and preview tables only; they preserve source metadata, warnings, reason codes, and mapping explanations without applying imported records to official academic-domain tables.

All seed data is mock-only. Mock data is not official university policy, and students must confirm high-impact academic guidance with the school or an advisor.

The project should not jump from Phase 4 directly into automatic registration, waitlist automation, seat-grabbing, credential storage, or portal bypass behavior.

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)
