# Security and Privacy

## 1. Guiding Principles

- Collect the least student data needed to provide planning guidance.
- Do not store school account passwords, SAML tokens, MFA secrets, or session cookies.
- Do not bypass authentication or school access controls.
- Keep student records private by default.
- Mark every recommendation with confidence and source context.

## 2. Sensitive Data

Potentially sensitive data includes:

- Student identity and contact information.
- Student ID or school identifier.
- Course history, grades, GPA, transfer credits, waivers, and academic standing.
- Declared majors, minors, certificates, and expected graduation term.
- Advisor notes and review comments.
- Browser-extension extracted page content.
- Data import preview content, normalized imported payload snippets, mapping candidates, and validation warnings.

## 3. Credential Policy

The system must never ask users to provide school passwords. Browser extension functionality, when implemented, must operate only on pages the user has already opened after authenticating directly with the school.

## 4. Browser Extension Constraints

The extension must:

- Use Chrome Extension Manifest V3.
- Require explicit user action before reading page content.
- Read only currently active, user-opened pages needed for import.
- Show a preview before sending extracted data to the backend.
- Send confirmed data only as non-official staging import data.
- Avoid background scraping.
- Avoid high-frequency polling.
- Avoid credential storage, password-field reading, SAML/MFA/CAPTCHA bypass, registration, drop, swap, waitlist, seat-state automation, or form-submit automation.

## 5. Data Accuracy Risk

Academic requirements are high-impact. Incorrect results may delay graduation, affect tuition, or cause registration mistakes. Mitigations:

- Store source metadata for every official rule.
- Display confidence levels.
- Separate mock, student-entered, inferred, advisor-confirmed, and official data.
- Require advisor confirmation messaging for high-risk results.
- Treat academic plans as advisory course-level snapshots; never convert them into add/drop/swap, waitlist, seat-state automation, or registration actions.
- Treat Phase 7A data imports as staging-only previews. Do not mark imported data official, and do not apply it to transcript, catalog, section, requirement, seat, waitlist, or registration tables.
- Treat Phase 7B review applications as explicit, audited, non-official internal planning writes. Confirmed unofficial transcript course attempts may create `student_course_attempts` with `is_official = false`, source metadata, duplicate checks, and applied-record logs. Do not use Phase 7B to create official transcript, catalog, section, seat, waitlist, advisor-approval, or registration state.
- Treat Phase 8A browser-extension imports as visible-page staging extracts with `source_type = BROWSER_EXTENSION`, `is_official = false`, and required Phase 7B review. Do not store raw HTML by default, do not read password fields, and do not claim extracted rows are official school policy.
- Treat Phase 8B section monitoring as advisory comparison of user-triggered non-official snapshots. Do not run background polling, refresh school pages automatically, alter seat or waitlist state, submit forms, or claim alerts are official portal status.
- Treat Phase 9A product-hardening UI as clarity-only work. Status cards, empty states, labels, and manual checklists must not add credential capture, portal submission, polling, background scraping, registration automation, waitlist automation, or seat-state changes.
- Treat Phase 9B as hardening-only work. Environment validation, safe HTTP headers, CORS tightening, audit logging, data-retention documentation, and safety regression tests must not add new academic authority, official imports, account systems, telemetry, registration automation, polling, portal submission, or deployment.
- Treat Phase 10A as release-readiness QA and final product review only. Release docs, demo scenarios, checklist review, and safety audit must not add new academic authority, official imports, account systems, telemetry, registration automation, polling, portal submission, credential handling, or deployment.
- Maintain regression fixtures for every catalog/program version.

## 6. Privacy Controls

Recommended controls:

- User-owned planning sessions.
- Role-based access for student, advisor, and administrator roles.
- Encrypted transport.
- Encryption at rest for sensitive fields where appropriate.
- Audit logs for advisor/admin access.
- Data export and deletion workflows.
- Short retention for raw imported page snapshots.
- Prefer metadata-only storage for Phase 7A uploads. If a future workflow stores raw imported files or browser-extracted snapshots, enforce short retention, encryption, explicit user review, and source labels.
- Keep imported academic data user-triggered, non-official, and review-gated until a future reviewed official-source workflow exists.
- Plan future user-facing deletion/export controls for import runs, review decisions, generated planning snapshots, and browser-extension staging records before handling real institutional data.

## 7. Threats and Mitigations

| Threat                                            | Mitigation                                                                                                                                                                                                                             |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Credential theft                                  | Never collect credentials; avoid storing cookies/tokens.                                                                                                                                                                               |
| Overbroad extension access                        | Use narrow permissions and user-triggered extraction.                                                                                                                                                                                  |
| Incorrect academic advice                         | Source versioning, confidence levels, advisor-confirmation warnings, tests.                                                                                                                                                            |
| Unauthorized advisor access                       | Role-based access control and audit logging.                                                                                                                                                                                           |
| Data leakage in logs                              | Structured logging with redaction.                                                                                                                                                                                                     |
| Prompt or fixture confusion                       | Clearly label mock data and never call it official.                                                                                                                                                                                    |
| Excessive school-system requests                  | No high-frequency polling; backoff and user-controlled refresh.                                                                                                                                                                        |
| Imported data mistaken for official policy        | Keep Phase 7A imports in staging tables, force `official_application_ready = false`, emit preview disclaimers, require Phase 7B review decisions, keep applied planning records non-official, and require advisor/school confirmation. |
| Review application creates unsafe records         | Allow application only through explicit POST, support dry-run with no domain writes, skip unsupported/duplicate/advisor-review records with reason codes, and audit every applied or skipped record.                                   |
| Browser extension overreach                       | Keep permissions minimal, avoid host permissions, require user action and confirmation, extract visible table text only, do not store credentials or raw HTML by default, and keep all data in staging import until review.            |
| Section monitoring mistaken for live registration | Store only non-official advisory snapshots, require manual verification messaging, deduplicate imported snapshots, avoid background polling, and provide no portal-action endpoints or extension code.                                 |
| Misconfigured production environment              | Validate environment, database URL scheme, production database defaults, CORS origins, public API URL, and safe HTTP headers before serving traffic.                                                                   |
| Sensitive data leakage through logs               | Log low-sensitivity event metadata only: IDs, source type, import type, counts, statuses, and reason codes. Do not log raw import content, HTML, credentials, tokens, passwords, or full academic records.             |

## 8. Compliance Considerations

Future deployment may need FERPA-aware handling, institutional data agreements, retention policies, and advisor access controls. The MVP should be designed so these controls can be added without reworking core data boundaries.

## 9. Phase 9B Production Readiness Checklist

Before production-like deployment, confirm:

- `ENVIRONMENT` is explicit and is not accidentally left as `development`.
- `DATABASE_URL` is a PostgreSQL psycopg URL and does not use local development credentials in production.
- `CORS_ORIGINS` contains only explicit origins; production origins use HTTPS and are not localhost.
- `NEXT_PUBLIC_API_BASE_URL` is an `http` or `https` URL without embedded credentials.
- Database migrations and Alembic drift checks pass.
- OpenAPI generation and OpenAPI drift checks pass.
- Unit, integration, e2e, lint, typecheck, format, build, and Docker Compose checks pass.
- Browser extension permissions are manually reviewed for no broad host access and no background polling primitives.
- No `.env`, credential, portal secret, production database secret, real student record dump, or school password is committed.
- Security/privacy review confirms no registration automation, add/drop, swap, waitlist automation, seat reservation, seat grabbing, portal submission, scraping, polling, credential capture, hidden automation, or external telemetry was added.

## 10. Phase 10A Final Safety Boundary Audit

Before demo or handoff review, confirm:

- Release QA docs cover user journeys without treating mock, imported, inferred, or ambiguous data as official school policy.
- Demo scenarios use imported snapshot, advisory alert, manual review required, read-only imported data, non-official data, and verify in the official portal language.
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
- No real production deployment exists without explicit approval.
