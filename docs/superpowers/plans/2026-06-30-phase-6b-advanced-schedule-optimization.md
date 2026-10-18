# Phase 6B Advanced Schedule Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Phase 6A semester scheduler with richer hard constraints, weighted soft preferences, transparent scoring, option diversity, and advisory repair suggestions.

**Architecture:** Keep the deterministic bounded-search scheduler as the default optimizer and place it behind a small protocol-style boundary. Persist Phase 6B scoring, diversity, and repair suggestion snapshots beside the existing Phase 6A schedule tables so API responses remain explainable and replayable.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Next.js, TypeScript, Zod, Playwright.

---

### Task 1: Backend Red Tests

**Files:**
- Modify: `apps/api/tests/test_schedule_optimizer.py`

- [x] Add failing pytest coverage for score breakdown fields, preference weights, course/section priority weights, hard pinned/excluded validation, max combination warnings, diversity metadata, and repair suggestions.
- [x] Run `python -m pytest apps/api/tests/test_schedule_optimizer.py -q` and confirm failures describe missing Phase 6B fields or behavior.

### Task 2: Persistence and Schema

**Files:**
- Modify: `apps/api/app/models/academic.py`
- Modify: `apps/api/app/schemas/academic.py`
- Modify: `apps/api/app/api/v1/academic.py`
- Create: `apps/api/alembic/versions/20260630_0009_phase_6b_schedule_optimization.py`

- [x] Add JSON-backed preference and priority fields to `ScheduleConstraintSet`.
- [x] Add score component, score explanation, diversity, and difference fields to `ScheduleOption`.
- [x] Add `ScheduleRepairSuggestion` with suggestion type, affected constraint/course/section, estimated impact, message, and advisor-confirmation flag.
- [x] Add request/response schema fields while keeping Phase 6A request fields backward-compatible.
- [x] Map new ORM fields into API responses and detail payloads.

### Task 3: Optimizer Engine

**Files:**
- Modify: `apps/api/app/services/schedule_optimizer/engine.py`
- Modify: `apps/api/app/services/schedule_optimizer/__init__.py`

- [x] Introduce a `ScheduleOptimizer` protocol and keep `BoundedSearchScheduleOptimizer` as the default implementation.
- [x] Accept `preference_weights`, `course_priority_weights`, `section_priority_weights`, `prefer_morning`, `prefer_afternoon`, `prefer_no_gaps`, `diversity_mode`, `allow_partial_options`, and `max_combinations`.
- [x] Enforce hard constraints without silently weakening them.
- [x] Return deterministic scoring components for credit, compactness, days, gaps, modality, time preference, priority, and penalties.
- [x] Re-rank alternatives for diversity when requested and persist difference summaries.
- [x] Generate advisory repair suggestions when full feasible schedules are unavailable.

### Task 4: Seed and API Coverage

**Files:**
- Modify: `apps/api/app/seed_dev.py`
- Modify: `apps/api/tests/test_seed_dev.py`

- [x] Extend mock sections for near-duplicates, morning/afternoon choices, online/in-person tradeoffs, required/excluded section demos, permission-required relaxation, and no-feasible repair cases.
- [x] Keep all mock data `source_type = MOCK` and `is_official = false`.
- [x] Keep seed idempotent.
- [x] Add API tests for advanced request fields, invalid weights, invalid pinned/excluded sections, repair suggestions, compare output, and OpenAPI schema shape.

### Task 5: Shared Types and Frontend

**Files:**
- Modify: `packages/shared/src/index.ts`
- Modify: `packages/shared/src/index.test.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/styles.css`
- Modify: `tests/e2e/home.spec.ts`

- [x] Extend Zod schemas and client request types for Phase 6B schedule fields.
- [x] Add UI controls for preference weights, pinned/required sections, excluded sections, no-Friday, and partial option behavior.
- [x] Display score breakdown, ranking explanation, diversity summary, repair suggestions, and top-option comparison.
- [x] Preserve all mock-data, no-registration, seat-availability, no-waitlist, and advisor-confirmation disclaimers.
- [x] Add E2E assertions for controls, breakdown, repair suggestions, comparison, no-feasible state, and disclaimer text.

### Task 6: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA_MODEL.md`
- Modify: `docs/DOMAIN_RULES.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TEST_STRATEGY.md`
- Modify: `docs/DECISIONS.md`

- [x] Document hard constraints vs soft preferences, score ranges, deterministic diversity, repair suggestions, bounded search limits, and OR-Tools deferral.
- [x] Regenerate OpenAPI artifacts.
- [x] Run the required local checks and report local blockers exactly.
