# Architecture Decision Log

## ADR-0001: Use a documentation-first implementation phase

Status: Accepted

Context: The repository started empty, while the requested product has high domain complexity and high academic-risk consequences.

Decision: Create product, architecture, data model, rule, security, roadmap, and test strategy documents before implementing application code.

Consequences:

- Shared understanding is established before code.
- MVP boundaries and non-goals are explicit.
- Later implementation can be tested against documented expectations.

## ADR-0002: Use a monorepo with pnpm workspace / Turborepo

Status: Proposed

Context: The product needs a Next.js web app, FastAPI backend, Chrome extension, shared TypeScript types, fixtures, and infrastructure configuration.

Decision: Use a monorepo so contracts, fixtures, documentation, and app code evolve together.

Consequences:

- Easier local development and cross-package testing.
- Requires clear task orchestration between Node and Python tooling.

## ADR-0003: Separate Course and Section entities

Status: Accepted

Context: Degree requirements and prerequisites apply primarily to courses, while schedules and instructors apply to sections.

Decision: Model `Course` and `Section` separately.

Consequences:

- Academic planning can happen without exact section data.
- Semester scheduling can select concrete sections after course planning.

## ADR-0004: Model degree requirements as rule trees

Status: Accepted

Context: Degree requirements include nested GE, major, elective, credit, GPA, upper-level, residency, and overlap policies.

Decision: Use versioned requirement rule trees rather than fixed arrays of courses.

Consequences:

- Supports multiple schools and catalog years.
- Requires a robust evaluator and golden fixtures.

## ADR-0005: Model prerequisites and restrictions as expression trees

Status: Accepted

Context: Eligibility rules can combine completed courses, minimum grades, standing, campus, major, permission, and corequisites.

Decision: Use composable logical expression trees for prerequisites, corequisites, and restrictions.

Consequences:

- Complex rules are expressible and testable.
- Unknown or manual-review outcomes can be represented explicitly.

## ADR-0006: Separate Academic Plan Optimizer and Semester Schedule Optimizer

Status: Accepted

Context: Long-range graduation planning and single-term section scheduling solve different problems at different levels of detail.

Decision: Keep course-level academic planning separate from section-level schedule optimization.

Consequences:

- Cleaner domain boundaries.
- Easier testing and explanation.
- Enables future scaling of optimizers independently.

## ADR-0007: Never store school credentials or automate registration in MVP

Status: Accepted

Context: Credential handling and registration automation create major privacy, legal, and operational risk.

Decision: Do not store school credentials, bypass authentication, or automate registration/drop actions. Browser extension reads only active user-opened pages after explicit user action.

Consequences:

- Lower security and compliance risk.
- Users remain responsible for official registration in school systems.

## ADR-0008: Use mock fixtures until official data is provided

Status: Accepted

Context: Verified Kean/WKU catalog, My Progress, and section data may not be available during early development.

Decision: Continue development using clearly labeled mock data and fixtures. Do not claim mock data is official.

Consequences:

- Core algorithms can be built and tested immediately.
- Accuracy validation remains a separate official-data onboarding task.
