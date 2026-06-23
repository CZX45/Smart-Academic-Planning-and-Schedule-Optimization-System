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
