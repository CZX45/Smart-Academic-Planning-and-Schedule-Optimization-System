# Architecture Decision Log

## ADR-0019: Package the LOCAL_DESKTOP FastAPI runtime as a PyInstaller one-folder artifact

Status: Accepted for Stage 6

Context: The Windows Local Desktop shell must start the FastAPI runtime without
requiring an end user's separately installed Python environment. The existing
runtime already provides dynamic loopback discovery, a versioned manifest,
SQLite bootstrap, readiness, and bounded supervision.

Decision: Use a PyInstaller one-folder Windows artifact that retains the
existing `app.run` entrypoint. The Tauri shell accepts the explicit
`SAPSOS_API_EXECUTABLE` override for packaged proof and fails clearly when that
artifact is missing. The development proof keeps its existing Python command
when the override is absent.

Alternatives considered: Nuitka was not selected because it is not installed
or established in this repository and would add a larger compilation and
troubleshooting surface for this proof. PyInstaller one-file was rejected
because extraction-time resource handling, startup, crash diagnostics, and
antivirus/SmartScreen behavior are less diagnosable. No evidence justified
changing FastAPI, Uvicorn, SQLite bootstrap, or the SERVER/PostgreSQL path.

Consequences: The packaged directory is larger than a one-file executable and
still requires developer-only Python/PyInstaller build tools, but end users
need only the produced artifact. Runtime resources, logs, and failure details
remain inspectable. Installer, signing, updater, Web UI packaging, and Node.js
removal remain later work.

## ADR-0020: Package the LOCAL_DESKTOP Web UI as static Tauri assets

Status: Accepted for Stage 7

Context: The Stage 5 Tauri proof started a Next.js development server, which
requires Node.js and pnpm at runtime. Stage 7 must remove that runtime
requirement while preserving the dynamically discovered FastAPI loopback URL.

Decision: Use Next.js `output: "export"` and copy the resulting static output
to `dist/local-desktop-web`. Release Tauri builds load those assets directly.
After the packaged API reaches readiness, Tauri passes its manifest `base_url`
as the `api_base_url` query parameter on the app document URL. The Web UI
validates and consumes that value after hydration. Debug builds retain the
existing development-server path for developer workflows, but release builds
compile out the Node/Next launch.

Alternatives considered: A packaged Node production server was rejected because
the current Web UI has no route handlers, middleware, server actions, dynamic
routes, or server-only data access; static export is sufficient and smaller.
Build-time `NEXT_PUBLIC_API_BASE_URL` injection was rejected because the API
port is allocated dynamically at runtime. A Tauri JavaScript IPC dependency was
not added because the document query bridge is explicit, testable, survives
reload, and keeps the Stage 7 change narrow.

Consequences: The static UI is approximately 1.08 MiB in the controlled build
and requires developer Node.js/Corepack only to build. Tauri release startup
depends on the packaged API readiness contract and fails clearly when the Web
artifact is missing. Installer, signing, updater, and a clean Windows VM proof
remain outside this stage; the available no-Node/no-Python evidence must be
reported as a controlled simulation unless a clean image is available.

## ADR-0001: Use a documentation-first implementation phase

Status: Accepted

Context: The repository started empty, while the requested product has high domain complexity and high academic-risk consequences.

Decision: Create product, architecture, data model, rule, security, roadmap, and test strategy documents before implementing application code.

Consequences:

- Shared understanding is established before code.
- MVP boundaries and non-goals are explicit.
- Later implementation can be tested against documented expectations.

## ADR-0002: Use a monorepo with pnpm workspace / Turborepo

Status: Proposed

Context: The product needs a Next.js web app, FastAPI backend, Chrome extension, shared TypeScript types, fixtures, and infrastructure configuration.

Decision: Use a monorepo so contracts, fixtures, documentation, and app code evolve together.

Consequences:

- Easier local development and cross-package testing.
- Requires clear task orchestration between Node and Python tooling.

## ADR-0003: Separate Course and Section entities

Status: Accepted

Context: Degree requirements and prerequisites apply primarily to courses, while schedules and instructors apply to sections.

Decision: Model `Course` and `Section` separately.

Consequences:

- Academic planning can happen without exact section data.
- Semester scheduling can select concrete sections after course planning.

## ADR-0004: Model degree requirements as rule trees

Status: Accepted

Context: Degree requirements include nested GE, major, elective, credit, GPA, upper-level, residency, and overlap policies.

Decision: Use versioned requirement rule trees rather than fixed arrays of courses.

Consequences:

- Supports multiple schools and catalog years.
- Requires a robust evaluator and golden fixtures.

## ADR-0005: Model prerequisites and restrictions as expression trees

Status: Accepted

Context: Eligibility rules can combine completed courses, minimum grades, standing, campus, major, permission, and corequisites.

Decision: Use composable logical expression trees for prerequisites, corequisites, and restrictions.

Consequences:

- Complex rules are expressible and testable.
- Unknown or manual-review outcomes can be represented explicitly.

## ADR-0006: Separate Academic Plan Optimizer and Semester Schedule Optimizer

Status: Accepted

Context: Long-range graduation planning and single-term section scheduling solve different problems at different levels of detail.

Decision: Keep course-level academic planning separate from section-level schedule optimization.

Consequences:

- Cleaner domain boundaries.
- Easier testing and explanation.
- Enables future scaling of optimizers independently.

## ADR-0007: Never store school credentials or automate registration in MVP

Status: Accepted

Context: Credential handling and registration automation create major privacy, legal, and operational risk.

Decision: Do not store school credentials, bypass authentication, or automate registration/drop actions. Browser extension reads only active user-opened pages after explicit user action.

Consequences:

- Lower security and compliance risk.
- Users remain responsible for official registration in school systems.

## ADR-0008: Use mock fixtures until official data is provided

Status: Accepted

Context: Verified Kean/WKU catalog, My Progress, and section data may not be available during early development.

Decision: Continue development using clearly labeled mock data and fixtures. Do not claim mock data is official.

Consequences:

- Core algorithms can be built and tested immediately.
- Accuracy validation remains a separate official-data onboarding task.

## ADR-0009: Implement Phase 2A as relational academic-domain storage

Status: Accepted

Context: Degree Audit, eligibility, academic planning, and schedule optimization need shared academic identities and source metadata before evaluators are introduced.

Decision: Implement Phase 2A as normalized SQLAlchemy/PostgreSQL storage for institutions, campuses, terms, academic programs, program versions, courses, course equivalencies, requirement nodes, requirement course options, student profiles, academic program declarations, course attempts, transfer credits, waivers, and substitutions. Requirement trees use relational adjacency lists rather than a single JSON blob.

Consequences:

- Future evaluators can share deterministic, versioned, source-tagged records.
- Course planning remains separate from section scheduling because Phase 2A models courses only.
- Pending or rejected exceptions can be stored without being applied before Degree Audit rules exist.
- Mock seed data can demonstrate the shape of catalog and student records without claiming official school policy.

## ADR-0010: Implement Phase 2B course rules and sections as relational storage

Status: Accepted

Context: Course Eligibility, Degree Audit, Academic Planning, and Semester Scheduling need shared storage for prerequisites, corequisites, restrictions, offering assumptions, concrete sections, and meeting times before those later engines evaluate anything.

Decision: Add relational tables for `CourseOfferingPattern`, `Section`, `SectionMeeting`, `CourseRule`, and `CourseRuleExpression`. Keep `Course` and `Section` separate. Store prerequisites, corequisites, restrictions, and permissions as expression trees rather than unqueryable text or a single JSON blob. Course-level rules are scoped to a course; section-level rules are constrained to the same course and institution as their section.

Consequences:

- Later eligibility and planning engines can query structured rule operands and source metadata.
- Section scheduling can use concrete section and meeting records without polluting course-level planning.
- Offering patterns remain advisory metadata and must not be presented as official school commitments.
- Phase 2B still does not evaluate student eligibility, run Degree Audit, optimize schedules, monitor seats, or automate registration.

## ADR-0011: Implement Phase 3A degree audit as persisted snapshots

Status: Accepted

Context: Degree progress results must be explainable, testable, and stable for advisor review. The same source data may later be audited under different assumptions, so the system needs traceable outputs rather than transient UI-only calculations.

Decision: Implement Degree Audit Core as a synchronous backend application service that evaluates one `StudentProfile` against one `ProgramVersion` and persists a `DegreeAuditRun` snapshot. Store one `RequirementEvaluation` per requirement node, explicit `AuditCourseApplication` rows for attempts/transfers/waivers/substitutions, and `DegreeAuditWarning` rows for advisor confirmation and data-quality issues.

Consequences:

- API responses can return stable snapshot IDs and explainable structured results.
- The frontend can render degree progress without reimplementing academic rules.
- `CURRENT` and `PROJECTED` modes can show completed, in-progress, and planned layers without confusing them.
- Phase 3A intentionally uses a deterministic baseline allocator rather than a global optimization solver.
- Phase 3B should address what-if scenarios and advanced allocation before eligibility or section scheduling work begins.

## ADR-0012: Implement Phase 3B scenarios as snapshot wrappers around Degree Audit

Status: Accepted

Context: What-if analysis must compare minors, second majors, certificates, concentrations, and change-major candidates without changing official student declarations or duplicating Degree Audit behavior.

Decision: Persist `AcademicPlanScenario` snapshots with `ScenarioProgram` rows and call the Phase 3A `DegreeAuditEngine` once per scenario program. Store each program result as a normal `DegreeAuditRun`, then run a separate deterministic bounded global allocator over the persisted audit applications. Store directional `ProgramCombinationRule` records for overlap policy; missing rules create advisor-review warnings rather than inferred policy.

Consequences:

- Scenario runs are traceable to the same audit snapshot structure as official program audits.
- What-if scenarios cannot silently mutate `StudentAcademicProgram`.
- Shared credit, unique secondary credit, and total earned credit remain separate concepts.
- The allocator can be replaced later without rewriting Degree Audit.
- Phase 3B estimates additional credits but does not predict graduation timing or evaluate eligibility.

## ADR-0013: Implement Phase 4 course eligibility as expression snapshot evaluation

Status: Accepted

Context: Stored course-rule expression trees must become explainable student/course eligibility decisions without duplicating frontend logic or crossing into schedule optimization or registration automation.

Decision: Implement Course Eligibility as a synchronous backend application service that evaluates one `StudentProfile` against one `Course`, optional `Section`, target term, and explicit eligibility mode. Persist an `EligibilityCheckRun` snapshot with `RuleEvaluation`, `RuleExpressionEvaluation`, and `EligibilityWarning` rows. Reuse the centralized grade policy and existing course-attempt/transfer status semantics. Return section availability as a separate snapshot field rather than folding seats into academic eligibility.

Consequences:

- Eligibility checks are auditable, repeatable, and tied to stored rules and expression evidence.
- The frontend can render eligibility results without reimplementing prerequisite/corequisite logic.
- `CURRENT`, `PROJECTED`, and `REGISTRATION` modes keep completed, in-progress, planned, and concurrent corequisite evidence distinct.
- Phase 4 can explain permissions, hard failures, conditional outcomes, and manual-review outcomes without building long-term plans or schedules.
- Phase 4 does not predict graduation timing, optimize schedules, call OR-Tools, monitor seats, or automate registration.

## ADR-0014: Implement Phase 5A academic planner as persisted course-level snapshots

Status: Accepted

Context: The system needs a long-term planner that can turn Degree Audit gaps and Course Eligibility evidence into explainable future course plans, but section scheduling, OR-Tools optimization, seat monitoring, and registration automation remain separate later boundaries.

Decision: Implement Phase 5A as a synchronous backend application service that creates one `AcademicPlanRun` snapshot with child term, planned-course, requirement-coverage, and warning rows. Reuse Degree Audit to identify remaining requirements and Course Eligibility to reason about prerequisite/corequisite status. Support `CURRENT_PROGRAM` and `WHAT_IF_SCENARIO` modes. Store structured source, status, reason code, and explanation fields for each course placement. Treat offering patterns and section snapshots as assumptions that can warn, not as official commitments.

Consequences:

- Plan results are repeatable, auditable snapshots rather than mutable student records.
- What-if plans can reference scenario snapshots without changing official declarations.
- The frontend can render term-by-term plans without reimplementing planner logic.
- Planner warnings preserve uncertainty for mock data, broad requirements, credit limits, horizon limits, and offering assumptions.
- Phase 5A remains course-level and deliberately does not select sections, check weekly meeting conflicts, monitor seats, or perform registration actions.

## ADR-0015: Implement Phase 6A semester scheduler as persisted bounded snapshots

Status: Accepted

Context: The system needs a section-level schedule optimizer that can rank concrete semester schedules, but live registration, seat monitoring, browser automation, and a full OR-Tools solver remain outside the current safety and complexity boundary.

Decision: Implement Phase 6A as a synchronous backend application service that creates one `ScheduleOptimizationRun` snapshot with child constraint-set, option, selected-section, conflict, and warning rows. Reuse Course Eligibility in `REGISTRATION` mode, but keep section availability informational and never mutate sections, seats, waitlists, student records, or registration data. Support `FROM_DEGREE_AUDIT`, `FROM_LONG_TERM_PLAN`, and `CUSTOM_COURSE_SET` modes. Use a deterministic bounded search and stable tie-breakers rather than OR-Tools in this foundation phase.

Consequences:

- Schedule results are repeatable, auditable snapshots rather than live registration state.
- The frontend can render ranked section options, conflicts, and warnings without reimplementing schedule logic.
- Hard constraints and preference scoring are explainable and testable.
- Search limits are explicit and warn rather than pretending to be exhaustive.
- Phase 6A remains read-only and deliberately does not poll seats, join waitlists, add, drop, swap, register, scrape portals, or bypass school authentication.

## ADR-0016: Extend Phase 6B scheduler with explainable scoring, diversity, and repair suggestions

Status: Accepted

Context: The Phase 6A scheduler can generate bounded section schedules, but students need more control over preferences, advisors need auditable score components, and infeasible runs need structured relaxation guidance. A full OR-Tools solver and live registration integrations remain outside the safety boundary.

Decision: Implement Phase 6B as an extension of the persisted schedule snapshot model. Add advanced constraint inputs for preference weights, course and section priorities, no-gap, morning, afternoon, diversity mode, partial-option behavior, and search bounds. Persist score components and score explanations on each option, store deterministic diversity metadata, and create `ScheduleRepairSuggestion` rows for infeasible or partial schedules. Keep the implementation behind a `ScheduleOptimizer` protocol and use a deterministic bounded-search implementation for this phase.

Consequences:

- API, shared TypeScript schemas, and the web app can render scoring and repair details without duplicating optimizer logic.
- Advanced preferences remain transparent soft inputs rather than hidden frontend ranking.
- High-diversity mode can provide meaningfully different options while preserving deterministic ordering.
- Repair suggestions are explanatory only and do not automate registration, add/drop, swaps, waitlists, seat monitoring, portal scraping, or authentication bypass.
- OR-Tools, richer minimal-relaxation search, instructor preferences, commute optimization, and live official section imports remain future work.

## ADR-0017: Implement Phase 7A imports as read-only staging previews

Status: Accepted

Context: Students may have mock or self-provided transcript, degree-audit, catalog, or section-schedule data before an official reviewed import workflow exists. Applying that data directly to transcript, catalog, requirement, section, seat, waitlist, or registration tables would blur source authority and could create high-impact academic errors.

Decision: Implement Phase 7A as a separate read-only data import staging boundary. Persist `DataImportRun`, `DataImportFile`, `ImportedRecord`, `ImportMappingCandidate`, `ImportValidationWarning`, and `ImportPreviewSummary` rows. Parse bounded CSV/JSON content, normalize generic course-code fields, propose mapping candidates, and emit warnings and preview disclaimers. Keep `official_application_ready = false`, reject official-source imports, and do not mutate academic-domain or registration tables.

Consequences:

- Users and advisors can inspect imported mock/student-provided data without confusing it with official school policy.
- API, shared TypeScript schemas, and the web app can render records, mapping candidates, warnings, and previews without duplicating parser logic.
- Future reviewed import/application workflows can build on a traceable staging model.
- Phase 7A deliberately does not implement browser extension import, real school login, SAML/MFA/CAPTCHA handling, scraping, OCR-heavy extraction, advisor approval queues, official data application, seat monitoring, waitlist handling, add/drop/swap, or automatic registration.

## ADR-0018: Require explicit review before applying imported data

Status: Accepted

Context: Phase 7A staging data can be mock, student-provided, ambiguous, unsupported, or unmatched. Automatically applying those records would create planning state that appears more authoritative than its source. At the same time, students need a controlled way to turn reviewed unofficial transcript rows into internal planning records for estimates.

Decision: Implement Phase 7B as an expl…51 tokens truncated…s and apply only through `POST /data-import-reviews/{review_id}/apply`; GET endpoints remain read-only. Support dry-run with no domain writes. Limit real application to confirmed unofficial transcript course attempts that map to a known course and term, create non-official internal `StudentCourseAttempt` records with source metadata, and audit every applied or skipped record with action, status, reason code, and message.

Consequences:

- Imported records remain distinguishable from official school data even after review.
- Duplicate prevention and application logs make re-apply behavior explainable.
- Unsupported catalog, section, requirement, unknown-course, rejected, deferred, advisor-review, and unsupported-grade records are skipped rather than silently applied.
- Phase 7B deliberately does not implement browser extension import, real school login, scraping, OCR-heavy extraction, official data ingestion, seat monitoring, waitlist handling, add/drop/swap, or automatic registration.

## ADR-0019: Implement browser extension imports as user-triggered staging handoff

Status: Accepted

Context: Students may need to import visible academic data from pages they have already opened, but browser automation can easily cross privacy, credential, and registration safety boundaries. The existing Phase 7A/7B import workflow already provides staging, warnings, preview, review decisions, dry-run, duplicate checks, and explicit application logs.

Decision: Implement Phase 8A as a read-only Manifest V3 browser extension foundation in `apps/extension`. Use minimal permissions (`activeTab`, `scripting`, and `storage`) and no broad host permissions. Extract visible transcript, degree-audit, catalog, and section-search tables only after user action, show a preview, and send data only after confirmation. Reuse `POST /api/v1/data-imports` with `source_type = BROWSER_EXTENSION`, `is_official = false`, and `official_application_ready = false`. Keep Phase 7B review required before any application.

Consequences:

- Extension imports reuse the existing staging and review safety model instead of creating a parallel ingestion path.
- Source metadata distinguishes browser-extension visible-page extracts from uploads, mock fixtures, inferred data, official data, and reviewed application logs.
- The extension does not store credentials, read password fields, bypass school authentication, scrape in the background, submit portal forms, publish production browser-store builds, poll seats, join waitlists, add, drop, swap, register, or grab seats.
- Read-only section-change alerts may be considered later, but they must remain advisory and unable to perform registration or seat-state automation.

## ADR-0020: Implement section monitoring as advisory snapshot comparison

Status: Accepted

Context: Students can benefit from noticing changes in section-search data they manually import, but live seat monitoring, portal polling, waitlist automation, and registration actions create accuracy, privacy, and operational risk.

Decision: Implement Phase 8B section monitoring as a read-only advisory boundary. Persist student-scoped monitor targets, non-official imported snapshots, and manual-review alerts. Compare only user-triggered browser-extension snapshots, deduplicate identical snapshots by hash, and expose alerts through `/api/v1/section-monitoring`. Render advisory UI messaging and a manual registration checklist. Do not schedule background polling, refresh portals, alter seat or waitlist state, submit forms, or mutate canonical section, seat, waitlist, student, plan, schedule, or registration state.

Consequences:

- Students can review status, seat, waitlist, meeting-time, instructor, and location changes without mistaking them for official portal status.
- API, shared schemas, extension extraction, and web UI have an explicit non-official monitoring contract.
- Future notification work must remain user-controlled and advisory unless a new reviewed architecture decision changes the boundary.
- Registration automation, waitlist handling, seat-state automation, portal scraping, credential storage, and authentication bypass remain out of scope.

## ADR-0021: Harden product dashboard clarity without expanding automation scope

Status: Accepted

Context: After Phase 8B, the product surface spans degree audit, data import, browser-extension import, section monitoring, schedule optimization, and what-if planning. Users need clearer status, empty-state, and advisory labeling so non-official imported data and manual next steps are hard to miss.

Decision: Implement Phase 9A as product hardening only. Add dashboard status cards, reusable UI helper copy, advisory labels, before/after formatting, timestamp formatting, empty states, manual checklist polish, and safety-text tests. Keep the existing APIs and workflows intact, and do not introduce new backend domains, registration automation, portal submission, polling, background scraping, credential capture, waitlist automation, or seat-state changes.

Consequences:

- Students and reviewers can quickly distinguish not-started, loading, empty, warning, and ready states.
- Browser-extension imports, data import previews, reviewed imported data, section monitoring snapshots, and alerts consistently show non-official/advisory/manual-review labels.
- UX tests now guard against misleading registration, seat guarantee, and official-availability claims.
- Any future automation or official-source workflow still requires a separate architecture decision.

## ADR-0022: Harden security and production readiness without expanding workflow authority

Status: Accepted

Context: After Phase 9A, the system has enough user-facing academic planning, import, review, schedule, and advisory monitoring surface that accidental misconfiguration or unsafe wording could create privacy and operational risk before any real deployment.

Decision: Implement Phase 9B as hardening-only work. Add API environment validation for PostgreSQL URL, app environment, timeout, and CORS origins; validate the web public API base URL; add safe API response headers and explicit CORS request headers; add low-sensitivity structured audit logs for data-import creation and advisory section-monitoring comparisons; document privacy, retention, safe logging, and production readiness; and add safety regression tests. Do not add new product domains, official source ingestion, account/auth systems, telemetry, production deployment, registration automation, portal submission, polling, waitlist automation, seat-state changes, or credential handling.

Consequences:

- Production-like misconfiguration fails early with clearer errors.
- API responses gain safe default browser-facing headers without relying on reverse-proxy-only behavior.
- Auditability improves while raw imported academic content, HTML, credentials, tokens, and secrets stay out of logs.
- The browser extension and section monitoring boundaries remain user-triggered, non-official, read-only, and advisory.
- Real data onboarding, advisor workflow expansion, deletion/export controls, external telemetry, and production deployment remain future work requiring separate review.

## ADR-0023: Treat Phase 10A as release-readiness QA and final product review

Status: Accepted

Context: After Phase 9B, the product has mock degree audit, what-if, planner, schedule optimization, data import, browser-extension import, section monitoring, dashboard, and security-hardening surfaces. Before final review or demo, the project needs an explicit QA and handoff layer that explains how to review the existing workflows without implying official data authority or school-system automation.

Decision: Implement Phase 10A as release-readiness QA and final product review only. Add release QA documentation, demo scenarios, a release checklist, final safety-boundary audit, documentation consistency cleanup, and lightweight wording regression tests. Do not add backend domains, official-source ingestion, notification workers, browser-store publishing, account/auth systems, credential handling, external telemetry, production deployment, polling, portal submission, registration automation, add/drop/swap automation, waitlist automation, seat reservation, or seat grabbing.

Consequences:

- Reviewers get a clear path through the main end-to-end user journeys.
- Demo language stays anchored in imported snapshots, advisory alerts, manual review required records, read-only imported data, non-official data, and official-portal verification.
- The release checklist connects local commands, CI validation, no-secrets review, extension permissions, prohibited automation review, docs review, and demo review.
- Safety boundaries remain explicit while future production, official-data, notification, and advisor-access work stay deferred until separately reviewed.

## ADR-0024: Implement Kean Student Portal import as a whitelisted browser-extension workflow

Status: Accepted

Context: The project needs to start addressing the original real-user import
goal, and the target Kean / Ellucian Student Portal prefix is now known. Real
portal imports create privacy and safety risk if implemented as crawling,
credential handling, background scraping, or enrollment automation. The existing
Phase 7A/7B staging and review model already provides the right safety boundary
for non-official imported academic data.

Decision: Implement Phase 11B as a Kean-specific browser-extension workflow
under `https://kean-ss.colleague.elluciancloud.com/Student/*`. Keep baseline
extension permissions to `activeTab`, `scripting`, and `storage`, and request
the optional Kean host permission only when the student starts guided import.
Use configurable page definitions for transcript, degree audit, MyProgress,
course catalog, section search, student planning, and schedule pages. Extract
only visible academic-planning table data after user action, show a preview, and
send confirmed data to `POST /api/v1/data-imports` as
`source_type = BROWSER_EXTENSION`, `is_official = false`, and
`official_application_ready = false`. Label Kean imports as
`KEAN_STUDENT_PORTAL` in safe source-reference and preview metadata. Preserve
Phase 7B review before planning use.

Consequences:

- Kean import support builds on the existing staging/review path instead of
  adding official-source ingestion.
- The extension can support current-page import and guided full import without
  broad crawling or hidden background work.
- Chrome host permissions are host-scoped, so the implementation documents that
  limitation and enforces the narrower `/Student/` prefix in code.
- Fake Kean/Ellucian-style fixtures cover allowed academic data, unsupported
  pages, login pages, hidden fields, unrelated personal/financial columns,
  malformed rows, and action controls.
- The workflow still does not store credentials, read password fields, store
  cookies or session tokens, bypass SAML/MFA/CAPTCHA, submit portal forms,
  automate registration, add/drop/swap courses, join waitlists, reserve seats,
  grab seats, poll portals, or publish a browser-store workflow.

## ADR-0025: Verify Kean MyProgress imports by exception, not by every row

Status: Accepted

Context: MyProgress pages include a top summary and progress bar that are more
authoritative for total-credit progress than summing visible requirement rows,
because the same course can appear in multiple requirement groups. Requiring
students to confirm every imported row defeats the purpose of reducing manual
checking, while blindly trusting low-confidence parser output would create
academic-planning risk.

Decision: For Kean MyProgress browser-extension imports, preserve the top
summary, progress-bar segments, field-level provenance, raw bounded snapshot
evidence, and validation diagnostics in the staging JSON payload. Validate
program, catalog year, GPA, total credits, segment reconciliation, remaining
credits, completion percentage, requirement groups, course-like evidence,
truncation state, and mock/real mixing before any downstream academic use.
Automatically confirm high-confidence fields and staging records when values
reconcile and no conflicts exist. Create manual-review work only for exception
items such as missing critical fields, conflicts, low confidence, unsupported
rows, truncation, duplicate/ambiguous applications, and failed validation.

Consequences:

- MyProgress preview can display `Real Imported Data - Auto Verified`,
  `Pending Review`, `Requires Exception Review`, or `Confirmed` instead of
  silently falling back to mock data.
- Degree progress display may use auto-verified MyProgress summary values for
  visible dashboard metrics, while the data remains non-official and advisory.
- Failed MyProgress validation blocks downstream academic analysis and returns
  structured reason codes.
- The import remains read-only: no registration, add/drop/swap, waitlist,
  seat-reservation, portal form submission, polling, credential handling, or
  official-source mutation is introduced.

## ADR-0026: Materialize reviewed MyProgress rows as advisory course-state snapshots

Status: Accepted

Context: A staging preview can explain extracted MyProgress rows but is not a
stable source for degree audit, eligibility, or planning. Mixing those rows with
seeded mock attempts can create plausible but false academic conclusions.

Decision: Explicit application materializes a versioned, immutable,
non-official course-state snapshot and row-level provenance. One validated
snapshot is active per student. Effective-attempt queries exclude mock history
when an active imported snapshot exists. Each downstream consumer receives an
independent readiness result; planned courses do not satisfy prerequisites, and
section scheduling stays demo-only.

Consequences:

- Reapplication is idempotent and invalid newer imports do not replace a valid
  active snapshot.
- Unmatched and exception rows remain inspectable but cannot silently become
  reliable academic history.
- The UI distinguishes staging, active imported state, and demo data, and shows
  structured blocking reasons.
- The feature remains advisory and does not expand browser or registration
  authority.

## ADR-0027: Use hashed bearer tokens and explicit student grants for production auth foundation

Status: Accepted

Context: The API has accumulated student-owned generated objects: degree
audits, eligibility checks, academic plans, schedule optimizations, staging
imports, review sessions, applications, course-state snapshots, monitoring
targets/alerts, and what-if scenarios. The next production step needs
authentication and object-level authorization without introducing school
password collection or an external identity-provider dependency before the
deployment model is finalized.

Decision: Add an application-auth foundation with tenants, users, hashed bearer
API tokens, and explicit student-profile access grants, while separating local
and server runtime behavior with `PRODUCT_MODE`. `LOCAL_DESKTOP` is the default
and uses an explicitly named `LocalRuntimeContext`; it does not use a public
development bypass or query authorization tables. `SERVER` requires
`AUTH_MODE=bearer`. A centralized FastAPI router dependency resolves
path/query/body object identifiers back to `student_profile_id` before route
handlers execute. Access is allowed only for explicit grants, tenant admins
within their tenant institution scope, or system admins. Health/readiness probes
remain outside `/api/v1`.

Consequences:

- The backend stores no school credentials, portal cookies, SAML tokens, MFA
  secrets, or plaintext API tokens.
- Student-owned object APIs are protected consistently without duplicating
  checks across every handler.
- Token issuance and external SSO/OIDC login remain future production work; the
  current foundation is intentionally narrow and reviewable.
- Browser-extension staging imports are local-app-only. The popup has no bearer
  token entry and the worker rejects non-loopback destinations before network
  access. SERVER bearer authentication remains an API-client boundary, not a
  school-page Extension handoff.
- `ENVIRONMENT` is independent from `PRODUCT_MODE`; production local-desktop
  mode remains a valid loopback local runtime.
- Local desktop API binding is loopback-only and Docker publishes its API port
  on loopback by default.

## ADR-0012: Stage 10A source-backed Program/Catalog review boundary

Existing ProgramVersion, RequirementNode, CourseRule, Degree Audit, and
Eligibility models describe academic rules, but imported or mock content must
not silently become authoritative policy. Stage 10A therefore introduces a
typed, source-aware staged rule-set contract with exact institution/program/
catalog-year identity, explicit lifecycle transitions, bounded deterministic
operators, and visible unsupported statements. Validation does not persist or
consume the payload; Stage 10B must separately add reviewed/active persistence
and consumption. Until reviewed source material is provided, the product must
not claim complete institutional coverage.

## ADR-0013: Stage 10B reviewed-rule consumption boundary

Degree Audit and Eligibility may consume only an exact active reviewed rule
set matched by institution code, program code, and catalog year. The selected
rule-set ID and source provenance are persisted with each run. A missing
reviewed course definition is `UNKNOWN`, not `ELIGIBLE`; an absent active set
is marked `MISSING` and retains the legacy path for compatibility. This keeps
synthetic fixtures and incomplete source coverage advisory until a reviewer
confirms authoritative source evidence.

# ADR-0023: Keep LOCAL_DESKTOP schema migration separate from Alembic

LOCAL_DESKTOP uses a file-backed SQLite database and now has a dedicated,
explicit migration registry. Each local migration declares its source and
target integer versions, and the runner builds a contiguous plan without
inferring order from filenames. The runner records attempts in a SQLite
journal, enables and validates foreign keys, runs `foreign_key_check` and
`integrity_check`, and fails closed for unknown, newer, failed, or interrupted
states. A schema version is advanced only after the planned work and
validation complete.

This foundation intentionally does not change the production schema version,
perform Tauri startup orchestration, implement rollback replacement, or
change PostgreSQL/Alembic behavior. Destructive migrations require a validated
safety-backup reference for the active database. The journal stores only safe
metadata and sanitized error text; it never stores credentials, cookies,
tokens, MFA data, pairing secrets, or academic data contents.

# ADR-0024: Orchestrate LOCAL_DESKTOP migrations before startup

Status: Accepted

LOCAL_DESKTOP schema upgrades are orchestrated by the Tauri shell before the
FastAPI child is started. The shell calls a versioned, JSON-only Python
preflight/execute contract; Python remains the owner of the migration registry,
plan calculation, journal semantics, SQLite integrity checks, and safety
snapshot creation. The shell owns startup ordering, the single-instance lock,
attempt marker, API/runtime-manifest/readiness gate, and rollback replacement.

Pending restore is processed before migration and never concurrently with it.
`CURRENT` databases do not create a migration safety snapshot. An upgrade must
have a validated snapshot bound to its attempt before execution. Migration
success is not startup success until the normal API reaches readiness and its
manifest identifies the expected child. Any later failure stops the child,
preserves failed-database evidence, restores the attempt-bound snapshot, and
leaves a non-replayable rollback marker. Interrupted or malformed markers fail
closed; the shell never retries migration in the same startup.

The contract accepts no database path argument. The active database is derived
from trusted LOCAL_DESKTOP runtime configuration, and all subprocess output is
machine-readable JSON on stdout with sanitized diagnostics only.

# ADR-0025: Keep LOCAL_DESKTOP diagnostics read-only and local

Status: Accepted

The first Diagnostics phase provides a versioned, typed read-only snapshot at
`GET /api/v1/local-diagnostics`. The coordinator aggregates isolated collectors
for runtime manifest, API/readiness, SQLite database, local migration journal,
restore state, extension pairing, and bounded startup-event summaries. A
collector failure produces an explicit unknown/error component state rather
than turning the whole snapshot into an unstructured server error.

Diagnostics is available only in `LOCAL_DESKTOP` mode, keeps the existing
Host/Origin/localhost-proof boundary, and never starts or restarts processes,
creates backups, executes migration or restore operations, changes markers or
journals, or accepts caller-controlled paths. `SERVER` does not expose local
SQLite, runtime-manifest, or pairing state.

The response contains no student records, academic rows, credentials, cookies,
tokens, pairing secrets, request proofs, absolute paths, raw SQL, or raw
tracebacks. Structured reason codes and allowlisted metadata are preferred;
legacy free text is fail-closed redacted. The snapshot contract deliberately
does not include telemetry, remote upload, diagnostics ZIP export, or a full
Diagnostics UI; those concerns require separate decisions and milestones.

# ADR-0028: Keep Diagnostics UI and export privacy-safe and user-initiated

Status: Accepted

The Diagnostics UI is a read-only, hash-routed workflow in the modular Web UI.
It reads the typed sanitized snapshot, exposes explicit refresh, and renders
`HEALTHY`, `DEGRADED`, `ACTION_REQUIRED`, `BLOCKED`, and `UNKNOWN` states with
user-readable explanations. It does not poll in the background, repair issues,
restart the API, reset pairing, run migrations, restore backups, or mutate
official school records.

Diagnostics export is available only in `LOCAL_DESKTOP` mode and only after an
explicit user action. The ZIP contains exactly `manifest.json`,
`diagnostics.json`, `startup-events.json`, and `README.txt`. The manifest
records the bundle format, generation time, application version/mode,
diagnostics contract version, allowlisted file list, per-file SHA-256 values,
privacy statement, exclusions, and redaction-policy version. The snapshot and
startup events are sanitized and bounded; the README states local generation,
no automatic upload, user review before sharing, non-official-record status,
and deletion guidance.

The bundle excludes student records, GPA, grades, course history, plans,
Sections, portal contents, raw import evidence, databases, backup archives,
raw logs, credentials, MFA data, cookies, SAML data, tokens, pairing secrets,
localhost proofs, absolute paths, Windows usernames, raw tracebacks, stderr,
stdout, SQL, and command lines. There is no telemetry, cloud logging, remote
upload, automatic GitHub issue submission, or automatic support submission.
`SERVER` mode does not expose local diagnostics export, and the existing
Host/Origin/localhost-proof boundary remains enforced.

# ADR-0029: Use one per-user NSIS foundation for Windows packaging

Status: Accepted — implementation complete through PR #76; documentation
closeout recorded in ADR-0031.

The Windows installer foundation uses the Tauri 2 NSIS bundler as its single
installer technology. WiX/MSI is not implemented in parallel: NSIS is already
supported by the Tauri shell and is sufficient for the first per-user package.
The configured `currentUser` mode installs without administrator elevation and
uses the user-scoped install directory `%LOCALAPPDATA%\Programs\SAPSOS Local
Desktop`. No system directories, school portals, browser credentials, or
official records are modified.

`desktop-shell/desktop-identity.json` is the authoritative identity source.
The product name, executable/package identity, bundle identifier, Windows
application identifier, publisher placeholder, semantic version, installer
artifact name, install directory, and `%LOCALAPPDATA%\SAPSOS` data root are
validated against Tauri, Cargo, and API configuration before packaging. The
identity is not derived from a user, school, machine path, or random identifier.

The existing `cargo run` development shell is explicitly not an installed
Windows product: it uses the development Web/API path and is never emitted by
the installer workflow or registered as an installed application. It therefore
shares the logical product identity only for exercising the same LOCAL_DESKTOP
data lifecycle; the installer identity and upgrade contract apply exclusively
to the release NSIS artifact. This is an intentional, documented exception to
the debug/release identity rule, not a second installer identity.

The package graph is Tauri executable → packaged FastAPI one-folder runtime →
static Next.js export → required resources and notices. The release shell
resolves the embedded API executable from `runtime/sapsos-api`; an explicit
`SAPSOS_API_EXECUTABLE` override remains available for controlled validation.
The package emits a versioned NSIS executable and `packaging-manifest.json`
with component paths, commit, signing status, size, and SHA-256. The paired
artifact validator checks those fields before the CI artifact is uploaded.
The release entry point uses a validated cleanup helper for stale generated
outputs and rejects user/AppData paths, repository roots, drive roots, parent
directories, and symlink/reparse-point traversal.

Install and upgrade preserve `%LOCALAPPDATA%\SAPSOS`, including the database,
pairing state, backups, migration evidence, and local Diagnostics state.
Uninstall removes application binaries but preserves that user data by default;
future destructive data removal requires an explicit, separately reviewed
choice. Code signing, auto-update, release publishing, cloud distribution,
telemetry, crash upload, and installer-level E2E are outside this foundation.
The current artifact is intentionally unsigned, and WebView2 bootstrapper
download behavior remains a clean-machine/network limitation until packaged
desktop E2E is completed.

`desktop-shell/data-retention-contract.json` classifies persistent user data,
recoverable operational state, ephemeral runtime state, and generated exports.
The installer does not run SQLite or Alembic migrations; existing Tauri
pre-start orchestration remains the migration and rollback owner.

# ADR-0030: Make Windows installer lifecycle and local-data deletion fail closed

Status: Accepted — implementation complete through PR #77; documentation
closeout recorded in ADR-0031.

NSIS remains the only Windows installer and continues to use per-user
`currentUser` installation with the existing product identity, bundle
identifier, install directory policy, and `%LOCALAPPDATA%\SAPSOS` data root.
Installer rollback is limited to installer-owned binaries, resources, staging,
and temporary files. It never rolls back or deletes the database, backups,
pairing, preferences, migration evidence, restore evidence, or external
exports; database migration rollback remains owned by the existing Tauri
pre-start migration orchestration.

The installer and uninstaller invoke a path-validated process coordinator before
their file operations. It matches the exact installed executable path and,
for the packaged API, the exact child executable path plus parent PID. It
requests normal desktop shutdown, waits with a bounded timeout, and blocks the
operation if the proven installed processes do not exit. It never terminates
processes by name alone and never touches development-worktree apps, unrelated
Python/uvicorn processes, browsers, or other localhost services.

Default uninstall removes only installer-owned content and explicitly preserves
the local database, SQLite sidecars, manual and migration backups, restore and
migration markers, pairing, preferences, sanitized startup state, local
Diagnostics state, and user-selected Documents/Downloads/Desktop exports.
Complete local-data removal is a separate LOCAL_DESKTOP-only operation requiring
a newly validated external backup, no active local operation, exact typed
confirmation `DELETE SAPSOS LOCAL DATA`, and a one-time deletion plan. The plan
is versioned and contains only the fixed logical category/entry allowlist, a
normalized AppData identity, nonce, expiry, confirmation and backup receipts,
execution state, and an integrity hash. It contains no student data,
credentials, pairing secret, runtime proof, database rows, or raw user paths.

Deletion paths are generated by the internal resolver, compared
case-insensitively, kept below the fixed AppData root, and checked for drive
roots, profile/AppData parents, install/repository/external roots, UNC/network
paths, traversal, symlinks, junctions, and reparse-point ancestors. Recursive
deletion walks the allowlist and refuses links; it never falls back to broad
directory deletion. A plan is marked in progress before deletion and becomes
failed or completed so cancellation, failure, expiry, tampering, and replay
cannot silently continue at the next startup. Partial failure stops further
deletion without widening the scope and retains the external backup.

The trusted packaged runtime performs the final filesystem operation only after
the desktop parent and API child have exited. The API exposes preparation and
cancel status only in `LOCAL_DESKTOP`; `SERVER` does not register the route.
Lifecycle CI uses an isolated temporary `LOCALAPPDATA`, runs clean install,
same-version repair, a real two-version same-identity upgrade, process
coordination, default uninstall retention, reinstall, and focused deletion
safety tests, and uploads only the unsigned next-version NSIS artifact. Test
version and AppData overrides require explicit CI-only flags and are rejected
by normal invocations.

Known limitations remain: the artifact is unsigned; WebView2 bootstrapper
network access may be required on a clean machine; and installer binary
replacement itself is not claimed to be fully transactional. Repair/reinstall
is the documented recovery path, while user data remains protected.

# ADR-0031: Close the Windows Installer/Uninstaller milestone

Status: Accepted — documentation closeout complete through this
documentation-only change.

## Decision

The Windows desktop package is a Tauri 2 NSIS installer using the Windows
per-user `currentUser` model. Product/application/bundle identity and the
`%LOCALAPPDATA%\SAPSOS` AppData root are stable. The package contains the
packaged FastAPI sidecar, static Web export, required resources, licenses, and
notices. A short controlled staging tree is mandatory because Tauri/NSIS cannot
reliably consume the deeply nested PyInstaller dist tree; native Python package
structure, including `pydantic_core` extensions, must remain package-relative.

The installer updates application binaries and resources. Tauri pre-start
orchestration remains responsible for LOCAL_DESKTOP migration safety backup,
migration execution/readiness, and database migration rollback. Installer
rollback and database-migration rollback are separate boundaries.

Default uninstall removes installer-owned files/resources and does not delete
the database or local user data. Full removal is a separate LOCAL_DESKTOP-only
workflow requiring external backup, exact typed confirmation, a fixed allowlist,
expiry, integrity/tamper/replay protection, and reparse/junction protection.
Partial failure is persisted, stale READY plans become EXPIRED, external files
are preserved, and arbitrary filesystem paths are rejected. SERVER mode does
not expose this workflow. Process safety uses exact path/PID/parent validation,
bounded waits, and no broad process-name kill; unverifiable cases fail closed.

## Validation evidence

PR #76 merged at `7228a0154821683e3b82500ff0894ec36547037a` and PR #77 merged
at `579708913d07ba55998723f366358530011a83b2`; PR #77 final head was
`b6669b177bb7442aa2ef3cbecf16125ce55f3464`. Regular CI, Windows Installer
Foundation CI, and Windows Installer Lifecycle CI passed. The final lifecycle
evidence includes real NSIS clean install, same-version repair, two-version
upgrade with version assertion, uninstall retention, reinstall, process
coordination, packaged-runtime startup, and artifact upload. The installer
artifact is unsigned; no run number is inferred here.

## Lessons learned and remaining limits

The durable packaged-runtime rules are to preserve the PyInstaller one-folder
native dependency layout, avoid flattening Python package/native-extension
directories during Tauri resource mapping, retain `pydantic_core/_pydantic_core*.pyd`
under its package-relative directory, and keep runtime-directory/DLL lookup
environment aligned with the installed layout. Lifecycle fixtures must be real,
valid LOCAL_DESKTOP SQLite fixtures.

Hosted-runner image changes must not silently remove the x64 Microsoft VC
runtime from that layout. When PyInstaller does not copy `MSVCP140.dll`, the
build resolves it only from the 64-bit Windows, Python, or installed Visual
Studio redistributable roots, then verifies Microsoft publisher metadata,
Authenticode status, PE architecture, and the staged hash. Missing or
unverifiable runtime files fail the build; the installer/runtime assertions are
not downgraded.

The installer remains an unsigned development artifact and may trigger
SmartScreen. Code signing, automatic updates, GitHub/public release
distribution, Store/MSIX packaging, and production publishing are not done.
Packaged Desktop E2E is the next milestone and is not implied by installer
lifecycle CI; it still requires real desktop startup, API supervision/readiness,
static UI rendering, key workflows, restart/persistence, applicable
extension/local integration, and failure/recovery validation. Beta and RC remain
not started.

# ADR-0032: Trust packaged runtime handoff by launch identity

Status: Proposed — validation pending on the fresh Packaged Desktop E2E head.

## Decision

The packaged desktop starts each API launch with a fresh UUID instance identity.
The Tauri child command receives that UUID through a launch-scoped environment
variable, and the API publishes the same value in `runtime.json`. Tauri accepts
readiness only when the manifest UUID matches the launch UUID, the manifest PID
resolves to the exact packaged API executable, its creation time is within the
launch window, and its process lineage is either the API spawn root, the Tauri
process through an explicit handoff, or the same process. A parent PID equal to
Tauri alone is not sufficient without the identity and creation-time checks.

The spawn root is therefore an observed launch identity, not a required living
ancestor. This accommodates PyInstaller handoff while preserving fail-closed
trust. Shutdown revalidates PID, creation time, and exact executable before
termination, waits within a bounded timeout, and removes `runtime.json` only
when its UUID still belongs to the stopped launch. Foreign, malformed, stale,
or reused-PID state is left untouched for diagnostics and recovery.

## Validation contract

The packaged E2E evidence must record only sanitized booleans and ownership
mode: instance match, creation-window validity, exact executable match, Tauri
ownership, listener owner, readiness, shutdown disappearance of the spawn root
and trusted runtime, restart UUID non-reuse, and absence of an orphan API. Raw
UUIDs, user paths, and student data are not evidence outputs. Full E2E remains
required before PR #79 can leave Draft; signing, release, Store/MSIX, Beta, and
RC work remain out of scope.

# ADR-0033: Pass the canonical per-user root to installer preflight

Status: Proposed — fresh-head Windows installer validation pending.

## Context

The Tauri currentUser NSIS template initializes a clean install to
`%LOCALAPPDATA%\\SAPSOS Local Desktop`, while the product identity contract
uses `%LOCALAPPDATA%\\Programs\\SAPSOS Local Desktop`. The preinstall hook
runs after `SetOutPath $INSTDIR`, so passing the untouched Tauri default to
the exact-path coordinator produces an invalid-root failure. NSIS then
incorrectly presents every nonzero coordinator result as a running-app error.

## Decision

The preinstall hook rewrites only the untouched Tauri currentUser default to
the canonical per-user Programs root before invoking coordination. A valid
existing canonical root remains unchanged; foreign, stale, or user-selected
roots are not silently trusted and remain subject to coordinator validation.
The preuninstall hook does not rewrite `$INSTDIR`, preserving stale-root
rejection and uninstall safety.

The coordinator uses privacy-safe local temporary diagnostics and a stable
exit contract: `0` success, `10` real trusted SAPSOS process still active,
`20` invalid install root, `30` process inspection failure, and `40` internal
failure. NSIS maps these categories to distinct user-facing messages while
keeping the real running-app message only for code `10`.

Diagnostics contain only timestamp, installer version, root values, category,
exit code, process count, and trusted candidate PID/path pairs. They contain
no student data, SQLite contents, credentials, cookies, tokens, or sessions.

# ADR-0034: Deploy the packaged runtime as a validated payload

Status: Proposed — fresh-head installer, lifecycle, packaged desktop, and
uploaded-artifact round-trip validation pending for BETA-A-INSTALL-003.

## Context

The 0.1.2 real-machine install reached the NSIS payload copy phase but showed
an opaque write failure for `runtime/sapsos-api/MSVCP140.dll`. Abort removed
the partial runtime tree, so the original Windows error category cannot be
reconstructed. ACL, Defender, a runtime lock, and a sharing violation are not
treated as proven causes.

## Decision

The packaged FastAPI one-folder runtime is carried through NSIS as one
versioned archive plus privacy-safe metadata. The archive and metadata are
explicitly embedded into and consumed from NSIS `$PLUGINSDIR`, a transient
installer resource directory; they are not supplied through Tauri's incidental
`bundle.resources` placement and are not left in the final install root. A
preinstall hook records an attempt before payload validation, so a missing
resource leaves a local diagnostic under `%TEMP%\SAPSOS\installer-runtime`.
A postinstall helper extracts into a same-volume staging directory, validates
`sapsos-api.exe` and `MSVCP140.dll`, then replaces the destination runtime
directory with bounded handling for confirmed sharing/lock errors. It restores
the previous runtime on a failed replacement and aborts the installer;
required runtime files are never ignored.

The helper records an attempt ID, timestamp, installer version, build/source
commit provenance, phase, source/staging/backup paths and existence flags,
destination path and attributes, archive identity, failing relative/absolute
path, Windows error code, category/message, retry count, rollback outcome,
install mode, and final outcome. It records no student data, SQLite contents,
credentials, cookies, tokens, or sessions. Only installer-owned program
payload paths participate in staging, rollback, and cleanup.
`%LOCALAPPDATA%\SAPSOS` is not touched.

The helper classifies access denied separately from sharing/lock violations,
and treats unknown I/O interference as unknown. The exact BETA-A-INSTALL-003
machine error remains unproven unless the same Windows error is observed. The
build emits a resource-delivery contract and provenance model, and Lifecycle CI
downloads the exact uploaded artifact before running an isolated installer
round-trip. Workspace-only validation is not treated as artifact-delivery
proof.

## ADR-0034: Use an OS-owned mutex for desktop startup ownership

The desktop startup marker previously used `create_new` and closed the file
immediately. An abnormal exit therefore left a persistent `startup.lock` that
could reject every later launch, and contention propagated through Tauri setup
as a panic. Windows packaged launches now use a per-user named mutex derived
from the stable LOCAL_DESKTOP data root. Windows releases the mutex
automatically when the owning process exits, including crash and forced
termination. The marker remains only as recoverable operational residue and
is rewritten after mutex acquisition.

Expected contention is diagnosed and exits cleanly. A stale marker does not
imply a live owner; successful mutex acquisition safely replaces it. The local
`startup-lock-diagnostics.json` file records only lock-path, build/version,
acquisition, ownership, recovery, and outcome metadata; it contains no student
data, credentials, portal data, or session material.

## ADR-0035: Bootstrap one unverified local student identity without guessing academic rules

Status: Accepted for controlled-beta candidate validation.

### Context

A fresh local database had no student profile, while every import is student
scoped. The web could recover a known persisted import but could not create the
first identity, and the Extension required the user to copy a raw profile UUID.
Using the deterministic development seed or inventing a program/catalog mapping
would make synthetic or guessed data look real.

### Decision

Add a `LOCAL_DESKTOP`-only first-profile API and web form. Creation is allowed
only when no non-mock student profile exists and creates existing `Institution`,
`Campus`, and `StudentProfile` records with server-fixed
`STUDENT_PROVIDED`, non-official, unverified provenance. It creates no program,
catalog, course rule, audit, or optimizer data. Conflicting codes return 409 and
never update stored data. Mock profiles are excluded from discovery and do not
block creation of the first non-mock profile.

Real profiles do not borrow the demo program when an audit is missing; the UI
shows an evidence-missing state. After pairing, the Extension worker signs a
local profile-list request with the credential it already owns. The popup
auto-selects only one returned profile and never receives the credential.
SERVER authorization remains unchanged. Extension handoff is a separate
local-only boundary defined by ADR-0036.

### Consequences

Fresh local participants can establish a pseudonymous, explicitly unverified
identity without direct database editing or a copied UUID. Academic conclusions
remain blocked until reviewed program/catalog and participant evidence exist.
Multiple-profile onboarding, authoritative institution lookup, and real-source
acceptance remain separate reviewed work.

## ADR-0036: Fail closed before controlled real-source acceptance

Status: Accepted for Phase 15 no-login preparation.

### Context

Real portal acceptance requires a participant-owned authenticated page, but
repository, parser, normalization, application, chronology, determinism, and
privacy boundaries can be audited without authentication. The Extension also
retained a legacy non-local bearer path, kept a stale student ID when profile
discovery was ambiguous, and did not catch failures raised inside the
asynchronous Chrome storage callback. Eligibility considered effective attempts
without target-term chronology.

### Decision

Real-source evidence is recorded in a matrix that separates fixture evidence
from real-page capture. Until the participant manually authenticates and gives
the exact read-only continuation authorization, real capture, PRD/PROD runs,
traffic observation, and downstream real acceptance remain blocked.

The Extension sends staging imports only through its paired worker to an
explicit loopback HTTP root. It has no bearer-token field or direct remote
handoff. Worker messages validate the destination before network access and
callback-scoped failures return a sanitized reason. Zero or multiple local
profiles clear stale scope; only exactly one profile is auto-selected.

Eligibility evidence is target-term relative. Prerequisites and completed
credits require an attempt ending before the target starts; exact-target-term
concurrency is allowed only for corequisites. Both stored expression trees and
reviewed catalog declarations use this rule.

### Consequences

Synthetic tests may establish readiness, idempotency, and deterministic engine
behavior, but cannot produce a real-source PASS. A real catalog page capture is
not itself an active reviewed degree-rule set. Real Degree Audit, Planner,
Optimizer, persistence, privacy traffic, participant UX, accessibility, and RC
classification remain blocked until their direct evidence exists. No provider
write, push, merge, tag, release, or installed 0.1.5 data mutation is part of
this decision.

## ADR-0037: Bound real MyProgress DOM traversal by unique visible evidence

Status: Accepted after controlled read-only MyProgress verification.

### Context

The authenticated MyProgress page contains deeply nested requirement groups,
17 visible academic tables, and thousands of repeated DOM visits during one
snapshot. The previous 5,000-node counter incremented the same nodes from
multiple traversal paths, counted hidden text before discarding it, and treated
outer table-owning containers as row-like evidence. The snapshot therefore
reached its budget before retaining the visible summary. Navigation text could
also select a different page definition before the exact MyProgress route was
considered. The page uses colon-delimited GPA labels, and a real course-state
label `ATTEMPTED` does not prove a passing completion.

### Decision

Count each inspected DOM node once with a `WeakSet`, count text only after its
ancestor is confirmed visible, and exclude both descendants and owners of
tables from row-like scanning. Raise the shared/content-script node ceiling to
8,000 based on the observed 6,850 unique-node population while retaining the
existing duration, text, row, cell, and truncation limits. Exact supported
route markers precede visible-navigation fallbacks. Accept optional colons in
summary labels. A missing catalog year remains a review warning, never a
guessed value. Preserve `ATTEMPTED` as source evidence, normalize it to
`UNKNOWN`, and require advisor review instead of manufacturing completion.

### Consequences

The controlled real MyProgress snapshot completes unbounded and retains all a nested multi-table structure (participant-derived counts omitted). Synthetic Chromium coverage reproduces the
nested/large DOM. The safety ceiling remains finite. Ambiguous attempted rows
and duplicate/conflicting representations remain fail-closed, so a parser PASS
does not imply Degree Audit or Planner readiness without an exact reviewed
catalog mapping and reliable course history.

## ADR-0038: Parse real Catalog cards and responsive SectionListing rows without inventing policy

Status: Accepted after controlled read-only Catalog and Sections verification.

### Context

The authenticated Catalog uses course cards rather than academic tables. Its
requisites mix explicit course dependencies with natural-language standing,
credit, permission, and petition clauses. SectionListing uses a responsive
table whose desktop `thead` is hidden and whose visible body cells expose field
labels through `data-role`. The combined Section Name carries course and
section identity, meeting blocks contain multiple visible lines, and the page
does not expose a CRN. Broad path matching also classified SectionListing as a
Catalog page before considering the explicit query view.

### Decision

Capture one Catalog record per nearest card container, split long descriptions
across bounded cells, exclude action buttons, preserve raw requisite clauses,
and classify only text patterns directly supported by the page. Every nonempty
requisite remains `MANUAL_CONFIRMATION_REQUIRED`; an exact course identity match
does not create a reviewed program rule set or catalog-year mapping.

Prefer the explicit `searchResultsView=SectionListing` query contract before
broad route markers. When the visible table header is hidden, recover headers
from body-cell `data-role` values while blanking Add To Schedule and Planned
Status columns. Parse combined course/section identity, preserve multiple
meeting blocks and raw availability evidence, and require exception review when
CRN is absent. Duplicate visible rows are reason-coded and never silently
accepted as separate section identities.

### Consequences

Real Catalog and Sections page/parser gates may pass independently from
academic-consumption gates. Missing exact active program rules, internal course
mapping, CRN, capacity, or waitlist semantics continue to block review/apply,
Degree Audit, Planner, Section Matching, and REVIEWED_IMPORTED optimization.
No provider action, registration workflow, or official-policy inference is
introduced.

## ADR-0039: Provision reviewed Catalog Course identities and keep CRN optional

Status: Accepted for implementation; controlled real-source revalidation is
still required. This decision supersedes ADR-0038 only where ADR-0038 treated
missing CRN as a universal Section-application blocker.

### Context

The Phase 15 controlled pages proved 30 unique Catalog course identities and 30
unique term/course/section tuples, but staging could map only to a pre-existing
Course. Catalog records had no target-specific Apply path, so every Section and
MyProgress course without a seed Course remained `UNMATCHED_COURSE_CODE`.
Section `external_reference` was already nullable and its database uniqueness
key did not contain CRN, yet the extension incorrectly made a missing CRN an
exception-review condition. The Catalog also did not expose course level or
repeatability for every row.

### Decision

An explicitly confirmed Catalog row with exact source course code, title, and
positive credits may create or update one non-official Course scoped by student
home institution + normalized subject + course number. The generated UUID is an
internal identity for that exact reviewed key, not a provider identifier. Apply
reconciles existing exact-code staging candidates for the same student and is
idempotent. It never uses title similarity, seed/mock courses, or inferred
aliases, and it never overwrites official/mock/unrelated records.

Reconciliation appends a new exact Course candidate and changes only current
staging selection state. Provisioning/unknown candidates and existing review
selections remain historical evidence. A same-code row that conflicts on
title, credits, provided description, or already-verified optional facts is
skipped until catalog-version evidence or an explicit conflict-resolution
workflow exists.

Course level and repeatability retain storage-compatible values plus explicit
verification flags. Unverified fields are exposed to API and Degree Audit as
null. PostgreSQL migration `20260824_0021` and LOCAL_DESKTOP schema version 2
add the flags; legacy browser/imported, student-provided, and inferred rows
migrate conservatively. Catalog
requisite prose remains manual-confirmation evidence and does not create rules,
equivalencies, ProgramVersions, or catalog-year bindings.

The migration orchestrator's safety snapshot validates the exact source schema
version selected by preflight. Ordinary backup/restore validation still
requires the current schema. This permits a version-1 database to be backed up
before the version-2 migration without accepting an arbitrary, newer, or
unexpected schema.

Section identity remains institution + term + Course + section code, which the
controlled Phase 15 population proved unique. CRN/external reference is
optional; absence is recorded as null plus `NOT_PROVIDED` provenance and is not
a validation error by itself. Exact term and campus mappings remain mandatory.

MyProgress program and requirement context is evidence-bearing even when a
reviewer rejects, defers, or escalates it, but only confirmed or
edited-and-confirmed context contributes to readiness. Confirmed subsets may
continue with `REQUIREMENT_EVIDENCE_PARTIAL`; uncertainty stays visible.
`MOCK`, `STUDENT_PROVIDED`, and `INFERRED` programs, versions, and
student-program assignments are excluded from real program identity resolution;
only `OFFICIAL`, reviewed `IMPORTED`, or reviewed `BROWSER_EXTENSION` domain
records may bind exactly.

### Consequences

Synthetic and isolated tests can prove Course provisioning, cross-source UUID
reuse, null-CRN Section Apply, idempotency, migrations, and deterministic
behavior. They cannot upgrade the real gates: Catalog/Sections must be captured
again through an authorized read-only browser session, and ProgramVersion plus
reviewed requirement/rule evidence remain separate prerequisites for a real
Degree Audit, Planner, and end-to-end optimizer result. No portal write,
registration action, credential access, or provider-side mutation is added.

## ADR-0040: Traverse the visible Kean Catalog with a bounded user-started state machine

Status: Accepted after controlled read-only feasibility review.

### Context

The manual Phase 15 Catalog workflow proved that visible course cards can be
captured and safely provision exact non-official Course identities, but it
required a user to repeat subject searches and confirmations. Controlled
inspection of the real Catalog landing and results pages found a public subject
select, a GET `CatalogListing` search, course-card results, a visible current
page number, and explicit page buttons. The sampled ACCT search returned 30
cards per page across four pages. The result route did not require a guessed
query or private XHR contract, and no infinite-scroll mechanism was observed.

### Decision

Add one explicitly user-started `Capture full Course Catalog` state machine to
the Extension worker. Enumerate only visible subject options; drive only the
reviewed GET search and explicit pagination buttons; keep concurrency at one
with a 2.5-second interval; and enforce subject, per-subject page, total page,
record, retry, and 45-minute runtime limits. Persist after every accepted page.
Pause and Cancel take effect at bounded action boundaries. A worker restart
restores an active run as `PAUSED`, so continuation always remains explicit.

Deduplicate by normalized Course code inside an institution and require an
identical visible-field fingerprint for overlap. Preserve safe page path,
subject, page number, capture timestamp, raw title, normalized code, and source
label. Require an exact visible-card/extracted-record count, wait for the first
course marker to change after pagination, and revalidate any accepted page
fingerprint before resuming. Missing optional fields are `NOT_PROVIDED`;
natural-language requisites remain raw review-required text. Rate limits,
provider errors, parser drift, truncation, malformed required fields,
conflicting duplicates, timeouts, and limit breaches stop fail-closed.

For each completed subject, submit only through the paired loopback Extension
worker. The local API deterministically confirms exact safe fields, performs a
dry-run, applies only successful non-official Course changes, reconciles exact
MyProgress candidates, and returns mapped/unmatched counts. No school state,
credential, cookie, token, ProgramVersion, catalog-year binding, or verified
policy is written or inferred.

### Consequences

One school-page click replaces repeated per-subject capture and local-review
clicks while keeping the provider boundary read-only. A full run can take many
minutes and may end `FAILED`, `PAUSED`, or `CANCELLED` with partial isolated
local results already applied; the UI reports that state rather than claiming
full completeness. Future refreshes remain manual user actions. The feature
adds no alarm, scheduled crawler, registration action, provider mutation,
push, merge, tag, release, or installed-runtime write.

## ADR-0041: Make Catalog traversal event-driven and independently observable

Status: Accepted after the first real 116-subject discovery stalled at ACCT.

### Context

The first real batch discovered 116 subjects but captured zero courses. Direct
inspection proved that Kean's Catalog/Section radio is a Knockout
`checked: searchResultsView` binding. Assigning `checked = true` changed the DOM
but not the bound view model, so the search submitted `SectionListing`. The
Catalog parser then correctly rejected the section grid. The original worker
also kept the entire traversal in one in-memory Promise with timer delays; that
design could not prove continuation after popup closure or an MV3 worker
suspension. The popup was the only progress surface.

### Decision

Trigger the reviewed Catalog radio with its actual click binding before the
read-only search click and fail explicitly on a Section Listing result. Replace
the in-memory loop with persisted, event-driven checkpoints. A subject search
navigates the single authorized tab; `tabs.onUpdated` installs one bounded
content-page observer; the observer wakes the worker only when the reviewed
result is ready, a provider/rate-limit signal appears, or the timeout expires.
Pagination installs the next observer before clicking the explicit page button.
No alarm, scheduled crawl, periodic school polling, or service-worker timer is
used.

Persist status, run ID, subject index/code, page, counts, warning/error,
transition, transition timestamp, and authorized tab ID. A session-storage
lease is not proof that the ephemeral worker listeners still own the run: a
new worker always restores a persisted `RUNNING` checkpoint as `PAUSED` and
resumable. Closing or navigating the authorized tab away pauses fail-closed
and never causes the Extension to open an authenticated school page.

The initial discovery uses the same durable browser-event handoff as Resume
and later subjects. Before the popup start response ends, persist
`LANDING_NAVIGATION_REQUESTED` and request a reload of the single authorized
Catalog landing tab. Only its later `tabs.onUpdated` completion may start the
first subject search. Popup closure therefore cannot own the discovery-to-ACCT
transition, and a rejected initial tab navigation is saved as `PAUSED` instead
of leaving an orphaned `RUNNING` state.

The landing-page completion event is not by itself proof that Kean's Knockout
search bindings are ready. Inject the readiness wait into the page main world,
require the reviewed controls and binding contexts to remain stable, and only
then perform the normal Catalog GET click. Before that wait begins, install a
revisioned isolated-world watchdog. Persist expected, content-ready, timeout,
and observed tab revisions; accept a timeout only for the current revision and
only while the authorized tab still has the exact landing URL.

Ship a Side Panel batch monitor and an extension-owned monitor-tab fallback.
Both reconnect from sanitized persisted state and expose Pause, Resume, and
Cancel. The popup remains responsible for pairing, visible-page extraction,
starting the batch, and opening the monitor. The first real acceptance run is
limited to two subjects; the full 116-subject action remains locked until that
bounded run completes.

The bounded-acceptance result is revisioned with the runner contract. A legacy
boolean or a pass from an earlier contract cannot unlock full Catalog capture;
the current two-subject acceptance must complete and persist the exact current
revision first. Any lifecycle or pagination change that alters real execution
must advance that revision and re-lock full capture until bounded acceptance is
re-established.

The popup opens the Side Panel directly inside the explicit user gesture. If
that API is unavailable or rejects the request, the same gesture opens the
packaged `src/monitor/index.html` tab. Preserve the sanitized Side Panel,
fallback-tab, runtime-message, authorized-tab path, start-message, and last
transition diagnostics in extension-local storage; never replace them with a
generic monitor error. A non-landing Catalog path fails before worker dispatch
with `BATCH_CATALOG_LANDING_REQUIRED`, while the monitor may still reconnect to
the last persisted checkpoint even when the worker message is unavailable.

The first bounded real run then proved 116-subject discovery, ACCT page-1
capture, and persistent monitoring, but failed at the page-2 checkpoint. The
real pagination input is labeled through
`label[for="course-results-current-page"]`; it has no `aria-label`. The old
observer defaulted a missing input to the requested page while the capture
check defaulted the same missing input to page 1, creating a false READY then a
`BATCH_CATALOG_PAGINATION_INVALID` failure on the correctly visible page 2.

Read the exact `#course-results-current-page` value with the legacy aria-label
selector only as a compatibility fallback. A same-URL page transition becomes
READY only when the requested page is visible, the result list contains cards,
the order-independent full marker-identity fingerprint differs from the prior page, any
result-level loading surface is inactive, and the same checkpoint remains
unchanged for a bounded settle window. Observe DOM mutations and condition-poll
the live controls because Knockout property updates do not necessarily mutate
attributes. Recheck the same fingerprint immediately before capture; stale or
partially updated DOM times out fail-closed instead of being accepted as a page.

The next bounded real run proved ACCT pages 1 through 4, 98 unique captures,
the first local subject completion, and persistent monitoring. It then paused
while starting AD: the landing-page watchdog fired after the search click left
the authorized tab on the landing route. The first ACCT search used the
landing page's initial subject state, but later subject selection could rebuild
the subject, result-view, and submit controls. The old code selected AD and
then clicked references acquired before that change; it verified only the old
radio's DOM `checked` property and never proved that the selected value,
Knockout context, or submit node still belonged to the connected control tree.

For every subject, reacquire the visible controls after subject input/change,
require the exact selected value and current Knockout contexts to remain stable
for the bounded settle window, then reacquire and click the current Catalog
Listing radio and submit control. A stale or rebuilt selector is retried by
condition, never hidden by a fixed sleep. Ignore late landing completion events
once the current subject revision has started; only that revision's watchdog
may pause a landing stall. Every READY result also carries the single subject
code derived from all visible course markers, and the controller rejects a
SearchResult that does not match the expected subject. This lifecycle change
advances the bounded-acceptance contract to
`phase15b-page-ready-v4` and re-locks full capture.

The next real diagnostic established a different page-1 readiness failure:
Kean had already hydrated the reviewed `SearchResult`, course-card list, and
subject identity, but page 1 omitted `#course-results-current-page`. The old
gate returned before recording the observed cards and therefore could never
become READY; increasing the timeout would not change that outcome. Page 1 may
now use a narrow fallback only when there is no prior-page marker, the expected
page is exactly 1, all explicit pagination targets are later pages, no
`aria-current` marker conflicts, the expected subject has nonempty cards, the
full marker fingerprint is stable, and no blocking spinner remains visible.
Missing page identity on later pages still times out fail-closed, while a stable
wrong page is classified as `BATCH_CATALOG_PAGE_NUMBER_MISMATCH`.

The following real v4 run reached the reviewed SearchResult route with page 1,
30 course cards, a nonempty identity fingerprint, and the current-page input,
but timed out solely on `KNOCKOUT_READY`. Extension content scripts do not
reliably share the page world's Knockout object, so framework binding context is
not authoritative evidence that visible business data is ready. Under
`phase15b-content-ready-v5`, Knockout state is diagnostic only. Readiness is
instead based on the exact SearchResult URL, one visible result container,
nonempty course identities and fingerprint, validated page semantics, a bounded
unchanged-content window, no conflicting subject evidence, and no blocking
error state. When the page exposes no reliable subject marker, the result may
remain bound to the exact persisted subject-search navigation revision as
`CHECKPOINT_BOUND`; conflicting visible subject evidence still fails closed.

Spinner class names and geometry are also diagnostic rather than sufficient to
block capture. A spinner is a hard gate only when the active Catalog result
surface, list, or a visible descendant explicitly declares `aria-busy=true`.
Persist selector, style, rectangle, accessibility, scope, interaction, and
hard-gate diagnostics plus a `BLOCKING`, `NON_BLOCKING`, or `UNKNOWN`
classification so later real evidence can distinguish a current payload load
from a persistent shared UI element. Only `BLOCKING` is a hard gate. Content
stability is computed independently of both Knockout and spinner heuristics and
requires the same connected result-list node, card count, parsed Course-identity
count, full fingerprint, and navigation revision throughout the bounded settle
window. Persist the passing predicate list and exact failed predicate; a timeout
is a terminal classification, not the readiness root cause. Loading v5 archives
a paused v4 run as `SUPERSEDED_BY_NEW_REVISION`; it is never resumed, and full
116-subject capture remains locked until a fresh two-subject v5 acceptance
completes.

The first real v5 bounded run
`dad8f3bb-d3f0-4a12-bf93-33813cf46e27` discovered all 116 subjects and then
failed before SearchResult navigation. Eight durable extension-storage
snapshots prove that the navigation watchdog completed and revision 1 was
persisted, while `startCatalogSubjectSearch` was the next operation. The v5
catch-all retained only `BATCH_CATALOG_UNEXPECTED_ERROR`; no safe name,
message, stack, or operation was stored, and the available Edge debug log
ended before the failure. The original exception text is therefore not
recoverable and must not be guessed.

`phase15b-content-ready-v6` makes that startup boundary observable and
fail-closed. Fresh state initializes failure diagnostics independently of
archived state, persists `FIRST_SUBJECT_INITIALIZED`,
`LANDING_READY_WAIT_STARTED`, `LANDING_READY`, and
`SUBJECT_SELECTION_STARTED`, and keeps `lastSuccessfulCheckpoint` separate
from `failedOperation`. A failure stores bounded, redacted error name,
message, stack, cause, phase, operation, checkpoint, run revision, navigation
revision, and timestamp. Stored-state restoration re-applies the same
redaction to both the summary error message and the structured diagnostic
before Monitor display.
Authorization and proxy-authorization values, Cookie and Set-Cookie values,
bearer/JWT values, credential/token/password/key/secret key-value pairs, URLs,
local paths, extension IDs, and UUIDs are removed before persistence. Browser
script injection, missing content execution,
stored-state schema, storage persistence, authorized-tab, landing preparation,
subject selection, and search-trigger failures retain distinct error codes;
only an operation
with no known classification may use `BATCH_CATALOG_UNEXPECTED_ERROR`.
Monitor rendering consumes these fields as optional observer data and renders
placeholders when they are absent; monitor formatting or old-schema data
cannot fail the runner. The failed v5 run is archived as immutable evidence
and superseded by v6 rather than resumed or merged.

This diagnostic revision does not relax the v5 content contract: Knockout
remains diagnostic-only, only an explicit blocking spinner is a hard gate,
the same connected result container and valid Course identities must remain
stable, and rebuilt containers reset the settle window. It also leaves the
explicit MyProgress remap service and fail-closed
`myprogress_remap_executed=true` evidence requirement unchanged. Full
116-subject capture remains locked; the next real acceptance is still exactly
two subjects.

The first real v6 bounded run
`14c1b82f-d5fa-4f33-b302-4fd91f4dadf4` deterministically failed at
`START_SUBJECT_SEARCH`: the MAIN-world Catalog search function clicked the
navigation control, Edge returned a `null` injection result as that document
was replaced, the worker's local `executeScript` type incorrectly promised a
non-null `CatalogSearchAction`, and `beginCatalogSubject` read `.action` from
that `null` value. `phase15b-navigation-contract-v7` separates the operation
into a result-bearing preparation function and a navigation-bearing submit
function. The preparation result proves the reviewed subject and Catalog
Listing checkpoints before any navigation. The submit transport explicitly
classifies `VALUE` and `NULL_RESULT`; a null result is retained as pending
navigation evidence and cannot itself advance `SEARCH_SUBMITTED`. A real tab
loading or SearchResult completion event advances that checkpoint, while the
existing revisioned watchdog pauses fail-closed if navigation never occurs.
Empty, missing, or unexpected non-navigation results remain terminal semantic
errors rather than reaching a property read.

Persisted failure diagnostics now also record the injection-result kind,
school-tab URL classification, subject code, and `providerActionsWritten=NO`
beside operation and runner/navigation revisions. Monitor renders those fields
without exposing raw URLs or portal data. Loading v7 archives the failed v6 run
as immutable `SUPERSEDED_BY_NEW_REVISION` evidence; it is never resumed or
rewritten. The explicit MyProgress remap contract and content-ready gates are
unchanged, full 116-subject capture remains locked, and v7 still requires a new
real two-subject acceptance after packaging and one Extension reload.

The first real v7 bounded run
`66fff0c2-de28-434c-aa24-ad8ea7eb84dc` proved that the MAIN-world preparation
call itself may also complete with an optional `null` injection result before
the submit function is dispatched. The Catalog tab remained on the reviewed
landing URL, no tab-loading signal was recorded, and the run stopped before any
course capture or local processing. `phase15b-preparation-contract-v8` therefore
models preparation as an explicit `VALUE | NULL_RESULT` outcome. A value must
still contain the exact reviewed checkpoint sequence. A null value claims no
preparation checkpoint and is allowed to proceed only to the existing,
independent submit function, which revalidates the exact landing URL, requested
subject value, CatalogListing selection, connected/enabled controls, and
Knockout bindings before it clicks Search. Empty or missing preparation results
remain terminal errors. The persisted public state and Monitor separately show
the last preparation and submit result kinds, and loading v8 archives the exact
failed v7 run as immutable superseded evidence.

This transport correction does not weaken content readiness or local Apply:
SearchResult navigation and revisioned content-ready signals remain mandatory,
the valid Course identity and connected-container stability gates are
unchanged, explicit MyProgress remap execution evidence remains fail-closed,
provider actions remain `NO`, and full 116-subject capture remains locked.

The first real v8 bounded run
`547fbad0-9939-406d-ad4b-3ea2b24b7b0d` proved that the two-call transport was
itself the remaining regression boundary. Both MAIN-world calls returned the
optional `null` result, no tab loading event occurred, the reviewed tab stayed
on the Catalog landing URL, and the revisioned watchdog paused before any
course capture or local processing. Earlier controlled real runs had already
reached the ordinary `SearchResult` route from the single MAIN-world
prepare-and-click execution, and the reviewed portal contract explicitly does
not use a same-document or guessed XHR result mode. The failure therefore does
not authorize relaxing SearchResult provenance.

`phase15b-main-world-checkpoint-v9` restores one MAIN-world execution for the
stable control preparation and Search click while preserving independent,
durable preparation evidence. Before that execution can click Search, it sends
an exact batch/revision/subject/token checkpoint through the shared page DOM to
the preinstalled ISOLATED-world watcher. The watcher forwards only the fixed
checkpoint tuple to the service worker. The controller revalidates the current
authorized tab, subject, revision, landing path, token, and ordered checkpoint
tuple, persists `preparationCheckpointRevision` plus
`CATALOG_LISTING_VERIFIED`, and only then returns an acknowledgment. The
MAIN-world function reacquires and revalidates the connected controls after the
acknowledgment before performing its one Search click. Missing, stale, rejected,
or timed-out acknowledgment fails closed without clicking. A landing timeout
also persists sanitized booleans and counts for the controls, result surface,
course identities, and Section Listing mismatch; it never stores raw portal
HTML or user data. Loading v9 archives the paused v8 run as immutable
`SUPERSEDED_BY_NEW_REVISION` evidence. All content-ready, spinner, stability,
valid-identity, explicit MyProgress remap, provider-action, and full-capture
locks remain unchanged.

Treat the popup only as the user-gesture launcher. Its direct click opens a
persistent side panel before any asynchronous worker request; an
extension-owned monitor tab is the bounded fallback. The monitor reloads from
sanitized extension storage, reconnects after worker suspension, and shows run,
revision, lease, page-ready, processing, and disabled-action reasons without
reading school DOM or authentication data. The persisted runner exposes the
reviewed subject-search checkpoints from connected, freshly queried controls,
then records SearchResult navigation/readiness, page capture, next-page,
last-page, subject completion, and next-subject checkpoints.

After the last page of each bounded subject, require the local endpoint to
return the ordered `LOCAL_STAGING`, `LOCAL_VALIDATION`, `LOCAL_REVIEW`,
`LOCAL_DRY_RUN`, `LOCAL_APPLY`, and `MYPROGRESS_REMAP` stages plus internally
consistent staged/reviewed/applied and MyProgress before/after counts. Reject an
incomplete or inconsistent response. `MYPROGRESS_REMAP` must invoke the
deterministic exact-code mapping service over the latest MyProgress import and
the successfully applied reviewed Catalog Courses before recounting; a recount
alone does not complete that stage. This path may provision reviewed internal
Course identities and remap existing MyProgress records, but must not create a
ProgramVersion, infer a program/catalog binding, or write to the provider.

Completing the v4 bounded acceptance records evidence but does not itself
unlock the 116-subject action. Version 0.1.6 keeps Full capture disabled in both
the popup and worker; a later, separately authorized decision must deliberately
change that build gate. This narrows ADR-0041's earlier “locked until bounded
completion” language so bounded success is necessary evidence, not sufficient
authorization.

Persist the runner revision at run creation rather than inferring it from
`boundedAcceptanceRevision`, because that second field is intentionally `null`
until a bounded run completes. On worker initialization, a `PAUSED` or `FAILED`
checkpoint from a different or missing runner revision is copied to sanitized
audit history as `SUPERSEDED_BY_NEW_REVISION`, then its active ownership and
session lease are cleared. Local import/review IDs and aggregate outcomes remain
in the archive; backend Catalog, review, provenance, MyProgress, and SQLite data
are untouched. Same-revision pauses retain Resume/Cancel ownership. Before a
new run replaces any terminal checkpoint, preserve its audit summary; completed
summaries are immutable and exempt from transient-history eviction.

### Consequences

Popup closure and tab switching no longer own batch lifetime. Every school-page
action remains a visible read-only search or explicit pagination click on the
original tab. Provider writes, credentials, cookies, authorization headers,
registration actions, ProgramVersion guesses, and unreviewed policy activation
remain prohibited. ADR-0041 supersedes ADR-0040 only for lifecycle scheduling,
monitoring, and the initial full-run gate; its provenance, deduplication, local
Apply, and fail-closed boundaries remain in force.


## 2026-10-18: scoped UI results and disposable E2E infrastructure

The local desktop repair keeps existing domain/API contracts and the v9 Catalog gate. Each workflow owns a generation scoped to API, student, demo state and relevant calculation inputs. A scope change clears rendered results synchronously and invalidates earlier async setters, including A-to-B-to-A transitions. The currently hardcoded mock candidates are usable only in explicit demo mode; real candidate selection is a documented follow-up, never a silent fallback.

Both Playwright entrypoints create fresh synthetic SQLite roots, seed mock data explicitly, and refuse existing server reuse. A caller DATABASE_URL cannot select participant data. Tests are headless and bounded. AUTO_VERIFIED remains a backward-compatible parser enum meaning structure-only; field/source review and internal Apply remain separate stages. No schema change or production activation is part of this repair.
