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

export type RequirementEvaluation = z.infer<
  typeof RequirementEvaluationSchema
>;

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

async function fetchJson(
  apiBaseUrl: string,
  path: string,
  options: RequestInit & FetchHealthOptions = {},
): Promise<unknown> {
  const { fetchFn, timeoutMs, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await (fetchFn ?? fetch)(buildApiUrl(apiBaseUrl, path), {
      cache: "no-store",
      ...requestOptions,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiRequestError(
        `API request to ${path} failed with status ${response.status}`,
      );
    }

    return await response.json();
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
    await fetchJson(apiBaseUrl, `/api/v1/students/${studentId}/degree-audits/latest`, options),
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
  const parsed = z.array(RequirementEvaluationSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/degree-audits/${auditId}/requirements`, options),
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
  const parsed = z.array(ScenarioProgramSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-scenarios/${scenarioId}/programs`, options),
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
  const parsed = z.array(ScenarioProgramAuditSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-scenarios/${scenarioId}/audits`, options),
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
  const parsed = z.array(ScenarioCourseAllocationSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-scenarios/${scenarioId}/allocations`, options),
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
  const parsed = z.array(ScenarioWarningSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-scenarios/${scenarioId}/warnings`, options),
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
    await fetchJson(apiBaseUrl, `/api/v1/academic-scenarios/${scenarioId}/comparison`, options),
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
  const parsed = z.array(AcademicScenarioSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/students/${studentId}/academic-scenarios`, options),
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
    await fetchJson(apiBaseUrl, `/api/v1/eligibility-checks/${checkId}`, options),
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
  const parsed = z.array(CourseEligibilityCheckSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/students/${studentId}/eligibility-checks`, options),
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
  const parsed = z.array(AcademicPlanTermSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-plans/${planId}/terms`, options),
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
  const parsed = z.array(AcademicPlanCourseSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-plans/${planId}/courses`, options),
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
  const parsed = z.array(AcademicPlanWarningSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/academic-plans/${planId}/warnings`, options),
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
  const parsed = z.array(AcademicPlanRunSchema).safeParse(
    await fetchJson(apiBaseUrl, `/api/v1/students/${studentId}/academic-plans`, options),
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
