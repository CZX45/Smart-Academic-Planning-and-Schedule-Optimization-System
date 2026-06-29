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

## 3. Credential Policy

The system must never ask users to provide school passwords. Browser extension functionality, when implemented, must operate only on pages the user has already opened after authenticating directly with the school.

## 4. Browser Extension Constraints

The extension must:

- Use Chrome Extension Manifest V3.
- Require explicit user action before reading page content.
- Read only currently active, user-opened pages needed for import.
- Show a preview before sending extracted data to the backend.
- Avoid background scraping.
- Avoid high-frequency polling.
- Avoid registration, drop, swap, waitlist, or form-submit automation.

## 5. Data Accuracy Risk

Academic requirements are high-impact. Incorrect results may delay graduation, affect tuition, or cause registration mistakes. Mitigations:

- Store source metadata for every official rule.
- Display confidence levels.
- Separate mock, student-entered, inferred, advisor-confirmed, and official data.
- Require advisor confirmation messaging for high-risk results.
- Treat academic plans as advisory course-level snapshots; never convert them into add/drop/swap, waitlist, seat-grabbing, or registration actions.
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

## 8. Compliance Considerations

Future deployment may need FERPA-aware handling, institutional data agreements, retention policies, and advisor access controls. The MVP should be designed so these controls can be added without reworking core data boundaries.
