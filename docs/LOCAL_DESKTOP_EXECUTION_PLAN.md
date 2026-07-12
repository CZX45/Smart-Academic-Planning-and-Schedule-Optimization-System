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
  `4e05c8bc46414cf688ada01c0bc083acf140c9e7`.
- PR 1 is merged as PR #35:
  `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/35`.
- PR 1 commit: `acde64e20f0404aa0c80d96bdf09ab76e957a071`.
- PR 1 delivered explicit `LOCAL_DESKTOP`/`SERVER` runtime isolation,
  loopback and non-wildcard CORS validation, preserved SERVER bearer
  authorization, stable app/data-directory contracts, and explicit Docker
  SERVER development defaults.
- The current PR is the isolated worktree
  `D:\Crystal\.cache\worktrees\establish-local-database-baseline`
  on branch `codex/establish-local-database-baseline`.
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
- Partial: local runtime mode exists, but embedded database and packaged
  runtime do not yet.
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
3. Local database baseline — current.
4. Dynamic runtime discovery.
5. API process supervision.
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

- Status: implementation in progress; not yet committed or pushed.
- Branch/worktree: `codex/establish-local-database-baseline` /
  `D:\Crystal\.cache\worktrees\establish-local-database-baseline`.
- Commit/PR/CI/merge: none yet.
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
- Remaining risks: rerun CI after the E2E environment fix, verify exact diff
  scope, and keep installer, backup, and upgrade migration work out of this PR.
- Exact next action: inspect the complete diff, commit only the Stage 2
  baseline files, push, and create the PR.

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

## Resume checkpoint

- Current milestone: Local Runtime Foundation.
- Current stage: Stage 2 — local database baseline.
- Current PR: PR 3, not yet created.
- Current branch/worktree: `codex/establish-local-database-baseline` /
  `D:\Crystal\.cache\worktrees\establish-local-database-baseline`.
- Last completed action: PR 2 merged and main synchronized to
  `4e05c8bc46414cf688ada01c0bc083acf140c9e7`; local SQLite startup, seed,
  and seeded E2E evidence executed.
- Last successful validation: all Stage 2 checks listed in the validation
  ledger, including seeded E2E 23/23.
- Outstanding blocker: default AppData directory creation is denied by this
  sandbox's host ACL; writable-path behavior is proven. Do not weaken the
  stable data-location contract to work around the sandbox.
- Exact resume instruction: inspect `git status --short` and
  `git diff --name-status`, confirm only Stage 2 baseline files are present,
  then commit and publish PR 3.

## Scope confirmation

No work has begun on Extension pairing, localhost request protection, real
MyProgress parser expansion, Program/Catalog ingestion, real Section import,
real Schedule Optimization integration, UI restructuring, Backup/Restore,
production migration, diagnostics center, installer/uninstaller, beta, or
release-candidate work.
