# Data Model

## 1. Modeling Principles

- Courses and sections are separate entities.
- Requirement rules are versioned trees.
- Prerequisites and restrictions are composable expression trees.
- School data is source-tagged and versioned.
- Student records distinguish completed, in-progress, planned, transferred, waived, and insufficient-grade attempts.
- Course allocation to requirements is not fixed at import time; it is an optimization/evaluation result.

## 2. Core Entities

### Phase 2A Implemented Storage

Phase 2A implements the first persistence slice in PostgreSQL through Alembic:

- `institutions`
- `campuses`
- `academic_terms`
- `academic_programs`
- `program_versions`
- `courses`
- `course_equivalencies`
- `requirement_nodes`
- `requirement_course_options`
- `student_profiles`
- `student_academic_programs`
- `student_course_attempts`
- `transfer_credits`
- `course_waivers`
- `course_substitutions`

Phase 2B adds the course-rule and section foundation:

- `course_offering_patterns`
- `sections`
- `section_meetings`
- `course_rules`
- `course_rule_expressions`

Phase 3A adds the degree audit snapshot foundation:

- `degree_audit_runs`
- `requirement_evaluations`
- `audit_course_applications`
- `degree_audit_warnings`

Phase 3B adds what-if scenario and multi-program allocation storage:

- `academic_plan_scenarios`
- `scenario_programs`
- `program_combination_rules`
- `scenario_program_audits`
- `scenario_course_allocations`
- `scenario_comparison_snapshots`
- `scenario_warnings`

Phase 4 adds course eligibility check snapshot storage:

- `eligibility_check_runs`
- `rule_evaluations`
- `rule_expression_evaluations`
- `eligibility_warnings`

Phase 5A adds long-term academic planner snapshot storage:

- `academic_plan_runs`
- `academic_plan_terms`
- `academic_plan_courses`
- `academic_plan_requirement_coverages`
- `academic_plan_warnings`

Phase 6A adds semester schedule optimizer snapshot storage:

- `schedule_optimization_runs`
- `schedule_constraint_sets`
- `schedule_options`
- `schedule_option_sections`
- `schedule_conflicts`
- `schedule_warnings`

Phase 6B extends schedule optimizer snapshots with:

- advanced preference fields on `schedule_constraint_sets`
- score-component and diversity fields on `schedule_options`
- `schedule_repair_suggestions`

Phase 7A adds read-only data import staging storage:

- `data_import_runs`
- `data_import_files`
- `imported_records`
- `import_mapping_candidates`
- `import_validation_warnings`
- `import_preview_summaries`

Phase 7B adds review and application audit storage:

- `data_import_review_sessions`
- `imported_record_reviews`
- `data_application_runs`
- `applied_imported_records`
- `data_review_warnings`

Phase 8A does not add new data tables. It adds `BROWSER_EXTENSION` as a source type for staged `data_import_runs` so visible-page extension imports can be distinguished from mock, imported, inferred, official, and student-provided sources.

Phase 8B adds advisory section monitoring storage:

- `section_monitor_targets`
- `section_monitor_snapshots`
- `section_monitor_alerts`

Phase 11B does not add new tables. Kean Student Portal imports reuse Phase 7A
staging rows with `source_type = BROWSER_EXTENSION`, safe source-reference
metadata, `source_label = KEAN_STUDENT_PORTAL` in preview summaries,
`is_official = false`, and `official_application_ready = false`.

Every Phase 2A academic-domain table includes `source_type`, `is_official`, source reference fields, and timestamps. The development seed uses only `source_type = MOCK` and `is_official = false`.

Phase 2B also source-tags offering patterns, sections, meetings, rules, and rule expressions. Mock data remains non-official and cannot be used as authoritative school policy.

Phase 3A audit rows are generated snapshots, not source records. They do not store school credentials or portal secrets. Each run stores `engine_version`, `calculation_mode`, source snapshot hash, credit totals, completion percentage as fixed-precision numeric data, and zero-or-more warnings.

Phase 3B scenario rows are generated snapshots. They do not modify `student_academic_programs`; each scenario stores its own membership, audit links, allocations, warnings, and comparison summary. `program_combination_rules` are source-tagged because they represent policy data. Mock rules must remain `source_type = MOCK` and `is_official = false`.

Phase 4 eligibility rows are generated snapshots. They do not modify `student_academic_programs`, `student_course_attempts`, `sections`, or registration data. They reference stored mock `CourseRule` and `CourseRuleExpression` rows and store rule/expression evidence so the API can explain why a course is eligible, conditional, blocked, permission-gated, or manual-review-only.

Phase 5A academic plan rows are generated snapshots. They do not modify `student_academic_programs`, `student_course_attempts`, `sections`, section meetings, or registration data. They reference stored degree-audit, course, requirement, term, scenario, eligibility, and offering-pattern inputs where available, and every planned course stores a source, status, reason code, and explanation.

Phase 6A and 6B schedule rows are generated snapshots. They do not modify `student_academic_programs`, `student_course_attempts`, `sections`, section meetings, seat counts, waitlists, or registration data. They reference stored course, term, section, meeting, and eligibility inputs where available, and every option, selected section, conflict, repair suggestion, and warning is explainable.

Phase 7A data import rows are staging-only previews. They do not modify `student_academic_programs`, `student_course_attempts`, `courses`, `sections`, `requirement_nodes`, seat counts, waitlists, or registration data. Every run is non-official, stores bounded file metadata rather than durable raw upload content, preserves normalized record payload snippets, and includes mapping candidates, validation warnings, preview disclaimers, and advisor-confirmation flags.

Phase 7B review rows sit between staging data and internal planning records. A review session belongs to one import run and student. Per-record reviews store the selected mapping candidate, decision, optional edited normalized payload, reviewer note, and advisor-confirmation flag. Application runs record explicit apply attempts; applied-record logs preserve the action, status, target entity type/id, reason code, and message for created, duplicate, rejected, deferred, advisor-review, and unsupported outcomes. Confirmed unofficial transcript course attempts may create non-official internal `student_course_attempts`; unsupported catalog, section, requirement, unknown-course, rejected, deferred, duplicate, advisor-review, and unsupported-grade records are skipped with warnings.

Phase 8A browser-extension imports reuse Phase 7A staging rows. A browser-extension import run must keep `source_type = BROWSER_EXTENSION`, `is_official = false`, and `official_application_ready = false`. The source reference may preserve a safe visible-page URL, but raw page HTML is not stored by default. Phase 7B review rows remain required before application.

Phase 11B Kean Student Portal imports are a labeled subset of Phase 8A
browser-extension imports. Backend handling may expose `KEAN_STUDENT_PORTAL` in
preview metadata, but it must not mark the data official, bypass Phase 7B
review, store portal credentials, store cookies or session tokens, or mutate
official academic, section, seat, waitlist, or registration records.

Kean MyProgress summary-first imports reuse the same tables and store structured
program summary, credit summary, progress-bar segments, field provenance, raw
snapshot diagnostics, validation results, and exception queues in
`imported_records.normalized_payload` and
`import_preview_summaries.summary_payload`. High-confidence MyProgress records
can be auto-confirmed in `imported_record_reviews`; failed validation blocks
downstream academic analysis with a structured reason code. These rows remain
non-official staging data and keep `official_application_ready = false`.

Phase 8B section monitoring rows are advisory, non-official, and student-scoped. Targets identify a course, section, and term the student wants to compare manually. Snapshots preserve imported section-search state such as status, seats, waitlist counts, meeting time, instructor, and location, plus a deterministic snapshot hash for deduplication. Alerts compare two snapshots and store the changed field, previous/current values, severity, acknowledgement state, advisory/manual-review flags, and a manual verification message. These rows do not mutate `sections`, seat counts, waitlists, student records, or registration state.

Important Phase 2A constraints include:

- `institutions.code` is globally unique.
- `campuses.code` is unique within an institution.
- Course identity is unique by institution, subject code, and course number.
- `ProgramVersion` is unique by program, campus, catalog year, and effective term.
- Requirement parents must belong to the same program version and cannot point to themselves.
- Requirement course options cannot repeat the same course for the same node.
- Course equivalencies and course substitutions cannot point a course at itself.
- A student can have only one active primary major.
- Course attempts keep separate positive attempt numbers for retakes.
- Transfer, waiver, and substitution records store approval status but do not affect audit results in Phase 2A.
- Phase 3A applies only approved transfers, waivers, and substitutions. Pending records generate warnings, and rejected records do not apply.
- Course offering patterns are advisory historical or predicted metadata, not school commitments.
- Sections are unique by institution, term, course, and section code.
- Section meetings are separate records so a section can include a lecture plus lab or other meeting components.
- Course rules are either course scoped or section scoped. Section-scoped rules are constrained to the same course and institution as the section.
- Course rule expressions are relational adjacency-list trees with one root per rule. Parent and child nodes must belong to the same rule.
- A degree audit run has one evaluation per requirement node.
- An audit course application must reference a clear source record: an attempt, transfer credit, waiver, or substitution. Approved substitutions may also reference the completed substitute attempt used to support the approval.
- A scenario can contain only one primary major and cannot repeat the same program version.
- Program combination rules are directional; primary-to-secondary policy does not imply secondary-to-primary policy.
- Program combination credit/course limits cannot be negative, and a rule cannot point a program version at itself.
- Scenario course allocations must reference a clear source record and include structured allocation type, reason code, and explanation.
- Scenario comparison values are nonnegative and must trace back to program audit and allocation rows.
- Eligibility runs reference a student, course, target term, optional section, explicit mode, engine version, source snapshot hash, overall result, and academic eligibility result.
- Eligibility run section references are constrained to the same course and institution as the checked course.
- A rule evaluation is unique per eligibility run and course rule.
- A rule expression evaluation is unique per rule evaluation and expression node and must include a reason code and explanation.
- Eligibility warnings must include a warning code, severity, message, and advisor-confirmation flag.
- An academic plan run references a student, program version, start term, target completion term, planning mode, engine version, and credit policy.
- A what-if academic plan run must reference an `AcademicPlanScenario`; a current-program run must not require one.
- Academic plan terms are unique by run/term and run/sequence.
- Academic plan courses are unique by plan term and course and store eligibility result, planning status, source, reason code, and explanation.
- Academic plan requirement coverage links planned courses to requirement nodes and stores coverage type and credits.
- Academic plan warnings must include a warning code, severity, message, and advisor-confirmation flag.
- A schedule optimization run references a student, term, optional academic plan run, planning mode, engine version, credit policy, requested option count, status, and completion timestamp.
- A schedule constraint set is unique per run and persists candidate course IDs, excluded days, unavailable time blocks, time windows, gap preferences, modality filters, required/excluded course and section IDs, preference weights, course priority weights, section priority weights, no-gap/morning/afternoon preferences, diversity mode, partial-option policy, search bound, and permission behavior.
- Schedule options are unique by run/rank and store status, score, score components, score explanation, diversity rank, difference summary, shared-section count, credit total, class-day count, time window, gap minutes, and explanation.
- Schedule option sections are unique by option/course and option/section and store selected course, section, credits, eligibility result, and selection reason.
- Schedule conflicts reference the run and optional option/sections, include a typed conflict reason, optional time window, and message.
- Schedule repair suggestions reference the run and optionally the course/section/conflict they repair; each suggestion includes a typed suggestion, reason code, explanation, impact estimate, and optional payload.
- Schedule warnings must include a warning code, severity, message, and advisor-confirmation flag.
- A data import run references a student, import type, status, parser version, storage strategy, file metadata, source metadata, counts, and `official_application_ready = false`.
- A data import file stores metadata, checksum, optional preview text, and storage strategy; Phase 7A uses metadata-only storage for mock or student-provided content.
- Imported records are unique by run/row number and store record type, status, external identifier, raw label, normalized payload, and confidence score.
- Import mapping candidates attach to imported records and include target entity type, optional target ID, match type, confidence score, selection flag, reason code, and explanation.
- Import validation warnings include warning code, severity, message, optional imported-record link, and advisor-confirmation flag.
- Import preview summaries are unique per run, repeat nonnegative counts, keep `official_application_ready = false`, and preserve preview disclaimers in structured payload.
- A data import review session references one import run and student, stores status, reviewer label, start/completion timestamps, and is service-guarded so only one active review exists per run.
- Imported record reviews are unique by review session and imported record. Decisions are explicit: unreviewed, confirmed, rejected, needs advisor review, edited and confirmed, or deferred.
- A data application run references a review session, stores nonnegative applied/skipped/warning/error counts, and is created only by `POST /data-import-reviews/{review_id}/apply`.
- Applied imported records are unique by application run and imported record. Each row includes action, status, reason code, target entity type/id, and an explanatory message.
- Data review warnings include warning code, severity, message, optional record-review/application links, and advisor-confirmation flag.
- Section monitor targets are unique by student, course code, section code, and term; they are always advisory and non-official.
- Section monitor snapshots are unique by student, course code, section code, term, and snapshot hash so duplicate user-triggered imports do not generate duplicate alerts.
- Section monitor alerts are unique by previous snapshot, current snapshot, alert type, and field name; they always require manual review and remain advisory.

### Institution and Versioning

- `institution`
  - `id`, `name`, `code`, `country`, `timezone`
- `campus`
  - `id`, `institution_id`, `name`, `code`, `location`
- `academic_term`
  - `id`, `institution_id`, `campus_id`, `term_code`, `name`, `start_date`, `end_date`
- `source_document`
  - `id`, `institution_id`, `title`, `url`, `document_type`, `published_at`, `retrieved_at`, `checksum`, `confidence_level`
- `catalog_version`
  - `id`, `institution_id`, `campus_id`, `catalog_year`, `effective_term_id`, `label`, `status`

### Course Catalog

- `subject`
  - `id`, `institution_id`, `code`, `name`
- `course`
  - `id`, `institution_id`, `subject_id`, `course_number`, `title`, `description`, `credits_min`, `credits_max`, `level`, `repeatable`, `source_document_id`
- `course_version`
  - `id`, `course_id`, `catalog_version_id`, `title`, `credits_min`, `credits_max`, `attributes`, `prerequisite_expr_id`, `corequisite_expr_id`, `restriction_expr_id`
- `section`
  - `id`, `institution_id`, `course_id`, `term_id`, `campus_id`, `section_code`, `external_reference`, `title_override`, `credits`, `status`, `modality`, `capacity`, `available_seats`, `waitlist_capacity`, `waitlist_available`, `instructor_display`, `source_type`, `is_official`, `last_synced_at`
- `section_meeting`
  - `id`, `section_id`, `meeting_type`, `day_of_week`, `start_time`, `end_time`, `start_date`, `end_date`, `building`, `room`, `timezone`, `is_arranged`, `is_online`, `display_order`, `source_type`, `is_official`
- `instructor`
  - `id`, `institution_id`, `display_name`
- `location`
  - `id`, `campus_id`, `building`, `room`, `geo_hint`

### Program and Requirements

- `academic_program`
  - `id`, `institution_id`, `program_type`, `code`, `name`, `degree_level`
- `program_version`
  - `id`, `program_id`, `campus_id`, `catalog_version_id`, `effective_term_id`, `version_label`, `total_credits_required`, `rule_tree_id`, `source_document_id`
- `requirement_node`
  - `id`, `program_version_id`, `parent_id`, `node_type`, `label`, `description`, `min_credits`, `min_courses`, `min_grade`, `course_filter`, `attribute_filter`, `gpa_rule`, `allow_double_counting`, `priority`, `metadata`
- `overlap_policy`
  - `id`, `program_version_id`, `other_program_type`, `max_overlap_credits`, `max_overlap_courses`, `policy_expr_id`

### Expression Trees

- `expression_node`
  - `id`, `expression_type`, `operator`, `left_id`, `right_id`, `literal`, `course_filter`, `grade_threshold`, `metadata`

Phase 2B implements course eligibility-rule storage as `CourseRule` plus `CourseRuleExpression`:

- `course_rule`
  - `id`, `institution_id`, `course_id`, `section_id`, `rule_type`, `name`, `description`, `effective_term_id`, `expiration_term_id`, `source_type`, `is_official`, `requires_manual_confirmation`
- `course_rule_expression`
  - `id`, `institution_id`, `course_rule_id`, `parent_id`, `node_type`, `display_order`, `referenced_course_id`, `minimum_grade`, `minimum_completed_credits`, `class_standing`, `referenced_program_id`, `referenced_campus_id`, `permission_type`, `text_value`, `source_type`, `is_official`

Prerequisites and corequisites use the same expression model. Restriction and permission rules also use the same tree shape. Phase 2B stores and returns these trees but does not evaluate them against a student record.

Phase 4 evaluates the stored expression trees and snapshots the result:

- `eligibility_check_run`
  - `id`, `institution_id`, `student_profile_id`, `course_id`, `section_id`, `target_term_id`, `mode`, `status`, `engine_version`, `overall_result`, `academic_eligibility_result`, `started_at`, `completed_at`, `source_snapshot_hash`, `created_at`, `updated_at`
- `rule_evaluation`
  - `id`, `eligibility_check_run_id`, `course_rule_id`, `result`, `rule_type`, `explanation`, `display_order`, `created_at`
- `rule_expression_evaluation`
  - `id`, `rule_evaluation_id`, `course_rule_expression_id`, `result`, `actual_value`, `expected_value`, `matched_course_id`, `matched_attempt_id`, `reason_code`, `explanation`, `created_at`
- `eligibility_warning`
  - `id`, `eligibility_check_run_id`, `rule_evaluation_id`, `warning_code`, `severity`, `message`, `requires_advisor_confirmation`, `created_at`

Expression examples:

- `ALL(prereq_course(FIN 301, min_grade=C), class_standing(junior_or_above))`
- `ANY(course_completed(MATH 105), placement_score(min=70))`
- `NOT(campus_restricted(excluded_campus=...))`

### Student Records

- `student`
  - `id`, `external_ref`, `home_institution_id`, `home_campus_id`, `class_standing`, `expected_graduation_term_id`
- `student_program_declaration`
  - `id`, `student_id`, `program_version_id`, `declaration_type`, `declared_at`, `status`
- `student_course_record`
  - `id`, `student_id`, `course_id`, `term_id`, `status`, `grade`, `credits_attempted`, `credits_earned`, `source`, `is_repeat`, `notes`
- `transfer_course_record`
  - `id`, `student_id`, `source_institution`, `source_course_code`, `equivalent_course_id`, `credits_earned`, `grade`, `status`, `source_document_id`
- `waiver_or_substitution`
  - `id`, `student_id`, `program_version_id`, `requirement_node_id`, `course_id`, `approval_reference`, `status`, `notes`

### Evaluation and Planning

- `degree_audit_run`
  - `id`, `student_profile_id`, `program_version_id`, `status`, `engine_version`, `calculation_mode`, `started_at`, `completed_at`, `total_required_credits`, `completed_credits`, `in_progress_credits`, `planned_credits`, `remaining_credits`, `completion_percentage`, `source_snapshot_hash`, `created_at`, `updated_at`
- `requirement_evaluation`
  - `id`, `degree_audit_run_id`, `requirement_node_id`, `status`, `required_credits`, `satisfied_credits`, `remaining_credits`, `required_courses`, `satisfied_courses`, `remaining_courses`, `minimum_grade`, `explanation`, `display_order`, `created_at`
- `audit_course_application`
  - `id`, `degree_audit_run_id`, `requirement_evaluation_id`, `course_id`, `student_course_attempt_id`, `transfer_credit_id`, `course_waiver_id`, `course_substitution_id`, `application_type`, `credit_amount`, `grade`, `is_completed`, `is_in_progress`, `is_planned`, `is_shared`, `explanation`, `created_at`
- `degree_audit_warning`
  - `id`, `degree_audit_run_id`, `requirement_evaluation_id`, `warning_code`, `severity`, `message`, `requires_advisor_confirmation`, `created_at`
- `academic_plan_scenario`
  - `id`, `student_profile_id`, `name`, `scenario_type`, `status`, `base_program_version_id`, `engine_version`, `created_at`, `updated_at`, `completed_at`
- `scenario_program`
  - `id`, `academic_plan_scenario_id`, `program_version_id`, `relationship_type`, `is_existing_program`, `is_hypothetical`, `priority`, `created_at`
- `program_combination_rule`
  - `id`, `primary_program_version_id`, `secondary_program_version_id`, `combination_type`, `maximum_shared_credits`, `minimum_unique_secondary_credits`, `minimum_unique_courses`, `allows_double_counting`, `requires_manual_confirmation`, `source_type`, `is_official`, `notes`, `effective_term_id`, `expiration_term_id`, `created_at`, `updated_at`
- `scenario_program_audit`
  - `id`, `academic_plan_scenario_id`, `scenario_program_id`, `degree_audit_run_id`, `created_at`
- `scenario_course_allocation`
  - `id`, `academic_plan_scenario_id`, `student_course_attempt_id`, `transfer_credit_id`, `course_waiver_id`, `course_substitution_id`, `course_id`, `program_version_id`, `requirement_node_id`, `allocation_type`, `credit_amount`, `is_shared`, `is_unique_to_program`, `allocation_rank`, `reason_code`, `explanation`, `created_at`
- `scenario_comparison_snapshot`
  - `academic_plan_scenario_id`, `completed_credits`, `in_progress_credits`, `planned_credits`, `remaining_requirement_credits`, `shared_credits`, `unique_secondary_credits`, `estimated_additional_credits`, `unresolved_requirements`, `manual_review_count`, `completion_percentage`, `is_estimate`, `created_at`
- `scenario_warning`
  - `id`, `academic_plan_scenario_id`, `scenario_program_id`, `warning_code`, `severity`, `message`, `requires_advisor_confirmation`, `created_at`
- `academic_plan_run`
  - `id`, `student_profile_id`, `program_version_id`, `academic_plan_scenario_id`, `planning_mode`, `status`, `engine_version`, `start_term_id`, `target_completion_term_id`, `minimum_credits_per_term`, `maximum_credits_per_term`, `preferred_credits_per_term`, `completed_at`, `created_at`, `updated_at`
- `academic_plan_term`
  - `id`, `academic_plan_run_id`, `term_id`, `sequence_index`, `planned_credits`, `status`, `explanation`, `created_at`
- `academic_plan_course`
  - `id`, `academic_plan_term_id`, `course_id`, `requirement_node_id`, `source`, `priority_rank`, `credits`, `eligibility_result`, `planning_status`, `reason_code`, `explanation`, `created_at`
- `academic_plan_requirement_coverage`
  - `id`, `academic_plan_run_id`, `academic_plan_course_id`, `requirement_node_id`, `coverage_type`, `credits`, `created_at`
- `academic_plan_warning`
  - `id`, `academic_plan_run_id`, `academic_plan_term_id`, `academic_plan_course_id`, `warning_code`, `severity`, `message`, `requires_advisor_confirmation`, `created_at`
- `planning_session`
  - `id`, `student_id`, `name`, `created_at`, `assumptions`, `status`
- `planned_course`
  - `id`, `planning_session_id`, `course_id`, `term_id`, `status`, `reason`
- `schedule_optimization_run`
  - `id`, `student_profile_id`, `term_id`, `academic_plan_run_id`, `planning_mode`, `status`, `engine_version`, `minimum_credits`, `maximum_credits`, `preferred_credits`, `requested_option_count`, `completed_at`, `created_at`, `updated_at`
- `schedule_constraint_set`
  - `id`, `schedule_optimization_run_id`, `candidate_course_ids`, `excluded_days`, `unavailable_time_blocks`, `earliest_start_time`, `latest_end_time`, `minimum_gap_minutes`, `maximum_gap_minutes`, `allowed_modalities`, `excluded_modalities`, `required_course_ids`, `excluded_course_ids`, `required_section_ids`, `excluded_section_ids`, preference booleans, `created_at`
- `schedule_option`
  - `id`, `schedule_optimization_run_id`, `option_rank`, `status`, `total_credits`, `class_days_count`, `earliest_start_time`, `latest_end_time`, `total_gap_minutes`, `score`, `explanation`, `created_at`
- `schedule_option_section`
  - `id`, `schedule_option_id`, `section_id`, `course_id`, `credits`, `eligibility_result`, `selection_reason`, `created_at`
- `schedule_conflict`
  - `id`, `schedule_optimization_run_id`, `schedule_option_id`, `conflict_type`, `section_id`, `other_section_id`, `day_of_week`, `start_time`, `end_time`, `message`, `created_at`
- `schedule_warning`
  - `id`, `schedule_optimization_run_id`, `schedule_option_id`, `warning_code`, `severity`, `message`, `requires_advisor_confirmation`, `created_at`

## 3. Suggested PostgreSQL Strategy

Use relational tables for identities, relationships, student records, courses, sections, and terms. Use JSONB selectively for versioned rule-tree metadata, optimizer assumptions, explanations, and imported raw snippets. Important JSON structures should also have Pydantic schemas and migration tests.

## 4. Status Enums

### Course Record Status

- `completed`
- `in_progress`
- `planned`
- `failed_or_insufficient_grade`
- `incomplete`
- `transferred`
- `waived`

### Requirement Status

- `SATISFIED`
- `IN_PROGRESS`
- `PLANNED`
- `PARTIALLY_SATISFIED`
- `NOT_SATISFIED`
- `WAIVED`
- `MANUAL_REVIEW_REQUIRED`
- `NOT_APPLICABLE`

### Degree Audit Run Status

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `COMPLETED_WITH_WARNINGS`

### Degree Audit Calculation Mode

- `CURRENT`: final completed and approved records can satisfy requirements; in-progress and planned records remain separate.
- `PROJECTED`: in-progress and planned records can be displayed as potential contributions but are not relabeled as completed.

### Course Eligibility Mode

- `CURRENT`: final completed and approved records can satisfy course rules.
- `PROJECTED`: in-progress and planned evidence can create conditional eligibility but is not final completion.
- `REGISTRATION`: evaluates the selected term/optional section and reports section availability separately from academic eligibility.

### Course Eligibility Overall Result

- `ELIGIBLE`
- `CONDITIONALLY_ELIGIBLE`
- `NOT_ELIGIBLE`
- `PERMISSION_REQUIRED`
- `MANUAL_REVIEW_REQUIRED`

### Academic Planning Mode

- `CURRENT_PROGRAM`
- `WHAT_IF_SCENARIO`

### Academic Plan Run Status

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `COMPLETED_WITH_WARNINGS`
- `FAILED`

### Academic Plan Term Status

- `PLANNED`
- `PARTIAL`
- `BLOCKED`
- `MANUAL_REVIEW_REQUIRED`

### Academic Plan Course Source

- `DEGREE_AUDIT_REMAINING`
- `WHAT_IF_REMAINING`
- `PREREQUISITE_UNLOCK`
- `COREQUISITE_PAIR`
- `MANUAL_PLACEHOLDER`

### Academic Plan Course Status

- `PLANNED`
- `CONDITIONALLY_PLANNED`
- `BLOCKED`
- `ALTERNATIVE`
- `MANUAL_REVIEW_REQUIRED`

### Academic Plan Coverage Type

- `DIRECT_REQUIREMENT`
- `ELECTIVE_POOL`
- `TOTAL_CREDITS`
- `PREREQUISITE_ONLY`
- `WHAT_IF_REQUIREMENT`

### Schedule Planning Mode

- `FROM_DEGREE_AUDIT`
- `FROM_LONG_TERM_PLAN`
- `CUSTOM_COURSE_SET`

### Schedule Run Status

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `COMPLETED_WITH_WARNINGS`
- `FAILED`

### Schedule Option Status

- `FEASIBLE`
- `FEASIBLE_WITH_WARNINGS`
- `PARTIAL`
- `INFEASIBLE`

### Schedule Conflict Type

- `TIME_OVERLAP`
- `UNAVAILABLE_TIME`
- `EXCLUDED_DAY`
- `CREDIT_LIMIT`
- `DUPLICATE_COURSE`
- `ELIGIBILITY_BLOCKED`
- `COREQUISITE_MISSING`
- `NO_SECTION_AVAILABLE`
- `MANUAL_REVIEW_REQUIRED`

### Audit Application Type

- `COURSE_ATTEMPT`
- `TRANSFER_CREDIT`
- `WAIVER`
- `SUBSTITUTION`
- `EQUIVALENCY`

### Audit Warning Severity

- `INFO`
- `WARNING`
- `ERROR`

### Source Type

- `MOCK`
- `OFFICIAL`
- `IMPORTED`
- `BROWSER_EXTENSION`
- `STUDENT_PROVIDED`
- `INFERRED`

### Academic Scenario Type

- `ADD_MINOR`
- `ADD_SECOND_MAJOR`
- `ADD_CERTIFICATE`
- `ADD_CONCENTRATION`
- `CHANGE_PRIMARY_MAJOR`
- `CUSTOM_COMBINATION`

### Academic Scenario Status

- `DRAFT`
- `RUNNING`
- `COMPLETED`
- `COMPLETED_WITH_WARNINGS`
- `FAILED`
- `ARCHIVED`

### Scenario Relationship Type

- `PRIMARY_MAJOR`
- `MINOR`
- `SECOND_MAJOR`
- `CERTIFICATE`
- `CONCENTRATION`

### Scenario Allocation Type

- `PRIMARY`
- `SHARED`
- `UNIQUE_SECONDARY`
- `TOTAL_CREDIT_ONLY`
- `UNALLOCATED`

### Section Status

- `PLANNED`
- `OPEN`
- `CLOSED`
- `WAITLIST`
- `CANCELLED`
- `COMPLETED`
- `UNKNOWN`

### Section Monitor Alert Type

- `STATUS_CHANGED`
- `SEATS_CHANGED`
- `SECTION_OPENED`
- `SECTION_CLOSED`
- `WAITLIST_CHANGED`
- `MEETING_TIME_CHANGED`
- `INSTRUCTOR_CHANGED`
- `LOCATION_CHANGED`
- `UNKNOWN_CHANGE`

### Section Modality

- `IN_PERSON`
- `ONLINE_SYNCHRONOUS`
- `ONLINE_ASYNCHRONOUS`
- `HYBRID`
- `ARRANGED`
- `UNKNOWN`

### Course Rule Type

- `PREREQUISITE`
- `COREQUISITE`
- `REGISTRATION_RESTRICTION`
- `REPEAT_RESTRICTION`
- `PERMISSION`

### Course Rule Expression Node Type

- `AND`
- `OR`
- `NOT`
- `COMPLETED_COURSE`
- `MINIMUM_GRADE`
- `MINIMUM_COMPLETED_CREDITS`
- `CLASS_STANDING`
- `MAJOR_RESTRICTION`
- `MINOR_RESTRICTION`
- `PROGRAM_RESTRICTION`
- `CAMPUS_RESTRICTION`
- `PERMISSION_REQUIRED`

## 5. Data Accuracy Metadata

Every official or imported rule should track:

- Institution.
- Campus.
- Catalog year.
- Effective term.
- Program version.
- Source document.
- Retrieval/import timestamp.
- Confidence level: official, advisor-confirmed, student-provided, inferred, mock.

## 6. Applied Course-State Snapshots

- `CourseStateSnapshot` links one student, import run, review session, and data
  application run. It stores source validation, program matching, bounded or
  truncated extraction flags, summary counts, imported program/credit/
  requirement summaries, and per-consumer readiness.
- `CourseStateRecord` preserves each reviewed source row, source table/row
  indices, field provenance, normalized status, catalog match, confidence,
  validation state, review decision, application reason, and warnings.
- `StudentCourseAttempt.course_state_snapshot_id` identifies attempts created
  from a snapshot. Only reliable `COMPLETED`, `IN_PROGRESS`, and `PLANNED` rows
  may create attempts. `NOT_STARTED` remains requirement evidence only.
- A PostgreSQL partial unique index permits one active snapshot per student;
  uniqueness on import and application IDs makes application idempotent.

Course-state statuses are `COMPLETED`, `IN_PROGRESS`, `PLANNED`,
`NOT_STARTED`, and `UNKNOWN`. Validation states are `RELIABLE`,
`RELIABLE_WITH_WARNINGS`, `EXTERNAL_EVIDENCE`, and `EXCEPTION`.
