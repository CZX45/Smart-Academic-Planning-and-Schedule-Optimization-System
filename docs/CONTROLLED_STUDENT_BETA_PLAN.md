# Controlled Student Beta Plan

## Purpose

Prepare a bounded, single-user Windows `LOCAL_DESKTOP` candidate for controlled
student testing. This document defines readiness and the protocol; it does not
declare that real-student testing has been completed.

## Scope and entry criteria

The beta covers local installation, first launch, extension pairing,
user-owned portal-page capture, review-gated local import, degree audit,
eligibility, academic planning, what-if isolation, reviewed section import,
advisory schedule optimization, backup, restore, diagnostics, restart, and
uninstall/reinstall.

Entry requires the latest `main` to include PR #79 merge
`8efa290103ebb465942ee0d2c744fcc11ea0eb93`; reviewed plan/checklist;
successful Regular CI, privacy/security checks, Windows installer foundation,
Windows installer lifecycle, and Windows Packaged Desktop E2E on the
authoritative runner; a Beta / Pre-release / Controlled Testing Only label; and
local backup space for each participant.

## Participants and environment

One student at a time tests on their own Windows computer with their own local
data. The app remains local-first, single-user, read-only/advisory, and
non-official. It adds no cloud account, shared database, telemetry, automatic
crash upload, cloud synchronization, advisor administration, or registration
action.

Use `PRODUCT_MODE=LOCAL_DESKTOP`, the loopback-only local API, SQLite in the
user's AppData, and the locally loaded browser extension. CI continues to use
synthetic/sanitized fixtures only. Real identity, transcripts, raw portal HTML,
credentials, cookies, tokens, sessions, and the SQLite student database must
not enter Git, GitHub, CI, or shared evidence.

## Privacy, retention, and diagnostics

Academic, planning, schedule, backup, restore, pairing, and diagnostics state
remain on the participant's computer. Feedback is manual. A participant may
voluntarily provide an inspected sanitized diagnostics bundle; no background
collection or automatic upload is enabled.

Normal uninstall removes application files and retains local data and backups.
Explicit local-data removal is separate, typed-confirmed, externally backed up,
allowlisted, expiry/replay/reparse protected, and must never remove the user's
backup accidentally.

## Portal and authentication safety

The participant alone enters username, password, MFA, SSO, CAPTCHA, and every
authentication challenge. Codex or the extension must never receive, store,
extract, or log authentication material. If authentication expires, pause until
the participant completes it and explicitly confirms: “Login complete, you may
continue.”

After that confirmation, computer-assisted work may navigate and read visible
pages and operate this product's local capture/import/review/apply flow. It must
remain read-only/advisory: never click Register, Add, Drop, Swap, Waitlist, seat
reservation, or any control that changes an official school record.

## Computer-assisted verification

Computer assistance is allowed only on the participant's current,
already-authenticated browser session and local app. It may perform bounded
navigation, visible-page reading, screenshots, extension capture, staging,
preview, review, local apply, planning, schedule comparison, backup, restore,
restart, diagnostics, and uninstall tests. It may not automate login, persist
sessions, extract cookies/tokens/headers, poll in the background, or submit
school forms.

Every real-portal result is labeled `MANUAL / COMPUTER-ASSISTED BETA
VERIFICATION`. Final academic interpretation remains manual and must be checked
against the official portal, catalog, Registrar, or advisor.

## Data and academic safety

MyProgress and Section workflows remain:

```text
capture → staging → preview → review → apply → reviewed persisted state
```

Staging cannot feed formal analysis. Applied data remains non-official and
source-tagged. The optimizer may use `REVIEWED_IMPORTED` only when institution,
term, course/section identity, provenance, observation time, age, and drift
checks pass; it must not silently fall back to `DEMO_MOCK`.

Degree audit, eligibility, planner, and optimizer outputs are advisory and
non-official. Unknown or insufficient rules remain `UNKNOWN`, `MANUAL_REVIEW`,
or `ADVISOR_REVIEW`; they must not become unjustified eligible, guaranteed
graduation, guaranteed registration, or guaranteed seats. Volatile capacity and
waitlist data is advisory evidence with `observed_at` only.

## Protocol and feedback

Participants execute the companion checklist in order: install/launch; pair;
manually authenticate and test MyProgress; verify audit, eligibility, planner,
and what-if isolation; import reviewed sections; run advisory optimization;
exercise backup, restore, diagnostics, restart, uninstall, retention, and
explicit-removal boundaries; then record findings and sanitized evidence.

No analytics, telemetry, crash reporting, or automatic diagnostics upload is
added. Findings use `BLOCKER`, `HIGH`, `MEDIUM`, or `LOW` and categories
`PARSER`, `DATA_MAPPING`, `ACADEMIC_RULE`, `MISLEADING_STATE`, `PLANNER`,
`SCHEDULE`, `EXTENSION`, `INSTALLER`, `RECOVERY`, `DIAGNOSTICS`,
`ACCESSIBILITY`, `PERFORMANCE`, `PRIVACY`, `SECURITY`, or `UX`.

## Focused readiness audit matrix

This is the pre-edit audit baseline. `READY` means supported by current code,
tests, or merged evidence; `PARTIAL` means a known limitation remains;
`MANUAL VERIFICATION REQUIRED` means the real Windows or participant step is
not established by local automation alone.

| Area | Status | Basis / remaining proof |
| --- | --- | --- |
| Installer | MANUAL VERIFICATION REQUIRED | Existing Windows foundation CI; candidate installer still needs runner proof. |
| First launch / packaged FastAPI / supervision / readiness | MANUAL VERIFICATION REQUIRED | PR #79 runner proof exists; rerun required for candidate head. |
| WebView and SQLite persistence | MANUAL VERIFICATION REQUIRED | PR #79 evidence exists; real candidate execution remains required. |
| Extension pairing | READY | Pairing implementation and regression tests; participant pairing remains checklist work. |
| MyProgress capture/staging/preview/review/apply | READY | Review-gated implementation and focused tests; real portal flow is manual. |
| Degree Audit / Eligibility / Planner | READY | Existing deterministic tests and advisory/unknown semantics; official comparison is manual. |
| What-If isolation | READY | Isolation tests cover no formal-state mutation. |
| Reviewed Section import / provenance | READY | Reviewed workflow, source metadata, age/drift fields, and tests exist. |
| Schedule Optimizer | READY | Reviewed-import gate, constraints, and infeasibility explanations are tested. |
| Backup / Restore / safe migration | PARTIAL | Local tests pass; historical PostgreSQL-specific revision `20260623_0004` remains limited. |
| Diagnostics and sanitized export | READY | Fixed-allowlist local diagnostics and privacy regression tests exist. |
| Restart / graceful shutdown / no orphan | MANUAL VERIFICATION REQUIRED | PR #79 evidence exists; candidate runner proof remains required. |
| Uninstall / retention / explicit removal | MANUAL VERIFICATION REQUIRED | Lifecycle script and tests exist; real Windows lifecycle proof is required. |
| Backup retention safety | READY | Lifecycle and local-data-removal protections are tested. |
| Mock / real-data isolation | READY | `REVIEWED_IMPORTED` gates, non-official labels, and safety tests exist. |
| Privacy / portal safety / authentication boundaries | READY | Policy docs and regression tests prohibit credential and record-writing automation. |
| Accessibility of critical workflows | MANUAL VERIFICATION REQUIRED | Formal accessibility audit is not complete. |
| Error handling and non-official disclaimers | READY | Error-state tests and advisory copy exist. |
| Beta plan/checklist | READY | This plan and companion checklist are present. |
| Manual verification boundaries | READY | Manual login/MFA pause and read-only portal rules are explicit. |

The audit found no confirmed code-level Controlled Beta blocker. The truthful
documentation status drift in the execution plan was a readiness blocker and is
reconciled in this change. Real Windows candidate execution, accessibility
review, and participant protocol execution remain manual requirements.

## Rollback, limitations, and exit

Stop and preserve the local backup for suspected corruption, privacy leak,
security issue, or official-record mutation. The historical SQLite
Alembic-from-base path remains incompatible at revision `20260623_0004` for
PostgreSQL-specific operations; the current `LOCAL_DESKTOP` production path
does not depend on that full historical chain. This milestone records that
limitation and does not rewrite historical migrations.

Other limitations include mock/sanitized fixture coverage, lack of formal
accessibility certification, and the need for manual school/advisor
confirmation of high-impact academic guidance.

Readiness is complete only after the documents, automated gates, authoritative
Windows installer/lifecycle/packaged E2E evidence, privacy/security review,
protected-artifact review, and PR review are complete. Controlled Student Beta
itself requires real participant execution, finding collection, and a separate
closeout.

## Explicit non-goals

No Release Candidate, production release, code signing, GitHub Release,
Store/MSIX package, automatic update, cloud backend, multi-user SaaS, SSO/OIDC
architecture, advisor portal, telemetry, registration automation, or beta
findings hardening is started by this plan.
