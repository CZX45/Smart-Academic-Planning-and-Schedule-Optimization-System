# Codebase Concerns

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| high | Persisted imported-student discovery was coupled to ephemeral demo activation | failed GitHub run plus source-E2E reproduction; `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1`, `apps/web/src/app/page.tsx` | Blocked installed restart readback | Keep demo ephemeral, restore the persisted import identity, and rerun authoritative Windows packaged E2E |
| high | A fresh local database has no production student-profile onboarding path | only `GET /students/{id}` exists; web has no create/select workflow; extension requires a manually entered ID | A real participant cannot begin the reviewed import flow without seed/direct-DB setup | Define a source-tagged onboarding contract; never guess institution/program identity or use mock seed as real data |
| high | Controlled real-student beta execution is not complete | `docs/CONTROLLED_STUDENT_BETA_PLAN.md` | Release Candidate cannot be truthfully declared | Close onboarding first, then execute only with participant-owned authenticated session and sanitized evidence |
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

### 6) `[ASK USER]` Questions

1. Should a fresh participant create a pseudonymous local profile by selecting a reviewed institution/campus/program, or should an administrator provision that profile from a signed/source-tagged package? This decision controls the missing onboarding API, UI, and extension-pairing contract.
2. Can the final installed candidate be run on a disposable Windows runner/account where the canonical product identity cannot touch an existing participant installation?

Real portal authentication and any risky data operation remain hard-stop user boundaries rather than implementation assumptions.

### 7) Evidence

- `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`
- `docs/CONTROLLED_STUDENT_BETA_PLAN.md`
- `apps/web/src/app/page.tsx`
- `scripts/windows/Invoke-Packaged-Desktop-E2E.ps1`
- `apps/api/app/db/bootstrap.py`
