# Phase 2A Academic Domain Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the read-only academic domain foundation for institutions, programs, courses, requirements, student records, mock seed data, and API access.

**Architecture:** Keep domain persistence in SQLAlchemy models under the FastAPI app, expose read-only `/api/v1` routers with Pydantic response models, and preserve source metadata on all mock records. Program identity remains separate from catalog/campus-specific ProgramVersion records; requirement rules use relational adjacency-list nodes with course options.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, PostgreSQL, pytest, Ruff, mypy, pnpm OpenAPI generation.

---

### Task 1: Persistence Model Tests

**Files:**
- Create: `apps/api/tests/test_academic_models.py`
- Modify: `apps/api/app/db/base.py`
- Create: `apps/api/app/models/academic.py`

- [ ] **Step 1: Write failing SQLite-backed constraint tests**

Cover uniqueness and check constraints for institution codes, campus codes, courses, program versions, requirement parent safety, course options, course equivalencies, active primary majors, attempts, transfer statuses, and substitutions.

- [ ] **Step 2: Run model tests and verify they fail**

Run: `cd apps/api && python -m pytest tests/test_academic_models.py -q`

Expected: import errors for missing academic models.

- [ ] **Step 3: Implement SQLAlchemy models with deterministic constraints**

Use UUID primary keys, string enum columns, check constraints, composite foreign keys, and partial unique indexes.

- [ ] **Step 4: Re-run model tests**

Run: `cd apps/api && python -m pytest tests/test_academic_models.py -q`

Expected: pass.

### Task 2: Migration

**Files:**
- Create: `apps/api/alembic/versions/20260622_0002_create_academic_domain.py`

- [ ] **Step 1: Add a reviewable Alembic revision**

Create all Phase 2A tables and constraints without modifying Phase 1 migration.

- [ ] **Step 2: Validate migration locally where database is available**

Run: `cd apps/api && python -m alembic upgrade head`

Expected: pass when PostgreSQL is running; otherwise report blocked and rely on CI.

### Task 3: Seed Tests and Seed Data

**Files:**
- Create: `apps/api/tests/test_seed_dev.py`
- Modify: `apps/api/app/seed_dev.py`

- [ ] **Step 1: Write failing tests for idempotent mock seed**

Create an in-memory test database, run the seed twice, assert counts do not increase, mock records are non-official, and the Finance requirement tree shape exists.

- [ ] **Step 2: Run seed tests and verify they fail**

Run: `cd apps/api && python -m pytest tests/test_seed_dev.py -q`

Expected: missing model/seed behavior failures.

- [ ] **Step 3: Implement deterministic UUID upsert seed**

Seed Mock University, Mock Main Campus, terms, Mock BS Finance 2024, mock courses, requirement tree, mock student, attempts, transfer/waiver/substitution examples, and a seed marker record.

- [ ] **Step 4: Re-run seed tests**

Run: `cd apps/api && python -m pytest tests/test_seed_dev.py -q`

Expected: pass.

### Task 4: Read-Only API

**Files:**
- Create: `apps/api/app/schemas/academic.py`
- Create: `apps/api/app/api/v1/academic.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_academic_api.py`

- [ ] **Step 1: Write failing API tests**

Verify `/api/v1/institutions`, `/api/v1/programs`, `/api/v1/programs/{program_version_id}`, `/api/v1/programs/{program_version_id}/requirements`, `/api/v1/courses`, `/api/v1/courses/{course_id}`, `/api/v1/students/{student_id}`, and `/api/v1/students/{student_id}/course-attempts`.

- [ ] **Step 2: Run API tests and verify they fail**

Run: `cd apps/api && python -m pytest tests/test_academic_api.py -q`

Expected: 404 for missing routes.

- [ ] **Step 3: Implement response models and router**

Return Pydantic models, not ORM objects; include source metadata; use consistent 404 payloads.

- [ ] **Step 4: Re-run API tests**

Run: `cd apps/api && python -m pytest tests/test_academic_api.py -q`

Expected: pass.

### Task 5: Documentation and Contract Artifacts

**Files:**
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA_MODEL.md`
- Modify: `docs/DOMAIN_RULES.md`
- Modify: `docs/TEST_STRATEGY.md`
- Modify: `docs/DECISIONS.md`
- Modify: `apps/api/openapi.json`
- Modify: `packages/shared/src/generated/openapi.json`

- [ ] **Step 1: Update docs to describe Phase 2A scope**

Document the schema, mock-only data rules, API boundaries, and deferred audit/eligibility/scheduling engines.

- [ ] **Step 2: Regenerate OpenAPI artifacts**

Run: `pnpm openapi:generate`

Expected: generated API artifacts include `/api/v1` read-only endpoints.

### Task 6: Quality Gate and Publish

**Files:**
- No planned source edits after this task unless verification finds a defect.

- [ ] **Step 1: Run required checks**

Run the pnpm, Python, migration, seed, and diff checks required by `AGENTS.md` and the Phase 2A brief.

- [ ] **Step 2: Commit and push**

Commit: `Implement phase 2a academic domain foundation`

Push: `git push -u origin codex-phase-2a-academic-domain`

- [ ] **Step 3: Open PR and monitor CI**

Open PR with base `main`, title `Implement Phase 2A academic domain foundation`, and do not merge it.
