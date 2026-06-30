# Domain Rules

## 1. Rule Philosophy

The system must evaluate academic requirements, not merely compare completed courses to missing course arrays. Requirements must be represented as reusable, versioned, explainable rule trees.

## 2. Degree Requirement Rule Tree

A requirement tree is composed of nodes such as:

- `all_of`: all children must be satisfied.
- `any_of`: at least one child must be satisfied.
- `min_credits`: a minimum credit total must be applied.
- `min_courses`: a minimum number of courses must be applied.
- `course_set`: specific courses or course groups.
- `course_attribute`: courses matching attributes such as GE category, upper-level, writing-intensive, major elective, or campus attribute.
- `level_requirement`: e.g., minimum upper-level credits.
- `gpa_requirement`: minimum GPA in a subset of courses.
- `residency_requirement`: credits that must be completed at a campus or institution.
- `manual_review`: requirement cannot be fully automated and must be advisor-confirmed.

Phase 2A stores requirement trees but does not evaluate them. The implemented storage uses relational `RequirementNode` rows with parent pointers and `RequirementCourseOption` rows for course-specific options. Stored nodes may express groups, required courses, all-of/any-of, choose-N, minimum credits/courses/grade, course level, residency, total credits, capstone, and exclusion concepts.

Phase 3A evaluates one `StudentProfile` against one `ProgramVersion` and persists a `DegreeAuditRun` snapshot. Every requirement node receives one `RequirementEvaluation`; unsupported or ambiguous configuration returns `MANUAL_REVIEW_REQUIRED` and a warning instead of being treated as satisfied.

## 3. Course Allocation

A course may be eligible for multiple requirement nodes. The evaluator should:

1. Build candidate requirement assignments for each eligible course.
2. Exclude failed or insufficient-grade courses unless a rule explicitly permits them.
3. Include transferred and waived records according to source and policy.
4. Optimize assignment based on requirement priority, graduation progress, overlap policies, and minimum extra credits.
5. Return explanations for chosen and rejected allocations.

Course allocation is deferred until the Degree Audit phase. Phase 2A does not mark requirements satisfied, does not apply transfer/waiver/substitution decisions, and does not choose between overlapping requirement candidates.

Phase 3A implements a deterministic baseline allocator, not a global optimizer. It evaluates stricter course-bearing requirements before broad credit pools, reserves a source record for one non-overlap requirement, and records `is_shared` when overlap is allowed. Total earned-credit summary is calculated separately from requirement applications so a shared course does not increase total credits twice. If local greedy allocation is ambiguous, Phase 3A emits advisor warnings and leaves advanced allocation to Phase 3B.

Phase 3B adds a deterministic bounded global allocator for what-if scenarios. It derives candidates from persisted Phase 3A audit applications, not from a second audit implementation. The allocator uses a lexicographic objective:

1. Maximize selected required requirement applications.
2. Prefer unique secondary credits when the requirement count is tied.
3. Maximize selected required credits.
4. Respect maximum shared-credit limits.
5. Minimize manual-review allocations.
6. Apply a stable tie-breaker using program priority, requirement order/code, course code, attempt number, and stable IDs.

If the search reaches its configured bound, the scenario records `ALLOCATION_SEARCH_LIMIT_REACHED` and reports the best found result instead of silently truncating.

Default retake policy:

- Preserve all attempts.
- Use the best valid completed attempt for the same course.
- Do not implement school-specific grade replacement.
- Do not count the same course twice for distinct-course requirements.
- Warn when multiple completed attempts make policy interpretation ambiguous.

Grade policy:

- The mock order is `A`, `A-`, `B+`, `B`, `B-`, `C+`, `C`, `C-`, `D+`, `D`, `D-`, `F`.
- Minimum-grade checks go through the centralized grade policy.
- `P`, `S`, and `CR` can satisfy requirements only when no letter minimum is configured; otherwise they require advisor review.
- `U`, `W`, `AU`, `NC`, `F`, and `I` do not satisfy completed-course requirements.
- Unknown grades produce warnings instead of being treated as passing.

Transfer, waiver, and substitution rules:

- Approved transfer credit can satisfy the equivalent course and adds earned credits.
- Pending transfer credit does not apply and produces a warning.
- Approved waivers can satisfy their target requirement but add no earned credits.
- Pending waivers do not apply and produce warnings.
- Approved substitutions apply only to their target program version and requirement, using the completed substitute course attempt.
- Rejected substitutions do not apply.
- Direct course equivalencies are used without computing an unlimited transitive closure.

What-if overlap rules:

- Requirement application means a course can satisfy a requirement in a specific program audit.
- Shared credit means one earned course source is used by requirements in more than one program.
- Total earned credit means the student earned the course credits once; shared application does not double total credits.
- Shared credit requires both `RequirementNode.allows_overlap = true` and a directional `ProgramCombinationRule` that allows double counting.
- `maximum_shared_credits` and `minimum_unique_secondary_credits` are evaluated from scenario allocations.
- Missing program-combination policy creates a manual-review warning; the system must not infer school policy.
- Waivers may satisfy requirements but do not add earned or shared credits.
- Approved transfers use the approved equivalent course; pending or rejected records do not participate.
- Approved substitutions apply only to their approved program requirement.

Estimated additional credits:

- `estimated_additional_credits` is a scenario summary estimate, not official policy.
- It is based on unresolved requirement credits and selected shared-credit effects from current completed/in-progress/planned records.
- It is never negative.
- It does not account for future section availability, prerequisite chains, course offering probability, tuition, GPA prediction, or graduation timing.
- Ambiguity produces warnings and advisor-confirmation flags.

Change-major scenarios:

- The current primary major remains the baseline.
- The candidate primary is hypothetical and does not update `StudentAcademicProgram`.
- Existing courses can be reusable for new program requirements, usable only as elective/total credits, or not directly applicable to the new major requirement tree.
- “Not used by the new major requirement” must not be presented as “wasted credits.”

## 4. Prerequisite and Restriction Expression Tree

Prerequisites, corequisites, and restrictions use logical expressions:

- `ALL`
- `ANY`
- `NOT`
- `COURSE_COMPLETED`
- `COURSE_IN_PROGRESS`
- `MIN_GRADE`
- `MIN_CREDITS_EARNED`
- `CLASS_STANDING`
- `MAJOR_IN`
- `PROGRAM_IN`
- `CAMPUS_IN`
- `MIN_GPA`
- `PLACEMENT_OR_PERMISSION`
- `ADVISOR_PERMISSION_REQUIRED`

The evaluator must distinguish:

- Satisfied.
- Not satisfied.
- Satisfied only if in-progress course is completed successfully.
- Unknown due to missing data.
- Requires manual permission or advisor confirmation.

Phase 2B stores these prerequisite, corequisite, restriction, repeat-restriction, and permission concepts as `CourseRule` records with relational `CourseRuleExpression` trees. A course-level rule has `course_id` and no `section_id`; a section-level rule also has `section_id` and must match the same course and institution. Prerequisites and corequisites share the same expression-tree shape so later evaluators can reason over both consistently.

Phase 2B does not answer whether a student is eligible for a course or section. It only returns stored rule metadata, source metadata, manual-confirmation flags, and expression-tree nodes. Any high-impact interpretation still requires official school or advisor confirmation when data is mock, inferred, student-provided, or ambiguous.

Phase 4 evaluates stored `CourseRuleExpression` trees for a selected student, course, optional section, target term, and explicit mode. It uses the centralized grade policy and the same student attempt/transfer status semantics as Degree Audit for completed evidence. In-progress and planned records can make a prerequisite or corequisite conditional in `PROJECTED` or `REGISTRATION` mode, but they are not treated as completed.

Course eligibility result priority is:

1. Hard unsatisfied prerequisite/restriction: `NOT_ELIGIBLE`.
2. Permission requirement with no hard failure: `PERMISSION_REQUIRED`.
3. In-progress, planned, or concurrent corequisite evidence: `CONDITIONALLY_ELIGIBLE`.
4. Missing or unsafe-to-automate evidence: `MANUAL_REVIEW_REQUIRED`.
5. All evaluated rules satisfied: `ELIGIBLE`.

Course-level and section-level rules are evaluated together. Section availability is reported separately as a snapshot (`OPEN`, `WAITLIST`, `CLOSED`, etc.) and must not be converted into academic eligibility. A waitlisted or closed section can still have academic eligibility `ELIGIBLE`; it simply has no currently available seat in that section snapshot.

Course offering patterns are historical or expected availability signals. They must not be presented as school commitments that a course will be offered in a future term.

## 5. Academic Plan Optimizer Rules

The Academic Plan Optimizer works at course level, not section level. It should consider:

- Remaining requirement needs.
- Prerequisite ordering.
- Course offering frequency assumptions.
- Credit minimum and maximum per term.
- Target graduation term.
- Student preferences and risk tolerance.
- Program simulations such as adding a minor or second major.

It should output:

- Planned courses by term.
- Requirements each course is expected to satisfy.
- Assumptions and risks.
- Explanation of why each course is placed in a term.

Phase 5A implements a deterministic baseline planner rather than a global mathematical optimizer. It creates persisted academic plan snapshots for `CURRENT_PROGRAM` and `WHAT_IF_SCENARIO` modes, derives remaining course candidates from Degree Audit results, and uses Course Eligibility to identify prerequisite, corequisite, permission, and manual-review constraints.

Phase 5A placement rules:

- Never place courses beyond the supplied maximum credits per term.
- Mark a term `PARTIAL` or `BLOCKED` when the requested minimum credits cannot be met.
- Place missing prerequisite courses in an earlier term when a stored prerequisite rule names a concrete course and credit limits allow it.
- Place required corequisite courses in the same term when credit limits allow it.
- Keep planned prerequisite evidence conditional; do not relabel a future course as completed.
- Prefer direct remaining requirements before broad or ambiguous requirements.
- Use stable tie-breakers from requirement order, requirement code, course code, and stable IDs.
- Record each placement with a source, planning status, reason code, and explanation.

Phase 5A availability rules:

- Existing sections can be used as evidence that a course has a term-specific offering snapshot.
- Closed or cancelled sections produce warnings but are not treated as academic impossibility.
- Offering patterns are assumptions, not school commitments.
- Missing or mismatched offering patterns produce warnings rather than authoritative claims that a course will or will not run.

Phase 5A safety boundaries:

- The planner does not select sections or build weekly schedules.
- The planner does not inspect time conflicts, instructor preferences, meeting locations, or commute times.
- The planner does not poll seats, join waitlists, register, add, drop, swap, or reserve courses.
- What-if plans may reference scenario snapshots but must not update official `StudentAcademicProgram` records.
- Mock, inferred, or ambiguous plan results must require advisor or school confirmation for high-impact decisions.

## 6. Semester Schedule Optimizer Rules

The Semester Schedule Optimizer works at section level. It should consider:

- Required or selected courses for one term.
- Sections and meeting times.
- Time conflicts.
- Commute or transition time between locations.
- User unavailable blocks.
- Earliest start and latest end preferences.
- No-Friday or limited-day preferences.
- Online/hybrid/in-person modality preferences.
- Instructor preferences.
- Backup sections and backup schedules.

Phase 6A implements a deterministic bounded baseline scheduler. Phase 6B extends that scheduler with advanced preference weights, course and section priorities, option diversity, and repair suggestions. A `Section` is a term-specific snapshot for a `Course`; a `SectionMeeting` stores one meeting component such as lecture, lab, seminar, exam, arranged, or online asynchronous work.

Phase 6A hard rules:

- Build schedules for one student and one term at a time.
- Keep academic planning separate from section scheduling; schedule runs may reference a long-term plan, but they select concrete sections only for the requested term.
- Never select two sections for the same course in one option.
- Never select sections whose required meetings overlap.
- Never select a section that intersects a hard unavailable block.
- Never select a section on an excluded day.
- Never select an excluded section.
- Never ignore a required section; if the required section is invalid, unavailable, or conflicts with another hard rule, report infeasibility or a partial option with a repair suggestion.
- Never exceed the hard maximum credit limit.
- Treat closed, waitlisted, cancelled, or unknown seat data as warnings or conflicts, not as permission to perform registration actions.
- Use Course Eligibility in `REGISTRATION` mode; `NOT_ELIGIBLE`, permission-required without explicit permission allowance, and manual-review results block automatic option selection.
- Record every rejected section or infeasible condition as a `ScheduleConflict` or `ScheduleWarning` when it affects the result.

Phase 6A preference rules:

- Prefer schedules closer to the preferred credit target.
- Prefer compact schedules when requested.
- Prefer fewer class days when requested.
- Prefer lower gap minutes when requested.
- Prefer morning or afternoon schedules only as soft preferences.
- Prefer online or in-person modalities only as scoring preferences unless the request supplies modality filters.
- Apply course priority weights and section priority weights as soft score components; invalid, unknown, or negative weights are rejected at the API/service boundary.
- Penalize early starts and late endings when requested.
- Return a score breakdown with credit, compactness, day-count, gap, modality, time-of-day, priority, and penalty components.
- In high-diversity mode, choose returned options with deterministic stable tie-breakers while reducing repeated selected sections across adjacent ranked options.
- Use stable tie-breakers so identical inputs produce the same option order.

Phase 6B repair suggestions:

- Repair suggestions are structured explanations for how a user or advisor might relax constraints; they do not perform registration, add/drop, swap, waitlist, seat monitoring, or portal actions.
- Suggestions may include relaxing an unavailable block, allowing an excluded day, removing a required section, allowing permission-required sections, reducing a credit target, or enabling partial options.
- A repair suggestion must include a reason code, explanation, estimated impact, and source constraint or conflict when available.

Phase 6A safety boundaries:

- The optimizer uses a bounded deterministic implementation behind an optimizer interface. It does not use OR-Tools in Phase 6B.
- The optimizer does not poll, refresh, reserve, or monitor seats.
- The optimizer does not register, add, drop, swap, waitlist, or suggest automated portal actions.
- Mock, inferred, ambiguous, or stale schedule data must require advisor or school confirmation for high-impact choices.

## 7. Infeasibility Explanations

When no valid result exists, the system should identify minimal blocking causes such as:

- No offered section for a required course.
- All sections conflict with another required course.
- User unavailable time blocks eliminate all sections.
- Credit maximum too low for graduation target.
- Prerequisite chain prevents desired timing.
- Campus or major restriction blocks registration.
- Section is full, cancelled, or waitlist-only.

It should propose minimal relaxations, for example:

- Allow Friday classes.
- Increase latest end time by one hour.
- Permit one online section.
- Move a course to a later term.
- Reduce target credit load.
- Ask advisor about permission/substitution.

## 8. Advisor Confirmation Rules

The system must recommend advisor confirmation for:

- Waivers, substitutions, transfer equivalencies, and manual exceptions.
- Adding a minor, double major, certificate, or concentration when overlap policies are unclear.
- Graduation eligibility decisions with missing official source data.
- GPA, residency, or upper-level credit calculations that depend on ambiguous policy.
- Any high-impact recommendation that may delay graduation or increase tuition.

Phase 3A specifically emits advisor-confirmation warnings for pending transfers, pending waivers, pending substitutions, repeated-course ambiguity, unsupported requirement scopes, missing requirement configuration, unknown/incomplete grades, and mock data that is not official policy.

Phase 3B additionally emits advisor-confirmation warnings for missing directional program-combination rules, unclear overlap policy, unmet unique-secondary-credit expectations, allocation search limits, and estimated additional credits.

Phase 4 additionally emits advisor-confirmation warnings for mock eligibility estimates, missing stored course restrictions, rules marked for manual confirmation, unknown or unsupported expression nodes, ambiguous campus/program restrictions, and permission requirements.

Phase 5A additionally emits advisor-confirmation warnings for mock plan estimates, broad requirements without concrete candidate courses, unplaced requirements, missing or uncertain offering patterns, credit-limit or horizon shortfalls, closed/cancelled section snapshots, and planner assumptions that could affect graduation timing.

Phase 6A additionally emits advisor-confirmation warnings for mock schedule data, missing or ambiguous section restrictions, eligibility estimates, permission-required sections, unavailable or conflicting sections, bounded-search limits, credit shortfalls, and any schedule recommendation based on non-official section snapshots. Phase 6B carries those warnings forward and adds structured repair suggestions when a hard constraint or preference set prevents a fully feasible schedule.

## 11. Read-only Data Import Preview Rules

Phase 7A stages mock or student-provided academic data for review. It supports bounded CSV/JSON previews for unofficial transcripts, degree-audit exports, course catalogs, section schedules, and generic records.

Phase 7A hard rules:

- Imported rows are staging records only.
- Every import run must preserve source type, source reference where available, parser version, file metadata, checksum, import type, status, record counts, warnings, and preview disclaimers.
- `official_application_ready` must remain false.
- Official-source imports are rejected until a later reviewed import workflow exists.
- Imported rows must not create, update, or delete `StudentCourseAttempt`, `TransferCredit`, `Course`, `Section`, `RequirementNode`, degree-audit, planner, schedule, registration, seat, or waitlist records.
- Mapping candidates are suggestions with confidence, reason code, and explanation; they are not applied matches.
- Unmatched, ambiguous, unsupported, or mock rows must produce warnings that require advisor or school confirmation for high-impact use.

Phase 7A allowed behavior:

- Normalize generic course-code fields such as `FIN 300` or `FIN-300`.
- Store bounded normalized payload snippets for preview and testing.
- Match staged course-like rows against existing mock catalog courses by exact normalized code.
- Return records, mapping candidates, warnings, preview summaries, and student import history through API endpoints.
- Render a web preview panel with non-official, staging-only, and advisor-confirmation disclaimers.

Phase 7A forbidden behavior:

- Real school login, SAML, MFA, CAPTCHA, portal scraping, browser extension import, OCR-heavy extraction, or official source ingestion.
- Automatic registration, add/drop, swap, seat polling, seat grabbing, waitlist handling, or advisor approval workflows.
- Presenting imported, mock, inferred, or student-provided data as official school policy.

## 12. Data Review And Confirmation Rules

Phase 7B turns Phase 7A staging previews into reviewable decisions. A review session can confirm, reject, defer, mark advisor review, or edit-and-confirm each imported record.

Phase 7B hard rules:

- No GET endpoint may apply imported data or create domain records.
- `dry_run = true` must return proposed application outcomes without writing domain records.
- Real application requires explicit `POST /data-import-reviews/{review_id}/apply`.
- Applied records must preserve source metadata and remain `is_official = false` unless a future official reviewed source workflow changes the rule.
- Duplicate prevention must skip records that were already applied or match an existing internal course attempt.
- Every applied or skipped record must include an action, status, reason code, and message.
- Records rejected, deferred, needing advisor review, unsupported by Phase 7B, unmatched to a safe course, using unsupported grades, or lacking a known term are skipped with warnings.

Phase 7B allowed behavior:

- Create review sessions from Phase 7A import runs.
- Store selected mapping candidates, edited normalized payloads, reviewer notes, and advisor-confirmation flags.
- Apply confirmed unofficial transcript course attempts into internal `student_course_attempts` for planning, with source metadata and audit logs.
- Render a review panel that supports decisions, simple field edits, dry-run, explicit apply, warnings, and application logs.

Phase 7B forbidden behavior:

- Applying course catalog, section, section-meeting, requirement, or unknown-course records unless a later phase implements and tests a safe target-specific application path.
- Treating imported data as official policy, official transcript data, registration state, seat availability, or advisor approval.
- Real school login, browser extension import, scraping, OCR-heavy extraction, automatic registration, add/drop/swap, waitlist handling, seat polling, or seat grabbing.

## 9. Phase 3A Requirement Status Semantics

- `SATISFIED`: the requirement is completed by valid completed records or approved transfer/substitution records.
- `WAIVED`: an approved waiver satisfies the requirement but does not add earned credits.
- `IN_PROGRESS`: completed work plus in-progress work could satisfy the requirement, but the requirement is not complete.
- `PLANNED`: completed/in-progress/planned work could satisfy the requirement, but planned work is not complete.
- `PARTIALLY_SATISFIED`: some completed work counts, but the requirement remains short.
- `NOT_SATISFIED`: no valid completed, in-progress, planned, approved transfer, waiver, or substitution record satisfies the requirement.
- `MANUAL_REVIEW_REQUIRED`: the rule scope or configuration is not safe to automate in Phase 3A.
- `NOT_APPLICABLE`: reserved for future explicitly non-applicable requirement branches.

Parent node status is derived from node semantics, not from raw string ordering. For example, an `ALL_OF` node with two completed children and one in-progress child is `IN_PROGRESS`, while an `ANY_OF` node with one completed child is `SATISFIED`.
