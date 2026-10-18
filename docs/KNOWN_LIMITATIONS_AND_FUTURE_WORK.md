# Known Limitations and Future Work

This document records the current Phase 10B limitations and recommended next
work. It is intended for handoff planning, not as a production launch checklist.

## Current Limitations

- Local Docker/PostgreSQL may not be available in every reviewer environment.
- Browser QA may be limited by local server setup, browser policy, or extension
  installation policy.
- Imported data is non-official unless a future reviewed official-source
  workflow says otherwise.
- Section monitoring depends on user-triggered imports and manual review.
- No real production deployment is included.
- No real school portal integration exists beyond user-triggered visible-page
  extraction and staging import.
- No browser-store publishing is included.
- No full production authentication/account system is included unless a future
  phase adds one.
- No automated registration actions, add/drop actions, swap actions, waitlist
  actions, portal submission, seat holds, or seat-taking behavior are included.
- Mock fixtures are intentionally limited and do not represent comprehensive
  school policy.
- Accessibility review has not been completed as a formal audit.
- Observability is limited and should avoid sensitive student data.

## Future Work

- Add a stronger account/auth layer with tenant, institution, role, and data
  ownership controls.
- Add student data deletion and export controls before production use.
- Create a production deployment plan with environment, migration, rollback,
  backup, and incident-response procedures.
- Expand real-world fixture coverage while preserving source metadata,
  confidence levels, and review status.
- Run a formal accessibility review of dashboard, import, planning, schedule,
  and extension flows.
- Improve low-sensitivity observability for API health, job health, migration
  status, and client error reporting after explicit approval.
- Add institution-specific mapping tools for catalog, transcript, program, and
  section formats.
- Review optional browser-store packaging only if the extension remains
  read-only and user-triggered.
- Add richer advisor-facing review workflows and comments.
- Add more optimizer tests for edge cases, infeasibility explanations, and
  preference tradeoffs.

## Production Readiness Before Real Use

Before using real student records or institution-provided data, complete:

- Institutional security and privacy review.
- FERPA or equivalent data-governance review where applicable.
- Threat modeling for authentication, authorization, data retention, imports,
  logging, and deployment.
- Accessibility and usability review.
- Legal and policy review for school-specific data sources.
- Clear support/runbook ownership for operations and incident response.

High-impact academic guidance must remain advisory and must be confirmed with
the school or an advisor.
