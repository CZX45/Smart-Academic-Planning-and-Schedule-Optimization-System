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

Status: completed.

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

Status: complete.

Deliverables:

- Prerequisite/corequisite expression evaluator over stored `CourseRuleExpression` trees.
- Minimum grade, standing, major, program, campus, permission, and section-rule support.
- Explicit `CURRENT`, `PROJECTED`, and `REGISTRATION` modes.
- Persisted eligibility check snapshots with rule-level and expression-level evidence.
- Blocking, conditional, permission-required, manual-review, and eligible outcomes.
- API endpoints for single, batch, detail, rules, warnings, and student eligibility history.
- Course Eligibility UI with mock disclaimers, expression evidence, warnings, and offline/failure/schema-error states.

Testable outcomes:

- Complex nested prerequisite expressions evaluate deterministically.
- Missing data produces unknown/manual-review warnings, not false certainty.
- Course-level and section-level rules are combined.
- Section seat availability is reported separately from academic eligibility.
- No eligibility check mutates declared programs, course attempts, sections, or registration records.

Deferred from Phase 4:

- Multi-term academic planning and earliest-graduation calculation.
- Semester schedule optimization, OR-Tools, time conflicts, seat monitoring, waitlists, browser extension import, real school scraping, and registration automation.

## Phase 5: Academic Plan Optimizer

Status: current phase, with Phase 5A core planner implemented.

Phase 5A deliverables:

- Course-level long-term planner service under `/api/v1/academic-plans`.
- Persisted `AcademicPlanRun`, term, course, requirement coverage, and warning snapshots.
- `CURRENT_PROGRAM` and `WHAT_IF_SCENARIO` planning modes.
- Credit minimum, preferred, and maximum controls.
- Deterministic prerequisite-unlock and corequisite-pair placement.
- Offering-pattern and closed/cancelled-section warnings without seat monitoring.
- Shared TypeScript schemas/client helpers and a Long-Term Academic Planner UI panel.
- Mock seed cases for prerequisite unlocks, corequisite pairs, closed sections, unknown offering patterns, and what-if planning.

Phase 5A testable outcomes:

- Planner creates repeatable mock course plans without mutating official student records.
- Planner respects maximum credits per term and reports minimum-credit shortfalls.
- Planner keeps weekly schedule conflicts and registration actions out of scope.
- Planner responses include structured warnings, reason codes, and explanations.

Deferred from Phase 5A:

- Earliest-graduation proof with a global optimizer.
- User preference optimization beyond simple credit controls.
- Multi-objective plan ranking and alternative-plan search.
- Semester section schedule optimization, OR-Tools, time conflicts, seat monitoring, waitlists, browser extension import, real school scraping, and registration automation.

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

Status: implemented and CI-verified in Phase 6B.

Phase 6A deliverables:

- Deterministic bounded section-level scheduler under `/api/v1/schedule-optimizations`.
- Persisted `ScheduleOptimizationRun`, constraint set, option, selected section, conflict, and warning snapshots.
- `FROM_DEGREE_AUDIT`, `FROM_LONG_TERM_PLAN`, and `CUSTOM_COURSE_SET` planning modes.
- Time overlap, unavailable block, excluded day, credit range, modality, permission, and eligibility filtering.
- Preference scoring for preferred credits, compactness, fewer days, online/in-person modality, early starts, and late endings.
- Shared TypeScript schemas/client helpers and a Semester Schedule Builder UI panel.
- Mock seed cases for section overlaps, Friday exclusion, online alternatives, and conditional/permission eligibility.

Phase 6B deliverables:

- Persisted advanced preference inputs, including preference weights, course priorities, section priorities, no-gap, morning, afternoon, high-diversity, partial-option, and bounded-search controls.
- Deterministic score breakdowns for credit target, compactness, class days, gap minutes, modality, time-of-day, priorities, and penalties.
- Required-section and excluded-section handling with validation against institution and term scope.
- High-diversity option selection that reduces repeated selected sections while preserving stable ranking.
- Structured repair suggestions for infeasible or partial schedules.
- Shared TypeScript schemas, UI controls, and E2E coverage for advanced schedule preferences.

Phase 6A testable outcomes:

- Scheduler creates repeatable mock section options without mutating official student records, sections, seats, waitlists, or registration data.
- Scheduler records conflicts and warnings for rejected sections and uncertain data.
- Scheduler keeps OR-Tools, seat monitoring, waitlists, browser extension import, real school scraping, and registration automation out of scope.
- Schedule responses include structured explanations, reason codes, warnings, and advisor-confirmation flags where appropriate.

Phase 6B testable outcomes:

- Advanced preferences affect ranking through explainable score components rather than hidden frontend logic.
- High-diversity mode returns stable option differences for near-duplicate section sets.
- Required/excluded section constraints are persisted, validated, and reflected in conflicts or repair suggestions.
- Partial and infeasible results include repair suggestions without performing registration or waitlist actions.

Deferred from Phase 6B:

- OR-Tools CP-SAT or global mathematical schedule optimization.
- Instructor preference data, commute/location optimization, backup schedules, and richer minimal-relaxation search.
- Live section updates, seat monitoring, waitlist handling, browser extension import, real school scraping, and registration automation.

Longer-term deliverables:

- Section-level schedule solver using OR-Tools CP-SAT.
- Time conflict, unavailable block, credit range, no-Friday, earliest/latest, compactness, modality, and instructor preferences.
- Multiple ranked schedules.
- Backup sections and infeasibility explanations.

Testable outcomes:

- Schedule optimizer never selects two sections of the same course unless explicitly allowed.
- Meeting conflicts and unavailable blocks are enforced.
- Preference scores are explainable.

## Phase 7A: Read-only Data Import Foundation

Status: complete.

Deliverables:

- Staging-only data import tables for runs, file metadata, imported records, mapping candidates, validation warnings, and preview summaries.
- Bounded CSV/JSON parser support for unofficial transcript, degree audit export, catalog, section schedule, and generic mock/student-provided records.
- Read-only `/api/v1/data-imports` endpoint family for create, detail, records, mapping candidates, warnings, preview, validation, and student import history.
- Mock seed import preview fixture with non-official source metadata.
- Shared TypeScript schemas/client helpers and Data Import Preview UI panel.
- Documentation and tests proving imports do not apply records to official academic-domain tables.

Testable outcomes:

- Import previews preserve source metadata, checksum, parser version, normalized payload snippets, mapping explanations, warning codes, advisor-confirmation flags, and non-official disclaimers.
- Official-source imports are rejected in Phase 7A.
- No import flow writes to `student_course_attempts`, `courses`, `sections`, requirements, seat counts, waitlists, advisor approval, or registration data.
- Browser extension import, real school login, SAML/MFA/CAPTCHA, scraping, OCR-heavy extraction, seat monitoring, automatic registration, and waitlist actions remain out of scope.

Deferred from Phase 7A:

- Applying reviewed imports to domain tables.
- Real school data connectors.
- Browser extension workflows.
- Advisor approval queues.
- OCR-heavy document extraction.
- Automatic registration, add/drop/swap, seat monitoring, and waitlist handling.

## Phase 7B: Data Review & Confirmation Workflow

Status: current phase.

Deliverables:

- Review-session, imported-record-review, application-run, applied-record, and review-warning tables.
- Explicit review decisions: unreviewed, confirmed, rejected, needs advisor review, edited and confirmed, and deferred.
- `/api/v1/data-import-reviews` endpoint family for create, detail, records, decision updates, dry-run/apply, application logs, warnings, application detail, and student review history.
- `DataReviewApplicationService.apply_review_session(...)` with dry-run support, duplicate prevention, source metadata preservation, and skipped-record reason codes.
- Non-official internal `student_course_attempts` application for confirmed unofficial transcript course attempts only.
- Shared TypeScript schemas/client helpers and Data Review & Confirmation UI panel.
- Mock seed scenarios and tests for edited records, advisor review, unsupported data, duplicate skip, dry-run, and application logs.

Testable outcomes:

- GET endpoints never apply data.
- Dry-run does not write domain records.
- Real apply requires explicit POST and audits every applied or skipped record.
- Duplicate, rejected, deferred, unsupported, unknown-course, advisor-review, and unsupported-grade records are skipped with reason codes and warnings.
- Browser extension import, real school login, scraping, seat monitoring, automatic registration, add/drop/swap, and waitlist handling remain out of scope.

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
