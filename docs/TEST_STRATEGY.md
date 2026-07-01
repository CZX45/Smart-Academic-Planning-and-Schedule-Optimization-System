# Test Strategy

## 1. Testing Goals

Testing must prove that academic rules are correct, explainable, versioned, and safe. The most important tests are deterministic domain tests for degree audit, eligibility, planning, and schedule optimization.

## 2. Test Pyramid

### Unit Tests

Python `pytest` tests for:

- Requirement rule node evaluation.
- Course allocation decisions.
- Prerequisite and restriction expression evaluation.
- GPA, credit, upper-level, and residency calculations.
- Academic plan constraints.
- Schedule conflict detection and preference scoring.

TypeScript `Vitest` tests for:

- Shared type guards and API client helpers.
- UI utility logic.
- Extension parser helpers when implemented.

### Integration Tests

- API endpoint tests using FastAPI test client.
- Database repository tests against PostgreSQL in Docker.
- Fixture loading and migration tests.
- OpenAPI contract tests between backend and generated frontend client.

Phase 2A adds SQLite-backed constraint tests for the SQLAlchemy metadata, deterministic mock seed idempotency tests, and FastAPI read-only `/api/v1` endpoint tests. PostgreSQL migration execution and Docker-based seed double-run remain part of CI when local Docker is unavailable.

Phase 2B extends those tests to course offering patterns, course rules, rule expression trees, sections, and section meetings. SQLite-backed tests cover model constraints and tree-shape validation; CI remains responsible for PostgreSQL Alembic execution, Docker Compose startup, and double-run seed idempotency against PostgreSQL.

Phase 3A adds deterministic Degree Audit coverage:

- Pure policy tests for grade ordering, pass/fail handling, unknown grades, and incomplete attempts.
- SQLite-backed model tests for audit snapshot constraints, one evaluation per requirement node, application source constraints, and nonnegative credit summaries.
- Seed tests for completed, in-progress, planned, low-grade, approved/pending transfer, approved/pending waiver, approved/rejected substitution, retake, upper-level, residency, total-credit, and manual-review fixtures.
- FastAPI tests for audit creation, retrieval, requirements, warnings, latest audit, invalid modes, 404s, and response schema shape.
- Shared TypeScript schema tests for audit run, requirement, application, and warning responses.
- Playwright tests for the Degree Progress UI shell, mock-policy warning, API failure, empty/error states, and schema-error handling.

Phase 3B adds deterministic what-if scenario coverage:

- Scenario lifecycle tests for creation, multiple scenarios per student, failure safety, and no mutation of `StudentAcademicProgram`.
- Program-combination tests for exactly one primary major, duplicate program rejection, institution scope, change-major candidates, and missing directional policy warnings.
- Combination-rule tests for maximum shared credits, minimum unique credits, directional policy, nonnegative values, same-program rejection, and mock/non-official metadata.
- Allocation tests proving global search can beat a local greedy choice, overlap requires both requirement and combination policy, shared credits do not double earned credits, unique secondary credits are tracked, deterministic tie-breakers are stable, and search limits warn.
- API tests for scenario creation, retrieval, programs, audits, allocations, warnings, comparison, student scenario list, compare endpoint, 404, invalid combinations, and schema validation.
- Shared TypeScript schema tests for scenario, scenario program, allocation, warning, and comparison responses.
- Playwright tests for selecting a mock candidate program, creating a scenario, displaying shared/unique/additional credits, warnings, mock-policy disclaimers, comparing saved scenarios, API failure, and schema-error handling.

Phase 4 adds deterministic course eligibility coverage:

- SQLite-backed model tests for eligibility check runs, rule evaluations, expression evaluations, warnings, uniqueness, and course/section consistency.
- Engine tests for completed prerequisite pass, hard missing prerequisite failure, projected and registration conditional evidence, explicit concurrent corequisite plans, section-level permission rules, no stored restrictions, and section availability separation.
- API tests for single check creation, detail, rules, warnings, student check list, batch checks, invalid section/course pairs, batch limits, 404s, and schema validation.
- Shared TypeScript schema tests for eligibility check, rule, expression, reason, warning, corequisite, availability, and schema-error responses.
- Playwright tests for Course Eligibility UI success, mock disclaimers, API offline/failure/empty/schema-error states, permission-required display, and seat availability separation.

Phase 5A adds deterministic long-term academic planner coverage:

- SQLite-backed model tests for plan runs, terms, planned courses, requirement coverage, warnings, uniqueness, credit constraints, and what-if scenario requirements.
- Engine tests for current-program planning, what-if planning without official declaration mutation, prerequisite-unlock ordering, corequisite pairing, maximum-credit enforcement, minimum-credit warnings, horizon shortfalls, unknown offering patterns, and closed/cancelled section warnings.
- API tests for plan creation, detail, terms, courses, warnings, student plan list, compare endpoint, invalid credit settings, 404s, and schema validation.
- Seed tests for mock planner source markers and cases covering prerequisite, corequisite, closed section, no offering pattern, and what-if candidate data.
- Shared TypeScript schema tests for academic plan run, term, course, coverage, warning, detail, comparison, and schema-error responses.
- Playwright tests for Long-Term Academic Planner UI success, required disclaimers, term-by-term output, requirement coverage, warnings, saved-plan comparison, API offline/failure/empty/schema-error states, and the absence of registration or weekly-conflict claims.

Phase 6A adds deterministic semester schedule optimizer coverage:

- SQLite-backed model tests for schedule runs, constraint sets, options, option sections, conflicts, warnings, uniqueness, credit constraints, and snapshot persistence.
- Engine tests for no-Friday constraints, unavailable blocks, time-overlap conflicts, online/in-person preference scoring, minimum-credit partial results, maximum-credit hard limits, permission-required blocking, and advisor-confirmation warnings.
- API tests for schedule creation, detail, options, conflicts, warnings, student schedule list, compare endpoint, invalid credit settings, 404s, and schema validation.
- Seed tests for mock section cases covering overlapping meetings, Friday exclusion, online alternatives, permission-required sections, and conditional eligibility.
- Shared TypeScript schema tests for schedule run, constraint set, option, selected section, meeting, conflict, warning, detail, comparison, and schema-error responses.
- Playwright tests for Semester Schedule Builder UI success, required disclaimers, ranked options, conflicts, warnings, saved-schedule comparison, API offline/failure/empty/schema-error states, and the absence of registration or waitlist actions.

Phase 6B extends deterministic semester schedule optimizer coverage:

- Engine tests for preference weights, course priorities, section priorities, no-gap scoring, morning/afternoon scoring, high-diversity option selection, required/excluded section validation, partial-option behavior, and repair suggestions.
- API tests for persisted advanced constraint fields, score breakdowns, diversity metadata, hard-constraint summaries, soft-preference summaries, repair suggestions, and invalid weight/search-bound validation.
- Seed tests for mock near-duplicate sections, morning versus afternoon options, online versus in-person alternatives, required/excluded section examples, infeasible hard-constraint cases, and partial repair demonstrations.
- Shared TypeScript schema tests for advanced schedule request fields, score breakdowns, repair suggestions, hard-constraint summaries, and soft-preference summaries.
- Playwright tests for advanced schedule controls, mock-data disclaimers, score breakdown rendering, option comparison, diversity metadata, repair suggestions, and the absence of registration, add/drop, or waitlist actions.

Phase 7A adds read-only data import preview coverage:

- SQLite-backed model tests for data import runs, files, imported records, mapping candidates, validation warnings, preview summaries, nonnegative counts, confidence ranges, unique row numbers, explanations, and official-source rejection.
- Service tests for bounded CSV/JSON parsing, course-code normalization, exact mock catalog matching, unmatched-course warnings, staging-only disclaimers, and no mutation of `StudentCourseAttempt`, `Course`, `Section`, requirement, seat, waitlist, or registration tables.
- API tests for import creation, detail, records, mapping candidates, warnings, preview, validation, student import list, 404s, official-source rejection, and schema validation.
- Seed tests for mock data import staging rows, warnings, preview summary, source metadata, non-official flags, and idempotency.
- Shared TypeScript schema tests for import run, imported record, mapping candidate, warning, preview, and create helper responses.
- Playwright tests for the Data Import Preview panel, required non-official disclaimers, staged records, mapping candidates, warnings, saved import loading, API failure, and schema-error states.

Phase 7B adds data review and confirmation coverage:

- Service/API tests for review creation, per-record decisions, dry-run application without domain writes, explicit apply into non-official internal course attempts, duplicate skips, warnings, and student review/application indexes.
- Seed tests for review sessions, edited-and-confirmed records, advisor-review skips, duplicate application logs, unsupported-grade warnings, non-official status, and idempotency.
- Shared TypeScript schema tests for review sessions, record reviews, application runs, applied-record logs, warnings, dry-run results, decision patching, and apply helpers.
- Playwright tests for the Data Review & Confirmation panel, create review, confirm/reject/defer/advisor-review controls, simple grade edit, dry-run output, explicit apply output, warnings, and application logs.

Phase 8A adds read-only browser extension import coverage:

- TypeScript extractor tests for transcript tables, degree-audit tables, course-catalog tables, section-search tables, unknown pages, empty tables, malformed rows, unknown columns, deterministic output, and password-field exclusion.
- Extension policy tests for Manifest V3, minimal permissions, no broad host permissions, no credential capture, no portal form submission, no background scraping, and confirmation-gated import sending.
- Backend/API tests proving `source_type = BROWSER_EXTENSION` imports stay non-official, keep `official_application_ready = false`, preserve source metadata, and enter Phase 7A staging.
- Shared TypeScript tests for browser-extension import handoff requests.
- Playwright coverage that Browser Extension Import appears in the web UI with staging-only, review-required, and no-registration messaging.

### End-to-End Tests

Playwright tests for:

- Student creates or loads a mock profile.
- Student views degree progress.
- Student simulates a minor or added program.
- Student generates an academic plan.
- Student generates schedules with preferences.
- System explains infeasibility when constraints are impossible.

## 3. Golden Fixtures

Maintain versioned fixtures for:

- Mock catalog.
- Mock BS Finance-like program.
- Mock GE requirements.
- Mock transcript with completed, in-progress, planned, failed, transferred, and waived courses.
- Mock sections with conflicts, full sections, online sections, and campus restrictions.
- Expected audit outputs and explanations.

Fixtures must clearly indicate `confidence_level: mock` unless based on official reviewed data.

## 4. Domain Test Matrix

| Area | Examples |
| --- | --- |
| Requirement status | satisfied, partially satisfied, in_progress, planned, unsatisfied |
| Course status | completed, in_progress, planned, failed_or_insufficient_grade, transferred, waived |
| Allocation | course eligible for major elective and GE; overlap limited by policy |
| Prerequisites | all-of, any-of, min grade, in-progress prereq, missing data |
| Restrictions | campus, major, class standing, permission required |
| Planner | impossible target term, prerequisite chain, credit overload |
| Scheduler | time conflict, no-Friday, latest end, unavailable block, online preference |
| Risk | missing source data, offering frequency uncertainty, advisor confirmation |

Phase 2A covers storage-level safety before evaluator behavior exists:

- Institution, campus, course, and program-version uniqueness.
- Requirement parent/version integrity and no self-parenting.
- Requirement course option uniqueness.
- Course equivalency and substitution no-self constraints.
- Active primary-major uniqueness.
- Course attempt retake preservation and positive attempt numbers.
- Transfer/waiver/substitution approval status storage.
- Mock seed idempotency and non-official source metadata.
- Basic API success and 404 responses.

Phase 2B covers additional storage and API safety:

- Course offering pattern uniqueness and mock/non-official metadata.
- Course-level and section-level rule scope constraints.
- Section rule course/institution consistency.
- Rule expression single-root, parent-same-rule, no-self-parent, leaf-operand, and tree-shape validation.
- Section uniqueness by institution, term, course, and section code.
- Section capacity, available-seat, modality, and cancelled-record storage.
- Section meeting time/date validity and multiple meetings per section.
- Seed idempotency for Phase 2A and Phase 2B data together.
- Read-only API coverage for section filters, section detail, meetings, rules, expression trees, offering patterns, 404, invalid filters, and OpenAPI generation.

Phase 3A covers audit behavior:

- `CURRENT` and `PROJECTED` modes keep completed, in-progress, and planned contributions separate.
- Grade policy is centralized and warns on pass/fail or unknown cases.
- Retakes preserve all attempts and use the best valid completed attempt.
- Approved transfer applies and pending transfer warns.
- Approved waiver satisfies without adding credits.
- Approved substitution applies only to the target requirement.
- Baseline allocation avoids unapproved double counting.
- Manual-review requirements are not treated as satisfied.

Phase 3B covers scenario behavior:

- Scenario snapshots do not edit official declarations.
- Per-program audits reuse Phase 3A snapshots.
- Directional combination rules are required for shared credit.
- Missing overlap policy is a warning, not a guessed rule.
- Requirement application, shared credit, and total earned credit remain separate.
- Estimated additional credits are estimates and never graduation-timing predictions.

Phase 4 covers course eligibility behavior:

- `CURRENT`, `PROJECTED`, and `REGISTRATION` modes are explicit and deterministic.
- Completed evidence reuses centralized grade policy and status semantics.
- In-progress, planned, and concurrent corequisite evidence remains conditional.
- Course-level and section-level rules are combined.
- Permission-required and manual-review results are traceable to expression evidence.
- Section status and seat counts are reported separately from academic eligibility.
- Mock and missing-rule data always carries warnings rather than official-policy certainty.

Phase 5A covers academic planner behavior:

- `CURRENT_PROGRAM` and `WHAT_IF_SCENARIO` modes create snapshots without mutating declarations.
- Remaining requirement candidates come from Degree Audit results, not duplicated frontend logic.
- Prerequisite and corequisite decisions reuse Course Eligibility evidence where available.
- Planned prerequisite evidence stays conditional.
- Maximum credit limits are hard placement limits; minimum-credit failures become warnings.
- Offering patterns are assumptions and never official commitments.
- Planner output remains course-level and does not select sections, inspect weekly conflicts, poll seats, or register.

Phase 6A covers semester schedule optimizer behavior:

- `FROM_DEGREE_AUDIT`, `FROM_LONG_TERM_PLAN`, and `CUSTOM_COURSE_SET` modes create snapshots without mutating declarations, attempts, sections, seats, waitlists, or registration data.
- Candidate courses can come from an audit, a long-term plan, or an explicit mock course set.
- Hard constraints reject overlapping meetings, unavailable blocks, excluded days, duplicate course sections, blocked eligibility, and credit overloads.
- Partial results and infeasibility produce structured conflicts, warnings, and explanations.
- Preference scoring is deterministic and explainable.
- Scheduler output remains section-level and does not poll seats, join waitlists, add, drop, swap, or register.

Phase 6B covers advanced schedule optimizer behavior:

- Required sections and excluded sections are hard constraints with institution/term validation.
- Preference weights, priorities, no-gap, morning, afternoon, modality, compactness, and class-day preferences are soft scoring inputs with persisted explanations.
- Score breakdowns sum to deterministic ranking inputs and expose penalties separately from positive preference components.
- High-diversity mode changes returned option selection only through deterministic section-overlap comparison.
- Repair suggestions explain feasible constraint relaxations without automating registration, seat monitoring, add/drop, swap, or waitlist behavior.

Phase 7A covers read-only data import behavior:

- Import runs are staging-only and never become official academic records.
- Metadata-only file storage preserves checksum, file name, MIME type, source metadata, parser version, counts, and preview disclaimers.
- Parsed records preserve row numbers, normalized payloads, record type, status, confidence, and raw labels.
- Mapping candidates include target type, optional target ID, match type, confidence, selection flag, reason code, and explanation.
- Validation warnings are emitted for staging-only use and ambiguous/unmatched data.
- API and UI flows do not perform real school login, browser extension import, scraping, OCR-heavy extraction, registration, seat polling, waitlist handling, or official table writes.

Phase 7B covers reviewed application behavior:

- Dry-run application must not create `student_course_attempts` or application-run rows.
- Real application must require explicit POST and must audit every applied or skipped record.
- Confirmed unofficial transcript course attempts may create internal `student_course_attempts` only with `is_official = false` and source metadata.
- Duplicate, rejected, deferred, unsupported, unknown-course, unsupported-grade, and advisor-review records must be skipped with reason codes and warnings.

Phase 8A covers browser-extension import behavior:

- Extraction reads visible table text only after user action and never reads password-field values.
- Extracted data is deterministic and compatible with existing staging import formats.
- Browser-extension imports use `source_type = BROWSER_EXTENSION`, `is_official = false`, and `official_application_ready = false`.
- Unknown or malformed visible page data produces warnings, not crashes.
- Extension handoff requires preview and explicit user confirmation before sending.
- Extension code does not include credential storage, SAML/MFA bypass, background scraping, live polling, portal submission, registration automation, add/drop/swap, waitlist automation, or seat grabbing.

## 5. Property and Constraint Tests

For optimizers, add property-like tests:

- No schedule candidate contains overlapping required meetings.
- No schedule candidate violates hard unavailable blocks.
- Credit totals are within hard bounds.
- Academic plans respect prerequisite ordering.
- Increasing allowed constraints should not reduce feasibility for the same data unless objective changes intentionally.

## 6. Regression Testing

Every official catalog/program version should have:

- Source fixtures.
- Expected degree audit outputs.
- Known edge cases.
- Regression tests for prior defects.

## 7. Manual QA

Manual QA should focus on:

- Explanation clarity.
- Advisor-confirmation warnings.
- Mock vs official labeling.
- Accessibility and mobile usability.
- Browser extension permission prompts when implemented.

## 8. Quality Gates

Expected commands once tooling is scaffolded:

- `pnpm lint`
- `pnpm test`
- `pnpm typecheck`
- `pytest`
- `ruff check .`
- `mypy .`
- `playwright test`

During the documentation-only phase, basic repository checks are limited to file existence, Markdown review, and Git status.
