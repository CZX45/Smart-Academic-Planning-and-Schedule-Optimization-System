# Codebase Concerns

## 2026-10-18 evidence refresh

Confirmed defects and remaining limitations are listed in the dated repair reports. The real-profile frontend still lacks reviewed program/course/term candidate selectors; those calculation controls now fail closed. Candidate installed lifecycle, real two-subject capture, and native DPI/accessibility remain UNVERIFIED/BLOCKED by this task boundary. No performance improvement is claimed.

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| high | Historical imported-student discovery defect is fixed in source; installed proof is still pending | failed GitHub run plus source-E2E reproduction; `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1`, `apps/web/src/app/page.tsx` | Blocked installed restart readback | Keep demo ephemeral, restore the persisted import identity, and rerun authoritative Windows packaged E2E |
| high | Fresh-profile onboarding lacks installed lifecycle proof | local-only list/create API, web selection, and signed Extension discovery now exist; no disposable Windows acceptance account is available | Source-level readiness cannot substitute for create/restart/rediscovery/pairing evidence from the installed candidate | Run the documented lifecycle on a disposable Windows account; never use the protected canonical install or data as a test fixture |
| high | Controlled real-student beta execution is not complete | `docs/CONTROLLED_STUDENT_BETA_PLAN.md` | Release Candidate cannot be truthfully declared | Execute only with a participant-owned authenticated session, explicit authorization, and sanitized evidence |
| medium | LOCAL_DESKTOP and SERVER have separate migration paths | `apps/api/app/db/bootstrap.py`, `apps/api/alembic/`, `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md` | Schema behavior can drift | Maintain paired migration tests and upgrade evidence |
| medium | Very large high-churn integration files | code metrics and git history: `apps/web/src/app/page.tsx`, `apps/api/app/api/v1/academic.py` | Broad regression surface | Prefer small tested extractions when required by a concrete change |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| PostgreSQL-specific historical migration cannot initialize SQLite from base | LOCAL_DESKTOP adopted a separate deterministic path | Alembic revision `20260623_0004`, execution-plan docs | Misleading cross-database assumptions | Keep limitation explicit; do not rewrite history without a reviewed migration plan |
| Main workflow UI remains large | Many phases accumulated in one page before feature extraction | `apps/web/src/app/page.tsx` | State-coupling bugs | Extract only around proven defects with E2E coverage |
| No numeric coverage threshold | Gates emphasize functional suites | manifests/workflows | Coverage regressions may be less visible | Add thresholds only after measuring stable baselines |

### 3) Security Concerns

| Risk | OWASP category (if applicable) | Evidence | Current mitigation | Gap |
|------|--------------------------------|----------|--------------------|-----|
| Local API invoked by hostile localhost/web origin | A01 | `apps/api/app/security/local_request.py` | loopback, origin allowlist, extension pairing/nonce | Continue regression testing across every local endpoint |
| Portal/student data leakage through logs/evidence | A09 / privacy | diagnostics and beta docs | fixed allowlist, sanitization, manual export, synthetic CI | Real beta evidence still needs human inspection |
| Extension permission expansion | A01 | `apps/extension/manifest.json` | MV3, narrow permissions, optional Kean host | Any new institution requires explicit permission review |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| Bounded in-process optimizers | `academic_planner/engine.py`, `schedule_optimizer/engine.py` | No current failure established | Combinatorial growth on realistic data | Benchmark realistic synthetic sets before changing algorithms |
| Large frontend bundle/workflow | `apps/web/src/app/page.tsx` | Cold build and integration complexity | UI maintenance and render cost | Profile before optimization; keep behavior tests |

No verified N+1 database query or unnecessarily sequential external-call defect was established during this bounded acquisition pass; those should be profiled before being reported as defects.

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|-------------|----------------------|
| `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1` | Coordinates installer, Tauri, API, SQLite, WebView2 and UIA | 25 recent changes in scan evidence | Root-cause first; exact installed regression |
| `apps/web/src/app/page.tsx` | Shared workflow state and UI boundary | 36 recent changes | Focused Playwright plus packaged restart verification |
| Installer tests/scripts | Filesystem/process/NSIS assumptions | installer test file among top churn | Use isolated roots and fail-closed identity checks |

### 6) External acceptance boundaries

The earlier onboarding design question is resolved by the existing local-only onboarding API and UI (`apps/api/app/api/local_onboarding.py`, `apps/web/src/app/page.tsx`). No new user decision is required for the authorized background repair. [TODO] Run installed lifecycle only on an explicitly authorized disposable Windows account. The current request forbids visible desktop/portal testing, so real acceptance remains pending.

### 7) Evidence

- `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`
- `docs/CONTROLLED_STUDENT_BETA_PLAN.md`
- `apps/web/src/app/page.tsx`
- `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1`
- `apps/api/app/db/bootstrap.py`
