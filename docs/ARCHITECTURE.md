# Architecture

## 1. Repository Assessment

The repository was empty at the start of this phase. Therefore, the first architectural deliverable is a documentation-first monorepo plan rather than full application code.

## 2. Proposed Monorepo

```text
apps/
  web/
    Next.js + TypeScript + Tailwind CSS
  api/
    FastAPI + SQLAlchemy + Pydantic + OpenAPI
  extension/
    Chrome Extension Manifest V3 + TypeScript
packages/
  shared/
    Shared TypeScript types, generated API client, validation helpers
  fixtures/
    Mock catalogs, programs, transcripts, requirements, and sections
  config/
    Shared ESLint, TypeScript, Vitest, and formatting config
services/
  optimizer/
    Python modules for academic plan optimization and section schedule optimization
infra/
  docker/
    Dockerfiles, compose helpers, local DB initialization
docs/
  Product and engineering documentation
```

A pnpm workspace with Turborepo orchestration is appropriate because it can coordinate the Next.js app, extension, shared TypeScript packages, and generated clients. Python services should remain first-class workspace members with separate tooling invoked by Turborepo tasks or Make targets.

## 3. High-Level Components

### Web Application
- Student dashboard.
- Degree-progress viewer.
- Program/minor simulation UI.
- Academic plan editor.
- Schedule preference editor.
- Schedule results and infeasibility explanations.
- Advisor review screens in later versions.

### Backend API
- Owns authoritative domain rules, student records, planning sessions, optimizer calls, and persistence.
- Exposes OpenAPI endpoints.
- Validates all input through Pydantic.
- Persists normalized data through SQLAlchemy to PostgreSQL.

### Browser Extension
- Later-phase optional data capture tool.
- Reads only user-opened authenticated pages after user action.
- Converts visible data into structured import drafts.
- Never stores school credentials.
- Never performs registration actions.

### Optimization Services
Two separate optimizer boundaries are required:

1. Academic Plan Optimizer
   - Input: degree requirements, completed/in-progress/planned courses, future term assumptions, term credit limits, prerequisite rules.
   - Output: multi-semester course plan and explanation.

2. Semester Schedule Optimizer
   - Input: selected courses for a term, section offerings, meeting times, preferences, section restrictions.
   - Output: ranked legal schedules, conflicts, backups, and infeasibility explanations.

These optimizers may initially live in the FastAPI codebase as Python modules and later be extracted to a separate service if scaling requires it.

## 4. Domain Boundaries

### Institution Catalog Boundary
Owns institutions, campuses, terms, subjects, courses, sections, instructors, rooms, modalities, and source metadata.

### Program Requirements Boundary
Owns degree programs, minors, certificates, concentrations, catalog-year versions, requirement trees, overlap policies, residency rules, GPA rules, and upper-level requirements.

### Student Academic Record Boundary
Owns student profile, academic standing, declared programs, course attempts, transfer credits, waivers, substitutions, in-progress courses, and planned courses.

### Degree Audit Boundary
Evaluates requirements against student records, performs course allocation, and produces requirement statuses and explanations.

### Eligibility Boundary
Evaluates prerequisites, corequisites, grade minimums, restrictions, and registration eligibility.

### Planning Boundary
Builds long-range course plans independent of section times.

### Scheduling Boundary
Builds section-level schedules for a single term.

### Advising and Risk Boundary
Produces risk flags, advisor review items, confidence levels, and high-risk recommendation warnings.

## 5. Data Flow

1. Data maintainer imports or enters versioned institution and program data.
2. Student imports or enters academic record data.
3. Degree Audit evaluates progress and candidate allocations.
4. Academic Plan Optimizer proposes future terms.
5. Schedule Optimizer ranks concrete section schedules for a selected term.
6. Risk Engine annotates results with missing-data, prerequisite-chain, offering-frequency, GPA, and advisor-review warnings.
7. UI presents explanations and lets users adjust assumptions.

## 6. API Design Principles

- OpenAPI is the source of truth for frontend/backend integration.
- All mutating endpoints must validate tenant, user, and data ownership.
- Optimizer endpoints should be asynchronous or job-based when solving can exceed request timeouts.
- Every recommendation response should include `explanations`, `assumptions`, `warnings`, and `source_references` where available.

## 7. Explainability Pattern

Each evaluator and optimizer returns:

- `decision`: chosen result.
- `status`: satisfied, blocked, warning, infeasible, or unknown.
- `inputs`: relevant IDs and versions.
- `rules_evaluated`: rule identifiers and outcomes.
- `assumptions`: missing or inferred data.
- `alternatives`: rejected candidates where useful.
- `advisor_confirmation_required`: boolean for high-risk decisions.

## 8. Technology Choices

- Next.js provides a strong TypeScript application shell and future server rendering.
- Tailwind CSS supports rapid, consistent UI development.
- FastAPI provides typed OpenAPI-first API development.
- PostgreSQL supports relational integrity, JSONB rule trees, and advanced constraints.
- SQLAlchemy gives mature Python ORM support.
- Pydantic enables strict validation and versioned schemas.
- OR-Tools CP-SAT is suitable for constraint optimization in planning and scheduling.
- Playwright enables realistic E2E tests for planner workflows.

## 9. Deployment Direction

MVP local development should use Docker Compose with services for web, API, PostgreSQL, and optional worker. Production should use managed PostgreSQL, containerized API/web deployments, encrypted secrets, structured logs, and background workers for optimizer jobs.
