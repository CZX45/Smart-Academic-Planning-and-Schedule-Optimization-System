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

Every Phase 2A academic-domain table includes `source_type`, `is_official`, source reference fields, and timestamps. The development seed uses only `source_type = MOCK` and `is_official = false`.

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
  - `id`, `course_id`, `term_id`, `section_code`, `crn`, `campus_id`, `modality`, `capacity`, `enrolled`, `waitlist_capacity`, `status`, `instructor_id`
- `section_meeting`
  - `id`, `section_id`, `day_of_week`, `start_time`, `end_time`, `timezone`, `location_id`, `meeting_type`
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
  - `id`, `student_id`, `program_version_id`, `created_at`, `input_hash`, `status`, `summary`
- `requirement_evaluation_result`
  - `id`, `audit_run_id`, `requirement_node_id`, `status`, `credits_applied`, `courses_applied`, `explanation`, `confidence_level`
- `course_requirement_assignment`
  - `id`, `audit_run_id`, `student_course_record_id`, `requirement_node_id`, `assignment_type`, `score`, `explanation`
- `planning_session`
  - `id`, `student_id`, `name`, `created_at`, `assumptions`, `status`
- `planned_course`
  - `id`, `planning_session_id`, `course_id`, `term_id`, `status`, `reason`
- `schedule_optimization_run`
  - `id`, `planning_session_id`, `term_id`, `preferences`, `status`, `objective_summary`
- `schedule_candidate`
  - `id`, `schedule_run_id`, `rank`, `score`, `warnings`, `explanation`
- `schedule_candidate_section`
  - `id`, `schedule_candidate_id`, `section_id`

## 3. Suggested PostgreSQL Strategy

Use relational tables for identities, relationships, student records, courses, sections, and terms. Use JSONB selectively for versioned rule-tree metadata, optimizer assumptions, explanations, and imported raw snippets. Important JSON structures should also have Pydantic schemas and migration tests.

## 4. Status Enums

### Course Record Status

- `completed`
- `in_progress`
- `planned`
- `failed_or_insufficient_grade`
- `transferred`
- `waived`

### Requirement Status

- `satisfied`
- `partially_satisfied`
- `in_progress`
- `planned`
- `unsatisfied`

### Section Status

- `open`
- `closed`
- `waitlist`
- `full`
- `cancelled`
- `tentative`
- `unknown`

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
