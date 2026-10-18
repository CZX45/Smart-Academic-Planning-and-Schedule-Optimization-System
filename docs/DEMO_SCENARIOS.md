# Demo Scenarios

Phase 10A — Release Readiness QA and Final Product Review demos should make the
product feel coherent while staying precise about source quality and safety
boundaries. Use mock or reviewed non-official data only.

## Demo-Safe Language

Preferred wording:

- imported snapshot
- advisory alert
- manual review required
- verify in the official portal
- read-only imported data
- non-official data
- advisor or school confirmation required

Avoid promising live portal state, seat guarantees, in-app registration,
in-app seat holds, continuous section watching, automated waitlist actions, or
official school policy unless a future reviewed official-source workflow
explicitly supports the claim.

## Scenario 1: Data Import Review and Confirmation

What to show:

- Create a mock data import preview from the dashboard.
- Open records, mapping candidates, validation warnings, and preview summary.
- Create a Phase 7B review session and show confirm/reject/defer/advisor-review
  decisions.
- Run dry run before applying confirmed supported rows.

What the user should understand:

- Phase 7A import data is staged, source-tagged, and non-official.
- Phase 7B review is the explicit human gate before any internal planning write.
- Applied records stay internal and non-official.

What not to claim:

- Do not imply imported rows are official transcript data.
- Do not imply review decisions replace school or advisor confirmation.
- Do not imply unsupported rows are silently applied.

Demo-safe wording:

- "This is a non-official imported snapshot for planning review."
- "Manual review required rows stay out of internal planning application."
- "The dry run shows proposed writes before anything changes."

Manual verification reminder:

- "For high-impact choices, verify in the official portal and with an advisor."

## Scenario 2: Browser Extension Read-only Import

What to show:

- Explain that the extension reads only the active visible page after user action.
- Show a local mock page extraction and preview.
- Confirm that the import is sent as `source_type = BROWSER_EXTENSION`.

What the user should understand:

- Extension data is read-only imported data.
- The extension does not store portal credentials or read password fields.
- Phase 7B review remains required before application.

What not to claim:

- Do not claim the extension is a production browser-store release.
- Do not claim it bypasses school authentication.
- Do not claim it submits or changes anything in a portal.

Demo-safe wording:

- "The extension converts visible table text into a non-official staging import."
- "The user confirms before data is sent to the backend."

Manual verification reminder:

- "Treat the imported snapshot as a starting point and verify in the official portal."

## Scenario 3: Section Monitoring Advisory Alert

What to show:

- Load an advisory monitor target.
- Compare user-triggered section-search snapshots.
- Open alert details for status, seat count, waitlist count, meeting, instructor,
  or location changes.

What the user should understand:

- Alerts are advisory and derived from non-official snapshots.
- The system does not change sections, seats, waitlists, schedules, or registration
  state.
- Alerts tell students what to review manually.

What not to claim:

- Do not claim official availability.
- Do not claim continuous portal watching.
- Do not claim the app can hold or change a seat.

Demo-safe wording:

- "This advisory alert compares imported snapshots and needs manual review."
- "Use this as a prompt to check the school system yourself."

Manual verification reminder:

- "Before acting, verify in the official portal."

## Scenario 4: Dashboard Status Cards and Empty States

What to show:

- Degree audit, data import review, browser extension import, section monitoring,
  schedule optimization, and what-if status cards.
- Empty states for missing imports, missing confirmed imports, missing targets,
  missing advisory alerts, missing schedules, and missing scenarios.
- Manual next-action copy and advisory labels.

What the user should understand:

- The dashboard is a review surface for existing workflows.
- Empty states are guidance, not hidden automation.
- Labels distinguish mock, non-official, advisory, and manual-review states.

What not to claim:

- Do not claim the dashboard is authoritative school policy.
- Do not claim it can perform official academic actions.

Demo-safe wording:

- "The dashboard keeps the next manual review step visible."
- "Every imported or advisory workflow keeps source uncertainty visible."

Manual verification reminder:

- "Use dashboard status to organize review, then confirm official details separately."

## Scenario 5: Schedule Optimization Review

What to show:

- Create or load a schedule optimization run.
- Review ranked options, selected sections, score breakdowns, conflicts, warnings,
  and repair suggestions.
- Show that schedule options are snapshots with explanations.

What the user should understand:

- The optimizer ranks possible mock section combinations for review.
- Closed, waitlisted, or uncertain section data is treated as a warning or
  conflict, not permission to act.
- Repair suggestions explain possible manual relaxations.

What not to claim:

- Do not claim an option is officially available.
- Do not claim the app changes enrollment.
- Do not claim the app performs add/drop/swap actions.

Demo-safe wording:

- "This schedule is an advisory planning option based on mock or imported data."
- "Warnings and conflicts explain what needs human review."

Manual verification reminder:

- "Confirm section status and any enrollment action directly with the school."

## Scenario 6: Security and Privacy Boundary Explanation

What to show:

- Security and privacy docs.
- Release checklist no-secrets and prohibited-automation review.
- Extension permission policy tests.
- Production safety policy tests.

What the user should understand:

- The system intentionally avoids portal credential storage and school-system
  automation.
- Imported data remains source-tagged and review-gated.
- Logs must contain low-sensitivity metadata only.

What not to claim:

- Do not claim production FERPA readiness without institutional review.
- Do not claim official source ingestion exists.
- Do not claim external telemetry is enabled.

Demo-safe wording:

- "This release candidate is scoped to advisory planning with mock and
  non-official reviewed data."
- "The safety tests guard against misleading action names and unsafe demo copy."

Manual verification reminder:

- "Security, privacy, and institutional-data handling require separate review before
  real deployment."
