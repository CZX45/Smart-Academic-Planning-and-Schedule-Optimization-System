# Feature Inventory

This inventory groups the completed work by phase and highlights user value,
verification coverage, and safety or boundary notes.

## Phase 1 - Monorepo Infrastructure

What was added:

- Workspace layout for API, web, extension, shared packages, fixtures, infra,
  tests, and docs.
- Root package scripts for install, dev, build, test, lint, typecheck,
  OpenAPI, and e2e workflows.

User value:

- Reviewers can run and inspect the project as one coherent workspace.

Verification coverage:

- Repository scripts, baseline tests, formatting, and e2e scaffolding.

Safety/boundary notes:

- No school-specific or student-sensitive data is required for the foundation.

## Phase 2A - Academic Domain Foundation

What was added:

- Institutions, campuses, terms, programs, program versions, courses,
  requirement trees, source metadata, mock students, declarations, course
  attempts, transfers, waivers, and substitutions.

User value:

- Academic data can be represented as versioned, source-aware domain records.

Verification coverage:

- Academic model and API tests.

Safety/boundary notes:

- Seed data is mock-only and must not be presented as official school policy.

## Phase 2B - Course Rules and Sections

What was added:

- Sections, meetings, offering patterns, course and section rules, and
  composable rule expressions.

User value:

- Courses and sections are separated, and rules are stored for later evaluation.

Verification coverage:

- Section, course-rule, and academic API tests.

Safety/boundary notes:

- Offering patterns are planning metadata, not school promises.

## Phase 3A - Degree Audit Core

What was added:

- Degree audit snapshots with requirement evaluations, applied courses,
  warnings, calculation mode, credits, and engine version.

User value:

- Students and advisors can review degree progress with traceable explanations.

Verification coverage:

- Degree audit policy and academic API tests.

Safety/boundary notes:

- Audit snapshots do not alter official student records.

## Phase 3B - What-if Scenarios

What was added:

- Scenario snapshots for hypothetical program combinations, audit runs,
  cross-program allocation, warnings, and comparisons.

User value:

- Students can explore potential academic changes before discussing them with an
  advisor.

Verification coverage:

- Academic scenario tests and shared schema coverage.

Safety/boundary notes:

- Scenarios do not change declared academic programs.

## Phase 4 - Course Eligibility Engine

What was added:

- Eligibility snapshots for course and section rules, expression evidence,
  warnings, modes, and batch checks.

User value:

- Users can understand why a student may be eligible, conditionally eligible, or
  blocked.

Verification coverage:

- Course eligibility tests and API schema tests.

Safety/boundary notes:

- Eligibility remains advisory and separates academic rules from section status.

## Phase 5A - Long-Term Academic Planner Core

What was added:

- Course-level academic plan snapshots with terms, planned courses, requirement
  coverage, credit constraints, offering assumptions, and warnings.

User value:

- Users can review a future course plan and compare possible paths.

Verification coverage:

- Academic planner tests and warning coverage.

Safety/boundary notes:

- The planner does not select concrete sections or perform course actions.

## Phase 6A - Semester Schedule Optimizer Foundation

What was added:

- Schedule optimization run, constraint set, option, option-section, conflict,
  and warning concepts for bounded section scheduling.

User value:

- Users can compare feasible section combinations for a term.

Verification coverage:

- Schedule optimizer tests for feasible and infeasible outcomes.

Safety/boundary notes:

- Schedule snapshots do not change enrollment state.

## Phase 6B - Advanced Schedule Optimization

What was added:

- Preference weights, score breakdowns, diversity ranking, difference summaries,
  soft-preference explanations, and repair suggestions.

User value:

- Users get more meaningful ranked options and clearer infeasibility guidance.

Verification coverage:

- Advanced schedule optimizer and shared schema tests.

Safety/boundary notes:

- Results remain planning options requiring manual verification.

## Phase 7A - Read-only Data Import Foundation

What was added:

- Staging imports for CSV/JSON content, normalized records, mapping candidates,
  warnings, preview summaries, and source metadata.

User value:

- Users can inspect imported academic data before it affects planning records.

Verification coverage:

- Data import tests for parsing, staging, warnings, and preview behavior.

Safety/boundary notes:

- Imports remain non-official and do not write to official academic-domain
  tables.

## Phase 7B - Data Review and Confirmation Workflow

What was added:

- Review sessions, per-record decisions, dry-run application, explicit apply,
  applied-record logs, skipped records, and warnings.

User value:

- Users control which supported imported rows become internal planning inputs.

Verification coverage:

- Data review tests for decisions, dry runs, application outcomes, and warnings.

Safety/boundary notes:

- Manual review is required for ambiguous or unsupported rows.

## Phase 8A - Read-only Browser Extension Import

What was added:

- Manifest V3 local-development extension for user-triggered visible-page table
  extraction and preview.

User value:

- Students can convert a visible page into a review-gated import without
  copying rows by hand.

Verification coverage:

- Extension extractor tests, manifest policy tests, and backend source-type
  import coverage.

Safety/boundary notes:

- The extension does not store credentials, inspect password fields, bypass
  school authentication, submit forms, or run hidden automation.

## Phase 8B - Read-only Section Monitoring Alerts

What was added:

- Monitor targets, user-triggered section-search snapshots, comparison logic,
  advisory alerts, and acknowledgement state.

User value:

- Users can see what changed between imported snapshots and decide what to check
  manually.

Verification coverage:

- Section monitoring tests and extension section-search extraction coverage.

Safety/boundary notes:

- Alerts are non-official and do not mutate canonical sections, seats,
  waitlists, schedules, or registration state.

## Phase 9A - Product Hardening and Dashboard Polish

What was added:

- Dashboard status cards, empty states, manual next-action copy, advisory labels,
  and shared frontend copy helpers.

User value:

- Main workflows are easier to demo and review from one dashboard.

Verification coverage:

- Shared TypeScript tests and Playwright dashboard coverage.

Safety/boundary notes:

- UI copy keeps source uncertainty, advisory status, and manual steps visible.

## Phase 9B - Security and Production Readiness Hardening

What was added:

- Environment validation, production-safe CORS checks, safe response headers,
  low-sensitivity logging boundaries, and security/privacy documentation.

User value:

- Reviewers can see the path toward safer production readiness.

Verification coverage:

- Config tests, security header tests, production safety policy tests, Ruff,
  mypy, and OpenAPI checks.

Safety/boundary notes:

- No credentials, account system, telemetry, production deployment, or school
  portal automation was added.

## Phase 10A - Release Readiness QA and Final Product Review

What was added:

- Release readiness QA matrix, demo scenarios, release checklist, and
  documentation consistency cleanup.

User value:

- The project can be reviewed and demoed with safer language and clearer QA
  expectations.

Verification coverage:

- Production safety policy tests validate Phase 10A doc existence and advisory
  wording.

Safety/boundary notes:

- Release docs confirm mock/non-official data and manual school confirmation.

## Phase 10B - Final Demo Handoff Package

What was added:

- Final project summary, final demo script, feature inventory, final
  architecture snapshot, known limitations and future work, final safety and
  non-automation statement, handoff checklist, README navigation, and final-doc
  regression test.

User value:

- Reviewers have a concise package for presenting, auditing, and continuing the
  project.

Verification coverage:

- `apps/api/tests/test_final_handoff_docs.py` checks required final docs and
  safety language.

Safety/boundary notes:

- Phase 10B is documentation and handoff only. It adds no backend domain,
  database migration, extension behavior, deployment, or course-action workflow.
