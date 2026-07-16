import { z } from "zod";

export const HealthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  database_configured: z.boolean(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const ReadinessResponseSchema = z.object({
  status: z.union([z.literal("ready"), z.literal("not_ready")]),
  service: z.string(),
  database_ready: z.boolean(),
});

export type ReadinessResponse = z.infer<typeof ReadinessResponseSchema>;

export const BackupStatusSchema = z.object({
  available: z.boolean(),
  product_mode: z.string(),
  schema_name: z.literal("LOCAL_DESKTOP"),
  schema_version: z.number().int().positive(),
  message: z.string(),
});

export type BackupStatus = z.infer<typeof BackupStatusSchema>;

export const RestorePreviewSchema = z.object({
  session_id: z.string().uuid(),
  backup_id: z.string().uuid(),
  created_at: z.string(),
  source_application_version: z.string().nullable(),
  format_version: z.number().int(),
  schema_version: z.number().int(),
  database_size_bytes: z.number().int(),
  database_sha256: z.string(),
  integrity_checks_passed: z.boolean(),
  full_replacement_warning: z.string(),
  encrypted: z.boolean(),
  pairing_notice: z.string(),
  restart_notice: z.string(),
  compatibility: z.string(),
  blocking_errors: z.array(z.string()),
  warnings: z.array(z.string()),
});

export type RestorePreview = z.infer<typeof RestorePreviewSchema>;

export const RestoreStageResultSchema = z.object({
  status: z.string(),
  message: z.string(),
  restart_required: z.boolean(),
});

export type RestoreStageResult = z.infer<typeof RestoreStageResultSchema>;

export const DiagnosticStatusSchema = z.enum([
  "HEALTHY",
  "DEGRADED",
  "ACTION_REQUIRED",
  "BLOCKED",
  "UNKNOWN",
  "NOT_RUN",
  "TIMED_OUT",
  "ERROR",
]);

export type DiagnosticStatus = z.infer<typeof DiagnosticStatusSchema>;

export const OverallDiagnosticStatusSchema = z.enum([
  "HEALTHY",
  "DEGRADED",
  "ACTION_REQUIRED",
  "BLOCKED",
  "UNKNOWN",
]);

const DiagnosticBaseSchema = z.object({
  status: DiagnosticStatusSchema,
  reason_code: z.string().nullable(),
  summary: z.string(),
});

export const RuntimeHealthSchema = DiagnosticBaseSchema.extend({
  current_mode: z.enum(["LOCAL_DESKTOP", "SERVER"]),
  manifest_present: z.boolean(),
  manifest_contract_supported: z.boolean().nullable(),
  manifest_parseable: z.boolean().nullable(),
  pid_valid: z.boolean().nullable(),
  api_base_url_loopback: z.boolean().nullable(),
  port_valid: z.boolean().nullable(),
  stale: z.boolean().nullable(),
  process_consistent: z.boolean().nullable(),
  conflict_detected: z.boolean(),
});

export const ApiHealthSchema = DiagnosticBaseSchema.extend({
  process_status: z.enum(["RUNNING", "NOT_RUNNING", "UNKNOWN"]),
  readiness_status: z.enum(["READY", "NOT_READY", "UNKNOWN"]),
  health_status: z.enum(["HEALTHY", "UNHEALTHY", "UNKNOWN"]),
  api_contract_version: z.string(),
  application_mode: z.enum(["LOCAL_DESKTOP", "SERVER"]),
  loopback_bound: z.boolean(),
  expected_database: z.enum(["SQLITE", "POSTGRESQL", "UNKNOWN"]),
  schema_match: z.boolean().nullable(),
  recent_child_process_exit: z.string().nullable(),
});

export const DatabaseHealthSchema = DiagnosticBaseSchema.extend({
  present: z.boolean(),
  readable: z.boolean(),
  sqlite_header_valid: z.boolean().nullable(),
  foreign_keys_status: DiagnosticStatusSchema,
  integrity_check_status: DiagnosticStatusSchema,
  foreign_key_check_status: DiagnosticStatusSchema,
  schema_version: z.number().int().nullable(),
  supported_schema_version: z.number().int(),
  schema_version_supported: z.boolean().nullable(),
  journal_mode: z.string().nullable(),
  sidecar_wal_present: z.boolean(),
  sidecar_shm_present: z.boolean(),
  sidecar_journal_present: z.boolean(),
  operation_state: z.enum(["NONE_DETECTED", "SIDECAR_PRESENT", "UNKNOWN"]),
  size_bucket: z.enum(["<1 MB", "1-10 MB", "10-100 MB", ">100 MB", "UNKNOWN"]),
});

export const MigrationHealthSchema = DiagnosticBaseSchema.extend({
  current_schema_version: z.number().int().nullable(),
  supported_schema_version: z.number().int(),
  schema_status: z.string(),
  migration_required: z.boolean().nullable(),
  migration_in_progress: z.boolean(),
  last_attempt_status: z.string().nullable(),
  last_successful_migration: z.string().nullable(),
  last_rollback_status: z.string().nullable(),
  interrupted_attempt_detected: z.boolean(),
  safety_backup_reference_exists: z.boolean().nullable(),
  blocking_reason_code: z.string().nullable(),
  recovery_action_category: z.enum([
    "NONE",
    "REVIEW",
    "RECOVERY_PREFLIGHT",
    "ADVISOR_CONFIRMATION",
    "UNKNOWN",
  ]),
});

export const RestoreHealthSchema = DiagnosticBaseSchema.extend({
  backup_capability_available: z.boolean(),
  last_manual_backup_result: z.string(),
  pending_restore_detected: z.boolean(),
  restore_validation_state: z.string(),
  restore_staged: z.boolean(),
  restore_confirmation_state: z.string(),
  last_restore_result: z.string(),
  last_restore_rollback_result: z.string(),
  restore_replay_blocked: z.boolean(),
  unresolved_restore_state: z.boolean(),
  backup_archive_format_version: z.number().int().nullable(),
  same_schema_only: z.boolean(),
});

export const PairingHealthSchema = DiagnosticBaseSchema.extend({
  status: z.enum([
    "NOT_PAIRED",
    "PAIRED",
    "EXPIRED",
    "INVALID",
    "REPAIR_REQUIRED",
    "UNKNOWN",
  ]),
  capability_available: z.boolean(),
  paired: z.boolean().nullable(),
  record_version: z.number().int().nullable(),
  record_parseable: z.boolean(),
  localhost_proof_contract_available: z.boolean(),
  replay_protection_enabled: z.boolean(),
  repair_required: z.boolean(),
});

export const StartupEventSchema = z.object({
  event_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  occurred_at: z.string(),
  component: z.string(),
  sanitized_summary: z.string(),
  resolved: z.boolean(),
  attempt_id: z.string().nullable(),
});

export const StartupHealthSchema = DiagnosticBaseSchema.extend({
  source_available: z.boolean(),
  events: z.array(StartupEventSchema),
});

export const DiagnosticsSnapshotSchema = z.object({
  contract_version: z.number().int().positive(),
  generated_at: z.string(),
  application_mode: z.enum(["LOCAL_DESKTOP", "SERVER"]),
  application_version: z.string(),
  platform_summary: z.object({
    operating_system: z.string(),
    architecture: z.string(),
    python_major_minor: z.string(),
  }),
  overall_status: OverallDiagnosticStatusSchema,
  runtime_health: RuntimeHealthSchema,
  api_health: ApiHealthSchema,
  database_health: DatabaseHealthSchema,
  schema_status: MigrationHealthSchema,
  migration_status: MigrationHealthSchema,
  restore_status: RestoreHealthSchema,
  pairing_status: PairingHealthSchema,
  recent_startup_status: StartupHealthSchema,
  warnings: z.array(z.string()),
  capabilities: z.object({
    read_only_snapshot: z.boolean(),
    local_desktop_only: z.boolean(),
    bundle_export: z.boolean(),
    automatic_repair: z.boolean(),
    telemetry: z.boolean(),
    remote_upload: z.boolean(),
  }),
}).strict();

export type DiagnosticsSnapshot = z.infer<typeof DiagnosticsSnapshotSchema>;

const UuidSchema = z.string().uuid();
const DecimalValueSchema = z.union([z.string(), z.number()]).transform(String);
const DateTimeSchema = z.string();

export const SourceMetadataSchema = z.object({
  source_type: z.string(),
  is_official: z.boolean(),
  source_reference: z.string().nullable().optional(),
  source_retrieved_at: DateTimeSchema.nullable().optional(),
  source_confidence: z.string().nullable().optional(),
});

export type SourceMetadata = z.infer<typeof SourceMetadataSchema>;

export type AcademicStatusTone =
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral";

export type AcademicStatusBadge = {
  label: string;
  tone: AcademicStatusTone;
};

export type AdvisoryLabelKey =
  | "NON_OFFICIAL_IMPORTED_DATA"
  | "MANUAL_REVIEW_REQUIRED"
  | "ADVISORY_ONLY"
  | "VERIFY_IN_OFFICIAL_PORTAL";

export type AcademicAdvisoryLabel = {
  text: string;
  tone: AcademicStatusTone;
};

export type AcademicEmptyStateKey =
  | "NO_DATA_IMPORTS"
  | "NO_CONFIRMED_IMPORTS"
  | "NO_SECTION_MONITORING_TARGETS"
  | "NO_SECTION_MONITORING_ALERTS"
  | "NO_GENERATED_SCHEDULE_PLANS"
  | "NO_WHAT_IF_SCENARIOS";

export type AcademicEmptyStateCopy = {
  title: string;
  explanation: string;
  reason: string;
  nextAction: string;
  disclaimer: string;
};

const warningStatuses = new Set([
  "AMBIGUOUS",
  "COMPLETED_WITH_WARNINGS",
  "CONDITIONALLY_ELIGIBLE",
  "CONDITIONALLY_PLANNED",
  "CONDITIONALLY_SATISFIED",
  "IN_REVIEW",
  "MANUAL_REVIEW_REQUIRED",
  "PARSED_WITH_WARNINGS",
  "PERMISSION_REQUIRED",
  "VALID_WITH_WARNINGS",
  "WAITLIST",
  "WARNING",
]);

const dangerStatuses = new Set([
  "BLOCKED",
  "ERROR",
  "FAILED",
  "INFEASIBLE",
  "NOT_ELIGIBLE",
  "NOT_SATISFIED",
  "OFFLINE",
  "SCHEMA_ERROR",
]);

const successStatuses = new Set([
  "ACTIVE",
  "APPLIED",
  "APPLIED_WITH_WARNINGS",
  "COMPLETED",
  "ELIGIBLE",
  "FEASIBLE",
  "OPEN",
  "READY",
  "SATISFIED",
  "SUCCESS",
]);

const infoStatuses = new Set(["LOADING", "PENDING", "PLANNED", "RUNNING"]);

const advisoryLabelCopy: Record<AdvisoryLabelKey, AcademicAdvisoryLabel> = {
  NON_OFFICIAL_IMPORTED_DATA: {
    text: "Non-official imported data",
    tone: "warning",
  },
  MANUAL_REVIEW_REQUIRED: {
    text: "Manual review required",
    tone: "warning",
  },
  ADVISORY_ONLY: { text: "Advisory only", tone: "info" },
  VERIFY_IN_OFFICIAL_PORTAL: {
    text: "Verify in official portal",
    tone: "danger",
  },
};

const emptyStateCopy: Record<AcademicEmptyStateKey, AcademicEmptyStateCopy> = {
  NO_DATA_IMPORTS: {
    title: "No data imports yet",
    explanation:
      "No staging imports have been created or loaded for the mock student.",
    reason:
      "Import preview starts empty until a student manually chooses data to stage.",
    nextAction: "Preview an import manually before review.",
    disclaimer: "Non-official imported data. Manual review required.",
  },
  NO_CONFIRMED_IMPORTS: {
    title: "No confirmed imports yet",
    explanation:
      "No imported records have been manually reviewed and confirmed.",
    reason:
      "A staging import must be previewed before review decisions can be applied.",
    nextAction:
      "Preview or load a staging import, then review each record manually.",
    disclaimer: "Manual review required. Advisory only.",
  },
  NO_SECTION_MONITORING_TARGETS: {
    title: "No section monitoring targets",
    explanation: "No sections are currently selected for advisory monitoring.",
    reason:
      "Monitoring starts only after a student manually selects sections from imported data.",
    nextAction:
      "Import section-search data and choose sections to monitor manually.",
    disclaimer: "Non-official imported data. Verify in official portal.",
  },
  NO_SECTION_MONITORING_ALERTS: {
    title: "No section monitoring alerts",
    explanation: "No advisory section changes have been detected yet.",
    reason:
      "There are no imported section snapshots with a detected before/after change.",
    nextAction:
      "Import a fresh section-search snapshot, then verify any change manually in the official portal.",
    disclaimer: "Advisory only. Verify in official portal.",
  },
  NO_GENERATED_SCHEDULE_PLANS: {
    title: "No generated schedule plans",
    explanation: "No semester schedule optimization has been generated yet.",
    reason:
      "The schedule builder starts empty until a student manually runs an optimization.",
    nextAction:
      "Choose a course set and build a schedule to compare advisory options.",
    disclaimer: "Advisory only. This is not registration.",
  },
  NO_WHAT_IF_SCENARIOS: {
    title: "No what-if scenarios",
    explanation: "No what-if program scenario has been created yet.",
    reason:
      "Scenario comparison starts empty until a student manually creates a scenario.",
    nextAction: "Choose a candidate program and create a scenario.",
    disclaimer: "Advisory only. Advisor confirmation may be required.",
  },
};

function normalizeStatus(status: string | null | undefined): string | null {
  const normalized = status?.trim().replaceAll("-", "_").toUpperCase();
  return normalized && normalized.length > 0 ? normalized : null;
}

function humanizeStatus(status: string): string {
  return status
    .toLowerCase()
    .split("_")
    .filter((part) => part.length > 0)
    .map((part, index) =>
      index === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part,
    )
    .join(" ");
}

export function getAcademicStatusBadge(
  status: string | null | undefined,
): AcademicStatusBadge {
  const normalized = normalizeStatus(status);
  if (!normalized) {
    return { label: "Not started", tone: "neutral" };
  }
  if (successStatuses.has(normalized)) {
    return { label: humanizeStatus(normalized), tone: "success" };
  }
  if (warningStatuses.has(normalized)) {
    return { label: humanizeStatus(normalized), tone: "warning" };
  }
  if (dangerStatuses.has(normalized)) {
    return { label: humanizeStatus(normalized), tone: "danger" };
  }
  if (infoStatuses.has(normalized)) {
    return { label: humanizeStatus(normalized), tone: "info" };
  }
  return { label: humanizeStatus(normalized), tone: "neutral" };
}

export function getAdvisoryLabels(
  keys: AdvisoryLabelKey[],
): AcademicAdvisoryLabel[] {
  return keys.map((key) => advisoryLabelCopy[key]);
}

export function formatAcademicTimestamp(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "Not available";
  }
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const month = months[date.getUTCMonth()] ?? "Jan";
  const hour24 = date.getUTCHours();
  const hour12 = hour24 % 12 || 12;
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");
  const amPm = hour24 < 12 ? "AM" : "PM";
  return `${month} ${date.getUTCDate()}, ${date.getUTCFullYear()}, ${hour12}:${minutes} ${amPm} UTC`;
}

function displayValue(value: string | null | undefined): string {
  const trimmed = value?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : "Unknown";
}

export function formatBeforeAfterValue(
  previousValue: string | null | undefined,
  currentValue: string | null | undefined,
): string {
  return `${displayValue(previousValue)} -> ${displayValue(currentValue)}`;
}

export function getAcademicEmptyStateCopy(
  key: AcademicEmptyStateKey,
): AcademicEmptyStateCopy {
  return emptyStateCopy[key];
}

export const DegreeAuditRunSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  program_version_id: UuidSchema,
  status: z.enum([
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
  ]),
  engine_version: z.string(),
  calculation_mode: z.enum(["CURRENT", "PROJECTED"]),
  started_at: DateTimeSchema.nullable(),
  completed_at: DateTimeSchema.nullable(),
  total_required_credits: DecimalValueSchema,
  completed_credits: DecimalValueSchema,
  in_progress_credits: DecimalValueSchema,
  planned_credits: DecimalValueSchema,
  remaining_credits: DecimalValueSchema,
  completion_percentage: DecimalValueSchema,
  source_snapshot_hash: z.string(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type DegreeAuditRun = z.infer<typeof DegreeAuditRunSchema>;

export const DegreeAuditWarningSchema = z.object({
  id: UuidSchema,
  degree_audit_run_id: UuidSchema,
  requirement_evaluation_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type DegreeAuditWarning = z.infer<typeof DegreeAuditWarningSchema>;

export const AuditCourseApplicationSchema = z.object({
  id: UuidSchema,
  course_id: UuidSchema.nullable(),
  course_code: z.string().nullable(),
  course_title: z.string().nullable(),
  student_course_attempt_id: UuidSchema.nullable().optional(),
  transfer_credit_id: UuidSchema.nullable().optional(),
  course_waiver_id: UuidSchema.nullable().optional(),
  course_substitution_id: UuidSchema.nullable().optional(),
  application_type: z.enum([
    "COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "WAIVER",
    "SUBSTITUTION",
    "EQUIVALENCY",
  ]),
  credit_amount: DecimalValueSchema,
  grade: z.string().nullable(),
  is_completed: z.boolean(),
  is_in_progress: z.boolean(),
  is_planned: z.boolean(),
  is_shared: z.boolean(),
  explanation: z.string(),
});

export type AuditCourseApplication = z.infer<
  typeof AuditCourseApplicationSchema
>;

export const RequirementEvaluationSchema = z.object({
  id: UuidSchema,
  degree_audit_run_id: UuidSchema,
  requirement_node_id: UuidSchema,
  requirement_code: z.string(),
  requirement_name: z.string(),
  requirement_type: z.string(),
  status: z.enum([
    "SATISFIED",
    "IN_PROGRESS",
    "PLANNED",
    "PARTIALLY_SATISFIED",
    "NOT_SATISFIED",
    "WAIVED",
    "MANUAL_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
  ]),
  required_credits: DecimalValueSchema.nullable(),
  satisfied_credits: DecimalValueSchema,
  remaining_credits: DecimalValueSchema,
  required_courses: z.number().nullable(),
  satisfied_courses: z.number(),
  remaining_courses: z.number(),
  minimum_grade: z.string().nullable(),
  explanation: z.string(),
  display_order: z.number(),
  applications: z.array(AuditCourseApplicationSchema),
  warnings: z.array(DegreeAuditWarningSchema),
});

export type RequirementEvaluation = z.infer<typeof RequirementEvaluationSchema>;

export const AcademicScenarioSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  name: z.string(),
  scenario_type: z.enum([
    "ADD_MINOR",
    "ADD_SECOND_MAJOR",
    "ADD_CERTIFICATE",
    "ADD_CONCENTRATION",
    "CHANGE_PRIMARY_MAJOR",
    "CUSTOM_COMBINATION",
  ]),
  status: z.enum([
    "DRAFT",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
    "ARCHIVED",
  ]),
  base_program_version_id: UuidSchema,
  engine_version: z.string(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
  completed_at: DateTimeSchema.nullable(),
});

export type AcademicScenario = z.infer<typeof AcademicScenarioSchema>;

export const ScenarioProgramSchema = z.object({
  id: UuidSchema,
  academic_plan_scenario_id: UuidSchema,
  program_version_id: UuidSchema,
  relationship_type: z.enum([
    "PRIMARY_MAJOR",
    "MINOR",
    "SECOND_MAJOR",
    "CERTIFICATE",
    "CONCENTRATION",
  ]),
  is_existing_program: z.boolean(),
  is_hypothetical: z.boolean(),
  priority: z.number(),
  program_code: z.string(),
  program_name: z.string(),
  source: SourceMetadataSchema,
  created_at: DateTimeSchema,
});

export type ScenarioProgram = z.infer<typeof ScenarioProgramSchema>;

export const ScenarioProgramAuditSchema = z.object({
  scenario_program: ScenarioProgramSchema,
  degree_audit_run: DegreeAuditRunSchema,
});

export type ScenarioProgramAudit = z.infer<typeof ScenarioProgramAuditSchema>;

export const ScenarioCourseAllocationSchema = z.object({
  id: UuidSchema,
  academic_plan_scenario_id: UuidSchema,
  student_course_attempt_id: UuidSchema.nullable().optional(),
  transfer_credit_id: UuidSchema.nullable().optional(),
  course_waiver_id: UuidSchema.nullable().optional(),
  course_substitution_id: UuidSchema.nullable().optional(),
  course_id: UuidSchema.nullable(),
  course_code: z.string().nullable(),
  course_title: z.string().nullable(),
  program_version_id: UuidSchema.nullable(),
  requirement_node_id: UuidSchema.nullable(),
  requirement_code: z.string().nullable(),
  allocation_type: z.enum([
    "PRIMARY",
    "SHARED",
    "UNIQUE_SECONDARY",
    "TOTAL_CREDIT_ONLY",
    "UNALLOCATED",
  ]),
  credit_amount: DecimalValueSchema,
  is_shared: z.boolean(),
  is_unique_to_program: z.boolean(),
  allocation_rank: z.number(),
  reason_code: z.string(),
  explanation: z.string(),
  created_at: DateTimeSchema,
});

export type ScenarioCourseAllocation = z.infer<
  typeof ScenarioCourseAllocationSchema
>;

export const ScenarioWarningSchema = z.object({
  id: UuidSchema,
  academic_plan_scenario_id: UuidSchema,
  scenario_program_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type ScenarioWarning = z.infer<typeof ScenarioWarningSchema>;

export const ScenarioComparisonSnapshotSchema = z.object({
  academic_plan_scenario_id: UuidSchema,
  completed_credits: DecimalValueSchema,
  in_progress_credits: DecimalValueSchema,
  planned_credits: DecimalValueSchema,
  remaining_requirement_credits: DecimalValueSchema,
  shared_credits: DecimalValueSchema,
  unique_secondary_credits: DecimalValueSchema,
  estimated_additional_credits: DecimalValueSchema,
  unresolved_requirements: z.number(),
  manual_review_count: z.number(),
  completion_percentage: DecimalValueSchema,
  is_estimate: z.boolean(),
  created_at: DateTimeSchema,
});

export type ScenarioComparisonSnapshot = z.infer<
  typeof ScenarioComparisonSnapshotSchema
>;

const EligibilityOverallResultSchema = z.enum([
  "ELIGIBLE",
  "CONDITIONALLY_ELIGIBLE",
  "NOT_ELIGIBLE",
  "PERMISSION_REQUIRED",
  "MANUAL_REVIEW_REQUIRED",
]);

const EligibilityRuleResultSchema = z.enum([
  "SATISFIED",
  "CONDITIONALLY_SATISFIED",
  "NOT_SATISFIED",
  "PERMISSION_REQUIRED",
  "MANUAL_REVIEW_REQUIRED",
  "NOT_APPLICABLE",
]);

export const EligibilityReasonSchema = z.object({
  reason_code: z.string(),
  explanation: z.string(),
  course_rule_id: UuidSchema.nullable().optional(),
  course_rule_expression_id: UuidSchema.nullable().optional(),
  referenced_entity_type: z.string().nullable().optional(),
  referenced_entity_id: UuidSchema.nullable().optional(),
  expected_value: z.string().nullable().optional(),
  actual_value: z.string().nullable().optional(),
});

export type EligibilityReason = z.infer<typeof EligibilityReasonSchema>;

export const CorequisiteSummarySchema = z.object({
  required_corequisite_courses: z.array(UuidSchema),
  already_completed: z.array(UuidSchema),
  currently_in_progress: z.array(UuidSchema),
  must_enroll_concurrently: z.array(UuidSchema),
});

export type CorequisiteSummary = z.infer<typeof CorequisiteSummarySchema>;

export const RegistrationAvailabilitySchema = z.object({
  section_status: z.string(),
  available_seats: z.number().nullable().optional(),
  waitlist_available: z.number().nullable().optional(),
  availability_note: z.string().nullable().optional(),
});

export type RegistrationAvailability = z.infer<
  typeof RegistrationAvailabilitySchema
>;

export const RuleExpressionEvaluationSchema = z.object({
  id: UuidSchema,
  rule_evaluation_id: UuidSchema,
  course_rule_expression_id: UuidSchema,
  node_type: z.string(),
  result: EligibilityRuleResultSchema,
  actual_value: z.string().nullable().optional(),
  expected_value: z.string().nullable().optional(),
  matched_course_id: UuidSchema.nullable().optional(),
  matched_attempt_id: UuidSchema.nullable().optional(),
  reason_code: z.string(),
  explanation: z.string(),
  created_at: DateTimeSchema,
});

export type RuleExpressionEvaluation = z.infer<
  typeof RuleExpressionEvaluationSchema
>;

export const RuleEvaluationSchema = z.object({
  id: UuidSchema,
  eligibility_check_run_id: UuidSchema,
  course_rule_id: UuidSchema,
  result: EligibilityRuleResultSchema,
  rule_type: z.string(),
  explanation: z.string(),
  display_order: z.number(),
  expressions: z.array(RuleExpressionEvaluationSchema),
  created_at: DateTimeSchema,
});

export type RuleEvaluation = z.infer<typeof RuleEvaluationSchema>;

export const EligibilityWarningSchema = z.object({
  id: UuidSchema,
  eligibility_check_run_id: UuidSchema,
  rule_evaluation_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type EligibilityWarning = z.infer<typeof EligibilityWarningSchema>;

export const CourseEligibilityCheckSchema = z.object({
  id: UuidSchema,
  institution_id: UuidSchema,
  student_profile_id: UuidSchema,
  course_id: UuidSchema,
  section_id: UuidSchema.nullable(),
  target_term_id: UuidSchema,
  mode: z.enum(["CURRENT", "PROJECTED", "REGISTRATION"]),
  status: z.enum([
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
  ]),
  engine_version: z.string(),
  overall_result: EligibilityOverallResultSchema,
  academic_eligibility_result: EligibilityOverallResultSchema,
  started_at: DateTimeSchema.nullable(),
  completed_at: DateTimeSchema.nullable(),
  source_snapshot_hash: z.string(),
  rule_evaluations: z.array(RuleEvaluationSchema),
  blocking_reasons: z.array(EligibilityReasonSchema),
  conditional_reasons: z.array(EligibilityReasonSchema),
  permissions_required: z.array(EligibilityReasonSchema),
  manual_review_reasons: z.array(EligibilityReasonSchema),
  corequisites_to_add: z.array(UuidSchema),
  corequisite_summary: CorequisiteSummarySchema.nullable(),
  registration_availability: RegistrationAvailabilitySchema.nullable(),
  warnings: z.array(EligibilityWarningSchema),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type CourseEligibilityCheck = z.infer<
  typeof CourseEligibilityCheckSchema
>;

export const CourseEligibilityBatchSchema = z.object({
  results: z.array(CourseEligibilityCheckSchema),
});

export type CourseEligibilityBatch = z.infer<
  typeof CourseEligibilityBatchSchema
>;

const AcademicPlanningModeSchema = z.enum([
  "CURRENT_PROGRAM",
  "WHAT_IF_SCENARIO",
]);

const AcademicPlanRunStatusSchema = z.enum([
  "PENDING",
  "RUNNING",
  "COMPLETED",
  "COMPLETED_WITH_WARNINGS",
  "FAILED",
]);

const AcademicPlanTermStatusSchema = z.enum([
  "PLANNED",
  "PARTIAL",
  "BLOCKED",
  "MANUAL_REVIEW_REQUIRED",
]);

const AcademicPlanCourseSourceSchema = z.enum([
  "DEGREE_AUDIT_REMAINING",
  "WHAT_IF_REMAINING",
  "PREREQUISITE_UNLOCK",
  "COREQUISITE_PAIR",
  "MANUAL_PLACEHOLDER",
]);

const AcademicPlanCourseStatusSchema = z.enum([
  "PLANNED",
  "CONDITIONALLY_PLANNED",
  "BLOCKED",
  "ALTERNATIVE",
  "MANUAL_REVIEW_REQUIRED",
]);

const AcademicPlanCoverageTypeSchema = z.enum([
  "DIRECT_REQUIREMENT",
  "ELECTIVE_POOL",
  "TOTAL_CREDITS",
  "PREREQUISITE_ONLY",
  "WHAT_IF_REQUIREMENT",
]);

export const AcademicPlanRunSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  program_version_id: UuidSchema,
  academic_plan_scenario_id: UuidSchema.nullable(),
  planning_mode: AcademicPlanningModeSchema,
  status: AcademicPlanRunStatusSchema,
  engine_version: z.string(),
  start_term_id: UuidSchema,
  target_completion_term_id: UuidSchema,
  minimum_credits_per_term: DecimalValueSchema,
  maximum_credits_per_term: DecimalValueSchema,
  preferred_credits_per_term: DecimalValueSchema,
  completed_at: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type AcademicPlanRun = z.infer<typeof AcademicPlanRunSchema>;

export const AcademicPlanTermSchema = z.object({
  id: UuidSchema,
  academic_plan_run_id: UuidSchema,
  term_id: UuidSchema,
  term_code: z.string(),
  sequence_index: z.number(),
  planned_credits: DecimalValueSchema,
  status: AcademicPlanTermStatusSchema,
  explanation: z.string(),
  created_at: DateTimeSchema,
});

export type AcademicPlanTerm = z.infer<typeof AcademicPlanTermSchema>;

export const AcademicPlanCourseSchema = z.object({
  id: UuidSchema,
  academic_plan_term_id: UuidSchema,
  term_id: UuidSchema,
  term_code: z.string(),
  course_id: UuidSchema,
  course_code: z.string(),
  course_title: z.string(),
  requirement_node_id: UuidSchema.nullable(),
  requirement_code: z.string().nullable(),
  source: AcademicPlanCourseSourceSchema,
  priority_rank: z.number(),
  credits: DecimalValueSchema,
  eligibility_result: EligibilityOverallResultSchema,
  planning_status: AcademicPlanCourseStatusSchema,
  reason_code: z.string(),
  explanation: z.string(),
  created_at: DateTimeSchema,
});

export type AcademicPlanCourse = z.infer<typeof AcademicPlanCourseSchema>;

export const AcademicPlanRequirementCoverageSchema = z.object({
  id: UuidSchema,
  academic_plan_run_id: UuidSchema,
  academic_plan_course_id: UuidSchema,
  requirement_node_id: UuidSchema,
  requirement_code: z.string(),
  coverage_type: AcademicPlanCoverageTypeSchema,
  credits: DecimalValueSchema,
  created_at: DateTimeSchema,
});

export type AcademicPlanRequirementCoverage = z.infer<
  typeof AcademicPlanRequirementCoverageSchema
>;

export const AcademicPlanWarningSchema = z.object({
  id: UuidSchema,
  academic_plan_run_id: UuidSchema,
  academic_plan_term_id: UuidSchema.nullable(),
  academic_plan_course_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type AcademicPlanWarning = z.infer<typeof AcademicPlanWarningSchema>;

export const AcademicPlanDetailSchema = AcademicPlanRunSchema.extend({
  terms: z.array(AcademicPlanTermSchema),
  planned_courses: z.array(AcademicPlanCourseSchema),
  requirement_coverage: z.array(AcademicPlanRequirementCoverageSchema),
  warnings: z.array(AcademicPlanWarningSchema),
});

export type AcademicPlanDetail = z.infer<typeof AcademicPlanDetailSchema>;

export const AcademicPlanComparisonSchema = z.object({
  academic_plan_run_id: UuidSchema,
  status: AcademicPlanRunStatusSchema,
  total_planned_credits: DecimalValueSchema,
  term_count: z.number(),
  planned_course_count: z.number(),
  warning_count: z.number(),
  completed_at: DateTimeSchema.nullable(),
});

export type AcademicPlanComparison = z.infer<
  typeof AcademicPlanComparisonSchema
>;

const DayOfWeekSchema = z.enum([
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
]);

const SectionStatusSchema = z.enum([
  "PLANNED",
  "OPEN",
  "CLOSED",
  "WAITLIST",
  "CANCELLED",
  "COMPLETED",
  "UNKNOWN",
]);

const SectionModalitySchema = z.enum([
  "IN_PERSON",
  "ONLINE_SYNCHRONOUS",
  "ONLINE_ASYNCHRONOUS",
  "HYBRID",
  "ARRANGED",
  "UNKNOWN",
]);

const MeetingTypeSchema = z.enum([
  "LECTURE",
  "LAB",
  "RECITATION",
  "SEMINAR",
  "EXAM",
  "OTHER",
]);

const SchedulePlanningModeSchema = z.enum([
  "FROM_DEGREE_AUDIT",
  "FROM_LONG_TERM_PLAN",
  "CUSTOM_COURSE_SET",
]);
const SectionDataModeSchema = z.enum(["DEMO_MOCK", "REVIEWED_IMPORTED"]);

const ScheduleRunStatusSchema = z.enum([
  "PENDING",
  "RUNNING",
  "COMPLETED",
  "COMPLETED_WITH_WARNINGS",
  "FAILED",
]);

const ScheduleOptionStatusSchema = z.enum([
  "FEASIBLE",
  "FEASIBLE_WITH_WARNINGS",
  "PARTIAL",
  "INFEASIBLE",
]);

const ScheduleDiversityModeSchema = z.enum(["STANDARD", "HIGH"]);

const ScheduleConflictTypeSchema = z.enum([
  "TIME_OVERLAP",
  "UNAVAILABLE_TIME",
  "EXCLUDED_DAY",
  "CREDIT_LIMIT",
  "DUPLICATE_COURSE",
  "ELIGIBILITY_BLOCKED",
  "COREQUISITE_MISSING",
  "NO_SECTION_AVAILABLE",
  "MANUAL_REVIEW_REQUIRED",
]);

export const ScheduleOptimizationRunSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  term_id: UuidSchema,
  academic_plan_run_id: UuidSchema.nullable(),
  planning_mode: SchedulePlanningModeSchema,
  section_data_mode: SectionDataModeSchema.default("DEMO_MOCK"),
  source_age_max_minutes: z.number().nullable().default(null),
  input_snapshot_hash: z.string().nullable().default(null),
  source_readiness: z.record(z.string(), z.unknown()).default({}),
  status: ScheduleRunStatusSchema,
  engine_version: z.string(),
  minimum_credits: DecimalValueSchema,
  maximum_credits: DecimalValueSchema,
  preferred_credits: DecimalValueSchema,
  requested_option_count: z.number(),
  completed_at: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type ScheduleOptimizationRun = z.infer<
  typeof ScheduleOptimizationRunSchema
>;

export const ScheduleUnavailableTimeBlockSchema = z.object({
  day_of_week: DayOfWeekSchema,
  start_time: z.string(),
  end_time: z.string(),
});

export type ScheduleUnavailableTimeBlock = z.infer<
  typeof ScheduleUnavailableTimeBlockSchema
>;

export const ScheduleConstraintSetSchema = z.object({
  id: UuidSchema,
  schedule_optimization_run_id: UuidSchema,
  excluded_days: z.array(DayOfWeekSchema),
  unavailable_time_blocks: z.array(ScheduleUnavailableTimeBlockSchema),
  earliest_start_time: z.string().nullable(),
  latest_end_time: z.string().nullable(),
  minimum_gap_minutes: z.number().nullable(),
  maximum_gap_minutes: z.number().nullable(),
  candidate_course_ids: z.array(UuidSchema),
  allowed_modalities: z.array(SectionModalitySchema),
  excluded_modalities: z.array(SectionModalitySchema),
  required_course_ids: z.array(UuidSchema),
  excluded_course_ids: z.array(UuidSchema),
  required_section_ids: z.array(UuidSchema),
  excluded_section_ids: z.array(UuidSchema),
  prefer_online: z.boolean(),
  prefer_compact_schedule: z.boolean(),
  prefer_fewer_days: z.boolean(),
  prefer_in_person: z.boolean(),
  avoid_early_start: z.boolean(),
  avoid_late_end: z.boolean(),
  allow_permission_required: z.boolean(),
  preference_weights: z.record(z.string(), DecimalValueSchema),
  course_priority_weights: z.record(UuidSchema, DecimalValueSchema),
  section_priority_weights: z.record(UuidSchema, DecimalValueSchema),
  prefer_no_gaps: z.boolean(),
  prefer_morning: z.boolean(),
  prefer_afternoon: z.boolean(),
  diversity_mode: ScheduleDiversityModeSchema,
  allow_partial_options: z.boolean(),
  max_combinations: z.number(),
  source_age_max_minutes: z.number().nullable().default(null),
  created_at: DateTimeSchema,
});

export type ScheduleConstraintSet = z.infer<typeof ScheduleConstraintSetSchema>;

export const ScheduleSectionMeetingSchema = z.object({
  id: UuidSchema,
  section_id: UuidSchema,
  meeting_type: MeetingTypeSchema,
  day_of_week: DayOfWeekSchema.nullable(),
  start_time: z.string().nullable(),
  end_time: z.string().nullable(),
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  building: z.string().nullable(),
  room: z.string().nullable(),
  timezone: z.string().nullable(),
  is_arranged: z.boolean(),
  is_online: z.boolean(),
  display_order: z.number(),
});

export type ScheduleSectionMeeting = z.infer<
  typeof ScheduleSectionMeetingSchema
>;

export const ScheduleOptionSectionSchema = z.object({
  id: UuidSchema,
  schedule_option_id: UuidSchema,
  section_id: UuidSchema,
  course_id: UuidSchema,
  course_code: z.string(),
  course_title: z.string(),
  section_code: z.string(),
  section_status: SectionStatusSchema,
  modality: SectionModalitySchema,
  credits: DecimalValueSchema,
  eligibility_result: EligibilityOverallResultSchema,
  selection_reason: z.string(),
  source_provenance: z.record(z.string(), z.unknown()).nullable().default(null),
  source_age_minutes: z.number().nullable().default(null),
  section_snapshot_hash: z.string().nullable().default(null),
  drift_status: z.enum(["NOT_CAPTURED", "UNCHANGED", "CHANGED"]).default("NOT_CAPTURED"),
  meetings: z.array(ScheduleSectionMeetingSchema),
  created_at: DateTimeSchema,
});

export type ScheduleOptionSection = z.infer<typeof ScheduleOptionSectionSchema>;

export const ScheduleScoreBreakdownSchema = z.object({
  total_score: DecimalValueSchema,
  credit_score: DecimalValueSchema,
  compactness_score: DecimalValueSchema,
  days_score: DecimalValueSchema,
  gap_score: DecimalValueSchema,
  modality_score: DecimalValueSchema,
  time_preference_score: DecimalValueSchema,
  priority_score: DecimalValueSchema,
  penalty_score: DecimalValueSchema,
  score_explanation: z.array(z.record(z.string(), z.unknown())),
});

export type ScheduleScoreBreakdown = z.infer<
  typeof ScheduleScoreBreakdownSchema
>;

export const ScheduleOptionSchema = z.object({
  id: UuidSchema,
  schedule_optimization_run_id: UuidSchema,
  option_rank: z.number(),
  status: ScheduleOptionStatusSchema,
  total_credits: DecimalValueSchema,
  class_days_count: z.number(),
  earliest_start_time: z.string().nullable(),
  latest_end_time: z.string().nullable(),
  total_gap_minutes: z.number(),
  score: DecimalValueSchema,
  total_score: DecimalValueSchema,
  credit_score: DecimalValueSchema,
  compactness_score: DecimalValueSchema,
  days_score: DecimalValueSchema,
  gap_score: DecimalValueSchema,
  modality_score: DecimalValueSchema,
  time_preference_score: DecimalValueSchema,
  priority_score: DecimalValueSchema,
  penalty_score: DecimalValueSchema,
  score_explanation: z.array(z.record(z.string(), z.unknown())),
  score_breakdown: ScheduleScoreBreakdownSchema,
  diversity_rank: z.number(),
  difference_summary: z.string(),
  shared_section_count_with_previous_option: z.number(),
  explanation: z.string(),
  selected_sections: z.array(ScheduleOptionSectionSchema),
  created_at: DateTimeSchema,
});

export type ScheduleOption = z.infer<typeof ScheduleOptionSchema>;

export const ScheduleConflictSchema = z.object({
  id: UuidSchema,
  schedule_optimization_run_id: UuidSchema,
  schedule_option_id: UuidSchema.nullable(),
  conflict_type: ScheduleConflictTypeSchema,
  section_id: UuidSchema.nullable(),
  other_section_id: UuidSchema.nullable(),
  day_of_week: DayOfWeekSchema.nullable(),
  start_time: z.string().nullable(),
  end_time: z.string().nullable(),
  message: z.string(),
  created_at: DateTimeSchema,
});

export type ScheduleConflict = z.infer<typeof ScheduleConflictSchema>;

export const ScheduleWarningSchema = z.object({
  id: UuidSchema,
  schedule_optimization_run_id: UuidSchema,
  schedule_option_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type ScheduleWarning = z.infer<typeof ScheduleWarningSchema>;

export const ScheduleRepairSuggestionSchema = z.object({
  id: UuidSchema,
  schedule_optimization_run_id: UuidSchema,
  suggestion_type: z.string(),
  affected_constraint: z.string().nullable(),
  affected_course_id: UuidSchema.nullable(),
  affected_section_id: UuidSchema.nullable(),
  estimated_impact: z.string(),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type ScheduleRepairSuggestion = z.infer<
  typeof ScheduleRepairSuggestionSchema
>;

export const ScheduleOptimizationDetailSchema =
  ScheduleOptimizationRunSchema.extend({
    constraint_set: ScheduleConstraintSetSchema.nullable(),
    options: z.array(ScheduleOptionSchema),
    conflicts: z.array(ScheduleConflictSchema),
    warnings: z.array(ScheduleWarningSchema),
    repair_suggestions: z.array(ScheduleRepairSuggestionSchema),
    hard_constraint_results: z.array(z.record(z.string(), z.unknown())),
    soft_preference_results: z.array(z.record(z.string(), z.unknown())),
  });

export type ScheduleOptimizationDetail = z.infer<
  typeof ScheduleOptimizationDetailSchema
>;

export const ScheduleOptimizationComparisonSchema = z.object({
  schedule_optimization_run_id: UuidSchema,
  status: ScheduleRunStatusSchema,
  option_count: z.number(),
  warning_count: z.number(),
  best_score: DecimalValueSchema.nullable(),
  best_total_credits: DecimalValueSchema.nullable(),
  completed_at: DateTimeSchema.nullable(),
});

export type ScheduleOptimizationComparison = z.infer<
  typeof ScheduleOptimizationComparisonSchema
>;

export const DataImportRunSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  import_type: z.enum([
    "UNOFFICIAL_TRANSCRIPT",
    "DEGREE_AUDIT_EXPORT",
    "COURSE_CATALOG",
    "SECTION_SCHEDULE",
    "GENERIC_CSV",
    "GENERIC_JSON",
    "UNKNOWN",
  ]),
  status: z.enum([
    "PENDING",
    "PARSING",
    "PARSED",
    "PARSED_WITH_WARNINGS",
    "FAILED",
    "REVIEW_REQUIRED",
    "ARCHIVED",
  ]),
  storage_strategy: z.enum([
    "METADATA_ONLY",
    "LOCAL_DEV_FIXTURE",
    "EXTERNAL_OBJECT_REFERENCE",
    "NOT_STORED",
  ]),
  file_name: z.string(),
  file_mime_type: z.string(),
  file_size_bytes: z.number(),
  file_sha256: z.string(),
  parser_version: z.string(),
  record_count: z.number(),
  valid_record_count: z.number(),
  warning_count: z.number(),
  error_count: z.number(),
  official_application_ready: z.boolean(),
  started_at: DateTimeSchema,
  completed_at: DateTimeSchema.nullable(),
  source: SourceMetadataSchema,
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type DataImportRun = z.infer<typeof DataImportRunSchema>;

export const ImportedRecordSchema = z.object({
  id: UuidSchema,
  data_import_run_id: UuidSchema,
  record_type: z.enum([
    "COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "REQUIREMENT",
    "COURSE",
    "SECTION",
    "SECTION_MEETING",
    "PROGRAM",
    "UNKNOWN",
  ]),
  row_number: z.number(),
  status: z.enum([
    "VALID",
    "VALID_WITH_WARNINGS",
    "AMBIGUOUS",
    "DUPLICATE",
    "INVALID",
    "UNSUPPORTED",
  ]),
  external_identifier: z.string().nullable(),
  raw_label: z.string(),
  normalized_payload: z.record(z.string(), z.unknown()),
  confidence_score: DecimalValueSchema,
  created_at: DateTimeSchema,
});

export type ImportedRecord = z.infer<typeof ImportedRecordSchema>;

export const ImportMappingCandidateSchema = z.object({
  id: UuidSchema,
  imported_record_id: UuidSchema,
  target_entity_type: z.enum([
    "COURSE",
    "SECTION",
    "ACADEMIC_TERM",
    "REQUIREMENT_NODE",
    "PROGRAM_VERSION",
    "STUDENT_COURSE_ATTEMPT",
    "UNKNOWN",
  ]),
  target_entity_id: UuidSchema.nullable(),
  match_type: z.enum([
    "EXACT_CODE",
    "NORMALIZED_CODE",
    "TITLE_SIMILARITY",
    "TERM_MATCH",
    "MANUAL_REQUIRED",
    "NO_MATCH",
  ]),
  confidence_score: DecimalValueSchema,
  is_selected: z.boolean(),
  reason_code: z.string(),
  explanation: z.string(),
  created_at: DateTimeSchema,
});

export type ImportMappingCandidate = z.infer<
  typeof ImportMappingCandidateSchema
>;

export const ImportValidationWarningSchema = z.object({
  id: UuidSchema,
  data_import_run_id: UuidSchema,
  imported_record_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type ImportValidationWarning = z.infer<
  typeof ImportValidationWarningSchema
>;

export const ImportPreviewSummarySchema = z.object({
  id: UuidSchema,
  data_import_run_id: UuidSchema,
  record_count: z.number(),
  valid_record_count: z.number(),
  warning_count: z.number(),
  error_count: z.number(),
  official_application_ready: z.boolean(),
  disclaimers: z.array(z.string()),
  summary_payload: z.record(z.string(), z.unknown()),
  created_at: DateTimeSchema,
});

export type ImportPreviewSummary = z.infer<typeof ImportPreviewSummarySchema>;

const SectionMonitorAlertTypeSchema = z.enum([
  "STATUS_CHANGED",
  "SEATS_CHANGED",
  "SECTION_OPENED",
  "SECTION_CLOSED",
  "WAITLIST_CHANGED",
  "MEETING_TIME_CHANGED",
  "INSTRUCTOR_CHANGED",
  "LOCATION_CHANGED",
  "UNKNOWN_CHANGE",
]);

export const SectionMonitorTargetSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  course_code: z.string(),
  section_code: z.string(),
  term: z.string(),
  title: z.string().nullable(),
  instructor: z.string().nullable(),
  status: z.string().nullable(),
  is_active: z.boolean(),
  is_advisory: z.boolean(),
  is_official: z.boolean(),
  latest_snapshot_created_at: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type SectionMonitorTarget = z.infer<typeof SectionMonitorTargetSchema>;

export const SectionMonitorSnapshotSchema = z.object({
  id: UuidSchema,
  target_id: UuidSchema.nullable(),
  data_import_id: UuidSchema.nullable(),
  course_code: z.string(),
  section_code: z.string(),
  term: z.string(),
  status: z.string().nullable(),
  seats_available: z.number().nullable(),
  seats_capacity: z.number().nullable(),
  waitlist_available: z.number().nullable(),
  waitlist_capacity: z.number().nullable(),
  meeting_days: z.string().nullable(),
  meeting_time: z.string().nullable(),
  location: z.string().nullable(),
  instructor: z.string().nullable(),
  raw_payload: z.record(z.string(), z.unknown()),
  source_type: z.string(),
  is_official: z.boolean(),
  source_reference: z.string().nullable().optional(),
  source_confidence: z.string().nullable().optional(),
  created_at: DateTimeSchema,
});

export type SectionMonitorSnapshot = z.infer<
  typeof SectionMonitorSnapshotSchema
>;

export const SectionMonitorAlertSchema = z.object({
  id: UuidSchema,
  target_id: UuidSchema,
  previous_snapshot_id: UuidSchema,
  current_snapshot_id: UuidSchema,
  alert_type: SectionMonitorAlertTypeSchema,
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  field_name: z.string(),
  previous_value: z.string().nullable(),
  current_value: z.string().nullable(),
  message: z.string(),
  is_acknowledged: z.boolean(),
  acknowledged_at: DateTimeSchema.nullable(),
  is_advisory: z.boolean(),
  requires_manual_review: z.boolean(),
  created_at: DateTimeSchema,
});

export type SectionMonitorAlert = z.infer<typeof SectionMonitorAlertSchema>;

export const SectionMonitorSnapshotCompareResponseSchema = z.object({
  snapshots: z.array(SectionMonitorSnapshotSchema),
  alerts: z.array(SectionMonitorAlertSchema),
  disclaimers: z.array(z.string()),
});

export type SectionMonitorSnapshotCompareResponse = z.infer<
  typeof SectionMonitorSnapshotCompareResponseSchema
>;

export const DataImportReviewSessionSchema = z.object({
  id: UuidSchema,
  data_import_run_id: UuidSchema,
  student_profile_id: UuidSchema,
  status: z.enum([
    "DRAFT",
    "IN_REVIEW",
    "READY_TO_APPLY",
    "APPLYING",
    "APPLIED",
    "APPLIED_WITH_WARNINGS",
    "FAILED",
    "ARCHIVED",
  ]),
  reviewer_label: z.string(),
  started_at: DateTimeSchema,
  completed_at: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type DataImportReviewSession = z.infer<
  typeof DataImportReviewSessionSchema
>;

export const ImportedRecordReviewSchema = z.object({
  id: UuidSchema,
  review_session_id: UuidSchema,
  imported_record_id: UuidSchema,
  selected_mapping_candidate_id: UuidSchema.nullable(),
  decision: z.enum([
    "UNREVIEWED",
    "CONFIRMED",
    "REJECTED",
    "NEEDS_ADVISOR_REVIEW",
    "EDITED_AND_CONFIRMED",
    "DEFERRED",
  ]),
  edited_normalized_payload: z.record(z.string(), z.unknown()).nullable(),
  review_note: z.string().nullable(),
  requires_advisor_confirmation: z.boolean(),
  imported_record: ImportedRecordSchema,
  selected_mapping_candidate: ImportMappingCandidateSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type ImportedRecordReview = z.infer<typeof ImportedRecordReviewSchema>;

export const DataApplicationRunSchema = z.object({
  id: UuidSchema,
  review_session_id: UuidSchema,
  status: z.enum([
    "PENDING",
    "APPLYING",
    "APPLIED",
    "APPLIED_WITH_WARNINGS",
    "FAILED",
    "ROLLED_BACK",
  ]),
  applied_count: z.number(),
  skipped_count: z.number(),
  warning_count: z.number(),
  error_count: z.number(),
  started_at: DateTimeSchema,
  completed_at: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type DataApplicationRun = z.infer<typeof DataApplicationRunSchema>;

export const CourseStateReadinessItemSchema = z.object({
  status: z.string(),
  reason_codes: z.array(z.string()),
  blocking_reasons: z.array(z.string()),
  warnings: z.array(z.string()),
  source_import_id: UuidSchema,
  source_validation_state: z.string(),
  source_bounded: z.boolean(),
  source_truncated: z.boolean(),
  last_applied_at: DateTimeSchema,
});

export type CourseStateReadinessItem = z.infer<
  typeof CourseStateReadinessItemSchema
>;

export const CourseStateSnapshotSchema = z.object({
  id: UuidSchema,
  student_profile_id: UuidSchema,
  data_import_run_id: UuidSchema,
  review_session_id: UuidSchema,
  data_application_run_id: UuidSchema,
  source_page_type: z.string(),
  source_validation_state: z.string(),
  program_mapping_state: z.string(),
  is_active: z.boolean(),
  is_advisory: z.boolean(),
  official_application_ready: z.boolean(),
  extraction_bounded: z.boolean(),
  extraction_truncated: z.boolean(),
  completed_count: z.number(),
  in_progress_count: z.number(),
  planned_count: z.number(),
  not_started_count: z.number(),
  matched_count: z.number(),
  unmatched_count: z.number(),
  exception_count: z.number(),
  program_summary: z.record(z.string(), z.unknown()),
  credit_summary: z.record(z.string(), z.unknown()),
  requirement_summary: z.array(z.unknown()),
  readiness: z.record(z.string(), CourseStateReadinessItemSchema),
  applied_at: DateTimeSchema,
  source: SourceMetadataSchema,
  created_at: DateTimeSchema,
  updated_at: DateTimeSchema,
});

export type CourseStateSnapshot = z.infer<typeof CourseStateSnapshotSchema>;

export const CourseStateRecordSchema = z.object({
  id: UuidSchema,
  snapshot_id: UuidSchema,
  imported_record_id: UuidSchema,
  imported_record_review_id: UuidSchema,
  matched_course_id: UuidSchema.nullable(),
  student_course_attempt_id: UuidSchema.nullable(),
  normalized_course_code: z.string(),
  source_course_code: z.string(),
  source_course_title: z.string(),
  status: z.enum([
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "NOT_STARTED",
    "UNKNOWN",
  ]),
  term: z.string().nullable(),
  credits: DecimalValueSchema.nullable(),
  grade: z.string().nullable(),
  requirement_context: z.string().nullable(),
  source_page_type: z.string(),
  source_table_index: z.string().nullable(),
  source_row_index: z.string().nullable(),
  provenance: z.record(z.string(), z.unknown()),
  confidence_score: DecimalValueSchema,
  validation_state: z.enum([
    "RELIABLE",
    "RELIABLE_WITH_WARNINGS",
    "EXTERNAL_EVIDENCE",
    "EXCEPTION",
  ]),
  review_decision: z.enum([
    "UNREVIEWED",
    "CONFIRMED",
    "REJECTED",
    "NEEDS_ADVISOR_REVIEW",
    "EDITED_AND_CONFIRMED",
    "DEFERRED",
  ]),
  application_reason_code: z.string(),
  reason_codes: z.array(z.string()),
  warnings: z.array(z.string()),
  created_at: DateTimeSchema,
});

export type CourseStateRecord = z.infer<typeof CourseStateRecordSchema>;

export const CourseStateSnapshotDetailSchema = z.object({
  snapshot: CourseStateSnapshotSchema,
  course_states: z.array(CourseStateRecordSchema),
});

export type CourseStateSnapshotDetail = z.infer<
  typeof CourseStateSnapshotDetailSchema
>;

export const AppliedImportedRecordSchema = z.object({
  id: UuidSchema.nullable(),
  data_application_run_id: UuidSchema.nullable(),
  imported_record_review_id: UuidSchema,
  imported_record_id: UuidSchema,
  target_entity_type: z.enum([
    "STUDENT_COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "COURSE",
    "SECTION",
    "SECTION_MEETING",
    "COURSE_OFFERING_PATTERN",
    "COURSE_STATE",
    "UNKNOWN",
  ]),
  target_entity_id: UuidSchema.nullable(),
  action: z.enum([
    "CREATED",
    "UPDATED",
    "SKIPPED_DUPLICATE",
    "SKIPPED_REJECTED",
    "SKIPPED_DEFERRED",
    "SKIPPED_ADVISOR_REVIEW",
    "SKIPPED_UNSUPPORTED",
  ]),
  status: z.enum(["SUCCESS", "WARNING", "FAILED", "SKIPPED"]),
  reason_code: z.string(),
  message: z.string(),
  created_at: DateTimeSchema.nullable(),
});

export type AppliedImportedRecord = z.infer<typeof AppliedImportedRecordSchema>;

export const DataReviewWarningSchema = z.object({
  id: UuidSchema,
  review_session_id: UuidSchema,
  imported_record_review_id: UuidSchema.nullable(),
  data_application_run_id: UuidSchema.nullable(),
  warning_code: z.string(),
  severity: z.enum(["INFO", "WARNING", "ERROR"]),
  message: z.string(),
  requires_advisor_confirmation: z.boolean(),
  created_at: DateTimeSchema,
});

export type DataReviewWarning = z.infer<typeof DataReviewWarningSchema>;

export const DataReviewApplicationSummarySchema = z.object({
  source_import_id: UuidSchema,
  snapshot_id: UuidSchema.nullable(),
  applied_count: z.number(),
  warning_count: z.number(),
  exception_count: z.number(),
  rejected_count: z.number(),
  deferred_count: z.number(),
  duplicate_count: z.number(),
});

export type DataReviewApplicationSummary = z.infer<
  typeof DataReviewApplicationSummarySchema
>;

export const DataReviewApplicationResultSchema = z.object({
  review_session: DataImportReviewSessionSchema,
  dry_run: z.boolean(),
  application: DataApplicationRunSchema.nullable(),
  applied_records: z.array(AppliedImportedRecordSchema),
  warnings: z.array(DataReviewWarningSchema),
  course_state_snapshot: CourseStateSnapshotSchema.nullable().optional(),
  summary: DataReviewApplicationSummarySchema,
});

export type DataReviewApplicationResult = z.infer<
  typeof DataReviewApplicationResultSchema
>;

export class ApiRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export class ApiResponseSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiResponseSchemaError";
  }
}

export type FetchHealthOptions = {
  apiBearerToken?: string;
  fetchFn?: typeof fetch;
  timeoutMs?: number;
};

export type CreateDegreeAuditRequest = {
  student_profile_id: string;
  program_version_id: string;
  calculation_mode: "CURRENT" | "PROJECTED";
};

export type CreateAcademicScenarioRequest = {
  student_profile_id: string;
  scenario_name: string;
  scenario_type:
    | "ADD_MINOR"
    | "ADD_SECOND_MAJOR"
    | "ADD_CERTIFICATE"
    | "ADD_CONCENTRATION"
    | "CHANGE_PRIMARY_MAJOR"
    | "CUSTOM_COMBINATION";
  calculation_mode: "CURRENT" | "PROJECTED";
  programs: Array<{
    program_version_id: string;
    relationship_type:
      | "PRIMARY_MAJOR"
      | "MINOR"
      | "SECOND_MAJOR"
      | "CERTIFICATE"
      | "CONCENTRATION";
    priority: number;
  }>;
};

export type CreateCourseEligibilityCheckRequest = {
  student_profile_id: string;
  course_id: string;
  section_id?: string | null;
  target_term_id: string;
  mode: "CURRENT" | "PROJECTED" | "REGISTRATION";
  planned_corequisite_course_ids?: string[];
};

export type CreateAcademicPlanRequest = {
  student_profile_id: string;
  program_version_id: string;
  academic_plan_scenario_id?: string | null;
  planning_mode: "CURRENT_PROGRAM" | "WHAT_IF_SCENARIO";
  start_term_id: string;
  terms_to_plan: number;
  minimum_credits_per_term: string | number;
  maximum_credits_per_term: string | number;
  preferred_credits_per_term: string | number;
};

export type CompareAcademicPlansRequest = {
  academic_plan_ids: string[];
};

export type CreateScheduleOptimizationRequest = {
  student_profile_id: string;
  term_id: string;
  academic_plan_run_id?: string | null;
  planning_mode:
    | "FROM_DEGREE_AUDIT"
    | "FROM_LONG_TERM_PLAN"
    | "CUSTOM_COURSE_SET";
  section_data_mode?: "DEMO_MOCK" | "REVIEWED_IMPORTED";
  source_age_max_minutes?: number | null;
  candidate_course_ids?: string[];
  minimum_credits: string | number;
  maximum_credits: string | number;
  preferred_credits: string | number;
  requested_option_count: number;
  max_options?: number | null;
  excluded_days?: Array<z.infer<typeof DayOfWeekSchema>>;
  unavailable_time_blocks?: ScheduleUnavailableTimeBlock[];
  earliest_start_time?: string | null;
  latest_end_time?: string | null;
  allowed_modalities?: Array<z.infer<typeof SectionModalitySchema>>;
  excluded_modalities?: Array<z.infer<typeof SectionModalitySchema>>;
  required_course_ids?: string[];
  excluded_course_ids?: string[];
  required_section_ids?: string[];
  excluded_section_ids?: string[];
  prefer_online?: boolean;
  prefer_compact_schedule?: boolean;
  prefer_fewer_days?: boolean;
  prefer_in_person?: boolean;
  avoid_early_start?: boolean;
  avoid_late_end?: boolean;
  allow_permission_required?: boolean;
  minimum_gap_minutes?: number | null;
  maximum_gap_minutes?: number | null;
  preference_weights?: Record<string, string | number>;
  course_priority_weights?: Record<string, string | number>;
  section_priority_weights?: Record<string, string | number>;
  prefer_no_gaps?: boolean;
  prefer_morning?: boolean;
  prefer_afternoon?: boolean;
  diversity_mode?: z.infer<typeof ScheduleDiversityModeSchema>;
  allow_partial_options?: boolean;
  max_combinations?: number;
};

export type CompareScheduleOptimizationsRequest = {
  schedule_optimization_run_ids: string[];
};

export type CreateDataImportRequest = {
  student_profile_id: string;
  import_type:
    | "UNOFFICIAL_TRANSCRIPT"
    | "DEGREE_AUDIT_EXPORT"
    | "COURSE_CATALOG"
    | "SECTION_SCHEDULE"
    | "GENERIC_CSV"
    | "GENERIC_JSON"
    | "UNKNOWN";
  file_name: string;
  file_mime_type: string;
  content: string;
  source_type?:
    | "MOCK"
    | "IMPORTED"
    | "BROWSER_EXTENSION"
    | "STUDENT_PROVIDED"
    | "INFERRED"
    | "OFFICIAL";
  source_reference?: string | null;
  page_type?: string | null;
  extracted_record_count?: number | null;
  visible_row_count?: number | null;
  academic_field_count?: number | null;
  warnings?: Array<Record<string, unknown>>;
  diagnostics?: Record<string, unknown>;
  bounded?: boolean | null;
  truncated?: boolean | null;
};

export type CreateSectionMonitorTargetRequest = {
  student_profile_id: string;
  course_code: string;
  section_code: string;
  term: string;
  title?: string | null;
  instructor?: string | null;
  status?: string | null;
};

export type UpdateSectionMonitorTargetRequest = {
  is_active?: boolean | null;
  title?: string | null;
  instructor?: string | null;
  status?: string | null;
};

export type SectionMonitorSnapshotInput = {
  target_id?: string | null;
  data_import_id?: string | null;
  course_code: string;
  section_code: string;
  term: string;
  status?: string | null;
  seats_available?: number | null;
  seats_capacity?: number | null;
  waitlist_available?: number | null;
  waitlist_capacity?: number | null;
  meeting_days?: string | null;
  meeting_time?: string | null;
  location?: string | null;
  instructor?: string | null;
  raw_payload?: Record<string, unknown>;
  source_reference?: string | null;
};

export type CompareSectionMonitorSnapshotsRequest = {
  student_profile_id: string;
  source_type?: "BROWSER_EXTENSION";
  snapshots: SectionMonitorSnapshotInput[];
};

export const MAX_SECTION_MONITOR_SNAPSHOT_COUNT = 50;
export const MAX_SECTION_MONITOR_RAW_PAYLOAD_BYTES = 8192;
export const MAX_SECTION_MONITOR_RAW_PAYLOAD_DEPTH = 8;
export const MAX_SECTION_MONITOR_RAW_PAYLOAD_KEYS = 100;

type SectionMonitorPayloadShape = { keyCount: number; maxDepth: number };

function sectionMonitorPayloadShape(
  value: unknown,
  depth = 0,
): SectionMonitorPayloadShape {
  if (depth > MAX_SECTION_MONITOR_RAW_PAYLOAD_DEPTH) {
    return { keyCount: Number.POSITIVE_INFINITY, maxDepth: depth };
  }
  if (Array.isArray(value)) {
    return value.reduce<SectionMonitorPayloadShape>(
      (summary, child) => {
        const childShape = sectionMonitorPayloadShape(child, depth + 1);
        return {
          keyCount: summary.keyCount + childShape.keyCount,
          maxDepth: Math.max(summary.maxDepth, childShape.maxDepth),
        };
      },
      { keyCount: 0, maxDepth: depth },
    );
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.values(record).reduce<SectionMonitorPayloadShape>(
      (summary, child) => {
        const childShape = sectionMonitorPayloadShape(child, depth + 1);
        return {
          keyCount: summary.keyCount + childShape.keyCount,
          maxDepth: Math.max(summary.maxDepth, childShape.maxDepth),
        };
      },
      { keyCount: Object.keys(record).length, maxDepth: depth },
    );
  }
  return { keyCount: 0, maxDepth: depth };
}

export function isSectionMonitorRawPayloadBounded(
  value: Record<string, unknown>,
): boolean {
  const shape = sectionMonitorPayloadShape(value);
  if (
    shape.keyCount > MAX_SECTION_MONITOR_RAW_PAYLOAD_KEYS ||
    shape.maxDepth > MAX_SECTION_MONITOR_RAW_PAYLOAD_DEPTH
  ) {
    return false;
  }
  return (
    new TextEncoder().encode(JSON.stringify(value)).length <=
    MAX_SECTION_MONITOR_RAW_PAYLOAD_BYTES
  );
}

export type UpdateSectionMonitorAlertRequest = {
  is_acknowledged: boolean;
};

export type CreateDataImportReviewRequest = {
  data_import_run_id: string;
  reviewer_label: string;
};

export type UpdateImportedRecordReviewRequest = {
  decision:
    | "UNREVIEWED"
    | "CONFIRMED"
    | "REJECTED"
    | "NEEDS_ADVISOR_REVIEW"
    | "EDITED_AND_CONFIRMED"
    | "DEFERRED";
  selected_mapping_candidate_id?: string | null;
  edited_normalized_payload?: Record<string, unknown> | null;
  review_note?: string | null;
  requires_advisor_confirmation?: boolean | null;
};

export type ApplyDataImportReviewRequest = {
  allow_advisor_review_records?: boolean;
  dry_run?: boolean;
};

const DEFAULT_TIMEOUT_MS = 5_000;

function buildApiUrl(apiBaseUrl: string, path: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  if (trimmedBaseUrl.length === 0) {
    throw new ApiRequestError("API base URL is not configured");
  }
  return `${trimmedBaseUrl}${path}`;
}

export async function fetchHealth(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const fetchFn = options.fetchFn ?? fetch;

  try {
    const response = await fetchFn(buildApiUrl(apiBaseUrl, "/health"), {
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiRequestError(
        `Health check failed with status ${response.status}`,
      );
    }

    const parsed = HealthResponseSchema.safeParse(await response.json());
    if (!parsed.success) {
      throw new ApiResponseSchemaError(
        "Health response did not match the expected schema",
      );
    }

    return parsed.data;
  } catch (error: unknown) {
    if (
      error instanceof ApiRequestError ||
      error instanceof ApiResponseSchemaError
    ) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError(`Health check timed out after ${timeoutMs} ms`);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : "Health check request failed",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchReadiness(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<ReadinessResponse> {
  const response = await (options.fetchFn ?? fetch)(
    buildApiUrl(apiBaseUrl, "/ready"),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ApiRequestError(
      `Readiness check failed with status ${response.status}`,
    );
  }

  const parsed = ReadinessResponseSchema.safeParse(await response.json());
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Readiness response did not match the expected schema",
    );
  }

  return parsed.data;
}

export async function fetchLocalDiagnostics(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<DiagnosticsSnapshot> {
  const parsed = DiagnosticsSnapshotSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/local-diagnostics", options),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Local diagnostics response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function downloadLocalDiagnosticsBundle(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<{ blob: Blob; filename: string | null }> {
  const { fetchFn, timeoutMs, apiBearerToken } = options;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const headers = new Headers();
  if (apiBearerToken && apiBearerToken.trim().length > 0) {
    headers.set("authorization", `Bearer ${apiBearerToken.trim()}`);
  }
  try {
    const response = await (fetchFn ?? fetch)(
      buildApiUrl(apiBaseUrl, "/api/v1/local-diagnostics/export"),
      { method: "POST", cache: "no-store", headers, signal: controller.signal },
    );
    if (!response.ok) {
      throw new ApiRequestError(
        `Local diagnostics export failed with status ${response.status}`,
      );
    }
    return {
      blob: await response.blob(),
      filename:
        response.headers
          .get("content-disposition")
          ?.match(/filename="?([^";]+)"?/)?.[1] ?? null,
    };
  } catch (error: unknown) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError(
        `Local diagnostics export timed out after ${timeoutMs ?? DEFAULT_TIMEOUT_MS} ms`,
      );
    }
    throw new ApiRequestError(
      error instanceof Error
        ? error.message
        : "Local diagnostics export failed",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchLocalBackupStatus(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<BackupStatus> {
  const parsed = BackupStatusSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/local-backup/status", options),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Backup status response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function downloadLocalBackup(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<{ blob: Blob; filename: string | null }> {
  const { fetchFn, timeoutMs } = options;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  try {
    const response = await (fetchFn ?? fetch)(
      buildApiUrl(apiBaseUrl, "/api/v1/local-backup"),
      { method: "POST", cache: "no-store", signal: controller.signal },
    );
    if (!response.ok) {
      throw new ApiRequestError(
        `Local backup request failed with status ${response.status}`,
      );
    }
    return {
      blob: await response.blob(),
      filename:
        response.headers
          .get("content-disposition")
          ?.match(/filename="?([^";]+)"?/)?.[1] ?? null,
    };
  } catch (error: unknown) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError(
        `Local backup timed out after ${timeoutMs ?? DEFAULT_TIMEOUT_MS} ms`,
      );
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : "Local backup request failed",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function validateLocalRestore(
  apiBaseUrl: string,
  file: File,
  options: FetchHealthOptions = {},
): Promise<RestorePreview> {
  const body = new FormData();
  body.append("file", file);
  const parsed = RestorePreviewSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/local-backup/restore/validate", {
      ...options,
      method: "POST",
      body,
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError("Restore preview response was invalid");
  }
  return parsed.data;
}

export async function confirmLocalRestore(
  apiBaseUrl: string,
  sessionId: string,
  confirmation: string,
  options: FetchHealthOptions = {},
): Promise<RestoreStageResult> {
  const parsed = RestoreStageResultSchema.safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/local-backup/restore/sessions/${sessionId}/confirm`, {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ confirmation }),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError("Restore staging response was invalid");
  }
  return parsed.data;
}

export async function cancelLocalRestore(
  apiBaseUrl: string,
  sessionId: string,
  options: FetchHealthOptions = {},
): Promise<void> {
  await fetchJson(apiBaseUrl, `/api/v1/local-backup/restore/sessions/${sessionId}`, {
    ...options,
    method: "DELETE",
  });
}

async function fetchJson(
  apiBaseUrl: string,
  path: string,
  options: RequestInit & FetchHealthOptions = {},
): Promise<unknown> {
  const { apiBearerToken, fetchFn, timeoutMs, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  const headers = new Headers(requestOptions.headers);
  if (apiBearerToken && apiBearerToken.trim().length > 0) {
    headers.set("authorization", `Bearer ${apiBearerToken.trim()}`);
  }

  try {
    const response = await (fetchFn ?? fetch)(buildApiUrl(apiBaseUrl, path), {
      cache: "no-store",
      ...requestOptions,
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiRequestError(
        `API request to ${path} failed with status ${response.status}`,
      );
    }

    return response.status === 204 ? null : await response.json();
  } catch (error: unknown) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError(`API request timed out after ${timeoutMs} ms`);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : "API request failed",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchLatestDegreeAudit(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<DegreeAuditRun> {
  const parsed = DegreeAuditRunSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/students/${studentId}/degree-audits/latest`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Latest degree audit response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createDegreeAudit(
  apiBaseUrl: string,
  request: CreateDegreeAuditRequest,
  options: FetchHealthOptions = {},
): Promise<DegreeAuditRun> {
  const parsed = DegreeAuditRunSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/degree-audits", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Created degree audit response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDegreeAuditRequirements(
  apiBaseUrl: string,
  auditId: string,
  options: FetchHealthOptions = {},
): Promise<RequirementEvaluation[]> {
  const parsed = z
    .array(RequirementEvaluationSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/degree-audits/${auditId}/requirements`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Degree audit requirements response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createAcademicScenario(
  apiBaseUrl: string,
  request: CreateAcademicScenarioRequest,
  options: FetchHealthOptions = {},
): Promise<AcademicScenario> {
  const parsed = AcademicScenarioSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/academic-scenarios", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Created academic scenario response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicScenarioPrograms(
  apiBaseUrl: string,
  scenarioId: string,
  options: FetchHealthOptions = {},
): Promise<ScenarioProgram[]> {
  const parsed = z
    .array(ScenarioProgramSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-scenarios/${scenarioId}/programs`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario programs response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicScenarioAudits(
  apiBaseUrl: string,
  scenarioId: string,
  options: FetchHealthOptions = {},
): Promise<ScenarioProgramAudit[]> {
  const parsed = z
    .array(ScenarioProgramAuditSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-scenarios/${scenarioId}/audits`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario audits response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicScenarioAllocations(
  apiBaseUrl: string,
  scenarioId: string,
  options: FetchHealthOptions = {},
): Promise<ScenarioCourseAllocation[]> {
  const parsed = z
    .array(ScenarioCourseAllocationSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-scenarios/${scenarioId}/allocations`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario allocations response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicScenarioWarnings(
  apiBaseUrl: string,
  scenarioId: string,
  options: FetchHealthOptions = {},
): Promise<ScenarioWarning[]> {
  const parsed = z
    .array(ScenarioWarningSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-scenarios/${scenarioId}/warnings`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario warnings response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicScenarioComparison(
  apiBaseUrl: string,
  scenarioId: string,
  options: FetchHealthOptions = {},
): Promise<ScenarioComparisonSnapshot> {
  const parsed = ScenarioComparisonSnapshotSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/academic-scenarios/${scenarioId}/comparison`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario comparison response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentAcademicScenarios(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicScenario[]> {
  const parsed = z
    .array(AcademicScenarioSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/academic-scenarios`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student academic scenarios response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function compareAcademicScenarios(
  apiBaseUrl: string,
  scenarioIds: string[],
  options: FetchHealthOptions = {},
): Promise<ScenarioComparisonSnapshot[]> {
  const parsed = z.array(ScenarioComparisonSnapshotSchema).safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/academic-scenarios/compare", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenario_ids: scenarioIds }),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic scenario comparison list response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createCourseEligibilityCheck(
  apiBaseUrl: string,
  request: CreateCourseEligibilityCheckRequest,
  options: FetchHealthOptions = {},
): Promise<CourseEligibilityCheck> {
  const parsed = CourseEligibilityCheckSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/eligibility-checks", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Course eligibility response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createCourseEligibilityBatch(
  apiBaseUrl: string,
  requests: CreateCourseEligibilityCheckRequest[],
  options: FetchHealthOptions = {},
): Promise<CourseEligibilityBatch> {
  const parsed = CourseEligibilityBatchSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/eligibility-checks/batch", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ checks: requests }),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Course eligibility batch response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchCourseEligibilityCheck(
  apiBaseUrl: string,
  checkId: string,
  options: FetchHealthOptions = {},
): Promise<CourseEligibilityCheck> {
  const parsed = CourseEligibilityCheckSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/eligibility-checks/${checkId}`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Course eligibility detail response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentEligibilityChecks(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<CourseEligibilityCheck[]> {
  const parsed = z
    .array(CourseEligibilityCheckSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/eligibility-checks`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student eligibility checks response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createAcademicPlan(
  apiBaseUrl: string,
  request: CreateAcademicPlanRequest,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanDetail> {
  const parsed = AcademicPlanDetailSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/academic-plans", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicPlan(
  apiBaseUrl: string,
  planId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanDetail> {
  const parsed = AcademicPlanDetailSchema.safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-plans/${planId}`, options),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan detail response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicPlanTerms(
  apiBaseUrl: string,
  planId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanTerm[]> {
  const parsed = z
    .array(AcademicPlanTermSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-plans/${planId}/terms`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan terms response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicPlanCourses(
  apiBaseUrl: string,
  planId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanCourse[]> {
  const parsed = z
    .array(AcademicPlanCourseSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-plans/${planId}/courses`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan courses response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchAcademicPlanWarnings(
  apiBaseUrl: string,
  planId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanWarning[]> {
  const parsed = z
    .array(AcademicPlanWarningSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/academic-plans/${planId}/warnings`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan warnings response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentAcademicPlans(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanRun[]> {
  const parsed = z
    .array(AcademicPlanRunSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/academic-plans`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student academic plans response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function compareAcademicPlans(
  apiBaseUrl: string,
  request: CompareAcademicPlansRequest,
  options: FetchHealthOptions = {},
): Promise<AcademicPlanComparison[]> {
  const parsed = z.array(AcademicPlanComparisonSchema).safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/academic-plans/compare", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Academic plan comparison response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createScheduleOptimization(
  apiBaseUrl: string,
  request: CreateScheduleOptimizationRequest,
  options: FetchHealthOptions = {},
): Promise<ScheduleOptimizationDetail> {
  const parsed = ScheduleOptimizationDetailSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/schedule-optimizations", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchScheduleOptimization(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ScheduleOptimizationDetail> {
  const parsed = ScheduleOptimizationDetailSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/schedule-optimizations/${runId}`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization detail response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchScheduleOptimizationOptions(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ScheduleOption[]> {
  const parsed = z
    .array(ScheduleOptionSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/schedule-optimizations/${runId}/options`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization options response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchScheduleOptimizationConflicts(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ScheduleConflict[]> {
  const parsed = z
    .array(ScheduleConflictSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/schedule-optimizations/${runId}/conflicts`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization conflicts response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchScheduleOptimizationWarnings(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ScheduleWarning[]> {
  const parsed = z
    .array(ScheduleWarningSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/schedule-optimizations/${runId}/warnings`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization warnings response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentScheduleOptimizations(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<ScheduleOptimizationRun[]> {
  const parsed = z
    .array(ScheduleOptimizationRunSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/schedule-optimizations`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student schedule optimizations response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function compareScheduleOptimizations(
  apiBaseUrl: string,
  request: CompareScheduleOptimizationsRequest,
  options: FetchHealthOptions = {},
): Promise<ScheduleOptimizationComparison[]> {
  const parsed = z.array(ScheduleOptimizationComparisonSchema).safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/schedule-optimizations/compare", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Schedule optimization comparison response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createDataImport(
  apiBaseUrl: string,
  request: CreateDataImportRequest,
  options: FetchHealthOptions = {},
): Promise<DataImportRun> {
  const parsed = DataImportRunSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/data-imports", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImport(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<DataImportRun> {
  const parsed = DataImportRunSchema.safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/data-imports/${runId}`, options),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import detail response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportRecords(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ImportedRecord[]> {
  const parsed = z
    .array(ImportedRecordSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-imports/${runId}/records`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import records response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportMappingCandidates(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ImportMappingCandidate[]> {
  const parsed = z
    .array(ImportMappingCandidateSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-imports/${runId}/mapping-candidates`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import mapping candidates response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportWarnings(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ImportValidationWarning[]> {
  const parsed = z
    .array(ImportValidationWarningSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-imports/${runId}/warnings`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import warnings response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportPreview(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ImportPreviewSummary> {
  const parsed = ImportPreviewSummarySchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/data-imports/${runId}/preview`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import preview response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function validateDataImport(
  apiBaseUrl: string,
  runId: string,
  options: FetchHealthOptions = {},
): Promise<ImportPreviewSummary> {
  const parsed = ImportPreviewSummarySchema.safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/data-imports/${runId}/validate`, {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import validation response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentDataImports(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<DataImportRun[]> {
  const parsed = z
    .array(DataImportRunSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/data-imports`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student data imports response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchSectionMonitorTargets(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorTarget[]> {
  const parsed = z
    .array(SectionMonitorTargetSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/section-monitoring/targets?student_profile_id=${encodeURIComponent(studentId)}`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor targets response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createSectionMonitorTarget(
  apiBaseUrl: string,
  request: CreateSectionMonitorTargetRequest,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorTarget> {
  const parsed = SectionMonitorTargetSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/section-monitoring/targets", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor target response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function updateSectionMonitorTarget(
  apiBaseUrl: string,
  targetId: string,
  request: UpdateSectionMonitorTargetRequest,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorTarget> {
  const parsed = SectionMonitorTargetSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/section-monitoring/targets/${targetId}`,
      {
        ...options,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      },
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor target response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchSectionMonitorAlerts(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorAlert[]> {
  const parsed = z
    .array(SectionMonitorAlertSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/section-monitoring/alerts?student_profile_id=${encodeURIComponent(studentId)}`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor alerts response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function updateSectionMonitorAlert(
  apiBaseUrl: string,
  alertId: string,
  request: UpdateSectionMonitorAlertRequest,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorAlert> {
  const parsed = SectionMonitorAlertSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/section-monitoring/alerts/${alertId}`,
      {
        ...options,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      },
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor alert response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function compareSectionMonitorSnapshots(
  apiBaseUrl: string,
  request: CompareSectionMonitorSnapshotsRequest,
  options: FetchHealthOptions = {},
): Promise<SectionMonitorSnapshotCompareResponse> {
  if (request.snapshots.length > MAX_SECTION_MONITOR_SNAPSHOT_COUNT) {
    throw new ApiRequestError(
      `Section monitor compare request cannot include more than ${MAX_SECTION_MONITOR_SNAPSHOT_COUNT} snapshots`,
    );
  }
  const oversizedPayload = request.snapshots.find(
    (snapshot) =>
      snapshot.raw_payload &&
      !isSectionMonitorRawPayloadBounded(snapshot.raw_payload),
  );
  if (oversizedPayload) {
    throw new ApiRequestError(
      "Section monitor raw_payload exceeds the allowed bounds",
    );
  }
  const parsed = SectionMonitorSnapshotCompareResponseSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      "/api/v1/section-monitoring/snapshots/compare",
      {
        ...options,
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      },
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Section monitor snapshot comparison response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function createDataImportReview(
  apiBaseUrl: string,
  request: CreateDataImportReviewRequest,
  options: FetchHealthOptions = {},
): Promise<DataImportReviewSession> {
  const parsed = DataImportReviewSessionSchema.safeParse(
    await fetchJson(apiBaseUrl, "/api/v1/data-import-reviews", {
      ...options,
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportReview(
  apiBaseUrl: string,
  reviewId: string,
  options: FetchHealthOptions = {},
): Promise<DataImportReviewSession> {
  const parsed = DataImportReviewSessionSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/data-import-reviews/${reviewId}`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review detail response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportReviewRecords(
  apiBaseUrl: string,
  reviewId: string,
  options: FetchHealthOptions = {},
): Promise<ImportedRecordReview[]> {
  const parsed = z
    .array(ImportedRecordReviewSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-import-reviews/${reviewId}/records`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review records response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function updateImportedRecordReview(
  apiBaseUrl: string,
  reviewId: string,
  recordReviewId: string,
  request: UpdateImportedRecordReviewRequest,
  options: FetchHealthOptions = {},
): Promise<ImportedRecordReview> {
  const parsed = ImportedRecordReviewSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/data-import-reviews/${reviewId}/records/${recordReviewId}`,
      {
        ...options,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      },
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Imported record review response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function applyDataImportReview(
  apiBaseUrl: string,
  reviewId: string,
  request: ApplyDataImportReviewRequest = {},
  options: FetchHealthOptions = {},
): Promise<DataReviewApplicationResult> {
  const parsed = DataReviewApplicationResultSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/data-import-reviews/${reviewId}/apply`,
      {
        ...options,
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      },
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review application response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportReviewApplications(
  apiBaseUrl: string,
  reviewId: string,
  options: FetchHealthOptions = {},
): Promise<DataApplicationRun[]> {
  const parsed = z
    .array(DataApplicationRunSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-import-reviews/${reviewId}/applications`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review applications response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataImportReviewWarnings(
  apiBaseUrl: string,
  reviewId: string,
  options: FetchHealthOptions = {},
): Promise<DataReviewWarning[]> {
  const parsed = z
    .array(DataReviewWarningSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/data-import-reviews/${reviewId}/warnings`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data import review warnings response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchDataApplication(
  apiBaseUrl: string,
  applicationId: string,
  options: FetchHealthOptions = {},
): Promise<DataReviewApplicationResult> {
  const parsed = DataReviewApplicationResultSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/data-applications/${applicationId}`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Data application response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchStudentDataImportReviews(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<DataImportReviewSession[]> {
  const parsed = z
    .array(DataImportReviewSessionSchema)
    .safeParse(
      await fetchJson(
        apiBaseUrl,
        `/api/v1/students/${studentId}/data-import-reviews`,
        options,
      ),
    );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Student data import reviews response did not match the expected schema",
    );
  }
  return parsed.data;
}

export async function fetchActiveCourseStateSnapshot(
  apiBaseUrl: string,
  studentId: string,
  options: FetchHealthOptions = {},
): Promise<CourseStateSnapshotDetail> {
  const parsed = CourseStateSnapshotDetailSchema.safeParse(
    await fetchJson(
      apiBaseUrl,
      `/api/v1/students/${studentId}/course-state-snapshots/active`,
      options,
    ),
  );
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Active course-state snapshot response did not match the expected schema",
    );
  }
  return parsed.data;
}
