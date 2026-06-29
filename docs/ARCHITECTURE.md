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
- Phase 2A exposes read-only academic-domain storage endpoints under `/api/v1`.
- Phase 2B adds read-only section, meeting, offering-pattern, course-rule, and rule-expression endpoints. It stores prerequisite, corequisite, restriction, and permission trees but does not evaluate eligibility, plans, schedules, or registration actions.
- Phase 3A adds a synchronous Degree Audit application service under `/api/v1`. The API layer validates request/response schemas and delegates audit creation to the application service, which calls the domain engine and persists a snapshot.
- Phase 3B adds synchronous academic scenario endpoints under `/api/v1/academic-scenarios`. The scenario service validates hypothetical program combinations, reuses Phase 3A Degree Audit per program, runs deterministic multi-program allocation, and persists comparison summaries and warnings.
- Phase 4 adds synchronous course eligibility endpoints under `/api/v1/eligibility-checks`. The eligibility service evaluates stored course-rule expression trees against student records, persists check snapshots, and reports rule/expression evidence without mutating student academic programs or registration data.
- Phase 5A adds synchronous long-term academic planner endpoints under `/api/v1/academic-plans`. The planner reuses Degree Audit and Course Eligibility, persists course-level term plans and warnings, and does not mutate official student records or registration data.

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

Phase 2B stores section snapshots as `Section` rows and one-to-many `SectionMeeting` rows. Sections belong to a course, term, campus, and institution; meetings can represent lectures, labs, recitations, seminars, exams, arranged meetings, or online asynchronous records. Instructor data is limited to non-sensitive display text.

### Program Requirements Boundary
Owns degree programs, minors, certificates, concentrations, catalog-year versions, requirement trees, overlap policies, residency rules, GPA rules, and upper-level requirements.

Phase 2A stores program identity as `AcademicProgram` and catalog/campus/effective-term identity as `ProgramVersion`. Requirement trees are stored as relational adjacency-list `RequirementNode` rows with `RequirementCourseOption` rows for course-specific options.

Phase 2B does not add degree requirement evaluation. It adds `CourseRule` and `CourseRuleExpression` storage for prerequisites, corequisites, restrictions, repeat restrictions, and permission requirements. Course-level rules are scoped by `course_id`; section-level rules also carry `section_id` and are constrained to the same course and institution.

### Student Academic Record Boundary
Owns student profile, academic standing, declared programs, course attempts, transfer credits, waivers, substitutions, in-progress courses, and planned courses.

Phase 2A stores attempts without overwriting prior attempts. Transfer credits, waivers, and substitutions are state records only; pending and rejected records are not applied to any audit because no audit engine exists yet.

### Degree Audit Boundary
Evaluates requirements against student records, performs baseline deterministic course allocation, and produces requirement statuses, applications, warnings, and explanations.

Phase 3A implements this boundary for one `StudentProfile` plus one `ProgramVersion` at a time. It uses:

- `DegreeAuditRun` as the snapshot root.
- `RequirementEvaluation` for one result per requirement node.
- `AuditCourseApplication` to record which attempt, transfer, waiver, or substitution was applied.
- `DegreeAuditWarning` for advisor-confirmation and data-quality warnings.

The baseline allocator is intentionally not a global optimizer. It reserves source records for non-overlap leaf requirements in deterministic requirement order and records `is_shared` only when overlap is allowed. Ambiguous or unsupported rule scope returns `MANUAL_REVIEW_REQUIRED` or a warning rather than a false satisfied result.

### What-if Scenario Boundary
Simulates academic program combinations without mutating official student declarations.

Phase 3B implements this boundary with:

- `AcademicPlanScenario` as the scenario snapshot root.
- `ScenarioProgram` for existing and hypothetical program versions in the scenario.
- `ProgramCombinationRule` for directional overlap policy between a primary and secondary program.
- `ScenarioProgramAudit` linking each scenario program to an independent Phase 3A `DegreeAuditRun`.
- `ScenarioCourseAllocation` for global allocation decisions.
- `ScenarioComparisonSnapshot` and `ScenarioWarning` for summary and advisor-review output.

The scenario service deliberately does not evaluate prerequisites, registration eligibility, future course offering probability, multi-term plans, or section schedules. Shared credit is allowed only when both the requirement application allows overlap and a directional combination rule allows double counting. Total earned credits are counted once even when a requirement application is shared.

### Eligibility Boundary
Evaluates prerequisites, corequisites, grade minimums, restrictions, and registration eligibility.

Phase 4 implements this boundary with:

- `EligibilityCheckRun` as the snapshot root for one student, course, optional section, target term, and mode.
- `RuleEvaluation` for each course-level or section-level `CourseRule` evaluated in the check.
- `RuleExpressionEvaluation` for each evaluated expression node, including reason codes, expected values, actual values, and matched course/attempt evidence where applicable.
- `EligibilityWarning` for mock-data, advisor-confirmation, missing-rule, and manual-review notices.
- A backend evaluator registry for `CourseRuleExpressionNodeType` leaves; the web app consumes API results and does not reimplement eligibility logic.

Eligibility modes are explicit: `CURRENT`, `PROJECTED`, and `REGISTRATION`. In-progress, planned, and concurrent corequisite evidence can make a result conditional but is not relabeled as final completion. Section availability is returned as an availability snapshot and is not treated as academic eligibility. Phase 4 deliberately does not predict graduation terms, build multi-term plans, optimize schedules, call OR-Tools, poll seats, or perform registration actions.

### Planning Boundary
Builds long-range course plans independent of section times.

Phase 5A implements this boundary with:

- `AcademicPlanRun` as the snapshot root for one student, program version, planning mode, start term, horizon, and credit policy.
- `AcademicPlanTerm` for each generated future term and its planned-credit total.
- `AcademicPlanCourse` for course-level placements with source, eligibility result, planning status, reason code, and explanation.
- `AcademicPlanRequirementCoverage` for traceable requirement coverage claims.
- `AcademicPlanWarning` for mock-data, credit-limit, offering-pattern, horizon, and advisor-review notices.

The planner remains deterministic and course-level. It can use section and offering-pattern snapshots as availability signals, but it does not select sections, inspect weekly meeting conflicts, optimize schedules, poll seats, or automate registration. What-if plans reference `AcademicPlanScenario` snapshots instead of changing `StudentAcademicProgram`.

### Scheduling Boundary
Builds section-level schedules for a single term.

### Advising and Risk Boundary
Produces risk flags, advisor review items, confidence levels, and high-risk recommendation warnings.

## 5. Data Flow

1. Data maintainer imports or enters versioned institution and program data.
2. Student imports or enters academic record data.
3. Phase 2A read-only APIs expose the stored mock catalog and mock student record with source metadata.
4. Phase 2B read-only APIs expose stored mock sections, meetings, offering patterns, and course-rule expression trees with source metadata.
5. Phase 3A Degree Audit creates explicit snapshots for stored mock student/program data.
6. Phase 3B What-if Scenarios create mock program-combination snapshots, per-program audit runs, allocations, warnings, and comparison summaries.
7. Phase 4 Course Eligibility Checks evaluate stored mock course rules and optional section rules for a selected course/term.
8. Phase 5A Academic Planner proposes course-level future terms and persists requirement coverage and warnings.
9. Schedule Optimizer ranks concrete section schedules for a selected term in a later phase.
10. Risk Engine annotates results with missing-data, prerequisite-chain, offering-frequency, GPA, and advisor-review warnings in a later phase.
11. UI presents explanations and warnings and will let users adjust assumptions as optimizer phases mature.

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
- OR-Tools CP-SAT is suitable for future constraint optimization in planning and scheduling; Phase 5A uses a deterministic baseline planner.
- Playwright enables realistic E2E tests for planner workflows.

## 9. Deployment Direction

MVP local development should use Docker Compose with services for web, API, PostgreSQL, and optional worker. Production should use managed PostgreSQL, containerized API/web deployments, encrypted secrets, structured logs, and background workers for optimizer jobs.
