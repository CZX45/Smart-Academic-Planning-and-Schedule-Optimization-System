# Current Project Baseline

Snapshot date: 2026-08-22 (Asia/Shanghai)

This document records the repository and CI state used for release-convergence work. Current Git, GitHub, source, tests, and workflows are authoritative; historical phase text is not treated as proof.

## Git and pull request baseline

| Item | Current evidence |
|------|------------------|
| Original checkout | `D:\Crystal`, branch `main`, HEAD `bce82aea587017435b4ec7741d95e11bae138335` |
| Original checkout condition | Behind `origin/main` by 119 commits and contains unrelated tracked/untracked user files; it is intentionally untouched |
| Remote baseline | `origin/main` at `8e055994e3e4435043c66e9362d9d0ede2365ec3` after `git fetch origin --prune` |
| Isolated worktree | `D:\Crystal\.cache\worktrees\release-convergence` |
| Working branch | `codex/release-convergence`, initially tracking PR #87 head |
| Starting HEAD | `8719748e6506a8591f7f58a5e369037605ca69a4` |
| PR #87 | Open draft, `beta-fix-first-run-empty-state` -> `main`, merge state `UNSTABLE` |
| Other open PR observed | PR #28, draft localization work |
| Remote mutation | None; no push, merge, release, provider write, or remote branch change was performed |

## Current CI baseline

PR #87's current checks at the start of this work were:

| Check | State | Evidence |
|-------|-------|----------|
| Regular CI checks | pass | GitHub PR #87 check rollup |
| Browser E2E | pass | GitHub PR #87 check rollup |
| Docker Compose validation | pass | GitHub PR #87 check rollup |
| Windows installer foundation/package | pass | GitHub PR #87 check rollup |
| Windows installer lifecycle | pass | GitHub PR #87 check rollup |
| Windows packaged desktop E2E | fail | run `30064769864`, job `89393469236` |

The failing packaged run reached install, first launch, explicit demo activation, synthetic import/review/apply, persistence write, graceful shutdown, and restart. It then timed out waiting for the saved-import preview marker `数据导入预览汇总` during `persistence_verify`.

## Confirmed packaged-E2E root cause

The historical prompt's `VersionInfo` failure in `installer_lifecycle_harness.ps1` is not the current failure.

PR #87 intentionally made demo workflow activation an in-memory, explicit user action. After a Tauri/WebView restart, `demoModeEnabled` correctly returns to `false`. The UI also used that in-memory flag as its only way to derive an active student, so it never discovered the already persisted import run and remained in the guarded empty state. The packaged harness then timed out waiting for `数据导入预览汇总`.

The source Playwright suite exposed an additional race in the existing test contract: saved-import scenarios activated demo immediately after navigation, sometimes before client hydration, which could make tests pass without proving that persisted real-import state was independent of demo state.

Evidence:

- `apps/web/src/app/page.tsx` previously derived the active student only from `demoModeEnabled` and guarded saved-import discovery behind that derived value.
- `tests/e2e/home.spec.ts` previously activated demo for saved real-import scenarios and did not wait for client readiness before clicking.
- `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1` restarted the WebView and correctly lost demo activation, then waited for persisted real-import UI state.
- Run `30064769864`, job `89393469236` reached the persisted write and restart before timing out on the readback marker.

The local fix keeps demo state ephemeral while restoring the persisted imported student: the UI discovers the known local student's saved import, records the import run's `student_profile_id` as active, and drives downstream state from that imported identity. Source E2E no longer enables demo for saved real-import scenarios. The packaged harness now waits for client hydration and, after restart, proves both that demo is disabled and that the imported-student marker is restored. The latest isolated seeded Playwright run completed with 26/26 tests passing, including explicit missing-profile and first-profile onboarding regressions.

## Fresh-install onboarding resolution and remaining proof

The candidate now provides a production-shaped local bootstrap for a genuinely
empty database:

- `GET/POST /api/v1/local-onboarding/student-profiles` list non-mock profiles
  and create only the first non-mock profile in `LOCAL_DESKTOP`; development
  mock seed records neither appear nor block that creation;
- the web form creates a pseudonymous student plus student-provided,
  non-official institution/campus labels and never creates a program/catalog or
  academic rule;
- reviewed or different code collisions return 409 without overwrite;
- a real profile with no audit remains an explained empty state and never
  borrows the deterministic mock program; and
- after pairing, the Extension worker signs profile discovery and auto-selects
  exactly one profile without exposing its credential or requiring UUID copy.

Focused API, shared-client, Extension, and browser tests cover this contract.
Installed create/restart/rediscovery/pairing proof has not yet run on a
disposable Windows account. No participant-owned authenticated portal session
or explicit real-source capture authorization is available, so real-source and
downstream academic acceptance remain blocked/manual rather than inferred from
synthetic evidence.

## Version and artifact baseline

`desktop-shell/desktop-identity.json` is the authoritative product/version source. The repository validators require all package surfaces to agree with it.

| Surface | Current value |
|---------|---------------|
| Product | `SAPSOS Local Desktop` |
| Authoritative version | `0.1.6` |
| Tauri/Cargo/API/web/extension/shared/config | `0.1.6` |
| Locally built installer | `dist/windows-installer/SAPSOS-Local-Desktop-0.1.6-x64-setup.exe` |
| Local build SHA-256 | `bf098bce67d8a663dfd9d821f185f26322a7d672fd9d00c16cc9e279e8a94800` |

The first local artifact was built successfully from the PR starting head before the current code, test, harness, and documentation changes. A final candidate artifact must be rebuilt from a clean committed candidate HEAD before its hash can be release evidence.

## Product and architecture baseline

- The current supported direction is a single-user, local-first Windows desktop product. SERVER mode remains a separate authenticated PostgreSQL path.
- Tauri owns packaged API startup/shutdown and local runtime identity; FastAPI owns validated APIs and domain services; SQLite owns LOCAL_DESKTOP persistence; the static Next.js UI renders advisory workflows.
- Imports follow staging -> review -> explicit apply. Source metadata, uncertainty, warnings, and structured explanations remain first-class.
- The extension is Manifest V3 and user-triggered. It operates only on a page the user already opened and authenticated, and it does not collect portal credentials or perform registration actions.
- Controlled student beta preparation exists, but real participant execution is not recorded as complete.

## Prompt-to-repository divergences

| Historical prompt statement | Current repository reality |
|-----------------------------|----------------------------|
| PR #87 is `phase-14b-controlled-beta-verification` | PR #87 is `beta-fix-first-run-empty-state` |
| `/system/preflight` and `/verification/run` exist | No such OpenAPI paths or route implementations were found |
| A Desktop Verification Center exists | No matching feature implementation was found |
| Production authorization/fingerprint/PROD guards exist | No matching runtime or CI implementation was found |
| The current packaged failure is a `VersionInfo` error | Current failure is persisted imported-student discovery being incorrectly coupled to ephemeral demo activation |
| Package validation is skipped downstream | Current workflows have installer validation/lifecycle jobs, but no separate job named package validation |
| Installer version is `0.0.0` | Current authoritative and packaged version is `0.1.6` |
| Phase 14B product/workflow is complete | Current docs say controlled beta readiness is prepared; real execution has not started |

## Local environment constraints

- Local toolchain: Node 24.13.1, pnpm 10.28.1, Python 3.14.3, Rust/Cargo 1.97.0, Tauri CLI 2.11.4.
- CI uses Python 3.12 and Windows Server runners, so local Python execution is useful but not an exact CI-runtime match.
- A pre-existing canonical `SAPSOS Local Desktop` 0.1.5 installation and its user data are present under the current Windows account. They are not test fixtures and were not uninstalled, overwritten, migrated, or used for business operations.
- A local isolated-root NSIS attempt did not produce a full runtime and was stopped at the install gate. Because the installer uses the same canonical per-user product identity, authoritative installed validation should run in a disposable clean Windows user/runner rather than risk the existing installation.

## Release-convergence baseline decision

The project is not yet a release candidate. The packaged restart defect and
fresh-profile code gap now have source/API/Extension regression evidence, but
authoritative post-fix installed execution still requires a disposable Windows
runner. No participant-owned authenticated source session was authorized.
Real-source work must remain blocked until a participant explicitly completes
authentication in a user-owned session and authorizes the read-only capture
flow.
