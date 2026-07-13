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
- `origin/main` is at merge commit
  `a6dc81e5dd7cd3724682432dc319b71ab836f764`; local `main` additionally
  contains the post-merge execution-plan checkpoint commit.
- PR 1 is merged as PR #35:
  `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/35`.
- PR 1 commit: `acde64e20f0404aa0c80d96bdf09ab76e957a071`.
- PR 1 delivered explicit `LOCAL_DESKTOP`/`SERVER` runtime isolation,
  loopback and non-wildcard CORS validation, preserved SERVER bearer
  authorization, stable app/data-directory contracts, and explicit Docker
  SERVER development defaults.
- Stage 5 PR #40 is merged. Its isolated implementation worktree remains at
  `D:\Crystal\.cache\worktrees\add-desktop-shell-proof` on branch
  `codex/add-desktop-shell-proof` for audit; `main` contains the merged proof.
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
- Partial: embedded local database, runtime discovery, API process supervision,
  and the unbundled desktop-shell proof are implemented; packaged runtime and
  production desktop shell do not yet exist.
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
5. API process supervision — complete.
6. Desktop-shell proof of concept — complete; PR #40 merged.
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

- Status: merged.
- Branch/worktree: `codex/add-process-supervision` /
  `D:\Crystal\.cache\worktrees\add-process-supervision`; worktree retained
  because generated browser/test caches were protected by Windows ACLs.
- Commits: `721279ad64b106c6f4c899fa5a618b52ee449bef`, review fix
  `fa7563663711aa2668c02aa9717a476a60921cb9`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/39`.
- CI: replacement run `29217386418` passed checks, E2E, and Docker Compose.
- Merge commit: `c9b18d540f1bb203d94fc7d991185a636184dc56`.
- Intended scope: API child-process startup, readiness waiting, graceful
  shutdown, crash/exit diagnostics, stale-manifest cleanup, duplicate-instance
  rejection, file log routing, and a bounded single restart policy.
- Explicitly out of scope: desktop shell, packaging, installer, Extension
  pairing, localhost request protection, and later product milestones.
- Validation: focused runtime/discovery/supervisor tests 10 passed;
  targeted Ruff, format, and MyPy passed.
- Integration proof: a real `python -m app.run` child started on a dynamic
  port, reached `ready`, routed output to `api.log`, and was gracefully
  stopped with its manifest removed.
- Remaining risks: Tauri toolchain availability, packaged runtime, and desktop
  shell remain incomplete.
- Exact next action: evaluate the Tauri desktop-shell proof after the required
  Rust toolchain is available.

### Stage 5 — desktop-shell proof of concept

- Status: complete; PR #40 merged.
- Branch/worktree: `codex/add-desktop-shell-proof` /
  `D:\Crystal\.cache\worktrees\add-desktop-shell-proof`.
- Evaluation candidate: Tauri, as required by the approved plan.
- The proof uses a minimal Tauri 2 Rust scaffold in `desktop-shell/` and starts
  the existing Node/Next Web UI plus FastAPI local runtime as child processes.
- The approved Windows prerequisites are installed: rustup 1.29.0, stable
  `rustc 1.97.0`, cargo 1.97.0, Visual Studio Build Tools with
  `Microsoft.VisualStudio.Workload.VCTools`, MSVC x64/x86, MSBuild, CMake, and
  Windows SDK 10.0.26100.0. WebView2 150.0.4078.65 was already installed.
- Live proof passed: a Tauri window rendered the existing Web UI, the API
  published a dynamic loopback runtime manifest and returned `/ready` 200, the
  Web UI returned 200, and file-backed SQLite was created under the local app
  data directory. Closing the window stopped the Tauri/API/Web processes and
  removed the owned runtime manifest.
- Review fix: the Web child now receives the discovered API `base_url` from the
  ready runtime manifest instead of a hard-coded port, so UI API requests use
  the actual dynamic loopback service.
- Scope decision: no packaging, installer, extension pairing, localhost
  protection, or later milestone code is included.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/40`.
- Merge commit: `a6dc81e5dd7cd3724682432dc319b71ab836f764`.
- CI: run `29265910798` passed checks, E2E, and Docker Compose for corrected
  head `385a0e90b81e47d455d5b3a675b487b18c3fb905`.
- Exact next action: stop at the Local Runtime Foundation boundary. Do not
  begin FastAPI/Web packaging or any later milestone without explicit scope.

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
- 2026-07-13 — PR 5 merged with bounded child-process supervision. The
  follow-up review added a PID ownership guard so a supervisor cannot adopt or
  delete another process's runtime manifest.
- 2026-07-13 — Stage 5 uses the approved minimal Tauri 2 proof. The shell
  starts the existing Web UI and FastAPI local runtime, waits for readiness,
  renders the Web UI in WebView2, and owns child-process shutdown. Packaging,
  installer work, and later milestones remain out of scope.
- 2026-07-13 — The approved official Windows prerequisites were installed and
  verified. The Tauri CLI bootstrapper was not required; the proof uses the
  official Tauri Rust crates directly. No repository source was changed during
  prerequisite installation.
- 2026-07-14 — PR #40 merged after the dynamic API base URL review correction.
  The shell now passes the ready manifest's discovered `base_url` to the Web
  child; CI run `29265910798` passed checks, E2E, and Docker Compose.
- 2026-07-14 — Automated review found that dynamic API discovery was not being
  passed to the Web child. The Tauri proof now waits for the ready manifest and
  passes its discovered `base_url` to `NEXT_PUBLIC_API_BASE_URL`.
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
| `rustup --version`, `rustc --version`, `cargo --version`, `rustup show` | Passed; stable `x86_64-pc-windows-msvc` active/default | Stage 5 Rust prerequisite |
| `cargo run` MSVC smoke program | Passed; printed `Hello, world!` | Stage 5 Rust/MSVC prerequisite |
| `vswhere` component query, MSVC `cl.exe`/`link.exe`, MSBuild, CMake, Windows SDK | Passed; Build Tools complete, MSVC 14.44.35207, SDK 10.0.26100.0 | Stage 5 Windows prerequisite |
| WebView2 registry detection | Passed; 150.0.4078.65 already installed | Stage 5 WebView2 prerequisite |
| `cargo check --manifest-path desktop-shell/src-tauri/Cargo.toml` | Passed | Stage 5 Rust scaffold |
| `cargo build --manifest-path desktop-shell/src-tauri/Cargo.toml --jobs 2` | Passed | Stage 5 Rust/Tauri build |
| Live Tauri launch, runtime manifest, `/ready`, Web UI `/` | Passed; dynamic loopback API, both HTTP probes 200, existing Web UI rendered | Stage 5 desktop-shell proof |
| Close-window lifecycle probe | Passed; Tauri/API/Web stopped and owned manifest removed | Stage 5 desktop-shell proof |
| Review-fix live proof with dynamic API base URL | Passed; manifest port `61232`, API `/ready` 200, Web UI `/` 200, clean close | Stage 5 review correction |
| CI run `29265910798` | Passed | corrected Stage 5 head, checks, E2E, Docker Compose |

## Resume checkpoint

- Current milestone: Local Runtime Foundation.
- Current stage: Stage 5 — desktop-shell proof of concept, complete.
- Current PR: #40 merged; Stage 4 PR 5 is merged.
- Current branch/worktree: `main` / `D:\Crystal`.
- Last completed action: PR #40 merged and local `main` fast-forwarded to
  `a6dc81e5dd7cd3724682432dc319b71ab836f764`.
- Last successful validation: CI run `29265910798`, corrected live Tauri proof,
  dynamic API `/ready` 200, Web UI `/` 200, and clean close lifecycle.
- Outstanding blocker: none for this milestone; later packaging is out of
  scope for this Goal.
- Exact resume instruction: wait for explicit authorization before beginning
  Stage 6 FastAPI runtime packaging.

## Scope confirmation

No work has begun on Extension pairing, localhost request protection, real
MyProgress parser expansion, Program/Catalog ingestion, real Section import,
real Schedule Optimization integration, UI restructuring, Backup/Restore,
production migration, diagnostics center, installer/uninstaller, beta, or
release-candidate work.
