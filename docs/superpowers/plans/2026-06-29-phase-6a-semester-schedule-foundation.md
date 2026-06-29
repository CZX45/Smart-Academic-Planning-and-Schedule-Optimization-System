# Phase 6A Semester Schedule Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, explainable single-term section schedule optimizer that persists schedule runs, constraints, options, selected sections, conflicts, and warnings.

**Architecture:** Add Phase 6A snapshot tables beside existing academic planner tables, then implement a backend schedule optimizer service that reuses Course Eligibility and existing Section/SectionMeeting records. Expose synchronous `/api/v1/schedule-optimizations` endpoints, generate shared TypeScript schemas/client helpers, and add a read-only Semester Schedule Builder panel to the existing mock UI.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Next.js, TypeScript, Zod, Vitest, Playwright.

---

### Task 1: Backend Tests First

**Files:**
- Create: `apps/api/tests/test_schedule_optimizer.py`

- [ ] Write failing SQLite-backed model tests for schedule runs, constraint sets, options, selected sections, conflicts, warnings, and failed run persistence.
- [ ] Write failing engine tests for time overlap, back-to-back meetings, asynchronous meetings, arranged warnings, unavailable blocks, excluded Friday, duplicate courses, credit limits, eligibility results, permission-required handling, partial output, and deterministic ranking.
- [ ] Write failing API tests for create, get run, options, conflicts, warnings, student list, compare, invalid term, invalid credit limits, and invalid candidate course.
- [ ] Run `cd apps/api && python -m pytest tests/test_schedule_optimizer.py -q` and confirm failures are for missing Phase 6A code.

### Task 2: Persistence and Migration

**Files:**
- Modify: `apps/api/app/models/academic.py`
- Create: `apps/api/alembic/versions/20260629_0008_create_schedule_optimizer.py`

- [ ] Add schedule enums for planning mode, run status, option status, conflict type, and preference polarity where needed.
- [ ] Add `ScheduleOptimizationRun`, `ScheduleConstraintSet`, `ScheduleOption`, `ScheduleOptionSection`, `ScheduleConflict`, and `ScheduleWarning` models with constraints and deterministic indexes.
- [ ] Add Alembic migration from `20260629_0007` with matching columns, enum checks, foreign keys, unique constraints, and PostgreSQL-safe constraint names.
- [ ] Run the targeted backend schedule tests and fix model/migration mismatches.

### Task 3: Schedule Optimizer Service

**Files:**
- Create: `apps/api/app/services/schedule_optimizer/__init__.py`
- Create: `apps/api/app/services/schedule_optimizer/exceptions.py`
- Create: `apps/api/app/services/schedule_optimizer/engine.py`

- [ ] Implement request validation for student, term, optional academic plan, candidates, credit limits, and bounded search limits.
- [ ] Determine candidates from explicit course IDs, selected academic plan term courses, or remaining degree audit requirements.
- [ ] Load target-term sections, reject hard-constraint violations, evaluate eligibility with Course Eligibility, and group by course.
- [ ] Generate deterministic bounded combinations, reject time conflicts and credit-limit violations, score soft preferences transparently, and persist top options.
- [ ] Persist conflicts/warnings for rejected and partial cases including mock data, closed sections, conditional/permission/manual-review eligibility, arranged/asynchronous timing, search limit, and no feasible schedule.
- [ ] Run targeted backend schedule tests and keep them green.

### Task 4: API and Schemas

**Files:**
- Modify: `apps/api/app/schemas/academic.py`
- Modify: `apps/api/app/api/v1/academic.py`

- [ ] Add Pydantic request/response models for schedule runs, constraints, options, selected sections, conflicts, warnings, details, and comparisons.
- [ ] Add POST/GET/list/compare endpoints under `/api/v1`.
- [ ] Ensure GET endpoints never generate schedules and response objects distinguish academic eligibility from section availability.
- [ ] Run targeted API tests.

### Task 5: Shared TypeScript Contract

**Files:**
- Modify: `packages/shared/src/index.ts`
- Modify: `packages/shared/src/index.test.ts`

- [ ] Add Zod schemas and TypeScript request/response types for Phase 6A schedule optimizer payloads.
- [ ] Add client helpers for create, get, option/conflict/warning list, student list, and compare.
- [ ] Add Vitest schema and malformed-payload tests.
- [ ] Run `pnpm --filter @sapsos/shared test`.

### Task 6: Mock Seed

**Files:**
- Modify: `apps/api/app/seed_dev.py`
- Modify: `apps/api/tests/test_seed_dev.py`

- [ ] Extend mock sections and meetings for multiple sections per course, conflicts, Friday exclusion, online asynchronous, hybrid, lecture plus lab, closed, conditional eligibility, permission required, no section available, compact vs spread alternatives, and at least two feasible schedules.
- [ ] Preserve `source_type = MOCK` and `is_official = false`.
- [ ] Keep seed idempotent.

### Task 7: Frontend

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/styles.css`
- Modify: `tests/e2e/home.spec.ts`

- [ ] Add a read-only Semester Schedule Builder panel with mock student/term/plan controls, credit controls, Friday exclusion, time bounds, modality preference, generation, weekly/structured option display, warnings/conflicts, comparison, and required disclaimers.
- [ ] Handle loading, offline, no feasible/partial, schema error, warnings, permission-required, and asynchronous sections.
- [ ] Add Playwright route fixtures and E2E tests for create, no-Friday constraint, options, warnings, compare, API failure, schema error, and disclaimer.

### Task 8: Documentation and Quality Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA_MODEL.md`
- Modify: `docs/DOMAIN_RULES.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TEST_STRATEGY.md`
- Modify: `docs/DECISIONS.md`

- [ ] Document Semester Schedule Builder vs Long-Term Planner, hard constraints vs soft preferences, time conflict detection, eligibility integration, seat availability separation, mock data, non-registration boundaries, and Phase 6B next steps.
- [ ] Run requested local quality gates, report unavailable commands honestly, commit, push, open a draft PR, monitor CI, and fix real failures without merging the Phase 6A PR.
