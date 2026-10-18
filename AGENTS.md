# AGENTS.md

## Scope and Priority
These rules apply to the entire repository. More specific `AGENTS.md` files may be added in subdirectories; direct user/developer instructions take precedence.

## Project Goal
Build a school-agnostic Smart Academic Planning and Schedule Optimization System: a multi-school, multi-campus, multi-program platform for degree progress analysis, academic plan optimization, and section-level schedule optimization.

Core goals:
- Represent institutions, campuses, catalog years, effective terms, program versions, courses, sections, student records, and source metadata as first-class concepts.
- Evaluate degree requirements, prerequisites, corequisites, restrictions, eligibility, GPA, credits, course statuses, and optimizer decisions in deterministic, explainable, testable ways.
- Keep academic-plan optimization separate from semester section-schedule optimization.
- Make every recommendation, warning, infeasibility result, and optimization decision traceable through an `explanation`, `reason_code`, or equivalent structured reason.

## Non-Goals and Safety Boundaries
- Do not build automatic registration, add/drop, swap, waitlist, seat-grabbing, or high-frequency polling features.
- Do not store school account passwords or secrets from student portals.
- Do not bypass or automate around SAML, MFA, CAPTCHA, rate limits, school authentication, authorization, or access controls.
- Browser extension work must be limited to pages the user has already logged into, actively opened, and explicitly asked the extension to inspect.
- Do not present mock, inferred, scraped, or unreviewed data as official school policy.
- High-risk academic guidance must tell students to confirm with the school or an advisor.

## Monorepo Structure
Use the following long-term layout unless an architecture document is updated first:

```text
apps/
  web/                 # Next.js student/advisor UI
  api/                 # FastAPI backend and API boundary
  extension/           # Chrome Extension Manifest V3
packages/
  shared/              # Shared TypeScript types, generated API clients, validators
  fixtures/            # Mock/source-tagged catalogs, programs, transcripts, sections
  config/              # Shared TS/ESLint/Vitest/formatting config
services/
  optimizer/           # Python planning/scheduling optimization modules/services
infra/
  docker/              # Dockerfiles, compose files, local infrastructure helpers
docs/                  # Architecture, data model, domain rules, security, testing, decisions
```

Canonical component locations:
- Frontend: `apps/web`.
- Backend API: `apps/api`.
- Browser extension: `apps/extension`.
- Shared TypeScript types and API clients: `packages/shared`.
- Optimizer domain modules: `services/optimizer` or backend-owned Python modules while the service is not extracted.
- Fixtures and mock data: `packages/fixtures`.

## Required Commands
Run the relevant commands before completing a task. If a package has not been scaffolded yet, report the command as not available rather than inventing a substitute.

Preferred workspace commands once tooling exists:
- Install dependencies: `pnpm install`
- Local development: `pnpm dev`
- Build: `pnpm build`
- Tests: `pnpm test`
- Lint: `pnpm lint`
- Format: `pnpm format`
- TypeScript type-check: `pnpm typecheck`
- Python tests: `pytest`
- Python lint: `ruff check .`
- Python format check/apply: `ruff format --check .` / `ruff format .`
- Python type-check: `mypy .`
- E2E tests: `pnpm exec playwright test`

During documentation-only phases, at minimum inspect Markdown and run repository-appropriate checks such as `git diff --check` and `git status --short`.

## Architecture and Domain Rules
- Model `Course` and `Section` as separate entities.
- Model degree requirements as versioned rule trees, not static hard-coded course lists.
- Model prerequisites, corequisites, restrictions, and eligibility as composable logical expression trees.
- Core domain logic must not live inside UI components. UI components may render state and call typed application/domain services, but rule evaluation, allocation, eligibility, GPA, credit, course-status, planning, and scheduling logic belong in domain modules with tests.
- Do not hard-code any specific school's curriculum, catalog, program map, or requirement sheet into a generic engine. School-specific data must be source-tagged, versioned fixture/seed/import data or official reviewed data.
- All amount, GPA, credit, requirement-status, course-status, and progress calculations must be deterministic, repeatable, and directly unit-testable.
- Longer domain rules belong in `docs/DOMAIN_RULES.md`, `docs/DATA_MODEL.md`, and `docs/ARCHITECTURE.md`; reference those docs instead of duplicating large rule descriptions here.

## Data and School-Rule Accuracy
- Use mock data and fixtures when verified school source data is unavailable.
- Every official or imported rule must preserve institution, campus, catalog year, effective term, program version, source document, retrieval/import timestamp, and confidence level.
- Do not use unverified school rules for authoritative recommendations. If data is mock, inferred, student-provided, or ambiguous, responses must expose that uncertainty and require advisor/school confirmation for high-impact guidance.
- If a recurring data/rule mistake appears, update this file or the relevant design document to prevent the same error from recurring.

## Database and Migration Rules
- PostgreSQL is the target database.
- All database schema changes must include a matching migration in the backend migration system.
- Migrations must be reviewable, deterministic, and safe for existing data. Include data migrations only when necessary and document assumptions.
- Schema changes that affect API contracts, fixtures, domain rules, or docs must update those artifacts in the same change.
- Add migration tests or repository/API tests for important schema behavior when migrations are introduced.

## API Design Rules
- OpenAPI is the source of truth for frontend/backend integration.
- API request and response schemas must be typed and validated, preferably with Pydantic on the backend and generated/shared TypeScript types for clients.
- All mutating endpoints must validate tenant, user, institution/campus scope, authorization, and data ownership.
- Long-running optimizer endpoints should be asynchronous or job-based when solving can exceed normal request timeouts.
- Recommendation and optimizer responses must include structured explanations such as `explanations`, `reason_codes`, `assumptions`, `warnings`, and `source_references` where available.
- Do not leak sensitive student data in logs, errors, analytics, or client-visible debugging output.

## TypeScript Rules
- TypeScript strict mode is required for frontend, extension, shared packages, generated clients, and test utilities.
- Do not weaken strictness (`strict`, `noImplicitAny`, null checks, etc.) to make code compile.
- Avoid `any`; use unknown narrowing, typed schemas, or generated API types.
- Keep shared types in `packages/shared`; do not duplicate API/domain types across apps.
- Do not put import-level `try`/`catch` blocks around imports.

## Python Rules
- Python code must be typed and compatible with mypy checking.
- Use Pydantic for API boundary validation and typed domain models where appropriate.
- Use Ruff for linting and formatting.
- Avoid untyped public functions in domain, optimizer, repository, and API boundary modules.
- Do not hide import failures with import-level `try`/`except` blocks.

## Testing Requirements
- Add or update tests for every implemented rule, parser, optimizer constraint, API boundary, migration, and non-trivial calculation.
- All rule-engine functionality must have deterministic unit tests.
- Optimizer tests must cover both feasible outputs and infeasibility explanations.
- Prefer fixtures and golden tests before integrating real school data.
- Use Vitest for TypeScript unit tests, pytest for Python tests, and Playwright for E2E workflows when implemented.
- Before finishing a task, run the relevant tests, lint, and type checks; report any command that cannot run and why.

## Documentation Requirements
- Keep documentation and implementation aligned.
- All new features must update relevant docs, such as `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/DOMAIN_RULES.md`, `docs/SECURITY_AND_PRIVACY.md`, `docs/TEST_STRATEGY.md`, or `docs/DECISIONS.md`.
- For substantial architecture changes, add or update a decision record in `docs/DECISIONS.md`.
- Do not duplicate long domain-policy text in this file; link or point to the relevant `docs/` document.

## Development Practices
- Use `rg` instead of recursive grep; do not use `ls -R`.
- Keep changes small, reviewable, and aligned with the project mission.
- Do not mix unrelated refactors with feature or documentation changes.
- Preserve explainability and source metadata when touching planner, audit, schedule, or rule logic.
- If the same error or confusion repeats, update `AGENTS.md` or a relevant design document as part of the fix.

## Completion Report Requirements
Every completed task report must include:
- Modified files.
- Tests/checks executed, with exact commands.
- Unresolved issues or follow-up work.
- Assumptions used.

## Pull Request Notes
PR descriptions should include:
1. Summary of changes.
2. Testing performed.
3. Known risks or follow-up work.
4. Whether any mock data was added or changed.
