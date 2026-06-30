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
- Avoid credential storage, password-field reading, SAML/MFA/CAPTCHA bypass, registration, drop, swap, waitlist, seat-grabbing, or form-submit automation.

## 5. Data Accuracy Risk

Academic requirements are high-impact. Incorrect results may delay graduation, affect tuition, or cause registration mistakes. Mitigations:

- Store source metadata for every official rule.
- Display confidence levels.
- Separate mock, student-entered, inferred, advisor-confirmed, and official data.
- Require advisor confirmation messaging for high-risk results.
- Treat academic plans as advisory course-level snapshots; never convert them into add/drop/swap, waitlist, seat-grabbing, or registration actions.
- Treat Phase 7A data imports as staging-only previews. Do not mark imported data official, and do not apply it to transcript, catalog, section, requirement, seat, waitlist, or registration tables.
- Treat Phase 7B review applications as explicit, audited, non-official internal planning writes. Confirmed unofficial transcript course attempts may create `student_course_attempts` with `is_official = false`, source metadata, duplicate checks, and applied-record logs. Do not use Phase 7B to create official transcript, catalog, section, seat, waitlist, advisor-approval, or registration state.
- Treat Phase 8A browser-extension imports as visible-page staging extracts with `source_type = BROWSER_EXTENSION`, `is_official = false`, and required Phase 7B review. Do not store raw HTML by default, do not read password fields, and do not claim extracted rows are official school policy.
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

## 7. Threats and Mitigations

| Threat | Mitigation |
| --- | --- |
| Credential theft | Never collect credentials; avoid storing cookies/tokens. |
| Overbroad extension access | Use narrow permissions and user-triggered extraction. |
| Incorrect academic advice | Source versioning, confidence levels, advisor-confirmation warnings, tests. |
| Unauthorized advisor access | Role-based access control and audit logging. |
| Data leakage in logs | Structured logging with redaction. |
| Prompt or fixture confusion | Clearly label mock data and never call it official. |
| Excessive school-system requests | No high-frequency polling; backoff and user-controlled refresh. |
| Imported data mistaken for official policy | Keep Phase 7A imports in staging tables, force `official_application_ready = false`, emit preview disclaimers, require Phase 7B review decisions, keep applied planning records non-official, and require advisor/school confirmation. |
| Review application creates unsafe records | Allow application only through explicit POST, support dry-run with no domain writes, skip unsupported/duplicate/advisor-review records with reason codes, and audit every applied or skipped record. |
| Browser extension overreach | Keep permissions minimal, avoid host permissions, require user action and confirmation, extract visible table text only, do not store credentials or raw HTML by default, and keep all data in staging import until review. |

## 8. Compliance Considerations

Future deployment may need FERPA-aware handling, institutional data agreements, retention policies, and advisor access controls. The MVP should be designed so these controls can be added without reworking core data boundaries.
