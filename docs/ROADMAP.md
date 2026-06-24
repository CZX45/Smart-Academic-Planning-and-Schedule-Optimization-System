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

Status: complete.

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

## Phase 2B: Course Rules and Section Foundation

Status: complete.

Deliverables:

- SQLAlchemy and Alembic models for course offering patterns, course rules, course-rule expression trees, sections, and section meetings.
- Mock sections for fall and spring terms, including in-person, online asynchronous, and hybrid sections.
- Mock lecture and lab meeting records.
- Mock prerequisite, corequisite, major restriction, permission-required, and offering-pattern data clearly labeled as mock.
- Read-only API endpoints for sections, meetings, rules, expression trees, and offering patterns.
- Constraint, seed-idempotency, and API tests.

Testable outcomes:

- Course and section identities remain separate.
- A section can have multiple meeting records.
- Prerequisites and corequisites share the same relational expression model.
- Section-level rules are constrained to the same course and institution as the section.
- Offering patterns are advisory metadata, not official commitments.
- Mock seed data remains source-labeled `MOCK` and `is_official = false`.
- Seed can run repeatedly without increasing record counts.

Deferred from Phase 2B:

- Degree Audit calculation.
- Student eligibility decisions.
- Long-term planning.
- Semester schedule optimization.
- OR-Tools.
- Browser extension work.
- Real school scraping, school login, seat monitoring, or registration automation.

## Phase 3A: Degree Audit Core

Status: complete.

Deliverables:

- `DegreeAuditRun`, `RequirementEvaluation`, `AuditCourseApplication`, and `DegreeAuditWarning` persistence.
- Centralized grade and retake policy.
- Requirement tree evaluator for stored Phase 2A node types.
- Deterministic baseline course-to-requirement allocation.
- Approved transfer, waiver, substitution, and direct equivalency handling.
- Snapshot API under `/api/v1/degree-audits`.
- Read-only mock Degree Progress UI.
- Unit, API, seed, shared schema, and E2E coverage.

Testable outcomes:

- Completed, in-progress, planned, transferred, waived, and failed records are handled correctly.
- One course can be evaluated against multiple candidate requirements.
- Evaluator explains allocations and gaps.
- Pending exceptions produce warnings and do not apply.
- Mock data is clearly identified as non-official.

Deferred from Phase 3A:

- Minor What-if.
- Double-major or multi-program combined audits.
- Global allocation optimization.
- Eligibility engine and prerequisite evaluation.
- Academic planning.
- Section scheduling.
- OR-Tools.

## Phase 3B: What-if and Advanced Allocation

Status: current phase.

Deliverables:

- Persisted `AcademicPlanScenario` snapshots that do not modify `StudentAcademicProgram`.
- Scenario program membership for mock minors, second majors, certificates, concentrations, and change-major candidates.
- Directional `ProgramCombinationRule` storage with max shared credits, minimum unique secondary credits, source metadata, and manual-review behavior.
- Per-scenario, per-program Phase 3A audit runs.
- Deterministic bounded global allocation over Phase 3A audit applications.
- Comparison summaries for shared credits, unique secondary credits, remaining requirement credits, estimated additional credits, unresolved requirements, and manual-review counts.
- Explore Programs / What-if Analysis UI and saved-scenario comparison.

Testable outcomes:

- Scenario creation leaves declared student programs unchanged.
- Missing directional combination rules produce advisor-review warnings instead of guessed policy.
- Shared credits require both requirement `allows_overlap` and a directional combination rule.
- Total earned credits are not duplicated by shared allocations.
- Estimated additional credits are labeled as estimates and never presented as graduation timing.

Deferred from Phase 3B:

- Course Eligibility Engine and prerequisite/corequisite evaluation.
- Multi-term academic planning and earliest-graduation calculation.
- Semester schedule optimization, OR-Tools, time conflicts, seat monitoring, waitlists, browser extension import, real school scraping, and registration automation.

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
