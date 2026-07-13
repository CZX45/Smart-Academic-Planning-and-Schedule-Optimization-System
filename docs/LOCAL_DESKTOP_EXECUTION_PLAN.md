# Local Desktop Execution Plan

## Purpose

The official product is a single-user Windows Local Desktop application. Each
student runs an independent copy. Imports, review/apply, Degree Audit, Course
Eligibility, planning, schedule optimization, and data storage are local by
default. The product is advisory and read-only: it may analyze and explain
academic data, but it must never register a student for a course or modify the
school's official records.

The browser extension may inspect only a page the user has actively opened and
can currently see after manually authenticating to the school portal. Local
data must remain clearly distinguished as official, imported, student-provided,
mock, inferred, or requiring review.

## Permanent prohibitions

Never implement automatic registration, add/drop/swap, waitlist actions, seat
grabbing or reservation, high-frequency registration polling, automatic portal
login, collection of school passwords, MFA secrets, cookies, or portal tokens,
modification of official transcripts, Degree Audit data, or registration
records, automatic advisor approval, or circumvention of SAML, MFA, CAPTCHA,
rate limits, authorization, or other school access controls.

The following directions are frozen unless explicitly reauthorized: SSO/OIDC,
tenant administration, advisor SaaS, multi-user SaaS, cloud databases, cloud
sync, mobile applications, enterprise RBAC, PostgreSQL RLS, paid subscriptions,
and multi-school platform work. Existing SERVER capabilities remain preserved,
but LOCAL_DESKTOP is the current official product.

## Current verified state

- Repository: `D:\Crystal`.
- `main` is synchronized with `origin/main` at merge commit
  `47841e2f9d3b804d820710ba39cd4ed9cdb0dcda`.
- PR 1 is merged as PR #35:
  `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/35`.
- PR 1 commit: `acde64e20f0404aa0c80d96bdf09ab76e957a071`.
- PR 1 delivered explicit `LOCAL_DESKTOP`/`SERVER` runtime isolation,
  loopback and non-wildcard CORS validation, preserved SERVER bearer
  authorization, stable app/data-directory contracts, and explicit Docker
  SERVER development defaults.
- The current PR is the isolated worktree
  `D:\Crystal\.cache\worktrees\add-process-supervision` on branch
  `codex/add-process-supervision`.
- Existing core academic domain, import staging, review/apply, course state,
  Degree Audit, eligibility, planner, section monitoring, and schedule
  optimizer logic remains present. Real school data and real section imports
  are not authoritative product data until reviewed and source-tagged.
- Mock/seed data remains development-only and must never be presented as
  official school policy.
- SERVER remains PostgreSQL-backed. LOCAL_DESKTOP now defaults to file-backed
  SQLite under the stable app-data contract, with deterministic local schema
  bootstrap and schema-version tracking.
- The repository-wide Prettier gate has known pre-existing drift in
  `apps/extension` and `packages/shared`; unrelated cleanup is out of scope.

### Stage 1 evidence

Direct SQLAlchemy metadata creation on SQLite succeeds repeatedly and produces
68 tables, 176 foreign keys, and 86 indexes. UUID, JSON, enum, timestamp
default, transaction rollback, and foreign-key cascade primitives are covered
by `apps/api/tests/test_sqlite_compatibility.py`.

The existing PostgreSQL Alembic history is not currently a safe SQLite
initializer. A direct sequential migration proof reaches revision
`20260623_0004_create_degree_audit_core` and fails because SQLite does not
support the migration's direct check-constraint drop/alter operation. The
history also contains additional direct PostgreSQL UUID declarations and
constraint alterations. This is a migration compatibility defect, not a reason
to make Docker/PostgreSQL the final LOCAL_DESKTOP dependency.

### Feature classification

- Local Desktop target: embedded database, local API process, local web UI,
  runtime discovery, process supervision, and packaged desktop shell.
- Partial: embedded local database and runtime discovery are implemented;
  process supervision, packaged runtime, and desktop shell do not yet exist.
- Mock-only: development seed fixtures and unreviewed sample academic data.
- SERVER-only/current development path: PostgreSQL-backed Docker Compose and
  explicit bearer-authenticated SERVER runtime.
- Known technical debt: migration history is PostgreSQL-specific in places;
  local schema versioning, data directory handling, runtime discovery,
  supervision, packaging, and extension pairing are not complete.

## Architecture decisions

1. `LOCAL_DESKTOP` is the default product mode; `SERVER` is explicit and
   optional. `ENVIRONMENT` is independent of `PRODUCT_MODE`.
2. LOCAL_DESKTOP requires an embedded database. PostgreSQL remains valid for
   SERVER and development integration testing.
3. FastAPI is preserved unless runtime packaging evidence disproves its
   suitability. The desktop shell remains subject to proof, with Tauri as the
   preferred evaluation candidate.
4. Extension pairing is required before final local request-security
   completion. It is not part of the current Local Runtime Foundation.
5. Real Section Optimization remains inside MVP. Section Monitoring remains
   after MVP.
6. Because the existing PostgreSQL Alembic history cannot currently initialize
   SQLite safely, the next database PR will evaluate a separate deterministic
   LOCAL_DESKTOP baseline/bootstrap with version tracking before considering
   any data-preserving migration corrections. No academic semantics may change.

## Dependency-ordered milestones

1. PR 1 delivery and runtime-mode isolation — complete.
2. Local embedded-database compatibility proof — complete.
3. Local database baseline — complete.
4. Dynamic runtime discovery — complete.
5. API process supervision — current.
6. Desktop-shell proof of concept.
7. FastAPI runtime packaging.
8. Web UI packaging.
9. Extension pairing.
10. Localhost request protection.
11. Real MyProgress stabilization.
12. Reviewed Program/Catalog rules.
13. Real Section import.
14. Real Section optimizer integration.
15. UI workflow modularization.
16. Backup/Restore.
17. Safe migration and rollback.
18. Diagnostics.
19. Windows Installer/Uninstaller.
20. Packaged Desktop E2E.
21. Controlled Student Beta.
22. Release Candidate.

## Progress log

### PR 1 — runtime-mode isolation

- Status: merged.
- Branch: `codex/pr-1`; remote branch `codex-pr-1` remains for audit.
- Worktree: removed after merge because Git confirmed it was clean and merged.
- Commit: `acde64e20f0404aa0c80d96bdf09ab76e957a071`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/35`.
- CI: required CI run 29195826320 passed checks, E2E, and Docker Compose.
- Merge commit: `99db1f6469308d25cb6bbd64426dcdabc20d4ccc`.
- Validation: `corepack pnpm test`, `corepack pnpm lint`,
  `corepack pnpm typecheck`, `corepack pnpm build`, `corepack pnpm e2e`
  (23/23), OpenAPI drift, Alembic, Docker Compose, Ruff, and
  `git diff --check` were reported and CI-confirmed.
- Decisions: default LOCAL_DESKTOP, explicit SERVER, independent environment,
  loopback local API, non-wildcard CORS, preserved SERVER authorization.
- Remaining risks: embedded database and packaged runtime are not implemented;
  known unrelated Prettier baseline drift remains.
- Exact next action: validate and merge the first local embedded-database proof
  PR after its focused and full checks pass.

### PR 2 — prove local embedded-database compatibility

- Status: merged.
- Branch: `prove-local-embedded-database-compatibility`; worktree removed after
  merge, with generated cache residue blocked by Windows ACL.
- Commit: `03795294c18756a243f610d37d9d887de9ab3203`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/36`.
- CI: run `29196320833` passed checks, E2E, and Docker Compose.
- Merge commit: `4e05c8bc46414cf688ada01c0bc083acf140c9e7`.
- Validation: direct metadata proof passed; direct sequential Alembic proof is
  blocked at revision `20260623_0004`; focused SQLite proof 3 passed; API
  regression 149 passed; recursive tests, lint, typecheck, build, OpenAPI
  drift, Ruff, format, MyPy, E2E 23/23, and `git diff --check` passed.
- Decision recorded: preserve PostgreSQL SERVER history and use a separate
  local baseline/bootstrap rather than weakening academic semantics.
- Exact next action: validate and publish the Stage 2 baseline PR below.

### PR 3 — establish local database baseline

- Status: merged.
- Branch: `establish-local-database-baseline`; worktree removed after merge.
- Commits: `44878e96763372bb5a268a766b5b4e4286a99a24`,
  `077a74faeb8e62b505837718ffa51d248b6d2684`,
  `d495286a7a6310d390fb0f19141c6b05ff46433b`,
  `f35431f5a8af8de2b32f1e088c8aa22503081108`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/37`.
- CI: run `29197278818` passed checks, E2E, and Docker Compose.
- Merge commit: `d766037e758ed194ccbcb4c7ecf7f393cb4f2637`.
- Changes in scope: SQLite is the LOCAL_DESKTOP default; PostgreSQL remains
  required for SERVER; SQLite engine options, file-directory creation, a
  deterministic metadata bootstrap, local schema-version tracking, startup
  initialization, standalone local seeding, E2E startup support, and explicit
  SERVER/PostgreSQL CI setup for checks are implemented.
- Validation: API regression 151 passed; recursive tests, lint, typecheck,
  build, OpenAPI drift, Ruff, format, and MyPy passed. File-backed SQLite was
  initialized twice and seeded twice with one institution. Seeded SQLite E2E
  passed 23/23. Default AppData startup is blocked in this sandbox by an ACL on
  `C:\Users\hp\AppData\Local\SAPSOS`; the same flow passed with a writable
  SQLite path.
- Decisions: LOCAL_DESKTOP uses embedded SQLite with schema bootstrap and
  version tracking; checks preserve SERVER/PostgreSQL; E2E uses seeded local
  SQLite; production SQLite foreign keys are enforced.
- Remaining risks: AppData ACL is environment-specific; installer, backup,
  and upgrade migration remain later stages.
- Exact next action: continue with PR 4 dynamic runtime discovery.

### PR 4 — add dynamic runtime discovery

- Status: merged.
- Branch/worktree: `codex/add-dynamic-runtime-discovery` /
  `D:\Crystal\.cache\worktrees\add-dynamic-runtime-discovery`; worktree
  retained because Windows ACL-protected caches blocked safe removal.
- Commit: `46e3bca73858da4aeb82c3de1e8891bcbc817ab3`; review fix commit
  `00e78986df8e3ef1d0ce80cc1e629ec6db1da5a8`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/38`.
- CI: replacement run `29216453312` passed checks, E2E, and Docker Compose.
- Merge commit: `47841e2f9d3b804d820710ba39cd4ed9cdb0dcda`.
- Changes in scope: dynamic loopback port allocation when `API_PORT=0`, typed
  protocol/versioned runtime manifest, atomic publication, stale-process
  detection, second-instance conflict protection, startup readiness update,
  and the local `/runtime` discovery endpoint.
- Validation: API regression 156 passed; runtime discovery tests 4 passed;
  recursive tests, lint, typecheck, build, Ruff, formatting, and MyPy passed.
  Seeded writable-SQLite E2E passed 23/23. Manual startup proved a dynamic
  port, manifest status `ready`, `/runtime` status `ready`, and `/ready` 200.
  OpenAPI was regenerated for `/runtime` and `RuntimeManifest`, and CI passed
  the committed OpenAPI drift check.
- Review fixes: IPv6 literals are bracketed in runtime URLs, and shutdown
  removes the owned manifest even after the listening socket closes.
- Remaining risks: process supervision, desktop shell, packaging, and
  installer work remain incomplete.
- Exact next action: implement and validate the bounded API process supervisor
  in the isolated Stage 4 worktree below.

### PR 5 — API process supervision

- Status: implementation in progress; no commit or PR yet.
- Branch/worktree: `codex/add-process-supervision` /
  `D:\Crystal\.cache\worktrees\add-process-supervision`.
- Intended scope: API child-process startup, readiness waiting, graceful
  shutdown, crash/exit diagnostics, stale-manifest cleanup, duplicate-instance
  rejection, file log routing, and a bounded single restart policy.
- Explicitly out of scope: desktop shell, packaging, installer, Extension
  pairing, localhost request protection, and later product milestones.
- Validation so far: focused runtime/discovery/supervisor tests 10 passed;
  targeted Ruff, format, and MyPy passed.
- Integration proof: a real `python -m app.run` child started on a dynamic
  port, reached `ready`, routed output to `api.log`, and was gracefully
  stopped with its manifest removed.
- Remaining risks: full regression gates, CI, review, and integration proof
  remain.
- Exact next action: add restart/lifecycle coverage as needed, inspect the
  complete diff, run the full repository gates, then publish PR 5.

## Decision log

- 2026-07-12 — PR 1 was pushed to non-hierarchical `codex-pr-1` because the
  existing remote `codex` branch must not be modified; PR #35 merged normally
  after exact-head CI success.
- 2026-07-12 — SQLAlchemy model metadata is sufficiently portable for an
  initial SQLite proof, but the historical PostgreSQL Alembic path is not.
  The first failing operation is a direct check-constraint alteration in
  `20260623_0004`; local baseline/bootstrap is the safer next evaluation.
- 2026-07-12 — No Extension pairing, real academic-data expansion, real
  Section import, optimizer integration, installer, Backup/Restore, or later
  milestone work began.
- 2026-07-12 — LOCAL_DESKTOP now defaults to file-backed SQLite under the
  stable app-data contract; SERVER remains PostgreSQL-backed and Alembic-owned.
  Local startup creates the schema and records schema version 1. No production
  upgrade migration or installer behavior is included.
- 2026-07-12 — Dynamic runtime discovery uses a versioned atomic manifest,
  loopback port allocation, stale process detection, and a single-instance
  ownership check. API process supervision remains a later stage.
- 2026-07-13 — PR 4 merged with a versioned runtime manifest and `/runtime`
  discovery endpoint. The follow-up review fixed IPv6 URL construction and
  shutdown manifest cleanup before merge.
- 2026-07-13 — Stage 4 supervision is isolated behind an explicit supervisor
  object. It starts `python -m app.run`, waits for manifest plus `/ready`,
  routes child output to a file, reports bounded log-tail diagnostics, shuts
  down gracefully before killing after timeout, rejects duplicate live
  instances, cleans stale manifests before launch, and permits at most one
  automatic restart by default.
- 2026-07-13 — The usage limit cleared. Full Stage 3 local gates and seeded
  writable-SQLite E2E completed; default AppData remained an environment ACL
  limitation, so runtime discovery was verified with an isolated writable
  LOCALAPPDATA path.
- 2026-07-12 — CI run `29196835215` showed the existing Alembic setup steps
  inherited the new SQLite default and failed before checks/E2E. The workflow
  now sets explicit SERVER/PostgreSQL environment only for migration, seed,
  and E2E setup, preserving LOCAL_DESKTOP as the ordinary test default.
- 2026-07-12 — Corrected CI run `29196975368` proved checks and Docker, but
  E2E returned 401 when forced into SERVER bearer mode. E2E now uses seeded
  file-backed LOCAL_DESKTOP SQLite; checks continue to validate SERVER
  PostgreSQL separately.
- 2026-07-12 — Automated review identified that SQLite foreign keys were
  enabled only in tests. Production SQLite connections now enable
  `PRAGMA foreign_keys=ON`, with a focused regression test; the standalone
  seed entrypoint also initializes the local schema before writing.

## Validation ledger

| Command or proof | Result | Scope |
| --- | --- | --- |
| PR 1 CI run `29195826320` | Passed | checks, E2E, Docker Compose |
| `git diff --check` on PR 1 | Passed | PR 1 diff |
| SQLite `Base.metadata.create_all` twice | Passed | 68 tables, 176 FKs, 86 indexes |
| Sequential existing Alembic upgrades on SQLite | Blocked | revision `20260623_0004`; direct constraint alteration unsupported |
| `python -m pytest apps/api/tests/test_sqlite_compatibility.py -q` | Passed, 3 tests | model/schema/storage proof |
| `python -m pytest` in `apps/api` | Passed, 149 tests, 1 warning | API regression |
| `CI=true corepack pnpm test` | Passed | recursive API/extension/shared/web tests |
| `CI=true corepack pnpm lint` | Passed | recursive lint |
| `CI=true corepack pnpm typecheck` | Passed | recursive type checking |
| `CI=true corepack pnpm build` | Passed | API/extension/shared/web build |
| `CI=true corepack pnpm openapi:check` | Passed | generated OpenAPI drift |
| `CI=true corepack pnpm e2e` | Passed, 23 tests | local API/web E2E |
| `python -m ruff check .` / `format --check .` | Passed | API lint/format |
| `python -m mypy .` | Passed | API strict typing |
| `git diff --check` | Passed | PR 2 diff |
| `python -m pytest` in `apps/api` | Passed, 151 tests, 1 warning | Stage 2 API regression |
| `CI=true corepack pnpm test` | Passed | Stage 2 recursive tests |
| `CI=true corepack pnpm lint` | Passed | Stage 2 recursive lint |
| `CI=true corepack pnpm typecheck` | Passed | Stage 2 recursive typecheck |
| `CI=true corepack pnpm build` | Passed | Stage 2 build |
| `CI=true corepack pnpm openapi:check` | Passed | Stage 2 OpenAPI drift |
| `CI=true corepack pnpm e2e` with seeded writable SQLite | Passed, 23 tests | Stage 2 local runtime E2E |
| `python -m app.seed_dev` twice with writable SQLite | Passed, 1 institution | Stage 2 persistence/idempotence |
| CI run `29196835215` before workflow fix | Failed at Alembic | SQLite default reached PostgreSQL-only CI setup |
| CI YAML parse / `node --check scripts/run-e2e.mjs` | Passed | CI follow-up validation |
| Focused config/local database tests after CI fix | Passed, 22 tests | CI follow-up validation |
| `python -m pytest tests/test_runtime_discovery.py -q` | Passed, 4 tests | Stage 3 discovery proof |
| Manual `python -m app.run` with `API_PORT=0` | Passed | dynamic port, ready manifest, `/runtime`, `/ready` |
| `python -m pytest` in `apps/api` | Passed, 156 tests, 1 warning | Stage 3 API regression |
| `CI=true corepack pnpm test` | Passed | Stage 3 recursive tests |
| `CI=true corepack pnpm lint` | Passed | Stage 3 recursive lint |
| `CI=true corepack pnpm typecheck` | Passed | Stage 3 recursive typecheck |
| `CI=true corepack pnpm build` | Passed | Stage 3 build |
| `python -m ruff check .` / `format --check .` | Passed | Stage 3 API lint/format |
| `python -m mypy .` | Passed | Stage 3 API strict typing |
| Seeded writable-SQLite `CI=true corepack pnpm e2e` | Passed, 23 tests | Stage 3 local runtime E2E |
| `python -m pytest tests/test_runtime_supervisor.py tests/test_runtime_discovery.py` | Passed, 10 tests | Stage 4 focused lifecycle/discovery proof |
| `python -m ruff check app/runtime tests/test_runtime_supervisor.py` / `format --check` | Passed | Stage 4 targeted lint/format |
| `python -m mypy app/runtime` | Passed | Stage 4 targeted strict typing |
| Real `ApiProcessSupervisor` child proof | Passed | dynamic port, readiness, log routing, graceful shutdown, manifest cleanup |
| Seeded writable-SQLite `CI=true corepack pnpm e2e` | Passed, 23 tests in CI; local run reached 22/23 before the pre-existing seeded-import 404 setup mismatch | Stage 4 regression; CI remains authoritative |

## Resume checkpoint

- Current milestone: Local Runtime Foundation.
- Current stage: Stage 4 — API process supervision.
- Current PR: PR 5, not yet created.
- Current branch/worktree: `codex/add-process-supervision` /
  `D:\Crystal\.cache\worktrees\add-process-supervision`.
- Last completed action: PR 4 merged and main synchronized to
  `47841e2f9d3b804d820710ba39cd4ed9cdb0dcda`; Stage 4 supervisor skeleton and
  focused tests are implemented.
- Last successful validation: focused runtime/discovery/supervisor tests 8
  passed; targeted Ruff, format, and MyPy passed.
- Outstanding blocker: full validation, commit, PR, CI, and review remain.
- Exact resume instruction: inspect `git status --short` and the complete diff,
  finish only Stage 4 lifecycle coverage, then run the repository gates.

## Scope confirmation

No work has begun on Extension pairing, localhost request protection, real
MyProgress parser expansion, Program/Catalog ingestion, real Section import,
real Schedule Optimization integration, UI restructuring, Backup/Restore,
production migration, diagnostics center, installer/uninstaller, beta, or
release-candidate work.
