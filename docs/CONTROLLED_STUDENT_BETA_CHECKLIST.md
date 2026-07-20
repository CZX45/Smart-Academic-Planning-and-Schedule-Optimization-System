# Controlled Student Beta Checklist

Record `PASS`, `FAIL`, `BLOCKED`, or `MANUAL VERIFICATION REQUIRED` per item.
Never record credentials, raw portal HTML, full transcripts, or raw screenshots
in the repository. Share only inspected sanitized evidence.

## A — Windows install and first launch

- [ ] Verify the installer is labeled Beta / Pre-release / Controlled Testing Only.
- [ ] Install and confirm Tauri, packaged FastAPI, loopback readiness, WebView,
      visible UI, and bounded startup-error handling.

## B — Extension pairing

- [ ] Verify local pairing success, invalid pairing, retry, expired pairing,
      desktop-unavailable behavior, and no remote student-data connection.
- [ ] Confirm no credential is collected.

## C — MyProgress computer-assisted flow

- [ ] Stop for participant login, password, MFA/SSO/CAPTCHA. Continue only after
      the participant explicitly says: “Login complete, you may continue.”
- [ ] Read only the visible MyProgress page; never extract cookies, tokens,
      headers, session storage, or click a record-writing control.
- [ ] Capture → stage → preview → review → apply, then check identity/title,
      status, credits, completed/in-progress/planned state, provenance, warnings,
      truncation, missing rows, and duplicates.
- [ ] Label the outcome `MANUAL / COMPUTER-ASSISTED BETA VERIFICATION`.

## D — Degree audit

- [ ] Compare completed, in-progress, planned, remaining, and unknown results
      with the official page; check duplicates, missing requirements, credits,
      program/catalog mapping, and silent mock fallback.
- [ ] Do not call the result officially verified.

## E — Eligibility

- [ ] Check prerequisite, corequisite, restriction, permission, unknown,
      manual-review, and advisor-review outcomes.
- [ ] Verify insufficient rules remain `UNKNOWN` or review-required, never an
      unjustified `ELIGIBLE` result.

## F — Planner and what-if

- [ ] Verify long-term plan, credits, save/close/restart/persistence, and
      What-If isolation; confirm What-If does not mutate formal academic state.

## G — Reviewed section import

- [ ] After manual authentication confirmation, select target term/institution,
      capture, stage, preview, review, and apply.
- [ ] Check course/section identity, term, institution, lecture/lab/recitation,
      meeting time, provenance, `observed_at`, source age, and drift.
- [ ] Never click Register, Add, Drop, Swap, or Waitlist.

## H — Schedule optimizer

- [ ] Confirm input is `REVIEWED_IMPORTED`, not silent mock data.
- [ ] Check credit limits, conflicts, Friday preference, earliest/latest time,
      unavailable blocks, lecture/lab association, infeasibility explanations,
      optimizer explanations, provenance, and advisory wording.
- [ ] Perform no registration action.

## I — Backup and J — Restore

- [ ] Run local Backup and verify archive, app version, schema version, metadata,
      and backup time; confirm no automatic upload.
- [ ] Preview Restore, explicitly confirm, restore, restart, verify data and
      rollback safety, and confirm the backup is not deleted.

## K — Diagnostics privacy

- [ ] Trigger export manually and inspect the ZIP before sharing.
- [ ] Confirm it contains only sanitized app/build/commit identity, product
      mode, runtime/API/database health, schema/migration, startup/restore/
      pairing status, and error categories—not identity, full academic history,
      raw portal HTML, password, cookie, token, session, auth data, or SQLite.

## L — Restart and no orphan

- [ ] Close the app; verify Tauri and packaged API exit, no orphan remains,
      restart reaches readiness, and persisted state is present.

## M — Uninstall and retention

- [ ] Run normal uninstall and verify default data retention; reinstall and
      verify persistence/restoration.
- [ ] If explicit local-data removal is offered, run it only with separate
      confirmation and an external backup; verify backups remain.

## Accessibility and findings

- [ ] Check keyboard navigation, focus visibility, semantic labels, major button
      names, error/status messages, zoom, and basic layout usability.
- [ ] Record each finding with severity/category, workflow, sanitized symptom,
      reproduction, expected/actual result, app/build identity, and remaining
      school/advisor confirmation. Do not attach real student data or auth data.
