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
submit authentication, enrollment, or data-modifying portal forms. The
user-started Catalog batch uses only the reviewed visible GET search and page
controls described below.

Before each subject search, the worker installs a revisioned landing-page
watchdog and waits in the page's main JavaScript world until Kean's Knockout
bindings for the Catalog radio and Search button are present and stable. The
same main-world execution sends the exact preparation checkpoint to the
preinstalled isolated-world watcher. Search is clicked only after the worker
has persisted that batch/revision/subject checkpoint and acknowledged it, then
the current controls are reacquired and revalidated. A missing acknowledgment
fails closed without clicking. A click that does not leave the landing page
pauses with a specific bounded navigation-timeout error; it cannot remain
silently `RUNNING`.

The navigation-timeout evidence contains only sanitized booleans and counts:
selected-subject agreement, Catalog Listing and Search availability,
preparation-signal receipt, result surface/list presence, course-card and valid
identity counts, and Section Listing presence. Raw page HTML, portal text,
authentication state, and user identifiers are not copied. The reviewed result
still requires ordinary navigation to the exact `SearchResult` route; a
landing-page DOM mutation is not treated as a result page.

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

## Read-only Full Course Catalog Mode

Mode C replaces repeated per-subject manual captures with one explicit user
action. The student opens the visible Course Catalog landing page and clicks
`Capture full Course Catalog`. Before starting, the popup states that the run is
read-only, non-official, performs no registration actions, and may take several
minutes. Pause, Resume, and Cancel remain visible while progress is active.
Version 0.1.6 keeps that Full action disabled even after the two-subject
acceptance completes; enabling 116 subjects requires a separate explicit build
authorization.

The controlled real-page review established this mechanism without guessing:

- the landing page exposes `#subject-0` with 116 non-placeholder subject
  options at the time of review;
- the reviewed search form uses GET and exposes `CatalogListing` plus the
  visible `#submit-search-form` control;
- results are visible course cards under `#course-resultul`;
- the sampled ACCT result exposed 30 cards per page and four explicit pages;
- pagination exposes a visible current-page input and buttons labelled
  `Link to results page N`;
- the reviewed result used ordinary page navigation at `SearchResult`; no
  infinite scrolling or guessed XHR/API contract is required.

The extension reads the public subject options, runs one normal Catalog search
at a time, and follows only the explicit next-page button. It waits for the
requested active page, a non-empty course-card identity set, no result-level
loading surface, and a bounded stable-DOM window instead of sleeping for a
fixed interval. Limits are fixed at one concurrent action, 200 subjects, 50
pages per subject, 2,500 total pages, 25,000 unique records, and 45 minutes. A
school rate-limit/error signal, unexpected page structure, truncated snapshot,
malformed required field, conflicting duplicate, timeout, or limit breach
stops the run fail-closed.

Progress is persisted after each accepted page. An Extension worker restart
changes a running batch to `PAUSED`; it never resumes secretly. Resume restarts
the current subject from its landing page and verifies every already accepted
page against its saved deterministic visible-field fingerprint before ignoring
the page key. A page is accepted only when its visible card count exactly
matches the extracted record count and its order-independent full course-marker
set differs from the prior page after pagination. Cancel stops before the next
bounded action. No alarm, periodic school refresh, or automatic future Catalog
refresh is scheduled.

Every new run persists a fresh run ID, runner/acceptance revision, Extension
version, creation time, and released/active lease state immediately. A
`PAUSED` or `FAILED` checkpoint from an older or unversioned runner is summarized
as `SUPERSEDED_BY_NEW_REVISION`, appended to extension-local audit history, and
releases active-run ownership without deleting local imports, reviews,
provenance, or Courses. Any same-revision pause, including a zero-progress
worker-recovery pause, keeps Start disabled and requires explicit Resume or
Cancel. Completed audit summaries are immutable and are never evicted by the
bounded transient-history limit.

Full Catalog capture stays locked until the current Extension build completes
its two-subject bounded acceptance. The pass is tied to the current durable
runner revision, so an acceptance saved by an older runner or pagination
contract does not unlock a changed full run.

The sanitized persisted state also records the expected navigation revision,
the latest authorized-tab revision/status, the content-ready revision, and the
installed timeout revision. The persistent Side Panel (or extension-owned tab
fallback) renders those checkpoints, safe page-ready diagnostics, local
post-processing phases/counts, button availability reasons, and archived
`SUPERSEDED` evidence without depending on the popup or school DOM. Stale
timeout messages cannot stop a newer subject navigation, and a timeout is
accepted only while the authorized tab still has the exact reviewed landing
URL.

Between subjects, changing the visible subject can cause Knockout to replace
the selector or search controls. The Extension therefore reacquires the live
controls after input/change, waits for the exact subject value and current
binding contexts to stabilize, and only then clicks the current Catalog
Listing radio and Search button. It ignores late landing completion events from
an older checkpoint and rejects a SearchResult whose visible course markers do
not all match the expected subject. This is a condition-based bounded wait, not
a fixed sleep.

SearchResult readiness is not inferred from `tabs.onUpdated=complete`. It
requires the expected subject, a non-empty `#course-resultul`, stable full-page
fingerprint, inactive blocking spinner, current navigation revision, and a
bounded stable interval. Kean may omit the current-page input on page 1. That
case is accepted only when there is no prior-page marker, all explicit page
targets point after page 1 (or the result is single-page), no conflicting
`aria-current` exists, and the subject/cards/fingerprint gates all agree. A
missing page-number input on later pages remains fail-closed.

Each safely completed subject is sent only to the paired loopback app. The
local API prepares deterministic review decisions for exact visible Course
identity, title, and positive credits, runs dry-run, applies only if every
result is safe, and returns updated MyProgress exact-Course mapping counts.
The persisted monitor phases are `CAPTURE_RUNNING`, `CAPTURE_COMPLETED`,
`LOCAL_STAGING`, `LOCAL_VALIDATION`, `LOCAL_REVIEW`, `LOCAL_DRY_RUN`,
`LOCAL_APPLY`, `MYPROGRESS_REMAP`, and `COMPLETED`; every completed local gate
and count must be present in the API response before the Extension advances the
subject.
Natural-language requisite text remains raw `REVIEW_REQUIRED` evidence.
Missing optional department, level, description, or rule fields remain
`NOT_PROVIDED`; no ProgramVersion or catalog-year binding is invented.

Course identity is institution plus normalized course code. Page overlap and
cross-search duplicates are ignored only when their visible field fingerprint
agrees; conflicting duplicates stop the batch. Every retained row includes the
safe result path, subject, page number, capture timestamp, raw visible title,
normalized code, and non-official source label.

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

Manual and guided imports must show a preview before import. The preview includes detected
page type, row counts by import type, warnings, non-official/manual-review
labels, and sample extracted rows. No silent import is allowed.

Confirmation must submit the same extraction that was previewed. For
MyProgress, the submit payload includes the page type, source type, warnings,
bounded/truncated flags, diagnostics, visible-row and academic-field counts,
course rows, and row provenance. If preview rows existed but the prepared
payload has no MyProgress rows, the extension blocks submission and asks the
student to re-extract the page.

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

`ATTEMPTED` is deliberately not treated as `COMPLETED`. The import preserves
`source_status = ATTEMPTED`, normalizes the planning status to `UNKNOWN`, emits
`ATTEMPTED_STATUS_REQUIRES_REVIEW`, and excludes the row from reliable course
history until separate reviewed passing evidence exists. `REGISTERED` remains
an in-progress state and `FULLY_PLANNED` remains planned.

## Local App Handoff

After confirmation, the extension sends academic staging data to:

```text
POST /api/v1/data-imports
```

This endpoint is reached only through the paired Extension worker at the
explicit local app loopback root. The popup has no bearer-token input and no
direct LAN, cloud, school-origin, or other non-local academic-data handoff.

Payloads are marked:

```text
source_type = BROWSER_EXTENSION
source_label = KEAN_STUDENT_PORTAL in preview metadata
is_official = false
official_application_ready = false
```

The source label is carried through safe source-reference text and backend
preview metadata; no new database table or migration is required.

The local app lists saved staging imports with timestamp, source type,
validation status, row counts, and confidence. When a newer MyProgress import is
broken or empty, the app should keep the latest usable MyProgress import visible
by default and let the student select the newer import explicitly for review.

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
- submits authentication, enrollment, or data-modifying portal forms;
- registers, drops, swaps, waitlists, reserves seats, or grabs seats;
- runs secret or unbounded background scraping or periodic polling;
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
