# Final Safety and Non-Automation Statement

The Smart Academic Planning and Schedule Optimization System is a read-only and
advisory planning platform. It helps users review academic progress, imported
data, eligibility, plans, schedule options, and section-change alerts. It does
not act inside school systems.

## Allowed Model

```text
User-triggered read-only import -> manual review -> advisory planning/alerts -> manual verification in official portal.
```

This means a user may choose to import visible or provided data, review it,
apply supported non-official records to internal planning state, and use
advisory outputs to decide what to check manually.

## Explicit Non-Automation Boundary

The system:

- does not store portal credentials;
- does not extract password fields;
- does not bypass SAML/MFA;
- does not scrape in background;
- does not poll portals;
- does not submit portal forms;
- does not register for courses;
- does not drop courses;
- does not swap courses;
- does not join waitlists;
- does not reserve seats;
- does not grab seats;
- does not publish the extension to a browser store;
- does not bypass school systems.

## Data and Source Boundary

Imported records, browser-extension rows, and section monitoring snapshots are
non-official unless a future reviewed workflow explicitly changes that status.
They must keep source references, source type, timestamps, warnings, and review
state visible.

## User Responsibility

Students and advisors should treat outputs as advisory planning support. Before
making high-impact choices, users must verify in the official portal and, when
appropriate, confirm with the school or an advisor.

## Future Changes

Any future feature that touches credentials, official school systems, external
telemetry, production deployment, or enrollment-affecting workflows requires a
new design review, security review, and explicit approval before implementation.
