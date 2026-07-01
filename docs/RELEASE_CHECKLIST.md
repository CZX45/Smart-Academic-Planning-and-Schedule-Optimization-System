# Release Checklist

Phase 11B — Kean Student Portal Import uses this checklist
before a demo, handoff, or release-candidate review. It is not a production
deployment checklist and does not approve official institutional data use.

## Local Verification

- [ ] `corepack pnpm format`
- [ ] `git diff --check`
- [ ] `corepack pnpm lint`
- [ ] `corepack pnpm typecheck`
- [ ] `corepack pnpm test`
- [ ] `corepack pnpm build`
- [ ] `corepack pnpm e2e`
- [ ] `corepack pnpm openapi:generate`
- [ ] `corepack pnpm openapi:check`
- [ ] `python -m ruff check apps/api`
- [ ] `python -m ruff format --check apps/api`
- [ ] `cd apps/api && python -m mypy .`
- [ ] `cd apps/api && python -m pytest`

## CI Verification

- [ ] Alembic migrations run with `cd apps/api && python -m alembic upgrade head`.
- [ ] Alembic drift check runs with `cd apps/api && python -m alembic check`.
- [ ] Docker Compose validates configuration.
- [ ] Docker Compose starts API, web, and database services.
- [ ] API `/health` and `/ready` pass in CI.
- [ ] Web root page responds in CI.
- [ ] Development seed is idempotent in CI.

## No-Secrets Review

- [ ] No `.env` file is committed.
- [ ] No real school account password is committed.
- [ ] No portal token, SAML token, MFA secret, session cookie, or production
  database secret is committed.
- [ ] No real student record dump is committed.
- [ ] Logs and docs avoid raw imported academic content, raw HTML, credentials,
  tokens, passwords, and full student data.

## Browser Extension Permission Review

- [ ] Manifest version remains 3.
- [ ] Permissions remain limited to `activeTab`, `scripting`, and `storage`.
- [ ] No broad `host_permissions` are added.
- [ ] The Kean host permission is optional and limited to
  `https://kean-ss.colleague.elluciancloud.com/*`.
- [ ] Kean extraction code enforces
  `https://kean-ss.colleague.elluciancloud.com/Student/*` and configured page
  definitions.
- [ ] Extraction remains user-triggered.
- [ ] Preview and explicit confirmation remain required before sending data.
- [ ] Extension remains local-development only unless a future review approves
  publication.

## Prohibited Automation Review

- [ ] No credential capture.
- [ ] No password-field extraction.
- [ ] No SAML/MFA/CAPTCHA bypass.
- [ ] No portal form submission.
- [ ] No background scraping.
- [ ] No polling.
- [ ] No automatic registration.
- [ ] No add/drop/swap automation.
- [ ] No waitlist automation.
- [ ] No seat reservation.
- [ ] No seat grabbing.
- [ ] No browser-store publishing.
- [ ] No hidden automation.
- [ ] No external telemetry without explicit approval.
- [ ] No real production deployment without explicit approval.

## Documentation Review

- [ ] `README.md` reflects current phase status and links release QA docs.
- [ ] `docs/ARCHITECTURE.md` describes the release-readiness boundary.
- [ ] `docs/DOMAIN_RULES.md` keeps Phase 10A hard rules explicit.
- [ ] `docs/SECURITY_AND_PRIVACY.md` includes final safety boundary review.
- [ ] `docs/TEST_STRATEGY.md` includes release-readiness QA coverage.
- [ ] `docs/ROADMAP.md` marks completed phases consistently.
- [ ] `docs/DECISIONS.md` records the current phase decision.
- [ ] `docs/RELEASE_READINESS_QA.md` covers the main user journeys.
- [ ] `docs/DEMO_SCENARIOS.md` uses demo-safe wording.

## Demo Scenario Review

- [ ] Data import review and confirmation scenario uses non-official wording.
- [ ] Browser extension scenario describes read-only imported data and user action.
- [ ] Kean import scenario describes manual portal login, optional permission,
  preview, confirmation, non-official import status, and Phase 7B review.
- [ ] Section monitoring scenario describes advisory alerts and manual review required.
- [ ] Dashboard scenario shows status cards, empty states, and manual next actions.
- [ ] Schedule optimization scenario explains snapshots, warnings, and repair
  suggestions.
- [ ] Security/privacy scenario explains no credential storage, no portal automation,
  and no production deployment.
- [ ] Every scenario reminds users to verify in the official portal for high-impact
  actions.

## Known Local Limitations

- [ ] Mock seed data is not official school policy.
- [ ] Browser extension workflows are local-development only.
- [ ] Docker-dependent checks require local Docker or CI.
- [ ] Production FERPA controls, institutional data agreements, deletion/export
  workflows, and advisor access controls remain future work.
- [ ] Official portal status and school policy must be confirmed outside the app.
