# Final Demo Script

This 5-8 minute script presents the project as a smart academic planning and
schedule optimization system. Use mock or reviewed non-official data only. Keep
the language advisory: imported snapshot, manual review required, advisory
alert, read-only import, non-official data, and verify in the official portal.

## 1. Opening / Project Motivation

What to show:

- The README and dashboard entry point.
- The final project summary and release-readiness docs.

What to say:

- "This project helps students and advisors reason about degree progress,
  eligibility, future plans, and possible section schedules in one explainable
  review surface."
- "It is not a registration bot and it does not change anything in a school
  portal."

Expected audience takeaway:

- The product is an advisory academic planning system with clear boundaries.

Safety wording reminder:

- "High-impact academic guidance must be confirmed with the school or an
  advisor."

## 2. Academic Data Import and Review

What to show:

- A Phase 7A import preview with records, mapping candidates, warnings, and
  preview summary.
- A Phase 7B review session with confirm, reject, defer, and advisor-review
  decisions.
- A dry run before applying supported rows to internal planning records.

What to say:

- "This is a non-official imported snapshot. It enters staging first."
- "Manual review required rows stay out of internal planning application until
  a user explicitly decides what to do."

Expected audience takeaway:

- Imported data is source-tagged, review-gated, and never treated as official by
  default.

Safety wording reminder:

- "The user should verify in the official portal before relying on imported
  academic data."

## 3. Degree Audit and Planning

What to show:

- Degree audit summary credits, requirement rows, warnings, and applied course
  explanations.
- Long-term plan terms, planned courses, coverage, and warnings.

What to say:

- "The audit is a deterministic snapshot with requirement-level explanations and
  reason codes."
- "The long-term planner stays course-level and separates planning from
  section-level scheduling."

Expected audience takeaway:

- Degree progress and plans are explainable and reviewable.

Safety wording reminder:

- "Mock, inferred, or ambiguous rules require advisor or school confirmation."

## 4. Course Eligibility

What to show:

- A course or section eligibility check with rule evaluations, expression
  evidence, warnings, and corequisite summary.

What to say:

- "Eligibility checks evaluate stored rule trees against a student planning
  record."
- "Section availability is shown separately from academic eligibility so seat
  status does not rewrite prerequisite or restriction results."

Expected audience takeaway:

- Eligibility results are structured and auditable, not hidden UI logic.

Safety wording reminder:

- "Eligibility output is advisory and should be confirmed with the school when
  it affects enrollment decisions."

## 5. Schedule Optimization

What to show:

- A semester schedule optimization run with requested courses, constraints,
  ranked options, conflicts, score breakdowns, and repair suggestions.

What to say:

- "The optimizer compares concrete mock sections for a term using hard
  constraints and preference scoring."
- "Repair suggestions explain how a student might manually relax constraints or
  review alternatives."

Expected audience takeaway:

- Schedule optimization is section-level, deterministic, and explainable.

Safety wording reminder:

- "These are advisory planning options, not official enrollment outcomes."

## 6. Browser Extension Read-Only Import

What to show:

- The local-development extension surface.
- A visible-page table extraction preview.
- Explicit confirmation before sending data to the API as a staging import.

What to say:

- "The extension reads only the active visible page after the user clicks the
  extension action."
- "It sends a read-only import to the same review-gated backend flow."

Expected audience takeaway:

- The extension is a controlled import assistant, not school-system automation.

Safety wording reminder:

- "It does not store credentials, read password fields, bypass school login, or
  submit portal forms."

## 7. Section Monitoring Advisory Alerts

What to show:

- A monitor target.
- Two user-triggered section-search snapshots.
- Advisory alerts for changed status, counts, meeting time, instructor,
  location, or unknown payload differences.

What to say:

- "Section monitoring compares imported snapshots and creates advisory alerts."
- "An alert tells a student what changed and what to review manually."

Expected audience takeaway:

- Monitoring helps organize review but does not represent official current
  portal state.

Safety wording reminder:

- "Before acting, verify in the official portal."

## 8. Dashboard Polish

What to show:

- Dashboard status cards for degree audit, data import review, browser
  extension import, section monitoring, schedule optimization, and what-if
  planning.
- Empty states and manual next-action copy.

What to say:

- "The dashboard keeps the next review step visible instead of hiding workflow
  state behind unsupported automation."
- "Labels distinguish mock, non-official, advisory, and manual-review data."

Expected audience takeaway:

- The UI is ready for demo and review across the main product journeys.

Safety wording reminder:

- "Dashboard guidance organizes review; it does not replace school policy."

## 9. Security, Privacy, and Read-Only Boundary

What to show:

- Security and privacy docs.
- Release checklist.
- Production safety policy tests.
- Final safety and non-automation statement.

What to say:

- "The project keeps school-portal boundaries explicit: no credential capture,
  no hidden automation, no portal form submission, and no course-action
  automation."
- "Logs and docs are designed to avoid leaking sensitive student data or
  overstating source quality."

Expected audience takeaway:

- Safety boundaries are documented and tested.

Safety wording reminder:

- "Real deployment needs separate institutional review, data governance, and
  production controls."

## 10. Final Conclusion

What to show:

- Final project summary.
- Feature inventory.
- Handoff checklist.

What to say:

- "The project now has an end-to-end advisory planning foundation, release QA,
  demo guidance, and a handoff package."
- "Next work should focus on production readiness, institutional review,
  accessibility, observability, and richer source-tagged fixture coverage."

Expected audience takeaway:

- The project is ready for review as a final demo and handoff package.

Safety wording reminder:

- "Students remain responsible for manual verification in official school
  systems."
