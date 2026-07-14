# Reviewed Program/Catalog Rules (Stage 10A)

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

Consumption by Degree Audit and Eligibility is reserved for Stage 10B after
the reviewed-rule persistence boundary is merged.

All Stage 10A fixtures are synthetic and are not institutional policy.
