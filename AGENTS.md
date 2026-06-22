# AGENTS.md

## Scope
These instructions apply to the entire repository.

## Project Mission
Build the Smart Academic Planning and Schedule Optimization System as a multi-school, multi-program academic planning platform. Do not hard-code Kean University, Wenzhou-Kean University, BS Finance, or any single catalog into core business logic.

## Architecture Principles
- Model `Course` and `Section` as separate entities.
- Model degree requirements as versioned rule trees, not static course lists.
- Model prerequisites, corequisites, restrictions, and eligibility as composable logical expression trees.
- Keep the Academic Plan Optimizer separate from the Semester Schedule Optimizer.
- Preserve explainability for every recommendation, warning, and optimization decision.
- Treat institution, campus, catalog year, effective term, and program version as first-class versioning dimensions.
- Use mock data and fixtures when verified school source data is unavailable. Never present fixture data as official school policy.

## Privacy and Safety Rules
- Do not store school account passwords.
- Do not bypass SAML, MFA, CAPTCHA, rate limits, or school authentication controls.
- Browser extension work must be limited to pages the user has already logged into and actively opened.
- The first version must not register, drop, swap, or waitlist courses automatically.
- High-risk academic guidance must tell the student to confirm with the school or an advisor.

## Preferred Stack
- Monorepo: pnpm workspace / Turborepo.
- Frontend: Next.js, TypeScript, Tailwind CSS.
- Backend: FastAPI, Python, Pydantic, SQLAlchemy.
- Database: PostgreSQL.
- Optimization: Google OR-Tools CP-SAT.
- Browser extension: Chrome Extension Manifest V3, TypeScript.
- Testing: pytest, Vitest, Playwright.
- Quality: Ruff, mypy, ESLint, TypeScript strict mode.

## Development Practices
- Keep documentation and implementation aligned.
- Add tests for every implemented rule, parser, optimizer constraint, and API boundary.
- Prefer fixtures and deterministic unit tests before integrating real school data.
- Do not introduce import-level try/catch blocks.
- Use `rg` instead of recursive grep, and do not use `ls -R`.

## Pull Request Notes
PR descriptions should include:
1. Summary of changes.
2. Testing performed.
3. Known risks or follow-up work.
4. Whether any mock data was added or changed.
