# Roadmap

## Phase 0: Documentation and Architecture Foundation

Status: complete.

Deliverables:

- Repository assessment.
- Product requirements.
- Architecture proposal.
- Data model draft.
- Domain rules draft.
- Security and privacy plan.
- Roadmap and test strategy.
- Architecture decision log.

Exit criteria:

- Required documentation files exist.
- MVP and non-goals are explicit.
- Core domain boundaries are defined.

## Phase 1: Monorepo and Tooling Scaffold

Status: complete.

Deliverables:

- pnpm workspace and Turborepo configuration.
- `apps/web` Next.js TypeScript app.
- `apps/api` FastAPI app.
- Docker Compose with PostgreSQL.
- Ruff, mypy, pytest, ESLint, Vitest, Playwright setup.
- CI-like local commands.
- OpenAPI generation baseline.

Testable outcomes:

- Web app starts locally.
- API health endpoint works.
- Database migrations run.
- Lint/type/test commands execute.

## Phase 2A: Academic Domain Foundation

Status: current phase.

Deliverables:

- SQLAlchemy and Alembic models for institutions, campuses, terms, programs, program versions, courses, course equivalencies, requirement trees, student programs, course attempts, transfer credits, waivers, and substitutions.
- Deterministic mock seed for Mock University, Mock Main Campus, Mock BS Finance 2024, mock courses, a mock requirement tree, and a mock student record.
- Read-only `/api/v1` endpoints for institutions, programs, program requirements, courses, students, and course attempts.
- Constraint, seed-idempotency, and API tests.

Testable outcomes:

- Course and section identities remain separate; Phase 2A implements courses only.
- Program identity and program version/catalog-year identity are separate.
- Requirement trees are relational adjacency lists with course options.
- Mock data is source-labeled `MOCK` and `is_official = false`.
- Seed can run repeatedly without increasing record counts.

Deferred from Phase 2A:

- Degree Audit calculation.
- Requirement completion status.
- Minor comparison and what-if calculation.
- Prerequisite parsing and eligibility.
- Course sections and meeting times.
- Academic plan optimization and semester schedule optimization.

## Phase 2B: Core Domain Schemas and Mock Fixtures

Deliverables:

- Pydantic and SQLAlchemy models for institutions, courses, sections, programs, requirements, expression trees, and student records.
- Mock Kean/WKU-like fixture dataset clearly labeled as mock.
- Fixture loader and validation tests.
- API endpoints for reading catalog, program, and student fixture data.

Testable outcomes:

- Fixtures validate against schemas.
- Mock degree program is source-labeled as mock.
- Course and section identities remain separate.

## Phase 3: Degree Audit Engine

Deliverables:

- Requirement tree evaluator.
- Course status handling.
- Candidate course-to-requirement allocation.
- Requirement status summaries.
- Explainability payloads.
- Unit and golden-file tests.

Testable outcomes:

- Completed, in-progress, planned, transferred, waived, and failed records are handled correctly.
- One course can be evaluated against multiple candidate requirements.
- Evaluator explains allocations and gaps.

## Phase 4: Eligibility Engine

Deliverables:

- Prerequisite/corequisite expression evaluator.
- Minimum grade, standing, major, program, campus, and section restriction support.
- Blocking/warning/unknown/manual-review statuses.
- API endpoint for eligibility checks.

Testable outcomes:

- Complex nested prerequisite expressions evaluate deterministically.
- Missing data produces unknown/manual-review warnings, not false certainty.

## Phase 5: Academic Plan Optimizer

Deliverables:

- Course-level multi-semester planning engine.
- Credit limit constraints.
- Prerequisite ordering.
- Term availability assumptions.
- Requirement coverage objective.
- Infeasibility explanations.

Testable outcomes:

- Planner generates feasible mock graduation paths.
- Planner explains why impossible targets are impossible.

## Phase 6: Semester Schedule Optimizer

Deliverables:

- Section-level schedule solver using OR-Tools CP-SAT.
- Time conflict, unavailable block, credit range, no-Friday, earliest/latest, compactness, modality, and instructor preferences.
- Multiple ranked schedules.
- Backup sections and infeasibility explanations.

Testable outcomes:

- Schedule optimizer never selects two sections of the same course unless explicitly allowed.
- Meeting conflicts and unavailable blocks are enforced.
- Preference scores are explainable.

## Phase 7: Product UI MVP

Deliverables:

- Student dashboard.
- Degree progress visualization.
- Course history editor/import draft UI.
- Academic plan view.
- Schedule preference form.
- Schedule candidate comparison.
- Advisor-confirmation warnings.

Testable outcomes:

- User can complete an end-to-end mock planning workflow.
- Playwright covers the happy path and common infeasibility path.

## Phase 8: Browser Extension Import Assistant

Deliverables:

- Manifest V3 extension scaffold.
- User-triggered extraction for active My Progress / course-search pages.
- Preview and confirmation flow.
- No credential storage and no registration automation.

Testable outcomes:

- Extension reads only active pages after user action.
- Extracted data is marked as user-provided or imported draft until validated.

## Phase 9: Real Data Onboarding and Advisor Workflow

Deliverables:

- Official source ingestion process.
- Program version comparison tools.
- Advisor review and comments.
- Exportable plan summaries.
- Data-quality dashboards.

Testable outcomes:

- Official source data includes source references and confidence levels.
- Advisor can approve, reject, or comment on a plan.

## Deferred / Future

- Seat-change notifications with safe refresh limits.
- GPA scenario analysis.
- Tuition estimation.
- Course workload balancing.
- Calendar export.
- Multi-institution admin tooling.
- Production FERPA workflows and data agreements.
