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
