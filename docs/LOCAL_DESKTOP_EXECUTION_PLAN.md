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
- `main` and `origin/main` are synchronized at the UI Workflow Modularization
  closeout commit `c9be585a41cb54c303b032a7bafd6bbbb24c781f`. PRs #63, #64,
  and #65 are merged.
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
18. Diagnostics — next milestone.
19. Windows Installer/Uninstaller.
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
  PostgreSQL/Bearer behavior remain unchanged.…8436 tokens truncated…mmit: `42fdd6c0f6efab0b55b0c762948564a29e83a9a8`.
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
- Final state: UI Workflow Modularization, Backup/Restore, and Safe migration
  and rollback are complete; static export and packaged runtime discovery
  remain supported; Diagnostics is the next dependency-ordered milestone.

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

### Next milestone: Diagnostics

Diagnostics is the next milestone and is only recorded here as scope. It may
provide a local diagnostics center covering API/runtime health, database health,
schema version, migration status, last migration/rollback result, restore
result, runtime manifest status, extension pairing status, and recent sanitized
startup failures. A privacy-safe log export may be included, with no student
records or credentials in the diagnostics bundle. No Diagnostics API, UI, or
implementation is part of this closeout.

The remaining dependency-ordered route is:

```text
Diagnostics
→ Windows Installer/Uninstaller
→ Packaged Desktop E2E
→ Controlled Student Beta
→ Release Candidate
```
