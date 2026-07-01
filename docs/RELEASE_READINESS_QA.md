# Release Readiness QA

Phase 10A — Release Readiness QA and Final Product Review prepares the current
mock, school-agnostic product for final review, demo, and handoff. It does not
add backend domains, official-source ingestion, production deployment,
credential handling, portal automation, or registration automation.

All QA evidence in this document assumes mock or student-provided data unless a
future reviewed official-source workflow states otherwise. High-impact academic
guidance remains advisory and must be confirmed with the school or an advisor.

## Scope

- Confirm the main end-to-end product journeys are reviewable.
- Confirm demo language uses non-official, read-only, advisory wording.
- Confirm the release checklist covers local commands and CI-only checks.
- Confirm the safety boundary is still visible in docs and tests.

## User Flow QA Matrix

| Flow | Purpose | Prerequisites | Test steps | Expected result | Safety boundary confirmation | Automated coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Create or review academic data import | Show Phase 7A staging import preview for mock or student-provided academic rows. | API, web app, mock seed data, and `NEXT_PUBLIC_API_BASE_URL` configured. | Open the dashboard, choose a mock import sample, create a preview, inspect records, mapping candidates, warnings, and preview summary. | Import rows remain staged with source metadata, mapping explanations, warnings, and non-official labels. | No imported row becomes official or writes to transcript, catalog, section, seat, waitlist, or registration state. | `apps/api/tests/test_data_imports.py`, shared schema tests, Playwright import flow coverage. |
| Confirm imported data through Phase 7B review | Show Phase 7B — Data Review and Confirmation Workflow for explicit review decisions and dry-run/apply outcomes. | A Phase 7A import run exists. | Create a review, confirm/reject/defer records, run dry run, then apply only confirmed supported records. | Application logs show applied and skipped records with reason codes; confirmed internal planning attempts remain non-official. | Manual review required for ambiguous records; GET endpoints do not apply data. | `apps/api/tests/test_data_reviews.py`, Playwright review panel coverage. |
| Use browser extension import for read-only imported data | Show Phase 8A — Read-only Browser Extension Import as a local-development visible-page import handoff. | Extension built locally, user has actively opened a page, and API is configured. | Click extension action, extract visible table rows, review the preview, confirm send to staging import. | Data enters Phase 7A as read-only imported data with `source_type = BROWSER_EXTENSION`. | No credentials, password fields, SAML/MFA bypass, portal submission, background scraping, or polling. | `apps/extension/tests/extractors.test.ts`, `apps/extension/tests/manifest-policy.test.ts`, backend source-type import tests. |
| Review section monitoring advisory alerts | Show Phase 8B — Read-only Section Monitoring Alerts for user-triggered snapshot comparison. | A monitor target and at least two non-official section-search snapshots exist. | Create/load a monitor target, compare snapshots, review alerts, acknowledge an alert. | Alerts explain changed fields and say to verify in the official portal before acting. | Alerts are advisory only and never change canonical sections, seats, waitlists, schedules, or registration state. | `apps/api/tests/test_section_monitoring.py`, extension section-search extractor tests, Playwright monitoring coverage. |
| Review degree audit and planner status | Show current degree progress and long-term planning status from existing mock data. | Mock student, program, audit, and planner fixtures are seeded. | Run/load a degree audit, inspect requirements, warnings, planner terms, planned courses, and coverage. | Results show requirements, warnings, assumptions, reason codes, and advisor-confirmation messaging. | Mock, inferred, or ambiguous policy is not presented as official school policy. | `apps/api/tests/test_degree_audit_policy.py`, `apps/api/tests/test_academic_planner.py`, shared schema tests, Playwright dashboard coverage. |
| Review schedule optimization status | Show section-level schedule optimization snapshots and infeasibility/repair explanations. | Mock sections, eligibility rules, and schedule fixtures are seeded. | Create/load a schedule optimization, inspect ranked options, conflicts, warnings, score breakdowns, and repair suggestions. | Options are explainable snapshots, not official registration state. | Scheduler does not poll seats, submit portal forms, alter waitlists, or perform registration actions. | `apps/api/tests/test_schedule_optimizer.py`, shared schema tests, Playwright schedule coverage. |
| Review manual action checklist | Confirm the UI and docs make user-owned follow-up explicit. | Dashboard is loaded with mock data. | Inspect status cards, monitoring panel, and release docs for manual next actions. | Copy uses advisory alert, manual review required, and non-official language. | Any official course change is outside the app and requires user action in school systems. | Playwright dashboard safety assertions and `apps/api/tests/test_production_safety_policy.py`. |
| Verify official portal manually | Confirm release messaging points users back to the school system. | User has independent school portal access outside this app. | Compare any imported snapshot, schedule option, or alert against the official portal manually. | User understands the app is not authoritative and does not replace school confirmation. | The system does not log in, submit, refresh, or bypass school systems. | Manual QA plus safety-policy regression tests. |

## Final Safety Boundary Audit

Before release review, confirm:

- No portal credentials are stored.
- No password fields are extracted.
- No SAML/MFA/CAPTCHA bypass exists.
- No portal form submission exists.
- No background scraping exists.
- No polling exists.
- No automatic registration exists.
- No add/drop/swap automation exists.
- No waitlist automation exists.
- No seat reservation exists.
- No seat grabbing exists.
- No browser-store publishing exists.
- No hidden automation exists.
- No external telemetry exists without explicit approval.
- No production deployment has been performed without explicit approval.

## Known Local Limitations

- Data is mock, student-provided, or imported from user-reviewed local fixtures.
- Docker Compose and Alembic validation may depend on local Docker availability.
- Browser extension behavior is local-development only.
- Official school policy, course availability, advisor approval, and registration
  status must be confirmed outside the app.

## Exit Criteria

- Release QA, demo scenarios, and release checklist docs are reviewed.
- Format, lint, typecheck, test, build, e2e, OpenAPI, Ruff, mypy, and pytest
  checks pass locally or are reported with exact blockers.
- CI validates Alembic migration checks and Docker Compose behavior.
- No credentials, secrets, prohibited automation, or misleading registration
  wording are added.
