# Smart Academic Planning and Schedule Optimization System

A planned full-stack system for intelligent academic planning, degree-progress analysis, and section-level schedule optimization. The initial target is Kean University / Wenzhou-Kean University with first-priority support for BS Finance, but the architecture is intentionally school-agnostic and program-agnostic.

> Current repository status: documentation-first foundation. This phase defines product scope, architecture, domain model, security posture, roadmap, and test strategy. It does **not** implement the full application yet.

## Problem Statement

Students often need to combine catalog requirements, four-year plans, curriculum sheets, My Progress data, term offerings, prerequisites, campus policies, and personal preferences. A simple "courses not yet taken" checklist is insufficient because one course can satisfy different requirement buckets, requirements may overlap, prerequisites form chains, registration restrictions vary by section, and schedule feasibility depends on exact meeting times.

This system aims to answer:

- What graduation requirements are truly unsatisfied?
- Which completed, in-progress, planned, transferred, waived, or failed courses count toward which requirements?
- Can a student add a minor, second major, concentration, or certificate without delaying graduation?
- What multi-semester plan is feasible and explainable?
- Which actual sections produce legal schedules matching student preferences?
- Why is no schedule possible, and what minimal constraint relaxation would help?

## Target Users

- Undergraduate students planning degree completion.
- Academic advisors reviewing student plans.
- Future administrators maintaining versioned program rules and course catalogs.

## MVP Focus

The MVP is a planner and advisor-support tool, not a registration bot. It will use verified data when available and otherwise clearly labeled mock fixtures.

MVP capabilities:

1. Import or manually enter a student's course history and current/planned courses.
2. Represent versioned degree requirements as rule trees.
3. Evaluate degree progress with explainable requirement allocation.
4. Represent prerequisites and restrictions as expression trees.
5. Generate a draft multi-semester academic plan from available fixture offerings.
6. Generate legal section schedules from fixture section data and user preferences.
7. Flag conflicts, eligibility issues, credit overloads, and high-risk assumptions.

## Non-Goals for First Version

- Automatic registration, add/drop, waitlist, or seat grabbing.
- Storing school credentials.
- Bypassing school authentication.
- Claiming mock or inferred rules are official school policy.
- High-frequency polling of school systems.

## Proposed Monorepo Layout

```text
apps/
  web/                 # Next.js student/advisor UI
  api/                 # FastAPI backend
  extension/           # Chrome MV3 extension for user-authorized page extraction
packages/
  shared/              # Shared TypeScript types and API clients
  fixtures/            # Mock catalogs, programs, transcripts, and sections
  config/              # Shared lint/test/TS config
services/
  optimizer/           # Python optimization domain modules, initially inside API or library
infra/
  docker/              # Dockerfiles and local support files
docs/                  # Product, architecture, data, rule, privacy, roadmap, and test docs
```

The repository is currently empty apart from the documentation created in this phase, so this layout is a proposal for the next implementation milestone.

## Documentation Index

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Domain Rules](docs/DOMAIN_RULES.md)
- [Security and Privacy](docs/SECURITY_AND_PRIVACY.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Architecture Decisions](docs/DECISIONS.md)

## Development Baseline

Recommended local toolchain for the next implementation phase:

- Node.js LTS with pnpm.
- Python 3.12+.
- Docker and Docker Compose.
- PostgreSQL 16+ via Docker Compose.
- Ruff, mypy, pytest for Python.
- ESLint, TypeScript strict mode, Vitest, Playwright for TypeScript.

## Required Real School Materials

Development can continue with fixtures, but official accuracy eventually requires:

- Catalog PDFs or web pages for each supported catalog year.
- BS Finance curriculum sheets and four-year plans.
- Degree requirements and GE requirements.
- Course descriptions, credits, prerequisites, corequisites, grade minimums, repeat rules, and restrictions.
- Section schedule data for target terms.
- Policies for transfer credit, waivers, substitutions, residency, upper-level credits, GPA, and minors.
- Example anonymized My Progress outputs.

All official data must be source-tagged and versioned.
