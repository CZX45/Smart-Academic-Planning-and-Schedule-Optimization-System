# Phase 8A Read-only Browser Extension Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe Manifest V3 browser extension foundation that extracts visible academic tables only after user action and sends confirmed data into the existing staging-only import pipeline.

**Architecture:** Add `apps/extension` as the canonical browser extension workspace. Keep extraction logic deterministic and DOM-driven, convert extracted tables to Phase 7A-compatible CSV payloads, and reuse `POST /api/v1/data-imports` with `source_type = BROWSER_EXTENSION`. Keep Phase 7B review/application as the only path from staging data into internal planning records.

**Tech Stack:** TypeScript strict mode, Vitest, MV3 extension APIs, existing FastAPI/SQLAlchemy import API, shared TypeScript API helpers, Next.js web UI, pytest and Playwright.

---

### Task 1: Browser Extension Extraction Core

**Files:**
- Create: `apps/extension/package.json`
- Create: `apps/extension/tsconfig.json`
- Create: `apps/extension/eslint.config.js`
- Create: `apps/extension/src/shared/types.ts`
- Create: `apps/extension/src/content/table-reader.ts`
- Create: `apps/extension/src/content/extractors.ts`
- Create: `apps/extension/tests/fixtures/*.html`
- Create: `apps/extension/tests/extractors.test.ts`
- Create: `apps/extension/tests/manifest-policy.test.ts`

- [ ] Write tests first for transcript, degree audit, catalog, section search, unknown page, empty table, malformed row, unknown columns, deterministic output, and password-field exclusion.
- [ ] Verify the extension tests fail because the package and extractors are not implemented yet.
- [ ] Implement the typed extractor model and DOM table reader.
- [ ] Add fixture-based parser helpers only for tests; production extraction must use browser DOM APIs.
- [ ] Verify extension tests pass.

### Task 2: MV3 Extension Shell And Confirmed Handoff

**Files:**
- Create: `apps/extension/manifest.json`
- Create: `apps/extension/src/popup/index.html`
- Create: `apps/extension/src/popup/popup.ts`
- Create: `apps/extension/src/background/service-worker.ts`

- [ ] Write tests proving minimal permissions, no host permissions, no credential capture fields, no form submission/click automation strings, and user confirmation required before sending.
- [ ] Verify tests fail before the manifest and popup handoff are implemented.
- [ ] Implement a popup that requests a current-tab extraction only after click, previews summary/warnings, and sends to the configured local API only after a second explicit confirmation.
- [ ] Keep content extraction read-only and do not add polling, alarms, registration, add/drop, swap, waitlist, or seat-grabbing behavior.
- [ ] Verify tests pass.

### Task 3: API And Shared Import Handoff

**Files:**
- Modify: `apps/api/app/models/academic.py`
- Modify: `apps/api/app/schemas/academic.py`
- Modify: `apps/api/app/services/data_imports/engine.py`
- Create: `apps/api/alembic/versions/20260701_0012_browser_extension_source_type.py`
- Modify: `apps/api/tests/test_data_imports.py`
- Modify: `packages/shared/src/index.ts`
- Modify: `packages/shared/src/index.test.ts`

- [ ] Write backend and shared tests that accept `source_type = BROWSER_EXTENSION`, keep `is_official = false`, keep `official_application_ready = false`, and preserve staging/review requirements.
- [ ] Verify targeted backend/shared tests fail before source-type support exists.
- [ ] Add the source type to Python models, Pydantic literals, SQLAlchemy check constraints via migration, and shared TypeScript request/response types.
- [ ] Add a browser-extension-specific staging disclaimer while reusing the Phase 7A import endpoint.
- [ ] Verify targeted backend/shared tests pass.

### Task 4: Web UI Integration

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/styles.css`
- Modify: `tests/e2e/home.spec.ts`

- [ ] Write E2E assertions that Browser Extension Import appears as experimental, staging-only, review-required, and no-registration-automation.
- [ ] Verify the E2E assertion fails before UI changes.
- [ ] Add a compact source-status panel inside the existing import section without redesigning the app.
- [ ] Ensure browser-extension import runs display `BROWSER_EXTENSION` source type in saved/import summaries.
- [ ] Verify targeted UI/E2E tests pass or report local browser limitations.

### Task 5: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA_MODEL.md`
- Modify: `docs/DOMAIN_RULES.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TEST_STRATEGY.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/SECURITY_AND_PRIVACY.md`

- [ ] Document Phase 8A as read-only, user-triggered, credential-free, no SAML/MFA bypass, no registration/add/drop/swap/waitlist/seat-grabbing, and staging-only.
- [ ] Document that Phase 7B review is still required before application.
- [ ] Add an ADR for the browser-extension import boundary.
- [ ] Mention the next possible phase as read-only section-change alerts only.

### Task 6: Verification, Commit, PR, And CI

**Files:**
- Update generated OpenAPI artifacts if schema changes require it.

- [ ] Run targeted tests after each implementation slice.
- [ ] Run the requested quality gates: `corepack pnpm format`, `corepack pnpm lint`, `corepack pnpm typecheck`, `corepack pnpm test`, `corepack pnpm build`, `corepack pnpm openapi:generate`, `corepack pnpm openapi:check`, `corepack pnpm e2e`, `git diff --check`, `python -m ruff check apps/api`, `python -m ruff format --check apps/api`, `cd apps/api && python -m mypy .`, and `cd apps/api && python -m pytest`.
- [ ] Commit with `Implement phase 8a read-only browser extension import`.
- [ ] Push `codex-phase-8a-readonly-browser-extension-import`.
- [ ] Create a draft PR titled `Implement Phase 8A read-only browser extension import`.
- [ ] Monitor CI and fix real failures. Do not merge the Phase 8A PR.
