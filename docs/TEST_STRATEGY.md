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
