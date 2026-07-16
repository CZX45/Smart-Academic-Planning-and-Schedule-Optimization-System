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
- Browser-extension non-local staging imports require an entered bearer token,
  and the popup does not persist that token.
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

Status: Accepted

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

Install and upgrade preserve `%LOCALAPPDATA%\SAPSOS`, including the database,
pairing state, backups, migration evidence, and local Diagnostics state.
Uninstall removes application binaries but preserves that user data by default;
future destructive data removal requires an explicit, separately reviewed
choice. Code signing, auto-update, release publishing, cloud distribution,
telemetry, crash upload, and installer-level E2E are outside this foundation.
The current artifact is intentionally unsigned, and WebView2 bootstrapper
download behavior remains a clean-machine/network limitation until packaged
desktop E2E is completed.

