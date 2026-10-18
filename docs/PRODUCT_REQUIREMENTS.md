# Product Requirements

## 1. Product Vision

Smart Academic Planning and Schedule Optimization System helps students and advisors make explainable, policy-aware academic planning decisions. It combines degree audit logic, prerequisite and eligibility checking, multi-semester planning, and section-level schedule optimization.

The first supported institution family is Kean University / Wenzhou-Kean University, and the first prioritized program is BS Finance. The product architecture must support additional institutions, campuses, catalog years, majors, minors, certificates, concentrations, double majors, and future policy variations.

## 2. User Personas

### Student
- Wants to understand what remains before graduation.
- Wants to simulate adding a minor, concentration, certificate, or second major.
- Wants a feasible semester-by-semester plan.
- Wants section schedules that respect time preferences and registration eligibility.

### Advisor
- Wants to review student plans and risks quickly.
- Wants explainable recommendations rather than opaque optimizer output.
- Wants to identify prerequisite-chain, term-offering, GPA, and overload risks.

### Rule/Data Maintainer
- Wants to enter and version institution, campus, catalog, program, and requirement rules.
- Wants validation tooling to detect inconsistent or incomplete rule data.

## 3. Core Jobs To Be Done

1. Read the student's applicable curriculum, catalog, four-year plan, degree requirements, and My Progress data.
2. Determine which requirements are satisfied, partially satisfied, in progress, planned, or unsatisfied.
3. Allocate courses to requirements optimally when multiple requirement buckets are possible.
4. Evaluate prerequisite, corequisite, minimum grade, major, class standing, campus, and section restrictions.
5. Simulate adding or changing academic programs.
6. Generate explainable academic plans until graduation.
7. Generate multiple legal section schedules from available sections and preferences.
8. Explain infeasibility and suggest minimal relaxation options.
9. Provide warnings about graduation delay, prerequisite chains, course offering frequency, workload, GPA, tuition, and advisor review needs.

## 4. MVP Scope

The MVP must include:

- Documentation-backed monorepo foundation.
- Mock fixtures for at least one institution, one campus, one catalog year, one BS Finance-like program, example transcript records, and example sections.
- Manual data entry/import stubs for course history and planned courses.
- Rule-tree representation for degree requirements.
- Expression-tree representation for prerequisites and restrictions.
- Degree-progress evaluator with explainable course-to-requirement allocation.
- Academic plan optimizer separated from section schedule optimizer.
- Section schedule optimizer that checks time conflicts, credit bounds, unavailable times, and simple preference scores.
- UI/API contract definitions before full UI polish.
- Explicit disclaimers for mock data and advisor-confirmation warnings.

## 5. Post-MVP Scope

Post-MVP versions may add:

- Browser extension extraction from user-opened My Progress and course-search pages.
- Official data ingestion pipelines with source citations and version management.
- Advisor review workflows and comments.
- Minor, double major, concentration, and certificate simulations with overlap policies.
- GPA scenario analysis.
- Tuition and fee estimation.
- Workload balancing from course metadata.
- Calendar export.
- Low-frequency seat and schedule-change notifications that respect school systems.
- Multi-school onboarding tools.

## 6. Explicit Non-Goals

The system must not:

- Automatically register, drop, swap, or waitlist courses in version 1.
- Store school usernames, passwords, SAML tokens, or MFA secrets.
- Bypass authentication, authorization, CAPTCHA, rate limits, or school technical controls.
- Scrape pages the student has not actively opened and authorized.
- Present mock, inferred, or manually-entered data as official school data.
- Replace an academic advisor for high-risk decisions.

## 7. Functional Requirements

### Degree Progress
- Support course statuses: `completed`, `in_progress`, `planned`, `failed_or_insufficient_grade`, `transferred`, `waived`.
- Support requirement statuses: `satisfied`, `partially_satisfied`, `in_progress`, `planned`, `unsatisfied`.
- Support reusable requirement rule types: all-of, any-of, min credits, min courses, course set, attribute match, level constraint, GPA constraint, residency constraint, and custom policy hook.
- Preserve all candidate allocations and final chosen allocation with explanations.

### Eligibility
- Evaluate prerequisites and corequisites as logical trees.
- Evaluate minimum grade, major restriction, class standing, campus restriction, cohort restriction, program restriction, and section-level restrictions.
- Report whether each issue is blocking, warning-only, or advisor-confirmation-required.

### Academic Planning
- Produce semester-by-semester plans under credit bounds.
- Respect prerequisite ordering and term availability assumptions.
- Separate long-range course planning from exact section scheduling.
- Explain why each course appears in a term.

### Schedule Optimization
- Treat course and section as separate entities.
- Generate multiple section combinations for selected courses.
- Detect meeting conflicts and insufficient transition/commute gaps.
- Support preferences: no Friday, earliest start, latest end, credit range, class days, compactness, online preference, professor preference, and unavailable time blocks.

## 8. Non-Functional Requirements

- Explainability: every recommendation must have traceable inputs and rule reasoning.
- Versioning: rules and source data must include institution, campus, catalog year, effective term, and program version.
- Auditability: official data must include source metadata and import timestamp.
- Privacy: collect the minimum necessary student data.
- Reliability: optimizer outputs must be deterministic for the same input unless explicitly randomized.
- Extensibility: adding a new school or program should not require changing core algorithms.

## 9. Runtime Product Modes

- `LOCAL_DESKTOP` is the default runtime for local software. It uses an
  explicit local runtime context, requires no bearer authentication, does not
  depend on tenant or server authorization records, and binds the API only to
  `127.0.0.1`, `localhost`, or `::1`.
- `SERVER` must be explicitly selected and uses bearer authentication with the
  existing tenant, user, token, grant, and object-authorization rules.
- `ENVIRONMENT` is independent from `PRODUCT_MODE`; production local-desktop
  mode is valid when it remains loopback-only.
- Both modes require explicit non-wildcard CORS allowlists. Pairing and
  complete localhost webpage protection are not implemented yet.
- The stable local application contract is
  `APP_ID=com.sapsos.smart-academic-planner`, `APP_DATA_DIR_NAME=SAPSOS`, with
  future data root `%LOCALAPPDATA%\\SAPSOS\\`. This phase does not create that
  directory.
