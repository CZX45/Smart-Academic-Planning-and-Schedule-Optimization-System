# Reviewed Program/Catalog Rules (Stage 10A/10B)

Stage 10A establishes the source and review contract for Program and Course
Catalog rules. It is separate from Degree Audit and Eligibility; the
validation endpoint is staging-only and cannot change academic results.

The repository currently contains synthetic/mock catalog and program data, but
no reviewed official Program/Catalog source inventory. Stage 10A therefore
does not claim real WKU, Kean, or any other institution's policy coverage.
Production onboarding requires a public institutional source, catalog year or
effective term, source location, short evidence excerpt, retrieval timestamp,
and a reviewed fingerprint. MyProgress may identify a visible program and
catalog year, but is not a complete authoritative catalog source.

The typed contract represents source identity, versioned courses, bounded
requirement primitives, explicit unsupported statements, and lifecycle states:
`DRAFT`, `REQUIRES_REVIEW`, `REVIEWED`, `ACTIVE`, `SUPERSEDED`, `RETIRED`, and
`REJECTED`. Supported operators are `REQUIRED_COURSE`, `ALL_OF`, `ANY_OF`,
`CHOOSE_N`, and `MINIMUM_CREDITS`. Unknown courses, duplicate IDs, invalid
cardinality, contradictory credits, and missing evidence are invalid.

Review and activation are separate explicit transitions. Draft and inactive
rules cannot affect Degree Audit or Eligibility. Exact catalog-year selection
returns no result when the requested reviewed active version is absent; it
never falls back to the newest year. Unsupported natural-language policy
remains visible and requires manual review.

The staging API is intentionally separate from academic consumers:

- `POST /api/v1/reviewed-rule-sets` persists a draft payload;
- `POST /api/v1/reviewed-rule-sets/validate` validates without persistence;
- `POST /api/v1/reviewed-rule-sets/{id}/review` requires explicit review;
- `POST /api/v1/reviewed-rule-sets/{id}/activate` requires reviewed state and
  preserves/supersedes an existing active version explicitly.

Stage 10B now consumes only an exact `ACTIVE` match on institution code,
program code, and catalog year. It does not select a newest-year fallback.
Degree Audit overlays only the bounded reviewed requirement primitives onto
the existing requirement graph and records the selected rule-set ID, source,
catalog year, and resolution explanation. Eligibility uses the bounded
reviewed prerequisite/corequisite declarations and persists each reviewed
reason with the same provenance. If a reviewed course definition is absent or
an identifier cannot be resolved, the result is `UNKNOWN` and requires advisor
confirmation; it must not become `ELIGIBLE`. Conflicting active records are a
manual-review error. When no active reviewed set exists, the legacy engine
remains available but the run is explicitly marked `MISSING`.

The reviewed integration is advisory and read-only. It does not register,
add/drop, swap, waitlist, poll, or mutate school systems.

All Stage 10A/10B fixtures are synthetic and are not institutional policy.
