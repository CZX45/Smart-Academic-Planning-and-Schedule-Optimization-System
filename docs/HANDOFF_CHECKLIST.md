# Handoff Checklist

Use this checklist when preparing the repository for demo, review, or a future
development phase.

## Repository Status

- Confirm the current branch and latest commit:

```bash
git status
git branch --show-current
git log -1 --oneline
```

- Confirm the working tree only contains intended current-phase changes before
  committing.
- Confirm no `.env`, credential, token, portal export with sensitive student
  data, or production secret is staged.

## Branch and PR Workflow

- For Phase 11B Kean import work, use
  `codex-phase-11b-kean-student-portal-import`.
- Commit with:

```bash
git add -A
git commit -m "Implement phase 11b Kean student portal import"
```

- Push with:

```bash
git push -u origin codex-phase-11b-kean-student-portal-import
```

- Open a draft PR into `main`.
- Do not mark the PR ready for review until CI passes.
- Do not merge the current-phase PR during handoff.

## Local Setup Commands

```bash
corepack enable
pnpm install --frozen-lockfile
python -m pip install -e "apps/api[dev]"
cp .env.example .env
```

For local mixed development:

```bash
pnpm dev
```

For full Docker development:

```bash
pnpm dev:docker
```

## Verification Commands

Run as many as the local environment supports:

```bash
corepack pnpm format
git diff --check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm e2e
corepack pnpm openapi:generate
corepack pnpm openapi:check
python -m ruff check apps/api
python -m ruff format --check apps/api
cd apps/api && python -m mypy .
cd apps/api && python -m pytest
```

If a command cannot run locally, record the exact command, the exact blocker,
and whether CI is expected to cover it.

## CI Checks

- Confirm the PR is draft.
- Record CI status, failing job names, and failing commands if any.
- Fix deterministic failures with the smallest necessary change.
- Do not weaken tests, lint, type checks, OpenAPI checks, migration checks, or
  safety wording guards.

## Docs to Read First

- [Final Project Summary](FINAL_PROJECT_SUMMARY.md)
- [Final Demo Script](FINAL_DEMO_SCRIPT.md)
- [Feature Inventory](FEATURE_INVENTORY.md)
- [Final Architecture Snapshot](FINAL_ARCHITECTURE_SNAPSHOT.md)
- [Known Limitations and Future Work](KNOWN_LIMITATIONS_AND_FUTURE_WORK.md)
- [Final Safety and Non-Automation Statement](FINAL_SAFETY_AND_NON_AUTOMATION_STATEMENT.md)
- [Release Readiness QA](RELEASE_READINESS_QA.md)
- [Demo Scenarios](DEMO_SCENARIOS.md)
- [Release Checklist](RELEASE_CHECKLIST.md)
- [Kean Student Portal Import Guide](KEAN_STUDENT_PORTAL_IMPORT_GUIDE.md)

## Demo Preparation

- Use mock or reviewed non-official data only.
- Prepare a short path through import review, degree audit, eligibility,
  schedule optimization, extension import, monitoring alerts, and dashboard
  status cards.
- Keep the demo within 5-8 minutes unless reviewers ask for implementation
  details.
- Use safe terms: imported snapshot, read-only import, advisory alert, manual
  review required, non-official data, and verify in the official portal.

## Safety Review

Confirm no current-phase work added:

- credentials or secrets;
- password-field extraction;
- SAML/MFA bypass;
- portal scraping beyond user-triggered visible-page import;
- unsupported Kean portal scanning beyond
  `https://kean-ss.colleague.elluciancloud.com/Student/*`;
- portal polling;
- portal form submission;
- course registration, drop, swap, waitlist, seat hold, or seat-taking actions;
- hidden automation;
- browser-store publishing;
- external telemetry;
- production deployment.

## Known Limitations

- Docker/PostgreSQL, browser QA, and Playwright can depend on local machine
  capabilities.
- Imported data and monitoring snapshots are non-official.
- Section monitoring depends on user-triggered imports.
- Production account/auth, data deletion/export, observability, deployment, and
  institutional review remain future work.

## Recommended Next Phases

- Production account/auth and authorization.
- Data deletion/export and retention controls.
- Institutional review and source-ingestion governance.
- Accessibility and usability review.
- More fixture coverage and domain-rule edge cases.
- Low-sensitivity observability and deployment runbooks.
