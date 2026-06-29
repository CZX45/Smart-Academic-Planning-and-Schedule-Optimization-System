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

## ADR-0009: Implement Phase 2A as relational academic-domain storage

Status: Accepted

Context: Degree Audit, eligibility, academic planning, and schedule optimization need shared academic identities and source metadata before evaluators are introduced.

Decision: Implement Phase 2A as normalized SQLAlchemy/PostgreSQL storage for institutions, campuses, terms, academic programs, program versions, courses, course equivalencies, requirement nodes, requirement course options, student profiles, academic program declarations, course attempts, transfer credits, waivers, and substitutions. Requirement trees use relational adjacency lists rather than a single JSON blob.

Consequences:

- Future evaluators can share deterministic, versioned, source-tagged records.
- Course planning remains separate from section scheduling because Phase 2A models courses only.
- Pending or rejected exceptions can be stored without being applied before Degree Audit rules exist.
- Mock seed data can demonstrate the shape of catalog and student records without claiming official school policy.

## ADR-0010: Implement Phase 2B course rules and sections as relational storage

Status: Accepted

Context: Course Eligibility, Degree Audit, Academic Planning, and Semester Scheduling need shared storage for prerequisites, corequisites, restrictions, offering assumptions, concrete sections, and meeting times before those later engines evaluate anything.

Decision: Add relational tables for `CourseOfferingPattern`, `Section`, `SectionMeeting`, `CourseRule`, and `CourseRuleExpression`. Keep `Course` and `Section` separate. Store prerequisites, corequisites, restrictions, and permissions as expression trees rather than unqueryable text or a single JSON blob. Course-level rules are scoped to a course; section-level rules are constrained to the same course and institution as their section.

Consequences:

- Later eligibility and planning engines can query structured rule operands and source metadata.
- Section scheduling can use concrete section and meeting records without polluting course-level planning.
- Offering patterns remain advisory metadata and must not be presented as official school commitments.
- Phase 2B still does not evaluate student eligibility, run Degree Audit, optimize schedules, monitor seats, or automate registration.

## ADR-0011: Implement Phase 3A degree audit as persisted snapshots

Status: Accepted

Context: Degree progress results must be explainable, testable, and stable for advisor review. The same source data may later be audited under different assumptions, so the system needs traceable outputs rather than transient UI-only calculations.

Decision: Implement Degree Audit Core as a synchronous backend application service that evaluates one `StudentProfile` against one `ProgramVersion` and persists a `DegreeAuditRun` snapshot. Store one `RequirementEvaluation` per requirement node, explicit `AuditCourseApplication` rows for attempts/transfers/waivers/substitutions, and `DegreeAuditWarning` rows for advisor confirmation and data-quality issues.

Consequences:

- API responses can return stable snapshot IDs and explainable structured results.
- The frontend can render degree progress without reimplementing academic rules.
- `CURRENT` and `PROJECTED` modes can show completed, in-progress, and planned layers without confusing them.
- Phase 3A intentionally uses a deterministic baseline allocator rather than a global optimization solver.
- Phase 3B should address what-if scenarios and advanced allocation before eligibility or section scheduling work begins.

## ADR-0012: Implement Phase 3B scenarios as snapshot wrappers around Degree Audit

Status: Accepted

Context: What-if analysis must compare minors, second majors, certificates, concentrations, and change-major candidates without changing official student declarations or duplicating Degree Audit behavior.

Decision: Persist `AcademicPlanScenario` snapshots with `ScenarioProgram` rows and call the Phase 3A `DegreeAuditEngine` once per scenario program. Store each program result as a normal `DegreeAuditRun`, then run a separate deterministic bounded global allocator over the persisted audit applications. Store directional `ProgramCombinationRule` records for overlap policy; missing rules create advisor-review warnings rather than inferred policy.

Consequences:

- Scenario runs are traceable to the same audit snapshot structure as official program audits.
- What-if scenarios cannot silently mutate `StudentAcademicProgram`.
- Shared credit, unique secondary credit, and total earned credit remain separate concepts.
- The allocator can be replaced later without rewriting Degree Audit.
- Phase 3B estimates additional credits but does not predict graduation timing or evaluate eligibility.

## ADR-0013: Implement Phase 4 course eligibility as expression snapshot evaluation

Status: Accepted

Context: Stored course-rule expression trees must become explainable student/course eligibility decisions without duplicating frontend logic or crossing into schedule optimization or registration automation.

Decision: Implement Course Eligibility as a synchronous backend application service that evaluates one `StudentProfile` against one `Course`, optional `Section`, target term, and explicit eligibility mode. Persist an `EligibilityCheckRun` snapshot with `RuleEvaluation`, `RuleExpressionEvaluation`, and `EligibilityWarning` rows. Reuse the centralized grade policy and existing course-attempt/transfer status semantics. Return section availability as a separate snapshot field rather than folding seats into academic eligibility.

Consequences:

- Eligibility checks are auditable, repeatable, and tied to stored rules and expression evidence.
- The frontend can render eligibility results without reimplementing prerequisite/corequisite logic.
- `CURRENT`, `PROJECTED`, and `REGISTRATION` modes keep completed, in-progress, planned, and concurrent corequisite evidence distinct.
- Phase 4 can explain permissions, hard failures, conditional outcomes, and manual-review outcomes without building long-term plans or schedules.
- Phase 4 does not predict graduation timing, optimize schedules, call OR-Tools, monitor seats, or automate registration.
