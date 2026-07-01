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
- Phase 6B adds advanced synchronous semester schedule optimizer endpoints under `/api/v1/schedule-optimizations`. The optimizer ranks bounded single-term section combinations, persists constraint/option/conflict/repair/warning snapshots, and does not mutate student records, section data, seats, waitlists, or registration data.
- Phase 7A adds synchronous read-only data import preview endpoints under `/api/v1/data-imports`. The import service parses bounded mock or student-provided CSV/JSON content into staging tables, proposes mapping candidates, emits warnings, and does not mutate catalog, transcript, requirement, section, seat, waitlist, or registration tables.
- Phase 8B adds read-only section monitoring endpoints under `/api/v1/section-monitoring`. The service stores user-selected advisory monitor targets, compares user-triggered non-official section-search snapshots, emits structured change alerts, and does not poll, refresh portals, change seat or waitlist state, or perform registration actions.
- Phase 9A adds product-hardening UI helpers and dashboard polish. It summarizes existing workflow status, empty states, manual next actions, and advisory labels without adding backend domains or changing the read-only/advisory boundary.
- Phase 9B adds production-readiness hardening. The API validates environment, database, timeout, and CORS settings; applies safe response headers; narrows CORS request headers; and emits low-sensitivity audit logs for imports and section-monitoring comparisons without adding product domains.
- Phase 10A adds release-readiness QA and final product review documentation. It covers user-flow QA, demo-safe wording, final checklist review, and safety-boundary audit without adding backend domains or changing workflow authority.
- Phase 11B adds Kean Student Portal browser-extension import handling through
  the existing `/api/v1/data-imports` and Phase 7B review path. It adds no new
  backend domain, official-source ingestion, credential handling, polling, or
  registration capability.

### Browser Extension

- Phase 8A local-development Manifest V3 data capture tool.
- Reads only active, user-opened pages after user action.
- Converts visible transcript, degree-audit, catalog, or section-search tables into structured import drafts.
- Shows a preview before sending and requires explicit confirmation.
- Phase 8B extraction includes section availability, waitlist count, meeting-time, location, and instructor fields so user-triggered imports can feed advisory comparisons.
- Phase 11B adds Kean-specific page definitions for transcript, degree audit,
  MyProgress, course catalog, section search, student planning, and schedule
  pages under `https://kean-ss.colleague.elluciancloud.com/Student/*`.
- Guided Kean import requests an optional Kean host permission only when the
  student starts the workflow, then captures only user-opened supported pages.
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

Phase 6B implements this boundary with:

- `ScheduleOptimizationRun` as the snapshot root for one student, term, planning mode, credit policy, and engine version.
- `ScheduleConstraintSet` for persisted hard constraints and preference inputs, including candidate course IDs, excluded days, unavailable blocks, time windows, modalities, required/excluded sections, priority weights, diversity mode, partial-option policy, search bound, and permission behavior.
- `ScheduleOption` for each ranked result with status, total score, score components, score explanations, diversity metadata, credit total, class-day count, time window, gap minutes, and explanation.
- `ScheduleOptionSection` for selected concrete sections with course, section, eligibility result, credits, and selection reason.
- `ScheduleConflict` and `ScheduleWarning` for rejected candidates, infeasibility causes, mock-data notices, advisor-confirmation warnings, and bounded-search assumptions.
- `ScheduleRepairSuggestion` for minimal, structured relaxations such as relaxing an unavailable block, required section, excluded day, permission rule, or credit target.

The Phase 6B scheduler is deterministic and bounded. It can use Course Eligibility in `REGISTRATION` mode, but section availability remains informational and registration actions are out of scope. It rejects overlapping required meetings, unavailable blocks, excluded days, invalid required/excluded sections, hard eligibility blocks, duplicate-course choices, and credit overloads. It scores feasible or partial options by preferred credits, compactness, fewer days, gap minutes, modality preference, morning/afternoon preferences, course/section priority weights, and early/late penalties. High-diversity mode uses deterministic greedy selection to reduce repeated section overlap across returned options after feasibility scoring. It does not use OR-Tools, poll seats, join waitlists, add, drop, swap, or register.

### Data Import Preview Boundary

Stages mock or student-provided academic data for review without applying it.

Phase 7A implements this boundary with:

- `DataImportRun` as the staging root for one student, import type, parser version, file metadata, source metadata, status, counts, and preview readiness flag.
- `DataImportFile` for metadata-only file tracking, checksum, storage strategy, and bounded content preview.
- `ImportedRecord` for normalized row payloads, record type, row number, status, external identifier, and confidence score.
- `ImportMappingCandidate` for target entity suggestions with match type, confidence, reason code, and explanation.
- `ImportValidationWarning` and `ImportPreviewSummary` for advisor-confirmation warnings and preview disclaimers.

The Phase 7A importer accepts small CSV/JSON payloads for unofficial transcript, degree audit export, catalog, section schedule, and generic records. It may match normalized course codes to existing mock catalog rows, but it never writes to `StudentCourseAttempt`, `Course`, `Section`, `RequirementNode`, seat, waitlist, or registration tables. Official-source imports are rejected in this phase; all results remain preview-only and require advisor or school confirmation before academic use.

Phase 7B adds an explicit review/application boundary on top of Phase 7A:

- `DataImportReviewSession` groups one review for one import run and student.
- `ImportedRecordReview` stores per-record decisions, selected mapping candidates, edited normalized payloads, notes, and advisor-confirmation flags.
- `DataApplicationRun`, `AppliedImportedRecord`, and `DataReviewWarning` record dry-run/application outcomes, duplicate skips, unsupported records, and warnings.
- `DataReviewApplicationService.apply_review_session(review_session_id, allow_advisor_review_records=False, dry_run=False)` is the only service entrypoint that can apply reviewed records.

Dry-run application returns proposed outcomes without writing domain records. Real application is limited to explicit `POST /data-import-reviews/{review_id}/apply`; GET endpoints never apply data. Confirmed unofficial transcript course attempts can create non-official internal `StudentCourseAttempt` records with source metadata. Catalog, section, requirement, unknown-course, rejected, deferred, duplicate, unsupported-grade, and advisor-review records are logged and skipped unless a later phase implements a safe, tested application path.

Phase 8A adds a browser-extension handoff into the same staging boundary:

- `apps/extension` provides a Manifest V3 shell with `activeTab`, `scripting`, and `storage` permissions only.
- Content extraction uses DOM table reads on the active page only after the popup requests it.
- Extracted rows are converted to Phase 7A-compatible CSV/JSON and sent to `POST /api/v1/data-imports` as `source_type = BROWSER_EXTENSION`.
- Extension data is always `is_official = false` and `official_application_ready = false`.
- Phase 7B review and explicit apply remain mandatory before internal planning records can be changed.
- No extension code stores credentials, reads password fields, submits forms, polls portals, publishes production builds, or automates registration, add/drop, swap, waitlist, or seat-state behavior.

Phase 11B specializes that handoff for Kean Student Portal:

- Supported portal prefix is
  `https://kean-ss.colleague.elluciancloud.com/Student/*`.
- The manifest keeps baseline permissions to `activeTab`, `scripting`, and
  `storage`, with an optional Kean host permission for guided import.
- Because Chrome host permissions are host-scoped, extraction code enforces the
  narrower `/Student/` prefix and page whitelist.
- Kean extracts are labeled `KEAN_STUDENT_PORTAL` in source-reference and
  preview metadata while staying non-official browser-extension imports.
- Unsupported Kean host pages, login pages, hidden fields, unrelated personal
  or financial columns, and action-only columns do not become import payload
  fields.

### Section Monitoring Boundary

Compares user-triggered section-search snapshots and produces advisory alerts only.

Phase 8B implements this boundary with:

- `SectionMonitorTarget` for student-selected course/section/term watch targets.
- `SectionMonitorSnapshot` for non-official imported section state.
- `SectionMonitorAlert` for structured status, seat-count, waitlist-count, meeting-time, instructor, location, and unknown-change advisories.

The service accepts non-official browser-extension snapshots, deduplicates identical snapshots by hash, and compares only against stored snapshots for the same student/course/section/term. Alerts include manual-review and advisory flags plus messages that tell students to verify in the official registration portal. The boundary deliberately does not schedule background jobs, poll portals, register, drop, swap, alter waitlist or seat state, submit forms, store credentials, or bypass school authentication.

### Production Readiness Boundary

Phase 9B keeps operational hardening separate from product expansion:

- API settings fail fast for unsupported `DATABASE_URL` schemes, unknown environments, empty or wildcard CORS origins, local production database defaults, and localhost production CORS origins.
- Web settings validate `NEXT_PUBLIC_API_BASE_URL` as an `http` or `https` URL without embedded credentials.
- API responses include safe default headers such as content-type sniffing protection, frame denial, referrer suppression, restrictive browser permissions policy, and no-store caching.
- Production HSTS is enabled only when `ENVIRONMENT=production`; reverse proxies should still terminate TLS and preserve host/protocol headers.
- Audit logs record event names, IDs, source type, import type, counts, and statuses only. They must not include raw imported content, HTML, school credentials, portal tokens, passwords, or full student data.
- This boundary does not deploy the system, add telemetry, add account/auth systems, ingest official school data, or change the read-only/advisory academic workflow.

Phase 10A keeps release-readiness QA separate from product expansion:

- Release QA docs describe the main reviewable user journeys: data import, Phase 7B review, browser-extension import, section monitoring alerts, degree audit/planner status, schedule optimization, manual action checklist, and manual official-portal verification.
- Demo scenarios must use imported snapshot, advisory alert, manual review required, read-only imported data, non-official data, and verify in the official portal wording.
- The release checklist must cover format, lint, typecheck, unit tests, backend tests, extension tests, Playwright e2e, OpenAPI checks, Alembic validation, Docker Compose validation, no-secrets review, extension permissions, prohibited automation review, docs review, demo review, and local limitations.
- Safety review confirms no credential capture, password-field extraction, SAML/MFA/CAPTCHA bypass, portal form submission, background scraping, polling, automatic registration, add/drop/swap automation, waitlist automation, seat reservation, seat grabbing, browser-store publishing, hidden automation, external telemetry, or production deployment.
- This boundary does not add source ingestion, scheduler jobs, notification workers, browser-store publishing, deployment, account systems, or new product domains.

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
9. Phase 6B Schedule Optimizer ranks concrete mock section schedules for a selected term and persists options, score breakdowns, diversity metadata, conflicts, repair suggestions, and warnings.
10. Phase 7A Data Import Preview stages mock or student-provided CSV/JSON rows, mapping candidates, warnings, and preview disclaimers without applying records to official domain tables.
11. Phase 7B Data Review and Confirmation records human decisions, dry-run outcomes, application runs, duplicate skips, and internal non-official course-attempt applications.
12. Phase 8A Browser Extension Import converts user-confirmed visible page tables into `BROWSER_EXTENSION` staging imports that still require Phase 7B review.
13. Phase 8B Section Monitoring stores user-selected advisory monitor targets and compares user-triggered section-search snapshots for manual-review alerts.
14. Phase 9A Product Hardening renders status cards, reusable advisory labels, empty states, safer before/after displays, and manual next-action copy for the existing workflows.
15. Phase 9B Production Readiness validates environment configuration, applies safe HTTP defaults, and logs low-sensitivity audit events around imports and advisory monitoring.
16. Phase 10A Release Readiness QA documents final user-flow QA, demo scenarios, checklist review, and safety-boundary audit for handoff.
17. Phase 11B Kean Student Portal Import captures user-authorized supported
    Kean pages into `BROWSER_EXTENSION` staging imports and preserves Phase 7B
    review.
18. Risk Engine annotates results with missing-data, prerequisite-chain, offering-frequency, GPA, and advisor-review warnings in a later phase.
19. UI presents explanations and warnings and will let users adjust assumptions as optimizer phases mature.

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
- OR-Tools CP-SAT is suitable for future constraint optimization in planning and scheduling; Phase 5A uses a deterministic baseline planner and Phase 6B uses a deterministic bounded scheduler behind an optimizer protocol so a future solver can be swapped in without changing API contracts.
- Playwright enables realistic E2E tests for planner workflows.

## 9. Deployment Direction

MVP local development should use Docker Compose with services for web, API, PostgreSQL, and optional worker. Production should use managed PostgreSQL, containerized API/web deployments, encrypted secrets, structured logs, and background workers for optimizer jobs.
