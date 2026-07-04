# Smart Academic Planning and Schedule Optimization System

A full-stack, school-agnostic foundation for explainable academic planning, degree-progress analysis, and section-level schedule optimization.

Phase 11B adds a user-authorized Kean Student Portal academic import workflow on top of the Phase 10B final demo and handoff package. Browser-extension and monitoring data remains `source_type = BROWSER_EXTENSION` or otherwise non-official, and students must verify manually in the official registration portal. The system does **not** store credentials, bypass SAML/MFA/CAPTCHA, scrape in the background, publish to a browser store, create official transcript data, register, add/drop/swap courses, join waitlists, alter seat state, run polling, submit forms, or provide authoritative academic advice. Development seed data is mock-only and must not be presented as official school policy.

## Monorepo Layout

```text
apps/
  api/                 # FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Ruff, mypy
  extension/           # Chrome Extension Manifest V3 read-only import assistant
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

- `ENVIRONMENT`
- `DATABASE_URL`
- `DATABASE_CONNECT_TIMEOUT_SECONDS`
- `NEXT_PUBLIC_API_BASE_URL`
- `CORS_ORIGINS`

`ENVIRONMENT` must be one of `development`, `test`, `staging`, or `production`. Production settings must use an explicit non-local PostgreSQL URL and HTTPS CORS origins; the API rejects wildcard CORS origins and unsupported database URL schemes. `NEXT_PUBLIC_API_BASE_URL` must be an `http` or `https` URL and must not contain credentials.

## Install

```bash
corepack enable
pnpm install --frozen-lockfile
python -m pip install -e "apps/api[dev]"
```

## Run as Local Software

Phase 11C provides a Windows local software workflow for running the web app,
API, PostgreSQL database, and browser-extension package without adding new
academic planning features.

Prerequisites:

- Git
- Node.js 24+ with Corepack/pnpm
- Python 3.12+
- Docker Desktop
- Chrome or Edge for the extension

Check prerequisites:

```powershell
.\scripts\windows\Check-Prerequisites.ps1
```

Start the local stack:

```powershell
.\scripts\windows\Start-Smart-Academic-Planner.ps1
```

Open the app:

- Web app: <http://localhost:3000> by default. Set `LOCAL_WEB_PORT=3001`,
  `3010`, or `3011` before starting when you need another local web port.
- API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

Stop the local stack:

```powershell
.\scripts\windows\Stop-Smart-Academic-Planner.ps1
```

Build the local browser extension package:

```powershell
corepack pnpm extension:package
```

Load the generated `dist/extension-unpacked` folder manually from
`chrome://extensions` or `edge://extensions` with Developer Mode enabled.

Detailed local-use docs:

- [User Software Manual](docs/USER_SOFTWARE_MANUAL.md)
- [Local App Package](docs/LOCAL_APP_PACKAGE.md)
- [Kean Portal Real-Page QA](docs/KEAN_PORTAL_REAL_PAGE_QA.md)

Safety boundary: the local software has no credential collection, no
cookie/session-token storage, no SAML/MFA/CAPTCHA bypass, no portal form
submission, no automatic registration, no waitlist automation, no background
polling, no seat reservation, no seat grabbing, no browser-store publishing,
and no hidden automation.

## Local mixed development

After dependencies are installed, this command starts Docker PostgreSQL plus local FastAPI and local Next.js dev servers:

```bash
pnpm dev
```

- Frontend: <http://localhost:3000> by default. E2E and local diagnostics also
  support `PLAYWRIGHT_WEB_PORT=3001`, `3010`, or `3011`.
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

Use <http://localhost:3000> for the frontend, or set `LOCAL_WEB_PORT` before
starting Docker Compose to expose the web app on another supported local port.
The default local API CORS configuration includes ports `3000`, `3001`, `3010`,
and `3011`. Stop containers with:

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

## Phase 7B — Data Review and Confirmation Workflow

Phase 7B reviews Phase 7A staging rows before any internal planning write. Users create a review session, update each imported record decision, run a dry-run application, and then explicitly POST an apply request. GET endpoints only read review/application state.

New endpoints include:

- `POST /api/v1/data-import-reviews`
- `GET /api/v1/data-import-reviews/{review_id}`
- `GET /api/v1/data-import-reviews/{review_id}/records`
- `PATCH /api/v1/data-import-reviews/{review_id}/records/{record_review_id}`
- `POST /api/v1/data-import-reviews/{review_id}/apply`
- `GET /api/v1/data-import-reviews/{review_id}/applications`
- `GET /api/v1/data-import-reviews/{review_id}/warnings`
- `GET /api/v1/data-applications/{application_id}`
- `GET /api/v1/students/{student_id}/data-import-reviews`

Review decisions are `UNREVIEWED`, `CONFIRMED`, `REJECTED`, `NEEDS_ADVISOR_REVIEW`, `EDITED_AND_CONFIRMED`, and `DEFERRED`. Confirmed unofficial transcript course attempts can create internal `student_course_attempts` rows with `is_official = false`, source metadata, application logs, and duplicate checks. Unsupported catalog, section, requirement, unknown-course, rejected, deferred, advisor-review, duplicate, and unsupported-grade records are skipped with reason codes and warnings rather than silently applied.

## Phase 8A — Read-only Browser Extension Import

Phase 8A introduces `apps/extension`, a local-development Manifest V3 extension scaffold. It reads only the active visible page after the user clicks the extension action, extracts mock-compatible transcript, degree-audit, catalog, or section-search tables, shows a preview, and sends data only after explicit confirmation.

Extension handoff reuses `POST /api/v1/data-imports` with:

- `source_type = BROWSER_EXTENSION`
- `is_official = false`
- staging CSV/JSON content derived from visible page tables
- source reference metadata for the visible page URL

Browser-extension imports remain staging-only. They do not bypass Phase 7A validation, Phase 7B review, or Phase 7B explicit apply. The extension does not store credentials, inspect password fields, bypass school authentication, submit portal forms, automate registration, add/drop/swap courses, join waitlists, grab seats, run live polling, or publish production browser-store builds in this phase.

## Phase 8B — Read-only Section Monitoring Alerts

Phase 8B creates advisory section monitoring under `/api/v1/section-monitoring`. A student can create a monitor target, submit user-triggered non-official section-search snapshots, compare snapshots, list alerts, and acknowledge alerts. Snapshot comparison deduplicates identical imports and alerts on section opened/closed changes, seat count changes, waitlist count changes, meeting-time changes, instructor changes, location changes, and unknown raw-payload changes.

New endpoints include:

- `GET /api/v1/section-monitoring/targets`
- `POST /api/v1/section-monitoring/targets`
- `PATCH /api/v1/section-monitoring/targets/{target_id}`
- `POST /api/v1/section-monitoring/snapshots/compare`
- `GET /api/v1/section-monitoring/alerts`
- `PATCH /api/v1/section-monitoring/alerts/{alert_id}`

Section monitoring is advisory and non-official. It does not mutate canonical `Section` rows, seat counts, waitlists, student records, academic plans, schedules, or registration state. It does not poll portals, change seat or waitlist state, submit forms, or perform registration actions. The web app includes a Section Monitoring panel with monitored sections, advisory alerts, required disclaimers, and a manual registration checklist.

## Phase 9A — Product Hardening and Dashboard Polish

Phase 9A improves the existing product surface without changing backend domains or the read-only/advisory boundary. The home dashboard adds status cards for degree audit, data import review, browser extension import, section monitoring, schedule optimization, and what-if planning. Each card shows a current status, concise explanation, recommended manual next action, advisory labels where relevant, and an in-page link to the existing workflow.

Phase 9A also adds clearer empty states for missing imports, missing confirmed imports, missing section monitoring targets, missing advisory alerts, missing schedule plans, and missing what-if scenarios. Shared TypeScript helpers now provide status badge copy, advisory label copy, UTC timestamp formatting, before/after value display, and reusable empty-state copy. The UI copy keeps browser extension imports, section monitoring snapshots/alerts, data import previews, and manually reviewed imports labeled as non-official, manual-review, and advisory-only where appropriate.

This phase does not add registration automation, portal submission, polling, background scraping, credential capture, waitlist automation, seat-state changes, or official school-policy claims.

## Phase 9B — Security and Production Readiness Hardening

Phase 9B adds focused operational hardening without changing product workflows. The API validates database URL, app environment, database timeout, and CORS origins with production-safe defaults. The web app validates `NEXT_PUBLIC_API_BASE_URL` through a typed helper before using it for API calls. The API also emits safe response headers, keeps CORS explicit, and logs import/section-monitoring events with low-sensitivity metadata only.

Phase 9B documentation clarifies imported academic data privacy, user-triggered import boundaries, data-retention principles, safety logging, and production readiness. Regression tests assert environment validation behavior, safe API headers, prohibited endpoint/action names, extension permission boundaries, no credential-like extraction fields, no background polling primitives, and existing misleading UI wording safeguards.

This phase does not add credentials, secrets, registration automation, polling, portal submission, waitlist automation, seat reservation, seat grabbing, external telemetry, account systems, or production deployment.

## Phase 10A — Release Readiness QA and Final Product Review

Phase 10A prepares the project for final review, demo, and handoff. It adds a release QA matrix, demo-safe scenario guide, final release checklist, and documentation consistency cleanup for Phase 7B through Phase 10A workflows.

Release-readiness docs:

- [Release Readiness QA](docs/RELEASE_READINESS_QA.md)
- [Demo Scenarios](docs/DEMO_SCENARIOS.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)

Phase 10A remains documentation, QA, and safety-review focused. It does not add backend domains, official source ingestion, account systems, credential handling, registration automation, polling, portal submission, waitlist automation, seat reservation, seat grabbing, browser-store publishing, external telemetry, or production deployment.

## Phase 10B — Final Demo Handoff Package

Phase 10B prepares the project for final presentation, review, and continuation by adding a final project summary, demo script, feature inventory, architecture snapshot, known limitations/future work, final safety statement, and handoff checklist.

Final handoff docs:

- [Final Project Summary](docs/FINAL_PROJECT_SUMMARY.md)
- [Final Demo Script](docs/FINAL_DEMO_SCRIPT.md)
- [Feature Inventory](docs/FEATURE_INVENTORY.md)
- [Final Architecture Snapshot](docs/FINAL_ARCHITECTURE_SNAPSHOT.md)
- [Known Limitations and Future Work](docs/KNOWN_LIMITATIONS_AND_FUTURE_WORK.md)
- [Final Safety and Non-Automation Statement](docs/FINAL_SAFETY_AND_NON_AUTOMATION_STATEMENT.md)
- [Handoff Checklist](docs/HANDOFF_CHECKLIST.md)

Phase 10B is documentation, demo readiness, handoff clarity, and safety framing only. It does not add backend domains, database tables, migrations, browser extension behavior, registration workflows, scraping, polling, notification workers, credential handling, or production deployment.

## Phase 11B — Kean Student Portal Academic Import

Phase 11B hardens the local-development extension for a Kean / Ellucian Student Portal workflow under:

```text
https://kean-ss.colleague.elluciancloud.com/Student/*
```

The student opens the official portal, logs in manually, opens the extension, and either extracts the current supported page or starts a guided Kean import. Guided import requests the narrowest Chrome host permission available for the Kean host, then still enforces the `/Student/` prefix and configured page whitelist in code.

Supported Kean page definitions include transcript, degree audit, MyProgress, course catalog, section search, student planning, and schedule pages. The extension extracts only visible academic-planning table fields, shows row counts/warnings/preview, and sends confirmed staging imports to the local API as `source_type = BROWSER_EXTENSION`, `is_official = false`, and `official_application_ready = false`. Backend preview metadata labels Kean imports as `KEAN_STUDENT_PORTAL`, and Phase 7B review remains required.

Phase 11B does not add automatic login, credential collection, cookie/session storage, SAML/MFA bypass, broad crawling, background scraping, polling, portal form submission, registration, add/drop/swap/waitlist automation, seat reservation, seat grabbing, browser-store publishing, official-source ingestion, or real student data.

Guide:

- [Kean Student Portal Import Guide](docs/KEAN_STUDENT_PORTAL_IMPORT_GUIDE.md)

## Final Review and Handoff

Start here for final review:

- [Release Readiness QA](docs/RELEASE_READINESS_QA.md)
- [Demo Scenarios](docs/DEMO_SCENARIOS.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)
- [Final Project Summary](docs/FINAL_PROJECT_SUMMARY.md)
- [Final Demo Script](docs/FINAL_DEMO_SCRIPT.md)
- [Feature Inventory](docs/FEATURE_INVENTORY.md)
- [Final Architecture Snapshot](docs/FINAL_ARCHITECTURE_SNAPSHOT.md)
- [Known Limitations and Future Work](docs/KNOWN_LIMITATIONS_AND_FUTURE_WORK.md)
- [Final Safety and Non-Automation Statement](docs/FINAL_SAFETY_AND_NON_AUTOMATION_STATEMENT.md)
- [Handoff Checklist](docs/HANDOFF_CHECKLIST.md)
- [Kean Student Portal Import Guide](docs/KEAN_STUDENT_PORTAL_IMPORT_GUIDE.md)

## Production readiness checklist

Before any real deployment, complete the focused [Release Checklist](docs/RELEASE_CHECKLIST.md) and verify:

- Environment variables are explicit for the target environment: `ENVIRONMENT`, `DATABASE_URL`, `DATABASE_CONNECT_TIMEOUT_SECONDS`, `CORS_ORIGINS`, and `NEXT_PUBLIC_API_BASE_URL`.
- No `.env` file, real credential, school password, portal token, production database secret, or student record dump is committed.
- Database migrations run cleanly with `cd apps/api && python -m alembic upgrade head` and drift is checked with `cd apps/api && python -m alembic check`.
- OpenAPI artifacts are regenerated and checked with `corepack pnpm openapi:generate` and `corepack pnpm openapi:check`.
- Unit, integration, e2e, type, lint, format, build, and Docker Compose checks pass.
- Security/privacy review confirms imported data stays non-official unless a future reviewed workflow changes that rule.
- Browser extension permissions remain Manifest V3, `activeTab`, `scripting`, `storage`, no broad `host_permissions`, and only the optional Kean host permission for the Phase 11B guided import workflow.
- Manual verification confirms no registration, add/drop, swap, waitlist, seat-state, portal submission, polling, background scraping, credential capture, or hidden automation behavior exists.
- Demo wording uses imported snapshot, advisory alert, manual review required, non-official data, and "verify in the official portal" language for high-impact decisions.

## Quality gates

Run the following before opening a pull request:

```bash
python -m ruff check apps/api
python -m ruff format --check apps/api
corepack pnpm format
git diff --check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm e2e
corepack pnpm openapi:generate
corepack pnpm openapi:check
cd apps/api && python -m alembic upgrade head
cd apps/api && python -m mypy .
cd apps/api && python -m pytest
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

Phase 7B adds `DataImportReviewSession`, `ImportedRecordReview`, `DataApplicationRun`, `AppliedImportedRecord`, and `DataReviewWarning`. These tables preserve review decisions, edited normalized payloads, dry-run/application outcomes, skipped duplicate/unsupported records, and warnings. Application is explicit and limited to internal planning records; it does not mark imported data official.

Phase 8A uses `source_type = BROWSER_EXTENSION` on `DataImportRun` rows to distinguish user-confirmed visible-page extension imports from uploads and mock fixtures. These rows remain non-official staging records and still require Phase 7B review before application.

Phase 8B adds `SectionMonitorTarget`, `SectionMonitorSnapshot`, and `SectionMonitorAlert` as advisory non-official monitoring snapshots. These rows compare user-triggered imports and do not update canonical sections, seats, waitlists, plans, schedules, student records, or registration state.

Phase 9B adds no new domain tables. It hardens configuration, HTTP safety defaults, privacy documentation, audit logging, and regression tests around the existing read-only/advisory workflows.

Phase 10A adds no new domain tables. It documents release QA, demo scenarios, final checklist review, and safety-boundary confirmation for the existing read-only/advisory workflows.

Phase 10B adds no new domain tables. It documents the final demo and handoff package for the existing read-only/advisory workflows.

Phase 11B adds no new domain tables. It labels Kean Student Portal browser-extension staging imports through source-reference and preview metadata while preserving `source_type = BROWSER_EXTENSION`, `is_official = false`, `official_application_ready = false`, and Phase 7B review.

All seed data is mock-only. Mock data is not official university policy, and students must confirm high-impact academic guidance with the school or an advisor.

The project should not jump from Phase 4 directly into automatic registration, waitlist automation, seat-state automation, credential storage, or portal bypass behavior.

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)
- [Release Readiness QA](docs/RELEASE_READINESS_QA.md)
- [Demo Scenarios](docs/DEMO_SCENARIOS.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)
- [Final Project Summary](docs/FINAL_PROJECT_SUMMARY.md)
- [Final Demo Script](docs/FINAL_DEMO_SCRIPT.md)
- [Feature Inventory](docs/FEATURE_INVENTORY.md)
- [Final Architecture Snapshot](docs/FINAL_ARCHITECTURE_SNAPSHOT.md)
- [Known Limitations and Future Work](docs/KNOWN_LIMITATIONS_AND_FUTURE_WORK.md)
- [Final Safety and Non-Automation Statement](docs/FINAL_SAFETY_AND_NON_AUTOMATION_STATEMENT.md)
- [Handoff Checklist](docs/HANDOFF_CHECKLIST.md)
- [Kean Student Portal Import Guide](docs/KEAN_STUDENT_PORTAL_IMPORT_GUIDE.md)
