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

Phase 2A stores requirement trees but does not evaluate them. The implemented storage uses relational `RequirementNode` rows with parent pointers and `RequirementCourseOption` rows for course-specific options. Stored nodes may express groups, required courses, all-of/any-of, choose-N, minimum credits/courses/grade, course level, residency, total credits, capstone, and exclusion concepts, but Phase 2A returns only the stored tree through the API.

## 3. Course Allocation

A course may be eligible for multiple requirement nodes. The evaluator should:

1. Build candidate requirement assignments for each eligible course.
2. Exclude failed or insufficient-grade courses unless a rule explicitly permits them.
3. Include transferred and waived records according to source and policy.
4. Optimize assignment based on requirement priority, graduation progress, overlap policies, and minimum extra credits.
5. Return explanations for chosen and rejected allocations.

Course allocation is deferred until the Degree Audit phase. Phase 2A does not mark requirements satisfied, does not apply transfer/waiver/substitution decisions, and does not choose between overlapping requirement candidates.

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
