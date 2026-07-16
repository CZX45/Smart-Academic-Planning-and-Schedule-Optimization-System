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
- `main` and `origin/main` are synchronized at the Diagnostics UI and safe
  export merge commit `e23c44c50a5f9cf5eee6fa0a5744953cd7fdd98c`. PRs #73 and
  #74 are merged; this document records the Diagnostics closeout.
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
- Implemented: file-backed LOCAL_DESKTOP SQLite bootstrap, runtime discovery,
  API process supervision, Tauri desktop shell, packaged FastAPI runtime,
  packaged static Web UI, secure Extension pairing, and localhost request
  protection are present in the merged product path.
- Mock-only: development seed fixtures and unreviewed sample academic data.
- SERVER-only/current development path: PostgreSQL-backed Docker Compose and
  explicit bearer-authenticated SERVER runtime.
- Known technical debt: migration history is PostgreSQL-specific in places;
  the historical SQLite Alembic incompatibility remains documented and is not
  part of Backup/Restore.

## Architecture decisions

1. `LOCAL_DESKTOP` is the default product mode; `SERVER` is explicit and
   optional. `ENVIRONMENT` is independent of `PRODUCT_MODE`.
2. LOCAL_DESKTOP requires an embedded database. PostgreSQL remains valid for
   SERVER and development integration testing.
3. FastAPI is the supervised LOCAL_DESKTOP API runtime. The Tauri shell starts
   it, discovers its runtime manifest, and loads the static Web export through
   the runtime `api_base_url` bridge.
4. Extension pairing and the localhost request boundary are complete merged
   security contracts; Backup/Restore must preserve them.
5. Real Section Optimization remains inside MVP. Section Monitoring remains
   after MVP.
6. Because the existing PostgreSQL Alembic history cannot currently initialize
   SQLite safely, LOCAL_DESKTOP uses the separate deterministic baseline,
   version tracking, and safe migration orchestration recorded below. No
   academic semantics change, and the PostgreSQL history remains authoritative
   for SERVER mode.

## Dependency-ordered milestones

1. PR 1 delivery and runtime-mode isolation — complete.
2. Local embedded-database compatibility proof — complete.
3. Local database baseline — complete.
4. Dynamic runtime discovery — complete.
5. API process supervision — complete.
6. Stage 5 — desktop-shell proof of concept — complete; PR #40 merged.
7. Stage 6 — FastAPI runtime packaging — complete; PR #44 merged.
8. Stage 7 — Web UI packaging — complete; PR #45 merged.
9. Stage 8A — secure local Extension pairing — complete; PR #46 merged.
10. Stage 8B — localhost request protection — complete; PR #47 merged.
11. Stage 9 — Real MyProgress stabilization — complete; PRs #49 and #50 merged.
12. Stage 10 reviewed Program/Catalog architecture and post-merge correctness —
    complete; PRs #52, #53, and #54 merged.
13. Stage 11 Real Section Import — complete; PRs #56, #57, and #58 merged.
14. Real Section Optimizer Integration — complete; PRs #60 and #61 merged.
15. UI workflow modularization — complete; PRs #63 and #64 merged.
16. Backup/Restore — complete through PRs #66, #67, and the documentation
    closeout.
17. Safe migration and rollback — complete through PRs #70, #71, and this
    documentation closeout.
18. Diagnostics — complete through PRs #73, #74, and this documentation
    closeout.
19. Windows Installer/Uninstaller — next milestone; not started.
20. Packaged Desktop E2E.
21. Controlled Student Beta.
22. Release Candidate.

The Local Runtime Foundation includes stages 1–8: local database, runtime
discovery and supervision, desktop-shell proof, FastAPI runtime packaging, Web
UI packaging, secure Extension pairing, and localhost request protection. The
foundation is complete through the merged Stage 8B security boundary. Stage 9
is complete through the merged 9A and 9B checkpoints.

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
- Follow-up completed: Stage 6 was subsequently implemented and merged through
  PR #44; later milestones were kept out of this Stage 5 implementation.

### PR 6 — reconcile the Stage 5 closeout plan

- Status: merged.
- Branch: `stage5-plan-closeout`; worktree: `D:\Crystal`.
- Commits: `15b574b`, `ae1825f`, `3deb320`, and `2d96b6b`.
- PR URL: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/41`.
- CI: run `29267033334` passed checks, E2E, and Docker Compose; the follow-up
  numbering correction was validated by run `29267033334` after head update.
- Merge commit: `45407d761dfbef63b20d9fa58f7d55a029387b95`.
- Validation: one-file documentation diff, `git diff --check`, full plan read,
  and comparison with `ROADMAP.md`, `ARCHITECTURE.md`, `DECISIONS.md`, and
  PR #40 state.
- Decision: Local Runtime Foundation includes Stages 1–8; Stage 6 FastAPI
  runtime packaging is the single next milestone, followed by Stage 7 Web UI
  packaging. No source code or later feature work was started.
- Remaining risks: packaged runtime proof, Windows clean-environment behavior,
  and packaging-specific antivirus/path behavior remain unverified.
- Follow-up completed: Stage 6 was subsequently merged through PR #44, Stage 7
  through PR #45, and Stage 8A/8B through PRs #46/#47.

### Stage 6 — package the FastAPI LOCAL_DESKTOP runtime

- Status: complete and merged through PR #44.
- Merge commit: `4d265ff001dc09211949bfa0860c29976b10b874`.
- Packaging decision: PyInstaller one-folder (`sapsos-api\\sapsos-api.exe`).
  FastAPI/Uvicorn, SQLAlchemy, SQLite, Pydantic/settings, and the existing
  `app.run` entrypoint remain intact. One-folder is preferred over one-file so
  bundled resources, logs, crash diagnostics, and antivirus behavior remain
  inspectable and the runtime does not extract itself at every start.
- Rejected alternatives: Nuitka was not selected because it is not installed
  or established in this repository and would add a larger compilation and
  troubleshooting surface for this proof. PyInstaller one-file was rejected
  for extraction-time resource handling, startup, crash diagnostics, and
  antivirus/SmartScreen tradeoffs. No evidence justified replacing FastAPI or
  changing the local schema/bootstrap architecture.
- Build contract: `scripts/windows/Build-FastAPI-Runtime.ps1` installs the
  pinned developer-only PyInstaller dependency, cleans an isolated output
  directory, builds from `apps/api/packaging/sapsos-api.spec`, and produces
  `dist\\local-desktop-api\\sapsos-api\\sapsos-api.exe`. The script records
  commit/product-mode metadata in the isolated build directory and fails with
  actionable messages for missing Python build tools or missing artifacts.
- Desktop integration: setting `SAPSOS_API_EXECUTABLE` makes the Tauri shell
  launch the packaged executable and fail closed if it is missing. When that
  variable is absent, the existing `PYTHON -m app.run` development proof is
  preserved. The packaged path does not silently fall back to Python.
- Runtime contract preserved: `PRODUCT_MODE=LOCAL_DESKTOP`, dynamic loopback
  port discovery, owned runtime manifest, `/runtime`, `/ready`, SQLite
  bootstrap, persistence, graceful shutdown, restart, and server-mode
  PostgreSQL/Bearer behavior remain unchanged.
- Clean-environment proof: no Windows VM or Sandbox was available. The
  documented fallback simulation launched the packaged executable with
  `PATH=C:\\Windows\\System32;C:\\Windows`, so no Python executable was
  discoverable through PATH; Python remained installed elsewhere on the build
  machine. The artifact ran from its one-folder output directory, with the
  source checkout present elsewhere on disk but not used as the runtime working
  directory. It reached `/ready` 200, published dynamic ports 63358 and
  63366 across restart, initialized the isolated SQLite file, and preserved its
  size across restart. Supervisor proof removed the owned manifest on stop.
  This is an honest controlled fallback simulation, not a clean Windows image.
- Measurements: the PyInstaller build completed in approximately 97 seconds;
  the one-folder artifact contains 1,570 files totaling 91.71 MiB, with a
  15.50 MiB executable. Packaged startup to the first ready probe was 4.23
  seconds in the controlled proof. These are machine-specific proof
  measurements, not release performance guarantees.
- Known limitations: this stage does not sign binaries, produce an installer,
  package the Web UI, remove Node.js, or claim antivirus/SmartScreen approval.

- Validation completed: API pytest 165 passed; repository Vitest 91 passed;
  repository lint, typecheck, build, OpenAPI drift, API Ruff, API format,
  strict MyPy, Tauri cargo fmt/check, packaged artifact build, packaged
  no-Python-PATH startup/restart, supervisor lifecycle, missing-build-tool
  failure, and Playwright E2E 23/23 passed. The first E2E attempt was blocked
  by the known AppData ACL and missing browser cache under the temporary
  `LOCALAPPDATA`; the successful rerun used writable `LOCALAPPDATA` and the
  existing Playwright browser cache explicitly.

### Stage 7 — package the LOCAL_DESKTOP Web UI

- Status: complete and merged through PR #45.
- Merge commit: `ad57e944fcb95d28311d0018a553dd4d2d2cf5b1`.
- Decision: Next.js static export is viable and selected. The current UI has
  only static App Router routes and browser-side API calls, so a packaged Node
  server is unnecessary. Release Tauri builds load
  `dist\local-desktop-web` directly and compile out the development-server
  launch.
- Build contract: `scripts/windows/Build-Web-UI.ps1`, exposed as
  `corepack pnpm web:package:windows`, builds the Web UI from the lockfile and
  copies the export to the deterministic `dist\local-desktop-web` directory.
  It records commit, strategy, file count, byte count, and the runtime bridge
  in `build-manifest.txt`; missing Corepack or missing `index.html` fails with
  an actionable message.
- Runtime bridge: after the packaged FastAPI executable publishes a ready
  manifest, Tauri creates the release window with
  `index.html?api_base_url=<manifest base_url>`. The Web UI validates that URL
  and uses it for all existing API-backed workflows. It does not hard-code an
  API port or use a build-time dynamic `NEXT_PUBLIC_*` value.
- Measurements: the controlled build produced 28 files totaling 1,133,023
  bytes. The Web packaging script completed in 5.95 seconds in this worktree.
  These are
  machine-specific measurements, not release guarantees.
- Validation completed so far: Web Vitest 14/14, Web lint, Web typecheck,
  static export, generated-asset scan, Tauri cargo fmt/check, and release
  cargo build. The generated asset scan found no developer absolute paths or
  `localhost:8000`/`127.0.0.1:8000` literals.
- Proof limitation: no Windows VM or Sandbox is available in this environment.
  The combined packaged API/Tauri no-Node/no-Python run must be recorded as a
  controlled PATH simulation, not as a clean Windows image. Installer,
  signing, updater, and Stage 8 remain out of scope.

## Decision log

- 2026-07-14 — Stage 6 selected PyInstaller one-folder packaging after
  evaluating FastAPI/Uvicorn compatibility, SQLAlchemy/SQLite inclusion,
  Pydantic/settings, hidden imports and metadata, resource handling, Windows
  paths, startup, size, reproducibility, diagnostics, and antivirus tradeoffs.
  The built proof artifact is 91.71 MiB and starts in 4.23 seconds on this
  machine. The Tauri shell selects it only through `SAPSOS_API_EXECUTABLE` and
  uses the artifact directory as its working directory; missing packaged
  artifacts fail without a Python fallback.

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

## Validation ledger — Stage 8 closeout

| Milestone | Status | Evidence |
| --- | --- | --- |
| Stage 6 — FastAPI runtime packaging | Complete and merged | PR #44; merge commit `4d265ff001dc09211949bfa0860c29976b10b874` |
| Stage 7 — Web UI packaging | Complete and merged | PR #45; merge commit `ad57e944fcb95d28311d0018a553dd4d2d2cf5b1` |
| Stage 8A — secure local Extension pairing | Complete and merged | PR #46; final head `96a45c7542dd727f06f99c1d542fbb9f83d8e764`; merge commit `0d058fe6b862c91788cd8d47d297ad06abf9270e` |
| Stage 8B — localhost request protection | Complete and merged | PR #47; final head `38414db6774cff8173e15cd6fe3cfa8397e399f4`; merge commit `33451600a35b749f861825d53733cbafb576ac62`; CI run `29304954951` passed checks, Docker Compose, and E2E |

## Stage 10 — reviewed Program/Catalog architecture and correctness closeout

Stage 10 is complete. It delivered reviewed Program/Catalog source and lifecycle
architecture, exact reviewed and ACTIVE rule consumption, source provenance,
conservative `UNKNOWN` behavior, safe PostgreSQL `UNKNOWN`-result constraints,
no stale/mock fallback after explicit reviewed mapping failure, semantic
Program-role priority, missing-corequisite conditional handling, and reviewed-
corequisite persistence with POST/GET round trips.

The five PR #53 correctness findings were fixed by PR #54, and all five PR #53
review threads were replied to and resolved. Fixtures remain synthetic; no
authoritative WKU or Kean Program/Catalog coverage is claimed. No real student
data or private portal data was added. No Section Import was started, no
Schedule Optimizer semantics changed, and no later milestone was started.

### Stage 10A checkpoint

- Status: merged.
- PR: #52.
- Merge commit: `cf614bd0b0f0eaef60a4c1775accc1eece55045d`.

### Stage 10B checkpoint

- Status: merged.
- PR: #53 — `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/53`.
- Original head: `de0dfb6a801c3a20c184d4f48a00457466a4bd20`.
- Merge commit: `3e12a0d8d9d680b87daa5fc4f0edd53c982a779e`.
- CI run: `238`, successful.

### Stage 10B post-merge correctness hotfix

- Branch: `stage10b-correctness-hotfix`.
- Worktree: `D:\Crystal\.cache\worktrees\stage10b-correctness-hotfix`.
- Hotfix PR: #54 — `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/54`.
- Final hotfix head: `fce4ee718f9c9cd491ac85c7bd88b6f8d237ef8b`.
- Hosted CI workflow run ID: `29339947589`; run number: `245`; conclusion:
  success. Checks, E2E, Docker Compose, and `git diff --check` passed.
- Merge commit: `fdd3765b8cb81ed3ffadba9e34da095454befcd2`.
- Corrected findings: upgraded PostgreSQL eligibility constraints now permit
  `UNKNOWN`; explicit reviewed course mappings never reuse stale options;
  missing reviewed corequisites are not unconditional `ELIGIBLE`; reviewed
  corequisite summaries survive persistence and GET; and Program selection uses
  explicit semantic priority with conservative ambiguity handling.
- Migration proof: PostgreSQL base-to-head and previous-revision upgrade,
  `alembic check`, UNKNOWN persistence, invalid-value rejection, constraint
  inspection, explicit downgrade, and re-upgrade passed. LOCAL_DESKTOP SQLite
  metadata/bootstrap and repeated startup tests passed. The full SQLite
  Alembic-from-base path remains blocked by the pre-existing
  `20260623_0004` direct constraint-alteration incompatibility. This limitation
  predates PR #54; LOCAL_DESKTOP SQLite metadata/bootstrap compatibility remains
  validated, and the limitation does not invalidate the PostgreSQL Stage 10B
  forward-migration proof. It was not fixed by Stage 10.
- Final local report: 194 API tests passed. Ruff check, Ruff format check, mypy,
  compileall, PostgreSQL migration upgrade/downgrade, UNKNOWN eligibility
  constraint validation, `corepack pnpm test`, lint, typecheck, build, OpenAPI
  check, and `git diff --check` passed. Hosted CI run 245 passed.
- Privacy/authenticity: synthetic fixtures only; no personal data, private
  portal data, credentials, cookies, tokens, or authoritative WKU/Kean policy
  coverage was added.

Stage 10 is complete through PRs #52, #53, and #54. Stage 11 Real Section
Import is complete through PRs #56, #57, and #58. Stage 12 Real Section
Optimizer Integration and its documentation closeout are complete through PRs
#60, #61, and #62. UI Workflow Modularization is complete through PRs #63,
#64, the Backup/Restore PR A and PR B merges, and the documentation closeout
below. Backup/Restore, Safe migration and rollback, and Diagnostics are
complete; Windows Installer/Uninstaller is next.

## Resume checkpoint

- Current milestone: Diagnostics is complete; Windows Installer/Uninstaller
  is next and not started.
- Stage 10 status: complete.
- Stage 11 status: Real Section Import complete; PRs #56, #57, and #58 merged.
- Real Section Optimizer Integration: complete; PRs #60 and #61 merged.
- Current stage checkpoint: Stage 10A and Stage 10B use synthetic fixtures
  because no reviewed official Program/Catalog source inventory is present.
  10B consumes exact active rules only and records provenance; missing course
  definitions remain `UNKNOWN`.
- Current PRs: PRs #52, #53, #54, #56, #57, #58, #60, #61, #62, #66, #67,
  #68, #70, and #71 are merged.
  Stage 11A
  PR #56 merged at `068a38eae02ef51b70172da1f380f398cea9419d`; Stage 11B
  PR #57 merged at `749dd959ce7a82c982fe3df2962376cfdab6bbc0`; closeout PR #58
  final head is `c2c9b3915e2c1c557f24e79f43e7c87675e342d9` and merged at
  `6040c36e9766e62d2e5566cd23a4b89723319847`.
- Final synchronized `main`/`origin/main` before UI modularization:
  `c4cbffa843d16134efb37b6b17aed7c53ebf5dfb`.
- Last completed action: completed the Stage 11A extraction/staging and Stage
  11B Review/Apply deliveries. Imported Sections and SectionMeetings remain
  non-official; Import → Review → Apply remains mandatory; volatile availability
  remains advisory. No monitoring, registration, portal mutation, or optimizer
  integration began.
- Last successful validation: hosted CI workflow run ID `29382651009` (run
  number `261`) passed checks, Docker Compose, and E2E for the Stage 11 closeout;
  Stage 12 closeout is synchronized at the commit above.
- UI Workflow Modularization PR A: branch `ui-workflow-shell-modularization`,
  isolated clone/worktree path
  `D:\Crystal\.cache\worktrees\ui-workflow-shell-modularization`, starting
  commit `c4cbffa843d16134efb37b6b17aed7c53ebf5dfb`. The original Web page is
  6,028 lines with 31 hook calls, 6 effects, 86 headings, 24 buttons, and
  approximately 230 local declaration/handler lines. Its measured coupling
  spans runtime/API discovery, student/source context, import Review/Apply,
  audit, eligibility, planning, sections, optimization, monitoring, and
  pairing. PR A establishes static-export-safe hash navigation, an application
  shell, workflow anchors, and shared shell status/context without moving
  feature mutation state. Final PR A head is
  `773d4b4390d030e13f27039b6f478be2c51970e2`; exact-head CI is workflow run
  `29408328244` / run `289` (success); merge commit is
  `9e610ef274053adc681c2baaa5ed09b12fd6c791`. The remote tree was verified
  after correcting earlier connector encoding/line-ending attempts.
- UI Workflow Modularization PR B local checkpoint: branch
  `ui-workflow-feature-modules`, isolated clone/worktree path
  `D:\Crystal\.cache\worktrees\ui-workflow-feature-modules`, checkpoint
  `499ee6d0f0238c744f17632f111a1a91c8e76777`. The local clone retains the
  equivalent PR A tree through the preserved local commit; final publication
  will use current remote `main` (including PR A merge) as its parent.
- PR B module boundaries now include import/review identity keys, audit and
  eligibility readiness contracts, plan draft/read-only route guards, What-If
  identity isolation, reviewed Section predicates, optimizer run identity,
  Section Monitoring reads, applied course-state reads, and local pairing.
  Request guards ignore stale responses and mutation guards prevent replay;
  Import → Review → Apply, academic semantics, real/mock isolation, and
  static-export/Tauri API-base behavior remain unchanged.
- UI Workflow Modularization PR B: branch `ui-workflow-feature-modules`, final
  remote head `ccdced2725bcf2917349f9255811256998a3d446`, PR #64, exact-head
  CI workflow run `29410865812` / run `295` (success), and merge commit
  `bacbe70efc40dd619fbea3c6b25db3201deadfc4`. PR B extracted applied
  course-state, Section Monitoring, and local pairing workflow owners and
  added Import, Review/Apply, Degree Audit, Eligibility, Academic Plan,
  What-If, reviewed Sections, and Schedule Optimizer identity/readiness
  boundaries with stale-response and mutation-replay tests.
- Final UI Workflow Modularization state: complete. Static export remains
  supported; packaged desktop runtime API discovery continues through the
  `api_base_url` bridge. Existing workflows, Import → Review → Apply, Degree
  Audit, Eligibility, Planner, What-If, reviewed real Sections, optimizer
  provenance, and real/mock isolation remain intact. No registration, portal
  mutation, automatic monitoring, polling, or private data was added.
- Final synchronized remote `main` before Backup/Restore:
  `bacbe70efc40dd619fbea3c6b25db3201deadfc4`. Backup/Restore was then
  completed through PRs #66 and #67 and the documentation closeout below.

## Scope confirmation

Stage 8A pairing and Stage 8B localhost request protection are complete and
merged. Stage 9A parser stabilization and Stage 9B validation/Review/Apply
safeguards are complete. Stage 11 Real Section Import is also complete through
PRs #56, #57, and #58. Program/Catalog ingestion, Real Section Optimizer
Integration, production migration,
diagnostics center, installer/uninstaller, beta, or release-candidate work.

## Stage 8A — secure local Extension pairing (merged)

The separately reviewable Stage 8A implementation adds user-initiated local
Extension pairing with a short-lived, single-use random pairing code,
verifier-only local persistence, protocol versioning, revocation, and a
background-service-worker-owned Extension credential. It intentionally
preceded the localhost request boundary.

- Status: merged.
- PR: #46 —
  `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/46`.
- Final head: `96a45c7542dd727f06f99c1d542fbb9f83d8e764`.
- CI: run `29303946463` passed checks, typecheck, tests, build, OpenAPI,
  E2E, Docker Compose, and `git diff --check`.
- Merge commit: `0d058fe6b862c91788cd8d47d297ad06abf9270e`.
- Main synchronization: `origin/main` was fetched to the merge commit while
  the protected root-worktree files remained untouched.

## Stage 8B — localhost request protection (merged)

Stage 8B began from the merged Stage 8A main state. Its boundary is centralized in the
API request path and currently covers loopback Host authority, explicit
desktop/paired-Extension Origin policy, pairing-only Extension credentials,
local Bearer rejection, bounded nonce/timestamp replay protection, failed
request rate limiting, and dynamic paired-Extension CORS response headers.

- Status: complete and merged through PR #47.
- Final head: `38414db6774cff8173e15cd6fe3cfa8397e399f4`.
- Merge commit: `33451600a35b749f861825d53733cbafb576ac62`.
- CI: run `29304954951` passed checks, Docker Compose, and E2E.
- Validation: API pytest 180 passed; Ruff check; Ruff format check; mypy;
  Python compileall; and `git diff --check` passed.
- Explicit boundary: health/readiness/runtime and pairing bootstrap routes are
  classified separately; `/api/v1` local requests cannot substitute a Bearer
  token for the paired Extension credential. Replay nonces are intentionally
  in-memory and bounded; a restart clears the nonce cache, while the paired
  verifier and timestamp skew remain authoritative.

Stage 8 security is limited to the local application boundary. It does not
protect against full local-machine compromise, malware running as the user, a
compromised browser, a compromised Extension runtime, or administrator-level
attackers.

## Stage 9 — Real MyProgress stabilization (PRs 9A and 9B merged)

Stage 9 is the next implementation checkpoint. It is limited to stabilizing
extraction and parsing of the real visible MyProgress page, preserving raw
source evidence and field provenance, improving deterministic validation and
exception review, and keeping imported data non-official until reviewed.

Stage 9 must preserve Import → Review → Apply, must not silently infer
uncertain academic facts, and must not begin Program/Catalog ingestion, real
Section import, or any change to Schedule Optimizer semantics. No Stage 9
implementation is included in the Stage 8 closeout.

### Stage 9A checkpoint — snapshot/parser/provenance

- Status: merged.
- Branch: `stabilize-myprogress-parser`.
- Worktree: `D:\Crystal\.cache\worktrees\stabilize-myprogress-parser`.
- Final head: `889ca73e2c4ff890f1a13cb408d417bfdd6f0eb1`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/49`.
- CI: run `29309386281` passed checks, Docker Compose, and E2E.
- Merge commit: `f450a045d1e16e8ae4afe86a6d73c572a1f2cbf7`.
- Scope: bounded visible-page evidence, conservative MyProgress row parsing,
  summary-only staging eligibility, bounded malformed-row evidence, and the
  mandatory Review boundary.
- Privacy: only existing synthetic/sanitized fixtures are used; no real portal
  HTML, screenshots, identifiers, credentials, cookies, tokens, or session data
  are included.

### Stage 9B checkpoint — validation and Review/Apply safeguards

- Status: merged.
- Branch: `stabilize-myprogress-review`.
- Worktree: `D:\Crystal\.cache\worktrees\stabilize-myprogress-review`.
- Starting HEAD: `f450a045d1e16e8ae4afe86a6d73c572a1f2cbf7`.
- Final head: `a43b4b59f594e5a057182bb9923315980647f133`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/50`.
- CI: run `29310590691` passed checks, Docker Compose, and E2E.
- Merge commit: `1c36fe99d8da69474be863bfe7809b1f5c4c86e1`.
- Scope: deterministic validation-state presentation, exception classification,
  confirmed-record application safeguards, idempotency regressions, and
  explicit non-official/source/provenance presentation.
- Privacy: synthetic/sanitized fixtures only; no real portal HTML, screenshots,
  identifiers, credentials, cookies, tokens, sessions, or local databases.

## Stage 11A — Real Section Import parser and staging checkpoint

Stage 11A is merged from an isolated worktree based on synchronized Stage 10
`origin/main`. Its scope was limited to visible-page Section extraction,
deterministic grouping and normalization, bounded evidence, field provenance,
validation diagnostics, and staging. Canonical `Section` and `SectionMeeting`
rows are not created or updated by this checkpoint. Review remains mandatory;
`AUTO_VERIFIED` describes structural parser consistency only.

- Status: merged through PR #56.
- Branch: `stage11a-section-import-parser`.
- Worktree: `D:\Crystal\.cache\worktrees\stage11a-section-import-parser`.
- Starting commit: `b90c19a4c4db47cad93f5973fa3b5f60ea07ee5c`.
- Final head: `f7ff558114408b5f6d33deb093e7dfc60d6a84ae`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/56`.
- CI: run `29381550519` passed checks, Docker Compose, and E2E.
- Merge commit: `068a38eae02ef51b70172da1f380f398cea9419d`.
- Parser contract: Section identity is grouped conservatively by visible term,
  course code, and Section code. Repeated rows preserve multiple meetings;
  recognized day/time forms are normalized while raw text remains evidence.
- Provenance: staged normalized records retain raw evidence, source table/row
  indices, field-level direct/derived metadata, validation state, completeness,
  and bounded/truncation diagnostics.
- Privacy: source references remain sanitized by the existing Extension path;
  credentials, cookies, tokens, authentication forms, action controls, and
  unrelated student-profile content are excluded. Fixtures are synthetic or
  sanitized only.
- Volatile availability: seats, capacity, and waitlist values remain nested
  staging evidence and are not written to canonical structural Section data or
  Section Monitoring targets.
- Focused validation: Extension Vitest 55 passed; Extension TypeScript
  typecheck and ESLint passed; API pytest 195 passed; API Ruff, format, mypy,
  TypeScript checks, workspace tests, build, OpenAPI check, and `git diff --check`
  passed.
- Protected root artifacts remain outside this worktree and untouched:
  `apps/web/next-env.d.ts`, `.codex-worktrees/`, and
  `localize-web-ui-zh-cn.patch`.
- Completed checkpoint: PR 11B Review/Apply and idempotent persistence of
  non-official Section and SectionMeeting rows. Real Section Optimizer
  Integration remains out of scope and unstarted.

## Stage 11B — Real Section Review/Apply checkpoint

Stage 11B is complete and merged on an isolated worktree created only after PR
11A merged and `origin/main` synchronized. It reuses the existing Import → Review →
Apply session, application-run, and audit records. It adds explicit dry-run and
Apply behavior for reviewed Section evidence, requiring mapped Course, term,
campus, and unambiguous Section identity.

- Status: complete and merged through PR #57.
- Branch: `stage11b-section-review-apply`.
- Worktree: `D:\Crystal\.cache\worktrees\stage11b-section-review-apply`.
- Starting commit: `068a38eae02ef51b70172da1f380f398cea9419d`.
- Final head: `d658ba0e67eec0fb055c50f4b676cce54a6e506d`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/57`.
- CI: run `29382465246` passed checks, Docker Compose, and E2E.
- Merge commit: `749dd959ce7a82c982fe3df2962376cfdab6bbc0`.
- Scope: non-official structural Section and SectionMeeting persistence,
  provenance, explicit conflicts for official/MOCK targets, no mutation on
  dry-run, repeat-Apply idempotency, and incomplete-snapshot deletion safety.
- Volatile availability: capacity, available seats, and waitlist values remain
  advisory evidence and are never written to canonical Section fields.
- Privacy and safety: no credentials, cookies, tokens, portal mutation,
  registration automation, monitoring, or schedule-optimizer integration.
- Validation: API pytest 197 passed; Extension Vitest 55, shared Vitest 28,
  and web Vitest 14 passed; Ruff check/format, mypy, workspace lint,
  typecheck, build, OpenAPI check, and `git diff --check` passed.
- Protected root artifacts remain outside this worktree and untouched:
  `apps/web/next-env.d.ts`, `.codex-worktrees/`, and
  `localize-web-ui-zh-cn.patch`.
- Stage 11 result: real visible-page Section data now follows Import → Review →
  explicit dry-run/Apply into non-official structural Section and
  SectionMeeting records with provenance. Availability remains advisory and
  separate from canonical structural data. Stage 12 optimizer work was kept
  out of Stage 11 and delivered afterward through the gated PRs above.
- Historical next-milestone checkpoint: Safe migration and rollback followed
  Backup/Restore and is complete through PRs #70 and #71 and its closeout;
  Diagnostics followed and is now complete through PRs #73 and #74 and the
  closeout below.

## Stage 12A — Real Section optimizer input boundary checkpoint

Stage 12A is complete and merged through PR 60. It established the safe
backend boundary for the dependency-ordered optimizer integration.

- Status: complete and merged.
- Branch: `real-section-optimizer-input-boundary`.
- Worktree: `D:\Crystal\.cache\worktrees\real-section-optimizer-input-boundary`.
- Starting commit: `42fdd6c0f6efab0b55b0c762948564a29e83a9a8`.
- Final head: `9d9ebc1f3d9697e7c7d23d24c5cb268dcaf6e787`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/60`.
- CI: workflow run `29387106741` (run number `275`) passed checks, Docker Compose, and E2E.
- Merge commit: `9e0e2d251dd5a29bc42d4228ee837a95e986d77b`.
- Data modes: explicit `DEMO_MOCK` preserves existing seeded behavior;
  `REVIEWED_IMPORTED` requires successful Stage 11 application provenance.
- Reviewed/applied predicate: centralized audit-chain evaluation requires the
  exact student, institution, term, and Course scope; confirmed or
  edited-and-confirmed review; successful Section application; non-official,
  non-MOCK source; supported Section import; valid, non-truncated structural
  payload; and valid meeting structure.
- Real/mock isolation: real mode filters candidates through that predicate and
  never falls back to or mixes in mock Sections. Demo mode remains unchanged.
- Readiness and provenance: the run persists Section mode, source-age policy,
  deterministic input snapshot hash, and a source-readiness summary. The
  existing Stage 11 import/application IDs remain discoverable through the
  validated audit join.
- Source age: exact age is computed from the applied Section extraction time;
  missing timestamps produce `SOURCE_AGE_UNKNOWN`; an optional maximum age is
  persisted and applied without treating it as an availability guarantee.
- TBA/arranged policy: such rows are identified and warned; they are not
  silently treated as conflict-free certainty.
- Availability separation: seat, capacity, and waitlist values remain outside
  structural candidate eligibility and ranking.
- Validation: API pytest 199 passed; focused optimizer/boundary tests 10
  passed; shared 56, Extension 55, and web 14 tests passed; workspace lint,
  typecheck, build, API Ruff, format, mypy, compileall, and diff checks passed.
  The documented SQLite full-Alembic-from-base blocker remains at revision
  `20260623_0004`.
- Gate evidence: root `main` and `origin/main` are synchronized at
  `9e0e2d251dd5a29bc42d4228ee837a95e986d77b`; protected root artifacts remain
  untouched.

## Stage 12B — Real Section optimizer execution and provenance checkpoint

Stage 12B is complete and merged through PR #61. It persists selected Section
provenance and source-age evidence, computes deterministic Section snapshots,
reports structural drift without automatic reruns, and exposes the
reviewed-imported mode in the schedule builder UI.

- Status: complete and merged; branch `real-section-optimizer-integration`.
- Worktree: `D:\Crystal\.cache\worktrees\real-section-optimizer-integration`.
- Starting commit: `9e0e2d251dd5a29bc42d4228ee837a95e986d77b`.
- Final head: `4e25d8d110cade1786621fddddf178f74055bd94`.
- PR: `https://github.com/CZX45/Smart-Academic-Planning-and-Schedule-Optimization-System/pull/61`.
- CI: workflow run `29387637590` passed checks, Docker Compose, and hosted
  Playwright E2E.
- Merge commit: `0d58ae99123b7b3a2a2070ab64037eb221b9a1d5`.
- Completed behavior: only reviewed and successfully applied Stage 11
  structural Sections are eligible in `REVIEWED_IMPORTED` mode; real and mock
  workflows remain isolated with no silent mock fallback; selected Section
  provenance, source age, and deterministic snapshots are persisted; structural
  drift is detected and reported without automatic reruns; the UI exposes
  reviewed-imported mode, provenance, source age, and drift; availability
  remains advisory and does not determine structural feasibility or ranking;
  optimizer output remains non-official and advisory, requiring manual official
  portal verification.
- Persistence: migration `20260715_0020` stores selected source provenance,
  source age, and Section snapshot hash on each selected option Section.
- API/UI: selected Sections report provenance, source age, and
  `NOT_CAPTURED`/`UNCHANGED`/`CHANGED` drift status; the UI requests
  `REVIEWED_IMPORTED` with a 24-hour source-age limit and tells the student to
  regenerate when a snapshot changes.
- Safety: no registration, add/drop/swap, waitlist automation, seat grabbing,
  portal mutation, background monitoring, or polling was added; no real student
  or private portal data was committed.
- Validation: API 200, Extension 55, Shared 28, Web 14, and focused optimizer
  tests 11 passed; lint, typecheck, OpenAPI check, Ruff, mypy, and
  `git diff --check` passed; hosted Docker Compose and hosted Playwright E2E
  passed.
- Final milestone state at this historical checkpoint: Stage 11 Real Section
  Import, Stage 12 Real Section Optimizer Integration, and Stage 13 UI Workflow
  Modularization are complete; PRs #60, #61, #63, and #64 are merged. The
  subsequent Backup/Restore milestone is recorded below.
- Protected root artifacts remain untouched: `apps/web/next-env.d.ts`,
  `.codex-worktrees/`, and `localize-web-ui-zh-cn.patch`.
- Known limitation: the full SQLite Alembic-from-base path remains blocked by
  the pre-existing `20260623_0004` constraint-alteration incompatibility. This
  predates Stage 12 and Stage 12 did not repair it. LOCAL_DESKTOP
  metadata/bootstrap behavior remains separate; PostgreSQL migration
  validation is authoritative for the new Stage 12 migrations.

## Stage 13 — UI Workflow Modularization checkpoint

Stage 13 is complete through PRs #63 and #64 plus this documentation-only
closeout. The shell/navigation work and feature workflow boundaries were
dependency-gated; PR B was published from merged PR A `main`, not from the
local pre-merge clone ancestry.

- PR A: branch `ui-workflow-shell-modularization`; final head
  `773d4b4390d030e13f27039b6f478be2c51970e2`; CI workflow run
  `29408328244` / run `289`; merge `9e610ef274053adc681c2baaa5ed09b12fd6c791`.
- PR B: branch `ui-workflow-feature-modules`; final head
  `ccdced2725bcf2917349f9255811256998a3d446`; base
  `9e610ef274053adc681c2baaa5ed09b12fd6c791`; CI workflow run
  `29410865812` / run `295`; merge
  `bacbe70efc40dd619fbea3c6b25db3201deadfc4`.
- Documentation closeout: branch `ui-workflow-final-closeout`; scope is only
  `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`. It records the final Stage 13
  evidence and does not alter application behavior.
- Original UI measurements: `apps/web/src/app/page.tsx` was 6,028 lines with
  31 hook calls, 6 effects, 86 headings, 24 buttons, and approximately 230
  local declaration/handler lines spanning runtime/API, student/source,
  Import/Review/Apply, audit, eligibility, planning, sections, optimizer,
  monitoring, and pairing.
- Module boundaries: the shell owns identity, navigation, API/source context,
  and workflow content. Feature boundaries cover MyProgress Import, Review and
  Apply, Degree Audit, Eligibility, Academic Plan, What-If, reviewed Sections,
  Schedule Optimizer, Section Monitoring, applied course-state reads, and local
  Extension pairing. Workflow keys isolate imports, reviews, students,
  scenarios, terms, and optimizer snapshots.
- Protection behavior: stale responses are ignored across request/effect
  changes; review/import and student/course identities cannot collide; real
  reviewed Section mode cannot mix with demo mock mode; mutation replay is
  guarded; route entry, refresh, back/forward, and saved-result viewing do not
  invoke Apply or optimizer generation.
- Accessibility/static export: semantic navigation and main landmarks,
  keyboard-operable hash links, `aria-current`, visible focus, async status,
  safety copy, and narrow-layout styles remain present. Static export produced
  `/` and `/_not-found`; packaged Tauri discovery continues through the
  runtime `api_base_url` query bridge. No server routes, middleware, Server
  Actions, or packaged Node runtime were introduced.
- Validation: local workspace tests passed with API 200, Extension 55, Shared
  28, Web 19; workspace lint, strict typecheck, build, OpenAPI check, Ruff
  check/format, mypy, compileall, pytest 200, and `git diff --check` passed.
  Focused local Playwright workflow-shell coverage passed 1 test; hosted PR B
  CI passed Docker Compose and the full Playwright E2E job. Review P2 findings
  for empty course-state snapshots and cross-effect stale reads were fixed in
  forward commit `ccdced2725bcf2917349f9255811256998a3d446` and resolved.
- Safety and privacy: academic semantics, Import → Review → Apply, Degree
  Audit, Eligibility, Planner, What-If, reviewed real Section optimizer
  semantics, provenance, and real/mock isolation remain intact. No
  registration, portal mutation, automatic monitoring, polling, credential
  capture, private data, or protected artifact changes were added. The known
  SQLite Alembic-from-base limitation at `20260623_0004` remains unchanged.
- Final state: UI Workflow Modularization, Backup/Restore, Safe migration and
  rollback, and Diagnostics are complete; static export and packaged runtime
  discovery remain supported; Windows Installer/Uninstaller is the next
  dependency-ordered milestone.

## Backup/Restore — PR A checkpoint

PR A is limited to the local backup archive foundation and explicit manual
export. It does not replace the active database and does not expose a working
restore action. PR B must begin only after PR A merges and local `main` is
synchronized with `origin/main`.

- PR A: branch `local-backup-archive-foundation`; starting commit
  `c9be585a41cb54c303b032a7bafd6bbbb24c781f`; final head
  `0ec009a21795cb81cf788336f1a0d3fa4c518341`; PR #66; exact-head CI run
  `29426489035` / run `306`; merge commit
  `067bc959519f6699b093fa330bc8cbc40b7083b1`.
- PR A worktree: `D:\Crystal\.cache\worktrees\local-backup-archive-foundation`.
- Backup format: `sapsos-backup` version 1, `.sapsos-backup` filename, ZIP
  entries exactly `manifest.json` and `database.sqlite`.
- Snapshot method: Python SQLite backup API from the active configured SQLite
  database URL; source and snapshot are checked with SQLite quick check,
  foreign-key check, and exact LOCAL_DESKTOP schema version validation.
- Manifest: canonical JSON records backup ID, UTC creation time, product mode,
  schema version, payload size and SHA-256, allowlist, and explicit pairing,
  runtime, and encryption flags. Archives are unencrypted; pairing/runtime
  state is excluded.
- API: `GET /api/v1/local-backup/status` and explicit `POST
  /api/v1/local-backup` download; the boundary is LOCAL_DESKTOP-only and does
  not expose arbitrary filesystem paths.
- Web: the static hash-routed `备份与恢复` workflow provides status, inclusion
  and exclusion warnings, an unencrypted-data warning, duplicate-click
  protection, and a manual binary download. Restore remains dependency-gated.
- Validation: PR A exact-head CI passed checks, Docker Compose, and full
  Playwright E2E. Local focused and full workspace validation passed; the
  local browser proof was environment-limited by the isolated Chromium cache,
  while hosted CI supplied the authoritative browser proof.
- Protected artifacts: `apps/web/next-env.d.ts`, `.codex-worktrees/`, and
  `localize-web-ui-zh-cn.patch` remain root-only and are excluded from this
  branch.

## Backup/Restore — PR B checkpoint

PR B begins only after PR A merge commit `067bc959519f6699b093fa330bc8cbc40b7083b1`
and synchronization of `main` with `origin/main`. PR B adds strict restore
validation, bounded staging, explicit confirmation, and pre-start desktop-shell
application with rollback. It does not add schema migration or migration
rollback.

- Branch: `local-restore-orchestration`.
- Worktree: `D:\Crystal\.cache\worktrees\local-restore-orchestration`.
- Starting commit: `067bc959519f6699b093fa330bc8cbc40b7083b1`.
- Restore API: multipart validation creates a server-controlled single-use
  session; `RESTORE` confirmation atomically writes `pending-restore.json`.
  Validation and confirmation never replace the active database.
- Marker: version 1, request/backup IDs, relative staged candidate, expected
  SHA-256/size/schema version, and pending status; no absolute paths, tokens,
  pairing data, or database URLs.
- Desktop startup: Tauri verifies marker containment, candidate checksum/size,
  SQLite header, and exact schema version marker before moving current SQLite
  database and `-wal`/`-shm`/`-journal` sidecars into a unique safety directory.
  It installs the staged database before FastAPI starts, keeps the safety copy
  on success, and restores the original database/sidecars after failed startup.
  Failed restore markers are consumed so startup cannot loop.
- Web: the existing `备份与恢复` workflow now supports explicit file selection,
  explicit validation, compatibility preview, `RESTORE` confirmation, cancel,
  restart-required state, and safe warnings. File selection alone has no side
  effect.
- Validation: local focused restore tests and Tauri unit tests pass; exact PR,
  CI, review, and merge evidence passed. PR #67 final head is
  `08e9bef5b69bd3e04b98cbfc1649dddbd9e1251a`; exact-head CI is workflow run
  `29428702027` / run `311`; merge commit is
  `bb0b6d55dbe368af64557c5c646286ce170772b5`. Review threads for invalid
  marker quarantine and DELETE preflight are resolved.
- Protected artifacts: `apps/web/next-env.d.ts`, `.codex-worktrees/`, and
  `localize-web-ui-zh-cn.patch` remain root-only and are excluded from this
  branch.

## Backup/Restore — final documentation closeout

Backup/Restore is complete through PR A #66, PR B #67, and the docs-only
closeout in PR #68. The dependency gate was preserved: PR B started from
merged PR A, and the closeout started from merged PR B at
`bb0b6d55dbe368af64557c5c646286ce170772b5`. Safe migration and rollback is
recorded in the closeout below. The pre-existing SQLite Alembic-from-base
limitation at `20260623_0004` remains unchanged.

- Final synchronized `main`/`origin/main` before this documentation-only
  closeout: `bb0b6d55dbe368af64557c5c646286ce170772b5`. Closeout PR #68 merged
  at `af2148e533dec3c39b0508ef18316d05c8dc400c` after exact-head CI run 314.
- Scope remains local-only and advisory: no registration, portal mutation,
  credentials, cloud sync, scheduling, arbitrary filesystem access, or
  automatic monitoring was added.

## Safe migration and rollback — final documentation closeout

Safe migration and rollback is complete through two implementation PRs and
this documentation-only closeout. PR #70 established the LOCAL_DESKTOP SQLite
migration foundation; PR #71 added Tauri pre-start orchestration, readiness,
automatic rollback, interrupted-attempt recovery, and replay prevention. The
closeout starts from merged PR #71 at `6142016` and does not change
implementation code.

### PR #70 — safe migration and rollback foundation

- PR: #70.
- CI: run `29438130368` passed.
- Final API validation: 216 passed; focused migration/Backup/Restore tests:
  17 passed.
- Final merge/main state before PR #71: `de5161d`.
- Delivered the LOCAL_DESKTOP migration registry with explicit from/to schema
  versions, deterministic migration planning, schema-status classification,
  migration journal, migration runner, integrity validation, foreign-key
  validation, and a validated safety-backup contract.
- Production LOCAL_DESKTOP schema version remains 1. No formal production
  version 2 migration was created.
- PostgreSQL Alembic behavior remains unchanged. Historical revision
  `20260623_0004` was not fixed or bypassed.

### PR #71 — Tauri startup orchestration

- PR: #71, `Add safe local migration startup orchestration`.
- CI: run `29440757350` passed checks, pnpm lint/typecheck/test/build,
  OpenAPI validation, Docker Compose, and Playwright.
- Merge commit: `6142016`.
- Delivered the versioned Python JSON preflight/execute contract,
  attempt-bound safety backup, Tauri startup lock, API readiness gate,
  pending-restore-first ordering, automatic rollback after migration or
  post-migration API startup failure, interrupted-attempt handling, marker
  replay prevention, and recovery-loop prevention.
- Migration safety backups remain application-owned and do not include
  pairing/runtime state. SERVER/PostgreSQL startup and Alembic behavior remain
  unchanged. ADR-0024 records the orchestration decision.
- Validation: API pytest 219 passed; Ruff, mypy, compileall, Rust fmt/test/
  build, hosted pnpm checks, OpenAPI, Docker Compose, and Playwright passed.

### Final LOCAL_DESKTOP startup and database lifecycle

```text
acquire startup/database lock
→ process pending restore first
→ inspect interrupted migration state
→ migration preflight
→ CURRENT: start API normally
→ UPGRADE_REQUIRED:
   create attempt
   create and validate safety backup
   execute ordered migration plan
   validate integrity and foreign keys
   start API
   wait for readiness
→ readiness success: complete startup
→ migration or readiness failure:
   stop API
   preserve failed database evidence
   restore verified safety backup
   record rollback
   stop safely
```

Restore has priority over migration; restore and migration do not run
concurrently, and one startup permits only one database replacement or
migration operation. Completing the migration command is not equivalent to a
successful upgrade: the API process, runtime manifest, target database, and
readiness endpoint must also be correct. After rollback, the same startup does
not migrate again. An interrupted attempt is recognized on the next startup
and must enter recovery preflight before normal startup can proceed.

### Safety boundaries and remaining limitations

The orchestration is LOCAL_DESKTOP-only and does not apply to SERVER/PostgreSQL.
It does not perform downgrade migration or cross-schema restore; automatically
repair unknown/corrupt databases; silently rebuild or delete a user database;
delete migration safety backups; restore `pairing.json` or `runtime.json`; or
accept a user-controlled database path. It rejects marker replay, stale safety backup reuse,
and unbounded migration/rollback loops. It never stores
school accounts, cookies, tokens, MFA secrets, or portal credentials, and it
does not emit unsanitized tracebacks or student records.

The full SQLite Alembic-from-base path still fails at revision
`20260623_0004`. This is a historical PostgreSQL-specific migration limitation;
LOCAL_DESKTOP does not depend on the complete Alembic history, PR #70 did not
modify that revision, and PostgreSQL migration history remains unchanged.

The current production local schema version remains 1. There is no real
production version 2 migration; orchestration was validated with test-only
migrations and temporary SQLite databases, without manufacturing a formal
schema bump for testing.

The local complete Windows packaged-desktop proof remains unexecuted. The
isolated clone lacked `node_modules`, so local full pnpm verification was
environment-limited; hosted CI supplied pnpm, OpenAPI, Docker Compose, and
Playwright evidence. Package-level proof remains part of the later Packaged
Desktop E2E milestone and must not be described as complete here.

## Diagnostics — final documentation closeout

Diagnostics is complete through PR #73 (backend foundation), PR #74 (UI and
privacy-safe export), and this documentation-only closeout. The implementation
is LOCAL_DESKTOP-only, user-initiated, read-only, advisory, and isolated from
SERVER mode. ADR-0025 records the decision to keep diagnostics local and
privacy-safe.

### PR #73 — Diagnostics backend foundation

- Merge commit: `51d0100b`.
- Delivered a LOCAL_DESKTOP-only diagnostics API, typed/versioned diagnostics
  contract, shared TypeScript contract, and isolated runtime, API, database,
  schema/migration, Backup/Restore, Extension pairing, and startup-status
  collectors.
- Centralized privacy sanitization preserves structured reason codes and
  allowlisted metadata while removing sensitive or machine-identifying data.
- LOCAL_DESKTOP/SERVER isolation and the existing Host/Origin/proof/replay
  protections remain preserved.
- Validation: API 231 passed; Shared 58 passed; Ruff, mypy, TypeScript, build,
  and OpenAPI passed; Rust check/test/build passed; CI checks, Docker Compose,
  and E2E passed.

### PR #74 — Diagnostics UI and safe export

- Merge commit: `e23c44c50a5f9cf5eee6fa0a5744953cd7fdd98c`.
- Delivered the Diagnostics workflow in the modular Web UI, hash navigation,
  static-export/Tauri runtime-bridge compatibility, readable status states
  (`HEALTHY`, `DEGRADED`, `ACTION_REQUIRED`, `BLOCKED`, `UNKNOWN`), explicit
  refresh, stale-response protection, and no background polling or automatic
  repair.
- Delivered a user-initiated, LOCAL_DESKTOP-only privacy-safe export with the
  fixed archive allowlist: `manifest.json`, `diagnostics.json`,
  `startup-events.json`, and `README.txt`.
- `manifest.json` records the bundle format version, `generated_at`, application
  version/mode, diagnostics contract version, file list, per-file SHA-256,
  privacy statement, exclusions, and redaction-policy version.
- `diagnostics.json` is the typed sanitized snapshot. `startup-events.json`
  contains bounded sanitized startup events. `README.txt` states local
  generation, no automatic upload, user review before sharing, that the bundle
  is not an official school record, and deletion guidance.
- The bundle excludes databases, backup archives, raw logs, pairing secrets,
  runtime proofs, credentials, student records, portal contents, and raw import
  evidence. Host/Origin/proof/replay protections remain preserved, and SERVER
  mode does not expose local diagnostics export.
- Validation: API, Web, OpenAPI, Docker Compose, and E2E passed in CI.

### Diagnostics safety boundary and user flow

Diagnostics is local-only, user-initiated, and has no telemetry, remote upload,
cloud logging, automatic GitHub issue submission, or automatic support
submission. It contains no student records, GPA, grades, course history, plans,
Section data, portal contents, raw import evidence, credentials, MFA, cookies,
SAML data, tokens, pairing secrets, localhost proofs, absolute paths, Windows
usernames, raw tracebacks, stderr, stdout, SQL, or command lines. The ZIP is
not a backup and cannot perform repair, migration, restore, pairing reset, or
API restart.

```text
user opens Diagnostics
→ reads a lightweight diagnostics snapshot
→ sees overall and component states
→ may explicitly refresh
→ may explicitly export a privacy-safe bundle
→ API packages only the fixed allowlisted files
→ archive entries and SHA-256 values are checked
→ user saves locally and reviews before sharing
→ nothing is automatically uploaded or shared
```

### Diagnostics limitations

- `cargo fmt --check` still reports a pre-existing blank-line issue in an
  unmodified Rust file. PR #74 did not modify that file; implementation CI
  otherwise passed. This closeout does not fix the issue and does not claim
  that the repository is fully rustfmt-clean.
- Full installed Windows packaged-desktop E2E has not been completed. Tauri,
  API, and Web components have CI and build coverage; installer-level proof
  belongs to Packaged Desktop E2E.
- Diagnostics is advisory, is not a backup, does not export database rows, and
  does not repair problems. Users must still use official school systems for
  official records.

### Next milestone: Windows Installer/Uninstaller

The next milestone is Windows Installer/Uninstaller and is not started. Its
future scope is limited to an official Windows installer packaging the Tauri
shell, FastAPI runtime, and static Web assets; stable AppData paths;
install/upgrade/uninstall flows; explicit preservation or removal of user data;
preservation of backups unless explicitly confirmed; signing strategy;
upgrade compatibility; uninstall safety; and installer validation. No
installer design or implementation is part of this closeout.

The remaining dependency-ordered route is:

```text
Windows Installer/Uninstaller
→ Packaged Desktop E2E
→ Controlled Student Beta
→ Release Candidate
```
