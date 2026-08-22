# Capability Matrix

Snapshot date: 2026-08-22 (Asia/Shanghai)

Classifications describe current release-convergence evidence, not historical phase labels:

- `COMPLETE`: implemented with current automated or installed evidence appropriate to the capability.
- `PARTIAL`: implemented, but an important test, installed, upgrade, or real-source acceptance layer remains.
- `BLOCKED`: required capability/evidence cannot currently be completed because an implementation or authorized external prerequisite is absent.
- `UNKNOWN`: current evidence is insufficient to classify safely.

| Capability | State | Code evidence | Test evidence | Real-world evidence | Remaining work |
|------------|-------|---------------|---------------|---------------------|----------------|
| Desktop shell | `PARTIAL` | `desktop-shell/src-tauri/src/main.rs`, Tauri config and identity contract | Cargo and installer lifecycle CI pass; post-fix source E2E passes | CI installs/launches/restarts; post-fix packaged E2E not yet run | Run fixed full packaged E2E on a disposable Windows runner |
| Local backend | `COMPLETE` | FastAPI entry/runtime discovery and local request security under `apps/api/app/` | API, runtime, packaging and CI suites pass at baseline | Failing packaged run proved ready local API through workflow write/restart | Reconfirm in final clean-head packaged run |
| Local database | `PARTIAL` | SQLite bootstrap/migrations under `apps/api/app/db/` | Local DB, persistence, backup and migration tests exist; source E2E proves restart readback | Packaged write completed; baseline harness failed before post-restart UI read | Re-run fixed installed persistence verification on a disposable runner |
| Student onboarding | `PARTIAL` | Local-only first-profile API/service, web create/select panel, and paired Extension discovery | API conflict/provenance tests, shared schemas, Extension worker/popup tests, focused browser E2E | Not yet exercised in a clean installed Windows account | Run create -> restart -> rediscover -> pair on a disposable installed candidate; keep school labels unverified and add reviewed program data separately |
| MyProgress import | `PARTIAL` | staging/review/apply APIs and parsers now have a supported fresh-profile bootstrap | Synthetic API/extension/browser tests; packaged synthetic import reached apply | No authorized participant source run | Execute controlled real source only after participant login and explicit authorization |
| Program Catalog import | `PARTIAL` | catalog/rule ingestion and reviewed-rule services | Fixture and domain/API tests | No controlled real catalog acceptance recorded | Validate official source, provenance and ambiguity behavior |
| Section import | `PARTIAL` | section import/review and optimizer provenance services | Synthetic section and optimizer tests | No controlled real section source run | Validate current real sections with stable source identity |
| Browser Extension capture | `PARTIAL` | MV3 popup/background/Kean extraction modules | Extension parser, permissions and synthetic DOM tests | No authorized current-session capture recorded | Participant login, explicit click, sanitized result, DOM-drift check |
| Source provenance | `PARTIAL` | source metadata models, import records and snapshot provenance | Parser/import/domain tests assert source references | Synthetic/fixture evidence only | Confirm provenance survives each controlled real-source workflow |
| Degree Audit | `PARTIAL` | degree audit/allocation services and persisted snapshots | Deterministic audit/allocation/API tests | No participant transcript/program acceptance | Compare result with reviewed source and advisor-facing explanation |
| Requirement evaluation | `PARTIAL` | versioned rule trees and evaluators | Deterministic rule tests | No controlled real program rule set | Validate official reviewed rules and uncertainty paths |
| Academic planning | `PARTIAL` | planner engine and scenario persistence | Feasible/infeasible planner tests | No participant plan acceptance | Run a controlled realistic plan and inspect explanations |
| Prerequisite checking | `PARTIAL` | composable eligibility expressions | Eligibility and domain tests | No controlled real catalog/student combination | Confirm with reviewed current catalog source |
| Corequisite checking | `PARTIAL` | composable eligibility expressions | Eligibility and domain tests | No controlled real catalog/student combination | Confirm concurrent-enrollment cases against reviewed source |
| Course eligibility | `PARTIAL` | eligibility service and reason codes | API/domain eligibility tests | No participant acceptance | Validate restrictions, standing and source assumptions |
| Schedule optimizer | `PARTIAL` | `apps/api/app/services/schedule_optimizer/` | Feasible, deterministic and infeasible tests | No real current section set | Run controlled real sections after source authorization |
| Conflict detection | `COMPLETE` | hard time-overlap constraints in optimizer | Deterministic conflict/infeasibility tests | Synthetic evidence is sufficient for the generic constraint | Reconfirm during full optimizer suite |
| Plan persistence | `PARTIAL` | scenario/plan models, APIs and snapshots | Persistence tests, packaged write phase, and source restart readback pass | Installed post-restart UI verification is not yet rerun on the fix | Pass fixed packaged restart readback |
| Backup | `PARTIAL` | backup service/API and local paths | Backup/security tests | No final-candidate installed backup exercise | Exercise on disposable synthetic installed DB |
| Restore | `PARTIAL` | restore validation/service/API | Restore, traversal, checksum/schema tests | No final-candidate installed restore exercise | Restore synthetic backup and prove equality on clean runner |
| Database migration | `PARTIAL` | Alembic for PostgreSQL; separate local SQLite migration runner | PostgreSQL CI and local migration tests; installer upgrade CI pass | Supported installed upgrade path passes CI | Keep historical SQLite-from-base limitation explicit; revalidate final HEAD |
| Verification Center | `BLOCKED` | No matching current UI/API feature found | No matching tests found | None | Decide whether this historical Phase 14B feature is required, then implement/test or remove it from release criteria |
| Preflight | `PARTIAL` | Packaged runtime has a local migration/process preflight command; no `/system/preflight` API | Runtime/installer preflight tests exist | Installer lifecycle CI uses runtime checks | Define/implement the requested system-level verification contract if required |
| Production authorization | `BLOCKED` | No current authorization CLI, repo/HEAD binding, fingerprint or PROD execution guard found | No matching security gate found | None; provider writes remain prohibited | Implement only from a reviewed threat model and explicit scope |
| Windows packaging | `COMPLETE` | identity/build/validation/NSIS scripts | Current CI package job passed; local 0.1.6 build and artifact validation passed | A local installer artifact was produced | Rebuild and re-hash from final clean committed HEAD |
| Installed runtime | `PARTIAL` | Tauri supervisor and packaged API bundle | Lifecycle CI passes; packaged E2E baseline fails after restart | Baseline CI proves install through restart; local canonical install intentionally untouched | Post-fix packaged green on disposable runner |
| Upgrade lifecycle | `COMPLETE` | lifecycle and versioned installer scripts | Current Windows installer lifecycle CI passes 0.1.5 -> 0.1.6 | CI exercises installed upgrade | Repeat for final candidate if release workflow changes |
| Uninstall / reinstall | `COMPLETE` | installer/uninstaller and data-retention contracts | Current lifecycle CI passes uninstall/reinstall and artifact roundtrip | CI confirms lifecycle; user data is retained by default | Reconfirm only on isolated synthetic data |
| Privacy / external egress | `COMPLETE` | loopback API, narrow extension permissions, diagnostics sanitization, no telemetry client | Security/policy/manifest tests and CI baseline pass | No external analytics/cloud integration is present | Re-run security gates on final HEAD; inspect real beta evidence manually |
| Security gates | `PARTIAL` | Current local-request, packaging, diagnostics, data-removal and extension policies exist | Corresponding repository tests and baseline CI pass | No production authorization/fingerprint gate exists | Run all current gates; separately decide missing historical Phase 14B gate scope |

## Cross-cutting blockers

1. Authoritative fixed packaged-desktop E2E requires a disposable Windows runner or clean Windows account; the current account contains a real canonical 0.1.5 install that must not be overwritten.
2. The local first-profile implementation now requires installed create/restart/rediscovery/pairing proof on a disposable Windows account; the current account's canonical data remains out of scope.
3. MyProgress, Program Catalog, Sections, extension capture, and downstream academic/optimizer real-source acceptance still require a participant-owned authenticated session and explicit authorization. No credentials may be requested, stored, logged, or pasted.
4. The historical prompt's Verification Center and production-authorization system are not present in the current repository. They cannot be reported complete or silently inferred from unrelated runtime checks.
