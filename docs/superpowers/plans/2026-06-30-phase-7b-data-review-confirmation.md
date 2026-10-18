# Phase 7B Data Review And Confirmation

## Scope
- Keep Phase 7A imports as staging data until an explicit review application POST.
- Add review sessions, per-record review decisions, application runs, applied-record logs, and review warnings.
- Support confirmed unofficial transcript course attempts being applied into internal student course attempts with source metadata and duplicate prevention.
- Keep catalog, requirement, section, and section-meeting imported records reviewable but not automatically applied unless a safe mapped target is implemented and tested.
- Expose dry-run application results without writing domain records.
- Add a focused frontend review panel for mock imports and make uncertainty visible.

## Implementation Steps
1. Add failing backend tests for review creation, decision updates, dry-run behavior, real application, duplicate skips, and API endpoints.
2. Add Phase 7B SQLAlchemy models, enums, and an independent Alembic migration after Phase 7A.
3. Implement `DataReviewApplicationService` under `apps/api/app/services/data_review/`.
4. Add Pydantic schemas and `/api/v1` data-review routes.
5. Add shared TypeScript schemas/client helpers and unit tests.
6. Add the web data review panel and Playwright coverage using mocked APIs.
7. Add deterministic mock seed records for review, warnings, dry-run/application outcomes, duplicates, unsupported data, and advisor-review cases.
8. Update architecture/data/testing/security docs.
9. Run required quality gates, push the branch, create a Draft PR, then monitor CI and fix real failures.

## Boundaries
- No Phase 7B PR auto-merge.
- No browser extension work.
- No real school login, scraping, auto-registration, waitlist, seat grabbing, or high-frequency polling.
- No mutation from GET endpoints.
