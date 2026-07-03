# Kean Student Portal Import Guide

Phase 11B adds a user-authorized, read-only browser-extension workflow for
Kean / Ellucian Student Portal academic-planning data. The workflow imports
only non-official staging data and keeps Phase 7B review required before any
planning use.

## Purpose

The Kean Student Portal Academic Import helps a student move visible
academic-planning rows from the Kean Student Portal into the local Smart
Academic Planner staging import workflow. It is not an official school data
feed and it is not a portal automation tool.

## Manual Login Model

The student opens the official portal and logs in manually:

```text
https://kean-ss.colleague.elluciancloud.com/Student
```

The extension does not log in, collect passwords, read password fields, store
school credentials, store cookies, store session tokens, bypass SAML/MFA, or
submit portal forms.

## Supported Origin

The only supported portal prefix is:

```text
https://kean-ss.colleague.elluciancloud.com/Student/*
```

Chrome host permissions are declared at host scope, so the optional manifest
permission is:

```text
https://kean-ss.colleague.elluciancloud.com/*
```

The extension enforces the narrower `/Student/` prefix in extraction code and
returns no data for other paths on the same host.

## Supported Academic Data

Allowed data is limited to academic-planning categories that are visibly
displayed on supported pages:

- transcript, completed-course, and attempted-course rows;
- course code, course title, grade, credit, term, status, and GPA-like summary
  values when visibly relevant;
- degree audit, MyProgress, satisfied requirement, unsatisfied requirement, and
  program requirement rows;
- course catalog rows, prerequisites, restrictions, descriptions, departments,
  levels, and credits;
- section search, student planning, and schedule rows with section ID, status,
  seats available, capacity, waitlist count, meeting days/time, instructor,
  location, and term.

Forbidden data includes usernames, passwords, MFA codes, hidden credential-like
fields, cookies, session tokens, payment information, unrelated personal data,
financial account data, emergency contact data, form submission payloads,
registration cart action payloads, add/drop/swap/waitlist action payloads, and
hidden form values used for portal actions.

## Current Page Import Mode

Mode A uses the currently active tab.

1. The student manually opens a supported Kean Student Portal page.
2. The student opens the extension.
3. The student clicks `Extract current page`.
4. The extension reads visible academic table text from the active page.
5. The extension shows detected page type, row counts, warnings, and a preview.
6. The student clicks `Confirm staging import` before anything is sent.

This mode uses `activeTab` and does not crawl or fetch other portal pages.

## Guided Full Academic Import Mode

Mode B is a guided, student-driven sequence.

1. The student clicks `Start Kean Academic Import`.
2. The extension explains the boundary and requests the Kean optional host
   permission if it has not already been granted.
3. The student manually opens each relevant supported page.
4. The student clicks `Capture current guided page` on each page.
5. The extension combines captured transcript, MyProgress/degree audit,
   catalog, section search, student planning, or schedule extracts.
6. The extension shows a combined preview.
7. The student clicks `Confirm staging import`.

The guided mode does not perform broad crawling, hidden background scraping,
periodic polling, form submission, or enrollment actions.

## Page Whitelist

The extension uses configurable page definitions rather than invented official
Kean routes. Current definitions are:

- `KEAN_TRANSCRIPT_PAGE`
- `KEAN_DEGREE_AUDIT_PAGE`
- `KEAN_MY_PROGRESS_PAGE`
- `KEAN_COURSE_CATALOG_PAGE`
- `KEAN_SECTION_SEARCH_PAGE`
- `KEAN_STUDENT_PLANNING_PAGE`
- `KEAN_SCHEDULE_PAGE`

Each definition includes page type, route markers, visible text markers,
extraction strategy, expected academic fields, missing-field warning codes, and
safety restrictions. If Kean/Ellucian changes labels or paths, update these
definitions and fixtures with fake data only.

## Permission Model

Baseline permissions remain narrow:

```text
activeTab
scripting
storage
```

The Kean host is an optional host permission requested only when the student
starts the guided Kean workflow. The extension does not use `<all_urls>`, broad
host permissions, `cookies`, background alarms, or publishing workflow code.

## Preview and Confirmation

The extension must show a preview before import. The preview includes detected
page type, row counts by import type, warnings, non-official/manual-review
labels, and sample extracted rows. No silent import is allowed.

## MyProgress Summary Verification

Kean MyProgress imports treat the top MyProgress summary and visible progress
bar as first-class source evidence. The browser-extension payload preserves:

- program, degree, major, department, catalog year, GPA, anticipated completion
  date, and total-credit summary fields;
- progress-bar segment text and reconciled completed, in-progress, planned,
  remaining, and completion-percentage values;
- field-level provenance with raw text, source area, confidence, and
  `requiresReview`;
- bounded raw snapshot evidence such as page title, safe URL, visible text
  sample, headings, visible tables and rows, requirement-like blocks,
  course-like rows, progress text, counts, and truncation diagnostics.

High-confidence MyProgress fields are auto-confirmed when formats are valid,
summary totals reconcile, no conflicts are detected, and the snapshot is not
truncated. Manual review is exception-based: missing critical fields,
conflicting values, unsupported or ambiguous rows, low parser confidence,
truncation, and mock/real mixing create exception items. The student should not
be asked to review every high-confidence MyProgress row.

## Local App Handoff

After confirmation, the extension sends academic staging data to:

```text
POST /api/v1/data-imports
```

Payloads are marked:

```text
source_type = BROWSER_EXTENSION
source_label = KEAN_STUDENT_PORTAL in preview metadata
is_official = false
official_application_ready = false
```

The source label is carried through safe source-reference text and backend
preview metadata; no new database table or migration is required.

## Phase 7B Review Requirement

Kean portal imports enter the same Phase 7A/7B path as other staging imports.
For MyProgress, high-confidence records may start as auto-confirmed staging
records and the UI should show only the exception queue. Failed MyProgress
validation blocks downstream academic analysis. Unsupported catalog, section,
requirement, ambiguous, rejected, deferred, advisor-review, and duplicate
records remain skipped with warnings. High-impact academic conclusions still
need Kean or advisor confirmation.

## Safety Boundaries

The extension never:

- logs in for the student;
- collects or stores school credentials;
- reads password fields;
- extracts hidden credential-like fields;
- stores cookies or session tokens;
- bypasses SAML, MFA, CAPTCHA, authorization, or access controls;
- submits portal forms;
- registers, drops, swaps, waitlists, reserves seats, or grabs seats;
- runs background scraping or periodic polling;
- scans unrelated portal areas;
- claims imported rows are official school policy;
- publishes a browser-store workflow.

High-impact academic guidance must still be confirmed with Kean or an advisor.

## Troubleshooting

- If the extension says the page is unsupported, confirm the URL starts with the
  supported `/Student/` prefix and that the visible page has academic-planning
  table rows.
- If permission is denied, restart guided import and grant the Kean host
  permission only when ready.
- If the local app/API fails, start the FastAPI backend locally and confirm the
  API base URL in the popup.
- If rows are missing expected fields, review warnings and confirm whether the
  Kean/Ellucian UI changed labels or layout.
- If data looks wrong, do not apply it. Re-open the official portal and verify
  manually before Phase 7B confirmation.

## Updating Selectors Safely

When Kean/Ellucian changes the UI:

1. Add or update fake HTML fixtures in `apps/extension/tests/fixtures`.
2. Add a failing extractor or policy test for the new visible academic field.
3. Update `apps/extension/src/shared/kean.ts` page definitions or allowed field
   aliases.
4. Do not add real student data, real credentials, hidden form values, or
   official-route claims unless reviewed source documentation is available.
5. Re-run extension policy tests to confirm no broad host permissions, no
   polling, no form submission, and no enrollment-action automation were added.
