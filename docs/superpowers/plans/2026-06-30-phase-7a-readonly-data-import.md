# Phase 7A Read-only Data Import Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, staging-only data import foundation for mock and user-provided transcript, catalog, section, and degree-audit fixture data without applying records to official academic tables.

**Architecture:** Add persisted import snapshots under the backend academic domain model, with `DataImportRun` as the root and imported records, mapping candidates, validation warnings, and preview summaries as child rows. Parsing, normalization, matching, and validation live in `apps/api/app/services/data_imports`, while API routes only validate input and serialize persisted results. The web app renders a compact read-only import preview panel using shared TypeScript schemas and client helpers.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Next.js, TypeScript, Zod, Vitest, Playwright.

---

### Task 1: Backend Domain Red Tests

**Files:**
- Modify: `apps/api/tests/test_academic_models.py`
- Create: `apps/api/tests/test_data_imports.py`

- [ ] Add failing model tests for import runs, files, records, mapping candidates, warnings, preview summaries, confidence ranges, mock-not-official constraints, and staging-only behavior.
- [ ] Add failing service/API-shape tests for transcript CSV, catalog CSV, section CSV, degree audit JSON, generic JSON, malformed/empty content, duplicate rows, unknown courses, unsupported grades, invalid meeting times, and preview summary counts.
- [ ] Run `python -m pytest apps/api/tests/test_academic_models.py apps/api/tests/test_data_imports.py -q` and confirm failures are caused by missing Phase 7A models/services.

### Task 2: Persistence and Migration

**Files:**
- Modify: `apps/api/app/models/academic.py`
- Create: `apps/api/alembic/versions/20260630_0010_phase_7a_data_imports.py`

- [ ] Add enums for import type, run status, file storage strategy, imported record type/status, mapping target/match type, and warning severity if existing warning severity is insufficient.
- [ ] Add `DataImportRun`, `DataImportFile`, `ImportedRecord`, `ImportMappingCandidate`, `ImportValidationWarning`, and `ImportPreviewSummary` ORM models.
- [ ] Add PostgreSQL-safe constraints for nonnegative file size, hash length, confidence ranges, nonempty warning messages, and `source_type = MOCK` implying `is_official = false`.
- [ ] Add Alembic migration from `20260630_0009`, without editing older migrations.

### Task 3: Parser, Normalizer, Matcher, Validator Service

**Files:**
- Create: `apps/api/app/services/data_imports/__init__.py`
- Create: `apps/api/app/services/data_imports/result.py`
- Create: `apps/api/app/services/data_imports/exceptions.py`
- Create: `apps/api/app/services/data_imports/normalizers.py`
- Create: `apps/api/app/services/data_imports/parsers/base.py`
- Create: `apps/api/app/services/data_imports/parsers/transcript_csv.py`
- Create: `apps/api/app/services/data_imports/parsers/course_catalog_csv.py`
- Create: `apps/api/app/services/data_imports/parsers/section_schedule_csv.py`
- Create: `apps/api/app/services/data_imports/parsers/degree_audit_json.py`
- Create: `apps/api/app/services/data_imports/parsers/generic_json.py`
- Create: `apps/api/app/services/data_imports/matchers.py`
- Create: `apps/api/app/services/data_imports/validators.py`
- Create: `apps/api/app/services/data_imports/engine.py`

- [ ] Define typed parser result dataclasses and parser/matcher protocols.
- [ ] Implement deterministic parser selection by import type and MIME/extension.
- [ ] Implement course-code normalization for `FIN-300`, `FIN 300`, and `fin300`.
- [ ] Implement narrow CSV/JSON fixture parsers with no network, OCR, browser automation, or raw document persistence.
- [ ] Implement deterministic matching against existing `Course`, `Section`, `AcademicTerm`, and `RequirementNode` records.
- [ ] Implement validation warnings for unknown course, ambiguous course match, unknown term, duplicate row, unsupported grade, missing/negative credits, invalid meeting time, unofficial source, and low confidence.
- [ ] Persist valid and invalid records for review; never apply them to `StudentCourseAttempt`, `Course`, `Section`, or requirement tables.

### Task 4: API and Schemas

**Files:**
- Modify: `apps/api/app/schemas/academic.py`
- Modify: `apps/api/app/api/v1/academic.py`
- Modify: `apps/api/openapi.json` through generation

- [ ] Add Pydantic request/response schemas for creating imports, validating content, records, mapping candidates, warnings, and preview.
- [ ] Add endpoints under `/api/v1/data-imports` and `/api/v1/students/{student_id}/data-imports`.
- [ ] Enforce content size limits and structured errors without logging raw file content.
- [ ] Return preview summaries with `official_application_ready = false` in Phase 7A.

### Task 5: Seed Fixtures and Backend Coverage

**Files:**
- Modify: `apps/api/app/seed_dev.py`
- Modify: `apps/api/tests/test_seed_dev.py`
- Modify/Create backend tests as needed

- [ ] Add mock source fixtures for clean transcript CSV, catalog CSV, section CSV, degree audit JSON, duplicate row, unknown course, unsupported grade, invalid meeting time, ambiguous match, and generic JSON.
- [ ] Keep all seed import runs `source_type = MOCK` and `is_official = false`.
- [ ] Keep seed idempotent and prove imports do not create official attempts/courses/sections.

### Task 6: Shared TypeScript Contract

**Files:**
- Modify: `packages/shared/src/index.ts`
- Modify: `packages/shared/src/index.test.ts`
- Modify: `packages/shared/src/generated/openapi.json` through generation

- [ ] Add Zod schemas and client helpers for import creation, details, records, mapping candidates, warnings, preview, student import list, and validate endpoint.
- [ ] Add Vitest coverage for successful import detail parsing, invalid official-application flags, schema errors, and client request helpers.

### Task 7: Frontend Preview Panel

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/styles.css`
- Modify: `tests/e2e/home.spec.ts`

- [ ] Add a compact Data Import Preview panel without redesigning existing panels.
- [ ] Support choosing import type and fixture content, running import, and showing summary, parsed records, mapping candidates, warnings, and parse failures.
- [ ] Display required staging-only disclaimers and handle loading, API failure, schema error, empty file, invalid rows, ambiguous matches, and offline state.
- [ ] Add Playwright coverage for mock transcript import, summary, records, warnings, mapping candidates, parse failure, staging-only disclaimer, API failure, and schema error.

### Task 8: Documentation, Verification, Publish

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA_MODEL.md`
- Modify: `docs/DOMAIN_RULES.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TEST_STRATEGY.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/SECURITY_AND_PRIVACY.md`

- [ ] Document Phase 7A staging-only import boundary, supported mock fixtures, no credential collection, no school login, no browser automation, no OCR-heavy parsing, validation/mapping warnings, and Phase 7B promotion deferral.
- [ ] Regenerate OpenAPI artifacts.
- [ ] Run all required local quality gates.
- [ ] Commit with `Implement phase 7a read-only data import foundation`.
- [ ] Push `codex-phase-7a-readonly-data-import`, create Draft PR, monitor CI, and fix only real Phase 7A failures.
