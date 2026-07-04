"use client";

import {
  ApiRequestError,
  ApiResponseSchemaError,
  compareAcademicPlans,
  compareAcademicScenarios,
  compareScheduleOptimizations,
  createAcademicPlan,
  createAcademicScenario,
  createDataImport,
  createDataImportReview,
  createCourseEligibilityCheck,
  createDegreeAudit,
  createScheduleOptimization,
  applyDataImportReview,
  fetchAcademicScenarioAllocations,
  fetchAcademicScenarioAudits,
  fetchAcademicScenarioComparison,
  fetchAcademicScenarioPrograms,
  fetchAcademicScenarioWarnings,
  fetchDataImportReviewApplications,
  fetchDataImportReviewRecords,
  fetchDataImportReviewWarnings,
  fetchDataImportMappingCandidates,
  fetchDataImportPreview,
  fetchDataImportRecords,
  fetchDataImportWarnings,
  fetchStudentDataImportReviews,
  fetchDegreeAuditRequirements,
  fetchHealth,
  fetchLatestDegreeAudit,
  fetchSectionMonitorAlerts,
  fetchSectionMonitorTargets,
  fetchStudentDataImports,
  fetchStudentScheduleOptimizations,
  fetchStudentAcademicPlans,
  fetchStudentEligibilityChecks,
  fetchStudentAcademicScenarios,
  formatAcademicTimestamp,
  formatBeforeAfterValue,
  getAcademicEmptyStateCopy,
  getAcademicStatusBadge,
  getAdvisoryLabels,
  updateImportedRecordReview,
  validateDataImport,
  type AcademicPlanComparison,
  type AcademicPlanDetail,
  type AcademicPlanRun,
  type AcademicScenario,
  type AcademicEmptyStateKey,
  type AdvisoryLabelKey,
  type CourseEligibilityCheck,
  type DataApplicationRun,
  type DataImportRun,
  type DataImportReviewSession,
  type DataReviewApplicationResult,
  type DataReviewWarning,
  type DegreeAuditRun,
  type HealthResponse,
  type ImportedRecord,
  type ImportedRecordReview,
  type ImportMappingCandidate,
  type ImportPreviewSummary,
  type ImportValidationWarning,
  type RequirementEvaluation,
  type ScheduleOptimizationComparison,
  type ScheduleOptimizationDetail,
  type ScheduleOptimizationRun,
  type SectionMonitorAlert,
  type SectionMonitorTarget,
  type ScenarioComparisonSnapshot,
  type ScenarioCourseAllocation,
  type ScenarioProgram,
  type ScenarioProgramAudit,
  type ScenarioWarning,
} from "@sapsos/shared";
import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useState,
  useSyncExternalStore,
} from "react";
import { parsePublicEnv } from "../lib/env";

type HealthState =
  | { status: "loading" }
  | { status: "online"; payload: HealthResponse }
  | { status: "offline"; message: string };

type AuditState =
  | { status: "loading" }
  | { status: "empty"; message: string }
  | {
      status: "ready";
      audit: DegreeAuditRun;
      requirements: RequirementEvaluation[];
    }
  | { status: "failed"; message: string };
type AuditFallbackState = Exclude<AuditState, { status: "ready" }>;
type CandidateProgram = {
  id: string;
  label: string;
  scenarioType:
    | "ADD_MINOR"
    | "ADD_SECOND_MAJOR"
    | "ADD_CERTIFICATE"
    | "ADD_CONCENTRATION"
    | "CHANGE_PRIMARY_MAJOR";
  relationshipType:
    | "MINOR"
    | "SECOND_MAJOR"
    | "CERTIFICATE"
    | "CONCENTRATION"
    | "PRIMARY_MAJOR";
  programVersionId: string;
};
type ScenarioDetail = {
  scenario: AcademicScenario;
  programs: ScenarioProgram[];
  audits: ScenarioProgramAudit[];
  allocations: ScenarioCourseAllocation[];
  warnings: ScenarioWarning[];
  comparison: ScenarioComparisonSnapshot;
};
type ScenarioState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      detail: ScenarioDetail;
      comparisons: ScenarioComparisonSnapshot[];
      savedScenarios: AcademicScenario[];
    }
  | { status: "empty"; message: string }
  | { status: "failed"; message: string };
type EligibilityState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      result: CourseEligibilityCheck;
      history: CourseEligibilityCheck[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type PlannerState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      plan: AcademicPlanDetail;
      comparisons: AcademicPlanComparison[];
      savedPlans: AcademicPlanRun[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type ScheduleState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      schedule: ScheduleOptimizationDetail;
      comparisons: ScheduleOptimizationComparison[];
      savedRuns: ScheduleOptimizationRun[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type DataImportPreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      run: DataImportRun;
      records: ImportedRecord[];
      candidates: ImportMappingCandidate[];
      warnings: ImportValidationWarning[];
      preview: ImportPreviewSummary;
      savedImports: DataImportRun[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type ReadyDataImportPreviewState = Extract<
  DataImportPreviewState,
  { status: "ready" }
>;
type ImportSourceStateLabel =
  | "Real Imported Data - Auto Verified"
  | "Real Imported Data - Requires Review"
  | "Real Imported Data - Pending Review"
  | "Demo / Mock Data"
  | "No Import Loaded";
type DataReviewState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      review: DataImportReviewSession;
      records: ImportedRecordReview[];
      warnings: DataReviewWarning[];
      applications: DataApplicationRun[];
      applicationResult: DataReviewApplicationResult | null;
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type SectionMonitoringState =
  | { status: "loading" }
  | {
      status: "ready";
      targets: SectionMonitorTarget[];
      alerts: SectionMonitorAlert[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed"; message: string }
  | { status: "schema-error"; message: string };
type CandidateCourse = {
  id: string;
  label: string;
  courseId: string;
  sectionId?: string;
  termId: string;
  mode: "CURRENT" | "PROJECTED" | "REGISTRATION";
  plannedCorequisiteCourseIds?: string[];
};
type PlannerScope = {
  id: string;
  label: string;
  planningMode: "CURRENT_PROGRAM" | "WHAT_IF_SCENARIO";
  candidateProgramId?: string;
};
type SchedulePreset = {
  id: string;
  label: string;
  candidateCourseIds: string[];
  termId: string;
};
type ScheduleSectionChoice = {
  id: string;
  label: string;
  sectionId: string;
};
type DataImportSample = {
  id: string;
  label: string;
  importType:
    | "UNOFFICIAL_TRANSCRIPT"
    | "DEGREE_AUDIT_EXPORT"
    | "COURSE_CATALOG"
    | "SECTION_SCHEDULE"
    | "GENERIC_CSV"
    | "GENERIC_JSON";
  fileName: string;
  fileMimeType: string;
  content: string;
};
type MyProgressProgramSummary = {
  programName?: string;
  degree?: string;
  major?: string;
  department?: string;
  catalogYear?: number;
  cumulativeGpa?: number;
  institutionGpa?: number;
  anticipatedCompletionDate?: string;
};
type MyProgressCreditSummary = {
  totalAppliedCredits?: number;
  totalRequiredCredits?: number;
  completedCredits?: number;
  inProgressCredits?: number;
  plannedCredits?: number;
  remainingCredits?: number;
  completionPercent?: number;
};
type MyProgressException = {
  code: string;
  message: string;
  source?: string;
  severity?: string;
};
type MyProgressPreviewDisplay = {
  realImportStatus: string;
  programSummary: MyProgressProgramSummary;
  creditSummary: MyProgressCreditSummary;
  requirementGroups: Record<string, unknown>[];
  exceptions: MyProgressException[];
  autoConfirmedFieldCount: number;
  autoConfirmedCourseRowCount: number;
  overallConfidenceScore: number;
  downstreamAnalysisAllowed: boolean;
  canApplyVerifiedImport: boolean;
  rawSnapshot: Record<string, unknown>;
  fieldProvenance: Record<string, unknown>;
};
type ProductStatusCard = {
  ariaLabel: string;
  title: string;
  explanation: string;
  status: string | null;
  statusLabel?: string;
  nextAction: string;
  href: string;
  actionLabel: string;
  advisoryLabels?: AdvisoryLabelKey[];
};

function configuredApiBaseUrl(): string | undefined {
  try {
    return parsePublicEnv({
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    }).apiBaseUrl;
  } catch {
    return undefined;
  }
}

const apiBaseUrl = configuredApiBaseUrl();

function subscribeToStableBrowserValue(): () => void {
  return () => undefined;
}

function getBrowserOrigin(): string {
  return window.location.origin;
}

function getServerOrigin(): string {
  return "Detecting web origin";
}
const mockStudentId = "74874476-4024-5e2d-807a-fbb4ab620249";
const mockProgramVersionId = "f65bee76-6061-515f-a3df-cdf5567514af";
const fall2024TermId = "f0f8e29f-d65a-568c-b2aa-22ca4e5dcaec";
const spring2025TermId = "fed14bfe-972b-5392-8c72-379ceb879e85";
const candidatePrograms: CandidateProgram[] = [
  {
    id: "accounting-minor",
    label: "Mock Accounting Minor",
    scenarioType: "ADD_MINOR",
    relationshipType: "MINOR",
    programVersionId: "171bf5ab-6512-546c-99a1-40ec5ec3574a",
  },
  {
    id: "economics-minor",
    label: "Mock Economics Minor",
    scenarioType: "ADD_MINOR",
    relationshipType: "MINOR",
    programVersionId: "028a1b37-b581-5861-8e32-cff0e64927ee",
  },
  {
    id: "second-major",
    label: "Mock Second Major",
    scenarioType: "ADD_SECOND_MAJOR",
    relationshipType: "SECOND_MAJOR",
    programVersionId: "a5c90b25-f029-5670-a291-633039c13281",
  },
  {
    id: "certificate",
    label: "Mock Certificate",
    scenarioType: "ADD_CERTIFICATE",
    relationshipType: "CERTIFICATE",
    programVersionId: "ba1a3533-af04-54cf-bf7e-9c1b32b6c363",
  },
  {
    id: "change-major",
    label: "Mock Alternative Primary Major",
    scenarioType: "CHANGE_PRIMARY_MAJOR",
    relationshipType: "PRIMARY_MAJOR",
    programVersionId: "25bb6050-f3fa-5cd9-b3e2-3314e419be20",
  },
];
const candidateCourses: CandidateCourse[] = [
  {
    id: "fin-300-current",
    label: "FIN 300 · current prerequisite pass",
    courseId: "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
    termId: fall2024TermId,
    mode: "CURRENT",
  },
  {
    id: "fin-350-projected",
    label: "FIN 350 · projected conditional prerequisite",
    courseId: "e8af4b61-f180-5018-8437-e4981c728c56",
    termId: spring2025TermId,
    mode: "PROJECTED",
  },
  {
    id: "fin-400-registration",
    label: "FIN 400 HYB · permission and waitlist",
    courseId: "b59bb40b-e3d0-57e3-a424-0d9b8bd2f305",
    sectionId: "404cdd60-5eb4-5128-8ae3-ecbe6430f6d1",
    termId: spring2025TermId,
    mode: "REGISTRATION",
  },
  {
    id: "fin-410-coreq",
    label: "FIN 410 · explicit corequisite plan",
    courseId: "b2002864-645f-5bf6-b4e0-1d92e60bef8a",
    termId: spring2025TermId,
    mode: "REGISTRATION",
    plannedCorequisiteCourseIds: ["f184da12-a8fd-5471-a571-856cc12097e9"],
  },
  {
    id: "fin-450-current",
    label: "FIN 450 · missing prerequisite",
    courseId: "4b01b0ee-7b75-59ab-a01a-0b4bb2f7be4a",
    termId: spring2025TermId,
    mode: "CURRENT",
  },
  {
    id: "free-100-closed",
    label: "FREE 100 · no stored restrictions, closed section",
    courseId: "ba71f086-848f-51e0-9b7f-d72be59cf1d7",
    sectionId: "3ff503ba-0b3b-5e2c-baea-45de63142192",
    termId: fall2024TermId,
    mode: "REGISTRATION",
  },
];
const plannerScopes: PlannerScope[] = [
  {
    id: "current-program",
    label: "Current Mock BS Finance",
    planningMode: "CURRENT_PROGRAM",
  },
  {
    id: "what-if-accounting-minor",
    label: "What-if: add Mock Accounting Minor",
    planningMode: "WHAT_IF_SCENARIO",
    candidateProgramId: "accounting-minor",
  },
];
const plannerStartTerms = [
  { id: fall2024TermId, label: "Fall 2024" },
  { id: spring2025TermId, label: "Spring 2025" },
];
const schedulePresets: SchedulePreset[] = [
  {
    id: "fall-fin-300-403",
    label: "Fall 2024: FIN 300 + FIN 403",
    termId: fall2024TermId,
    candidateCourseIds: [
      "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
      "9413e6c7-26a0-5acf-9de4-88b132dc802d",
    ],
  },
  {
    id: "fall-fin-300",
    label: "Fall 2024: FIN 300 only",
    termId: fall2024TermId,
    candidateCourseIds: ["e6ab2a34-d85a-5446-875e-83fd36d5b08e"],
  },
];
const scheduleSectionChoices: ScheduleSectionChoice[] = [
  {
    id: "none",
    label: "None",
    sectionId: "",
  },
  {
    id: "fin-403-002",
    label: "Pin FIN 403 002",
    sectionId: "b4af4050-6534-5112-8351-c572d43bec95",
  },
  {
    id: "fin-403-friday",
    label: "Pin FIN 403 Friday",
    sectionId: "27e7ccdb-06ed-558d-972b-ec6dab0166de",
  },
  {
    id: "fin-300-web",
    label: "Exclude FIN 300 WEB",
    sectionId: "d532bfdd-4f45-574c-87f6-900565e163ee",
  },
  {
    id: "fin-300-afternoon",
    label: "Exclude FIN 300 AFT",
    sectionId: "2c2da55d-20aa-521c-938d-f35caee39eba",
  },
];
const sanitizedMyProgressSampleId = "sanitized-kean-myprogress-sample";
const sanitizedMyProgressSampleContent = JSON.stringify({
  page_type: "KEAN_MY_PROGRESS_PAGE",
  sampleNotice:
    "Sanitized local test data only. Not official school policy and not portal-sourced real student data.",
  programSummary: {
    programName: "Finance, BS",
    degree: "Bachelor of Science",
    major: "Finance",
    department: "Accounting & Finance",
    catalogYear: 2024,
    cumulativeGpa: 3.916,
    institutionGpa: 3.916,
    anticipatedCompletionDate: "12/20/2028",
  },
  creditSummary: {
    totalAppliedCredits: 104,
    totalRequiredCredits: 120,
    completedCredits: 67,
    inProgressCredits: 24,
    plannedCredits: 13,
    remainingCredits: 16,
    completionPercent: 86.67,
  },
  progressBarSegments: [
    { label: "Completed", credits: 67 },
    { label: "In Progress", credits: 24 },
    { label: "Planned", credits: 13 },
  ],
  fieldProvenance: {
    programName: {
      source: "sanitized-kean-my-progress-finance-summary.html",
      confidence: "high",
      rawText: "Finance, BS",
    },
    catalogYear: {
      source: "sanitized-kean-my-progress-finance-summary.html",
      confidence: "high",
      rawText: "2024",
    },
    totalAppliedCredits: {
      source: "sanitized-kean-my-progress-finance-summary.html",
      confidence: "high",
      rawText: "104 of 120",
    },
    completionPercent: {
      source: "sanitized-kean-my-progress-finance-summary.html",
      confidence: "high",
      rawText: "67 + 24 + 13 of 120",
    },
  },
  requirementGroups: [
    {
      name: "GE Foundation Requirements 13 S.H.",
      statusText: "4 of 5 Completed",
      credits: 13,
      confidence: "high",
      requiresReview: false,
    },
  ],
  courseRows: [],
  validation: {
    status: "AUTO_VERIFIED",
    exceptionCount: 0,
    exceptions: [],
    autoConfirmedFieldCount: 14,
    autoConfirmedCourseRowCount: 0,
    overallConfidenceScore: 0.98,
    downstreamAnalysisAllowed: true,
  },
  rawSnapshot: {
    fixture:
      "apps/extension/tests/fixtures/kean-my-progress-finance-summary.html",
    progressBarText: "67 24 13",
    visibleTextSample:
      "My Progress Finance, BS Catalog 2024 GPA 3.916 Total Credits 104 of 120",
  },
});
const dataImportSamples: DataImportSample[] = [
  {
    id: "mock-transcript-csv",
    label: "Mock transcript CSV",
    importType: "UNOFFICIAL_TRANSCRIPT",
    fileName: "mock-transcript.csv",
    fileMimeType: "text/csv",
    content: [
      "term,course_code,title,grade,credits,status",
      "2024FA,FIN 300,Mock Managerial Finance,B,3.0,COMPLETED",
      "2024FA,FIN 999,Unreviewed Special Topic,A,3.0,COMPLETED",
    ].join("\n"),
  },
  {
    id: "mock-degree-audit-json",
    label: "Mock degree audit JSON",
    importType: "DEGREE_AUDIT_EXPORT",
    fileName: "mock-degree-audit.json",
    fileMimeType: "application/json",
    content: JSON.stringify({
      records: [
        {
          term: "2024FA",
          course_code: "FIN 300",
          title: "Mock Managerial Finance",
          credits: "3.0",
          status: "SATISFIED",
        },
        {
          term: "2025SP",
          course_code: "FIN 999",
          title: "Unreviewed Elective Placeholder",
          credits: "3.0",
          status: "MANUAL_REVIEW_REQUIRED",
        },
      ],
    }),
  },
  {
    id: sanitizedMyProgressSampleId,
    label: "Sanitized Kean MyProgress sample (local test only)",
    importType: "DEGREE_AUDIT_EXPORT",
    fileName: "sanitized-kean-myprogress-finance.json",
    fileMimeType: "application/json",
    content: sanitizedMyProgressSampleContent,
  },
];

function describeHealthError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected health response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "Unknown API health error";
}

function describeAuditError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected degree audit response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "Unknown degree audit error";
}

function describeScenarioError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected academic scenario response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error
    ? error.message
    : "Unknown what-if scenario error";
}

function describeEligibilityError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected course eligibility response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error
    ? error.message
    : "Unknown course eligibility error";
}

function describePlannerError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected academic plan response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error
    ? error.message
    : "Unknown academic planner error";
}

function describeScheduleError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected schedule optimization response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error
    ? error.message
    : "Unknown schedule optimizer error";
}

function describeDataImportError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected data import response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "Unknown data import error";
}

function describeSectionMonitoringError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected section monitoring response shape.";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error
    ? error.message
    : "Unknown section monitoring error";
}

function localApiRestartGuidance(): string {
  return `API may be stale or not restarted. Restart API and web dev servers, check that the browser port is allowed by CORS, and verify the current API base URL: ${
    apiBaseUrl ?? "not configured"
  }.`;
}

function describeApiRequestFailure(error: ApiRequestError): string {
  return `${error.message} ${localApiRestartGuidance()}`;
}

function isNotFound(error: unknown): boolean {
  return (
    error instanceof ApiRequestError && error.message.includes("status 404")
  );
}

function formatCredits(value: string): string {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  });
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

function recordFromUnknown(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function recordsFromUnknown(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value
        .map(recordFromUnknown)
        .filter((item) => Object.keys(item).length > 0)
    : [];
}

function numberFromUnknown(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value !== "string" || value.trim().length === 0) {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function stringFromUnknown(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0
    ? value
    : undefined;
}

function myProgressPreviewFromSummary(
  preview: ImportPreviewSummary,
): MyProgressPreviewDisplay | null {
  const payload = preview.summary_payload;
  const realImportStatus = stringFromUnknown(payload.real_import_status);
  if (!realImportStatus?.startsWith("REAL_IMPORTED_DATA")) {
    return null;
  }
  const program = recordFromUnknown(payload.program_summary);
  const credits = recordFromUnknown(payload.credit_summary);
  const exceptions = recordsFromUnknown(payload.exceptions).map(
    (exception) => ({
      code: stringFromUnknown(exception.code) ?? "UNKNOWN_EXCEPTION",
      message:
        stringFromUnknown(exception.message) ?? "Manual review is required.",
      source: stringFromUnknown(exception.source),
      severity: stringFromUnknown(exception.severity),
    }),
  );
  return {
    realImportStatus,
    programSummary: {
      programName: stringFromUnknown(program.programName),
      degree: stringFromUnknown(program.degree),
      major: stringFromUnknown(program.major),
      department: stringFromUnknown(program.department),
      catalogYear: numberFromUnknown(program.catalogYear),
      cumulativeGpa: numberFromUnknown(program.cumulativeGpa),
      institutionGpa: numberFromUnknown(program.institutionGpa),
      anticipatedCompletionDate: stringFromUnknown(
        program.anticipatedCompletionDate,
      ),
    },
    creditSummary: {
      totalAppliedCredits: numberFromUnknown(credits.totalAppliedCredits),
      totalRequiredCredits: numberFromUnknown(credits.totalRequiredCredits),
      completedCredits: numberFromUnknown(credits.completedCredits),
      inProgressCredits: numberFromUnknown(credits.inProgressCredits),
      plannedCredits: numberFromUnknown(credits.plannedCredits),
      remainingCredits: numberFromUnknown(credits.remainingCredits),
      completionPercent: numberFromUnknown(credits.completionPercent),
    },
    requirementGroups: recordsFromUnknown(payload.requirement_groups),
    exceptions,
    autoConfirmedFieldCount:
      numberFromUnknown(payload.auto_confirmed_field_count) ?? 0,
    autoConfirmedCourseRowCount:
      numberFromUnknown(payload.auto_confirmed_course_row_count) ?? 0,
    overallConfidenceScore:
      numberFromUnknown(payload.overall_confidence_score) ?? 0,
    downstreamAnalysisAllowed: payload.downstream_analysis_allowed === true,
    canApplyVerifiedImport: payload.can_apply_verified_import === true,
    rawSnapshot: recordFromUnknown(payload.raw_snapshot),
    fieldProvenance: recordFromUnknown(payload.field_provenance),
  };
}

function myProgressPreviewFromState(
  state: DataImportPreviewState,
): MyProgressPreviewDisplay | null {
  return state.status === "ready"
    ? myProgressPreviewFromSummary(state.preview)
    : null;
}

function preferMyProgressImports(
  savedImports: DataImportRun[],
): DataImportRun[] {
  const degreeAuditRuns = savedImports.filter(
    (run) => run.import_type === "DEGREE_AUDIT_EXPORT",
  );
  const otherRuns = savedImports.filter(
    (run) => run.import_type !== "DEGREE_AUDIT_EXPORT",
  );
  return [...degreeAuditRuns, ...otherRuns];
}

async function loadDataImportPreviewState(
  baseUrl: string,
  run: DataImportRun,
  savedImports: DataImportRun[],
): Promise<ReadyDataImportPreviewState> {
  const [records, candidates, warnings, preview] = await Promise.all([
    fetchDataImportRecords(baseUrl, run.id, { timeoutMs: 5_000 }),
    fetchDataImportMappingCandidates(baseUrl, run.id, {
      timeoutMs: 5_000,
    }),
    fetchDataImportWarnings(baseUrl, run.id, { timeoutMs: 5_000 }),
    fetchDataImportPreview(baseUrl, run.id, { timeoutMs: 5_000 }),
  ]);
  return {
    status: "ready",
    run,
    records,
    candidates,
    warnings,
    preview,
    savedImports,
  };
}

async function loadPreferredDataImportPreviewState(
  baseUrl: string,
  savedImports: DataImportRun[],
): Promise<ReadyDataImportPreviewState | null> {
  let fallback: ReadyDataImportPreviewState | null = null;
  for (const run of preferMyProgressImports(savedImports)) {
    const previewState = await loadDataImportPreviewState(
      baseUrl,
      run,
      savedImports,
    );
    if (myProgressPreviewFromSummary(previewState.preview)) {
      return previewState;
    }
    fallback ??= previewState;
  }
  return fallback;
}

function importModeLabel(
  display: MyProgressPreviewDisplay | null,
): ImportSourceStateLabel {
  if (!display) {
    return "Demo / Mock Data";
  }
  if (
    display.realImportStatus === "REAL_IMPORTED_DATA_AUTO_VERIFIED" &&
    display.downstreamAnalysisAllowed &&
    display.canApplyVerifiedImport &&
    display.exceptions.length === 0
  ) {
    return "Real Imported Data - Auto Verified";
  }
  if (
    display.exceptions.length > 0 ||
    !display.downstreamAnalysisAllowed ||
    !display.canApplyVerifiedImport
  ) {
    return "Real Imported Data - Requires Review";
  }
  return "Real Imported Data - Pending Review";
}

function dashboardSourceLabel(
  display: MyProgressPreviewDisplay | null,
  reviewState: DataReviewState,
  auditState: AuditState,
  dataImportState: DataImportPreviewState,
): ImportSourceStateLabel {
  if (display) {
    return importModeLabel(display);
  }
  if (
    dataImportState.status === "failed" ||
    dataImportState.status === "offline" ||
    dataImportState.status === "schema-error"
  ) {
    return "No Import Loaded";
  }
  return auditState.status === "ready"
    ? "Demo / Mock Data"
    : "No Import Loaded";
}

function canUseDownstreamAnalysis(
  display: MyProgressPreviewDisplay | null,
): boolean {
  return Boolean(
    display?.downstreamAnalysisAllowed &&
    display.canApplyVerifiedImport &&
    display.exceptions.length === 0,
  );
}

export default function Home() {
  const webOrigin = useSyncExternalStore(
    subscribeToStableBrowserValue,
    getBrowserOrigin,
    getServerOrigin,
  );
  const [health, setHealth] = useState<HealthState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [auditState, setAuditState] = useState<AuditState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : {
          status: "failed",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [selectedCandidateId, setSelectedCandidateId] = useState(
    candidatePrograms[0].id,
  );
  const [scenarioState, setScenarioState] = useState<ScenarioState>({
    status: "idle",
  });
  const [selectedCourseId, setSelectedCourseId] = useState(
    candidateCourses[0].id,
  );
  const [eligibilityState, setEligibilityState] = useState<EligibilityState>(
    () =>
      apiBaseUrl
        ? { status: "idle" }
        : {
            status: "offline",
            message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
          },
  );
  const [selectedPlannerScopeId, setSelectedPlannerScopeId] = useState(
    plannerScopes[0].id,
  );
  const [selectedPlannerStartTermId, setSelectedPlannerStartTermId] = useState(
    plannerStartTerms[0].id,
  );
  const [termsToPlan, setTermsToPlan] = useState(4);
  const [minimumCredits, setMinimumCredits] = useState(3);
  const [preferredCredits, setPreferredCredits] = useState(6);
  const [maximumCredits, setMaximumCredits] = useState(9);
  const [plannerState, setPlannerState] = useState<PlannerState>(() =>
    apiBaseUrl
      ? { status: "idle" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [selectedSchedulePresetId, setSelectedSchedulePresetId] = useState(
    schedulePresets[0].id,
  );
  const [scheduleNoFriday, setScheduleNoFriday] = useState(true);
  const [scheduleAvoidTuesdayBlock, setScheduleAvoidTuesdayBlock] =
    useState(true);
  const [schedulePreferOnline, setSchedulePreferOnline] = useState(false);
  const [schedulePreferCompact, setSchedulePreferCompact] = useState(true);
  const [schedulePreferFewerDays, setSchedulePreferFewerDays] = useState(true);
  const [schedulePreferNoGaps, setSchedulePreferNoGaps] = useState(true);
  const [schedulePreferMorning, setSchedulePreferMorning] = useState(true);
  const [schedulePreferAfternoon, setSchedulePreferAfternoon] = useState(false);
  const [schedulePinnedSectionChoiceId, setSchedulePinnedSectionChoiceId] =
    useState("fin-403-002");
  const [scheduleExcludedSectionChoiceId, setScheduleExcludedSectionChoiceId] =
    useState("none");
  const [scheduleDiversityMode, setScheduleDiversityMode] = useState<
    "STANDARD" | "HIGH"
  >("HIGH");
  const [scheduleAllowPartialOptions, setScheduleAllowPartialOptions] =
    useState(true);
  const [scheduleState, setScheduleState] = useState<ScheduleState>(() =>
    apiBaseUrl
      ? { status: "idle" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [selectedDataImportSampleId, setSelectedDataImportSampleId] = useState(
    dataImportSamples[0].id,
  );
  const [dataImportState, setDataImportState] =
    useState<DataImportPreviewState>(() =>
      apiBaseUrl
        ? { status: "idle" }
        : {
            status: "offline",
            message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
          },
    );
  const [dataReviewState, setDataReviewState] = useState<DataReviewState>(() =>
    apiBaseUrl
      ? { status: "idle" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [sectionMonitoringState, setSectionMonitoringState] =
    useState<SectionMonitoringState>(() =>
      apiBaseUrl
        ? { status: "loading" }
        : {
            status: "offline",
            message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
          },
    );

  useEffect(() => {
    let cancelled = false;

    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }

    async function loadDegreeProgress(baseUrl: string): Promise<void> {
      try {
        const payload = await fetchHealth(baseUrl, { timeoutMs: 5_000 });
        if (cancelled) {
          return;
        }
        setHealth({ status: "online", payload });

        let audit: DegreeAuditRun;
        try {
          audit = await fetchLatestDegreeAudit(baseUrl, mockStudentId, {
            timeoutMs: 5_000,
          });
        } catch (error: unknown) {
          if (!isNotFound(error)) {
            throw error;
          }
          audit = await createDegreeAudit(
            baseUrl,
            {
              student_profile_id: mockStudentId,
              program_version_id: mockProgramVersionId,
              calculation_mode: "PROJECTED",
            },
            { timeoutMs: 5_000 },
          );
        }

        const requirements = await fetchDegreeAuditRequirements(
          baseUrl,
          audit.id,
          {
            timeoutMs: 5_000,
          },
        );
        if (!cancelled) {
          setAuditState(
            requirements.length === 0
              ? {
                  status: "empty",
                  message:
                    "No degree audit snapshot results are available yet.",
                }
              : { status: "ready", audit, requirements },
          );
        }
      } catch (error: unknown) {
        if (!cancelled) {
          const message = describeAuditError(error);
          setAuditState({ status: "failed", message });
          if (health.status !== "online") {
            setHealth({
              status: "offline",
              message: describeHealthError(error),
            });
          }
        }
      }
    }

    void loadDegreeProgress(apiBaseUrl);

    return () => {
      cancelled = true;
    };
  }, [health.status]);

  useEffect(() => {
    let cancelled = false;

    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }

    async function loadSectionMonitoring(baseUrl: string): Promise<void> {
      setSectionMonitoringState({ status: "loading" });
      try {
        const [targets, alerts] = await Promise.all([
          fetchSectionMonitorTargets(baseUrl, mockStudentId, {
            timeoutMs: 5_000,
          }),
          fetchSectionMonitorAlerts(baseUrl, mockStudentId, {
            timeoutMs: 5_000,
          }),
        ]);
        if (cancelled) {
          return;
        }
        setSectionMonitoringState({ status: "ready", targets, alerts });
      } catch (error: unknown) {
        if (!cancelled) {
          setSectionMonitoringState({
            status:
              error instanceof ApiResponseSchemaError
                ? "schema-error"
                : "failed",
            message: describeSectionMonitoringError(error),
          });
        }
      }
    }

    void loadSectionMonitoring(apiBaseUrl);

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }

    async function loadLatestImportPreview(baseUrl: string): Promise<void> {
      try {
        const savedImports = await fetchStudentDataImports(
          baseUrl,
          mockStudentId,
          { timeoutMs: 5_000 },
        );
        if (cancelled || savedImports.length === 0) {
          return;
        }
        const previewState = await loadPreferredDataImportPreviewState(
          baseUrl,
          savedImports,
        );
        if (!previewState) {
          return;
        }
        if (!cancelled) {
          setDataImportState(previewState);
        }
      } catch (error: unknown) {
        if (!cancelled) {
          setDataImportState({
            status:
              error instanceof ApiResponseSchemaError
                ? "schema-error"
                : "failed",
            message: describeDataImportError(error),
          });
        }
      }
    }

    void loadLatestImportPreview(apiBaseUrl);

    return () => {
      cancelled = true;
    };
  }, []);

  const warnings =
    auditState.status === "ready"
      ? auditState.requirements.flatMap((requirement) => requirement.warnings)
      : [];
  const myProgressPreview = myProgressPreviewFromState(dataImportState);
  const currentImportMode = dashboardSourceLabel(
    myProgressPreview,
    dataReviewState,
    auditState,
    dataImportState,
  );
  const downstreamAnalysisAllowed = canUseDownstreamAnalysis(myProgressPreview);

  return (
    <main>
      <section className="progress-shell">
        <div className="topbar">
          <p className={`badge ${health.status === "online" ? "ok" : "warn"}`}>
            {health.status === "loading"
              ? "API checking"
              : health.status === "online"
                ? "API connected"
                : "API unavailable"}
          </p>
          <p className="notice compact">{currentImportMode}</p>
        </div>

        <DevelopmentDiagnostics
          apiBaseUrl={apiBaseUrl}
          webOrigin={webOrigin}
          health={health}
          dataImportState={dataImportState}
          sourceLabel={currentImportMode}
          downstreamAnalysisAllowed={downstreamAnalysisAllowed}
        />

        <h1>Degree Progress</h1>
        <p className="subtle">
          Advisor confirmation is required for high-impact academic guidance.
        </p>

        <ProductStatusDashboard
          auditState={auditState}
          dataImportState={dataImportState}
          myProgressPreview={myProgressPreview}
          dataReviewState={dataReviewState}
          scenarioState={scenarioState}
          scheduleState={scheduleState}
          sectionMonitoringState={sectionMonitoringState}
        />

        {auditState.status === "ready" ? (
          <DegreeProgress
            audit={auditState.audit}
            requirements={auditState.requirements}
            myProgressPreview={myProgressPreview}
          />
        ) : (
          <AuditFallback state={auditState} health={health} />
        )}

        {warnings.length > 0 ? (
          <section className="warning-panel" aria-label="Advisor warnings">
            <h2>Warnings</h2>
            <ul>
              {warnings.map((warning) => (
                <li key={warning.id}>
                  <strong>{warning.warning_code}</strong>
                  <span>{warning.message}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <WhatIfAnalysis
          selectedCandidateId={selectedCandidateId}
          setSelectedCandidateId={setSelectedCandidateId}
          scenarioState={scenarioState}
          setScenarioState={setScenarioState}
          canUseDownstreamAnalysis={downstreamAnalysisAllowed}
          sourceLabel={currentImportMode}
        />

        <CourseEligibilityChecker
          selectedCourseId={selectedCourseId}
          setSelectedCourseId={setSelectedCourseId}
          eligibilityState={eligibilityState}
          setEligibilityState={setEligibilityState}
        />

        <AcademicPlanner
          selectedPlannerScopeId={selectedPlannerScopeId}
          setSelectedPlannerScopeId={setSelectedPlannerScopeId}
          selectedPlannerStartTermId={selectedPlannerStartTermId}
          setSelectedPlannerStartTermId={setSelectedPlannerStartTermId}
          termsToPlan={termsToPlan}
          setTermsToPlan={setTermsToPlan}
          minimumCredits={minimumCredits}
          setMinimumCredits={setMinimumCredits}
          preferredCredits={preferredCredits}
          setPreferredCredits={setPreferredCredits}
          maximumCredits={maximumCredits}
          setMaximumCredits={setMaximumCredits}
          plannerState={plannerState}
          setPlannerState={setPlannerState}
          canUseDownstreamAnalysis={downstreamAnalysisAllowed}
          sourceLabel={currentImportMode}
        />

        <SemesterScheduleBuilder
          selectedSchedulePresetId={selectedSchedulePresetId}
          setSelectedSchedulePresetId={setSelectedSchedulePresetId}
          scheduleNoFriday={scheduleNoFriday}
          setScheduleNoFriday={setScheduleNoFriday}
          scheduleAvoidTuesdayBlock={scheduleAvoidTuesdayBlock}
          setScheduleAvoidTuesdayBlock={setScheduleAvoidTuesdayBlock}
          schedulePreferOnline={schedulePreferOnline}
          setSchedulePreferOnline={setSchedulePreferOnline}
          schedulePreferCompact={schedulePreferCompact}
          setSchedulePreferCompact={setSchedulePreferCompact}
          schedulePreferFewerDays={schedulePreferFewerDays}
          setSchedulePreferFewerDays={setSchedulePreferFewerDays}
          schedulePreferNoGaps={schedulePreferNoGaps}
          setSchedulePreferNoGaps={setSchedulePreferNoGaps}
          schedulePreferMorning={schedulePreferMorning}
          setSchedulePreferMorning={setSchedulePreferMorning}
          schedulePreferAfternoon={schedulePreferAfternoon}
          setSchedulePreferAfternoon={setSchedulePreferAfternoon}
          schedulePinnedSectionChoiceId={schedulePinnedSectionChoiceId}
          setSchedulePinnedSectionChoiceId={setSchedulePinnedSectionChoiceId}
          scheduleExcludedSectionChoiceId={scheduleExcludedSectionChoiceId}
          setScheduleExcludedSectionChoiceId={
            setScheduleExcludedSectionChoiceId
          }
          scheduleDiversityMode={scheduleDiversityMode}
          setScheduleDiversityMode={setScheduleDiversityMode}
          scheduleAllowPartialOptions={scheduleAllowPartialOptions}
          setScheduleAllowPartialOptions={setScheduleAllowPartialOptions}
          scheduleState={scheduleState}
          setScheduleState={setScheduleState}
          canUseDownstreamAnalysis={downstreamAnalysisAllowed}
          sourceLabel={currentImportMode}
        />

        <DataImportPreviewPanel
          selectedDataImportSampleId={selectedDataImportSampleId}
          setSelectedDataImportSampleId={setSelectedDataImportSampleId}
          dataImportState={dataImportState}
          setDataImportState={setDataImportState}
          dataReviewState={dataReviewState}
          setDataReviewState={setDataReviewState}
        />

        <SectionMonitoringPanel state={sectionMonitoringState} />
      </section>
    </main>
  );
}

function DevelopmentDiagnostics({
  apiBaseUrl,
  webOrigin,
  health,
  dataImportState,
  sourceLabel,
  downstreamAnalysisAllowed,
}: {
  apiBaseUrl: string | undefined;
  webOrigin: string;
  health: HealthState;
  dataImportState: DataImportPreviewState;
  sourceLabel: ImportSourceStateLabel;
  downstreamAnalysisAllowed: boolean;
}) {
  const shouldShowGuidance =
    health.status === "offline" ||
    dataImportState.status === "offline" ||
    dataImportState.status === "failed" ||
    dataImportState.status === "schema-error";
  const importStatus =
    dataImportState.status === "ready"
      ? `${sourceLabel} from ${dataImportState.run.source.source_type}`
      : `${sourceLabel}; import loader ${dataImportState.status}`;

  return (
    <section className="diagnostics-panel" aria-label="Development diagnostics">
      <h2>Local Diagnostics</h2>
      <dl>
        <div>
          <dt>API base URL</dt>
          <dd>{apiBaseUrl ?? "Not configured"}</dd>
        </div>
        <div>
          <dt>Web origin</dt>
          <dd>{webOrigin}</dd>
        </div>
        <div>
          <dt>API connection status</dt>
          <dd>{health.status}</dd>
        </div>
        <div>
          <dt>Import source status</dt>
          <dd>{importStatus}</dd>
        </div>
        <div>
          <dt>Downstream analysis</dt>
          <dd>{downstreamAnalysisAllowed ? "Allowed" : "Blocked"}</dd>
        </div>
      </dl>
      {shouldShowGuidance ? (
        <p className="advisor-note">{localApiRestartGuidance()}</p>
      ) : null}
    </section>
  );
}

function AuditFallback({
  state,
  health,
}: {
  state: AuditFallbackState;
  health: HealthState;
}) {
  const title =
    state.status === "loading"
      ? "Loading audit"
      : state.status === "empty"
        ? "No degree audit snapshot yet"
        : "Audit unavailable";
  const message =
    state.status === "loading"
      ? "Checking for the latest mock degree audit snapshot."
      : state.status === "empty"
        ? state.message
        : state.message;

  return (
    <section className="state-panel" aria-live="polite">
      <h2>{title}</h2>
      <p>{message}</p>
      {health.status === "offline" ? <pre>{health.message}</pre> : null}
    </section>
  );
}

function DegreeProgress({
  audit,
  requirements,
  myProgressPreview,
}: {
  audit: DegreeAuditRun;
  requirements: RequirementEvaluation[];
  myProgressPreview: MyProgressPreviewDisplay | null;
}) {
  const program = myProgressPreview?.programSummary;
  const credits = myProgressPreview?.creditSummary;
  const hasRealMyProgress = myProgressPreview !== null;
  const myProgressRequirementGroups =
    myProgressPreview?.requirementGroups ?? [];
  return (
    <>
      <section
        className="summary-grid"
        id="degree-audit"
        aria-label="Degree audit summary"
      >
        <SummaryMetric
          label="Data Mode"
          value={importModeLabel(myProgressPreview)}
        />
        <SummaryMetric
          label="Program"
          value={program?.programName ?? "No real MyProgress import loaded"}
        />
        <SummaryMetric
          label="Audit Mode"
          value={statusLabel(audit.calculation_mode)}
        />
        {hasRealMyProgress ? (
          <>
            <SummaryMetric
              label="Catalog"
              value={
                program?.catalogYear
                  ? String(program.catalogYear)
                  : "Not loaded"
              }
            />
            {program?.degree ? (
              <SummaryMetric label="Degree" value={program.degree} />
            ) : null}
            {program?.department ? (
              <SummaryMetric label="Department" value={program.department} />
            ) : null}
            {program?.cumulativeGpa ? (
              <SummaryMetric
                label="GPA"
                value={program.cumulativeGpa.toFixed(3)}
              />
            ) : null}
            {program?.institutionGpa ? (
              <SummaryMetric
                label="Institution GPA"
                value={program.institutionGpa.toFixed(3)}
              />
            ) : null}
            {credits?.totalAppliedCredits !== undefined &&
            credits.totalRequiredCredits !== undefined ? (
              <SummaryMetric
                label="Total Credits"
                value={`${formatCredits(String(credits.totalAppliedCredits))} / ${formatCredits(
                  String(credits.totalRequiredCredits),
                )}`}
              />
            ) : null}
            <SummaryMetric
              label="Completed"
              value={formatCredits(String(credits?.completedCredits ?? 0))}
            />
            <SummaryMetric
              label="In Progress"
              value={formatCredits(String(credits?.inProgressCredits ?? 0))}
            />
            <SummaryMetric
              label="Planned"
              value={formatCredits(String(credits?.plannedCredits ?? 0))}
            />
            <SummaryMetric
              label="Remaining"
              value={formatCredits(String(credits?.remainingCredits ?? 0))}
            />
            <SummaryMetric
              label="Completion"
              value={`${Number(credits?.completionPercent ?? 0).toFixed(2)}%`}
            />
            {program?.anticipatedCompletionDate ? (
              <SummaryMetric
                label="Expected Completion"
                value={program.anticipatedCompletionDate}
              />
            ) : null}
          </>
        ) : (
          <>
            <SummaryMetric
              label="Current MyProgress Import"
              value="Not loaded"
            />
            <SummaryMetric label="Mock Values" value="Sample data only" />
          </>
        )}
      </section>

      {!hasRealMyProgress ? (
        <section
          className="state-panel"
          aria-label="No real MyProgress import loaded"
        >
          <h2>No real MyProgress import has been loaded yet</h2>
          <p>
            Demo / Mock Data is visible only as sample planning data. Mock
            values are sample data only and are not the active real academic
            state.
          </p>
          <ul className="compact-list">
            <li>Use the browser extension import from Kean MyProgress.</li>
            <li>Load a saved staging import from this local database.</li>
            <li>
              Load sanitized MyProgress sample for local testing only; it is not
              official school data.
            </li>
          </ul>
        </section>
      ) : null}

      <section className="requirement-tree" aria-label="Requirement Tree">
        <h2>
          {hasRealMyProgress
            ? "MyProgress Requirement Summary"
            : "Demo Requirement Tree"}
        </h2>
        {hasRealMyProgress ? (
          <>
            <p className="subtle">
              Showing high-confidence requirement groups from the staged
              MyProgress import. The older mock requirement snapshot is not used
              for the real imported summary.
            </p>
            <ul className="compact-list">
              <li>
                <strong>Downstream analysis</strong>
                <span>
                  {myProgressPreview.downstreamAnalysisAllowed
                    ? "Auto-verification passed with 0 exceptions."
                    : "Validation exceptions must be reviewed before use."}
                </span>
              </li>
              <li>
                <strong>Review scope</strong>
                <span>
                  Exception queue only; high-confidence rows do not require
                  manual row-by-row review.
                </span>
              </li>
            </ul>
            {myProgressRequirementGroups.length > 0 ? (
              myProgressRequirementGroups.map((group, index) => {
                const name =
                  stringFromUnknown(group.name) ??
                  stringFromUnknown(group.requirements) ??
                  `MyProgress requirement group ${index + 1}`;
                const statusText =
                  stringFromUnknown(group.statusText) ??
                  stringFromUnknown(group.status_text) ??
                  "High-confidence requirement group.";
                const confidence =
                  stringFromUnknown(group.confidence) ?? "high";
                return (
                  <article key={`${name}-${index}`} className="requirement-row">
                    <div className="requirement-detail">
                      <h3>{name}</h3>
                      <p>{statusText}</p>
                      <p className="advisor-note">
                        Auto-confirmed requirement row · {confidence} confidence
                      </p>
                    </div>
                  </article>
                );
              })
            ) : (
              <section className="state-panel">
                <h3>No MyProgress requirement groups</h3>
                <p>
                  The summary still preserves program, GPA, and credit fields;
                  missing requirement groups enter exception review.
                </p>
              </section>
            )}
          </>
        ) : (
          <>
            <p className="subtle">
              Sample requirement rows are shown only for development context
              until a real MyProgress import is loaded or confirmed.
            </p>
            {requirements.map((requirement) => (
              <details key={requirement.id} className="requirement-row">
                <summary>
                  <span>{requirement.requirement_name}</span>
                  <span
                    className={`status-pill ${requirement.status.toLowerCase()}`}
                  >
                    {statusLabel(requirement.status)}
                  </span>
                </summary>
                <div className="requirement-detail">
                  <dl>
                    <div>
                      <dt>Required</dt>
                      <dd>
                        {requirement.required_courses ?? "—"} courses /{" "}
                        {requirement.required_credits
                          ? formatCredits(requirement.required_credits)
                          : "—"}{" "}
                        credits
                      </dd>
                    </div>
                    <div>
                      <dt>Satisfied</dt>
                      <dd>
                        {requirement.satisfied_courses} courses /{" "}
                        {formatCredits(requirement.satisfied_credits)} credits
                      </dd>
                    </div>
                    <div>
                      <dt>Remaining</dt>
                      <dd>
                        {requirement.remaining_courses} courses /{" "}
                        {formatCredits(requirement.remaining_credits)} credits
                      </dd>
                    </div>
                  </dl>
                  <p>{requirement.explanation}</p>
                  {requirement.applications.length > 0 ? (
                    <ul className="applications">
                      {requirement.applications.map((application) => (
                        <li key={application.id}>
                          <strong>
                            {application.course_code ??
                              application.application_type}
                          </strong>
                          <span>
                            {statusLabel(application.application_type)} ·{" "}
                            {formatCredits(application.credit_amount)} credits
                            {application.grade
                              ? ` · grade ${application.grade}`
                              : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {requirement.warnings.some(
                    (warning) => warning.requires_advisor_confirmation,
                  ) ? (
                    <p className="advisor-note">
                      Advisor confirmation required.
                    </p>
                  ) : null}
                </div>
              </details>
            ))}
          </>
        )}
      </section>
    </>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProductStatusDashboard({
  auditState,
  dataImportState,
  myProgressPreview,
  dataReviewState,
  scenarioState,
  scheduleState,
  sectionMonitoringState,
}: {
  auditState: AuditState;
  dataImportState: DataImportPreviewState;
  myProgressPreview: MyProgressPreviewDisplay | null;
  dataReviewState: DataReviewState;
  scenarioState: ScenarioState;
  scheduleState: ScheduleState;
  sectionMonitoringState: SectionMonitoringState;
}) {
  const dataImportMode = importModeLabel(myProgressPreview);
  const cards: ProductStatusCard[] = [
    {
      ariaLabel: "Degree audit status card",
      title: "Degree audit",
      explanation: "Latest deterministic audit snapshot and requirement tree.",
      status:
        auditState.status === "ready"
          ? auditState.audit.status
          : auditState.status,
      nextAction:
        auditState.status === "ready"
          ? "Review requirement warnings and confirm high-impact guidance with an advisor."
          : "Load or generate a degree audit snapshot.",
      href: "#degree-audit",
      actionLabel: "Review audit",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
    {
      ariaLabel: "Data import review status card",
      title: "Data import review",
      explanation: "Exception review gate for staged imported records.",
      status: myProgressPreview
        ? myProgressPreview.realImportStatus
        : dataReviewState.status === "ready"
          ? dataReviewState.review.status
          : dataReviewState.status === "idle"
            ? null
            : dataReviewState.status,
      statusLabel: myProgressPreview
        ? dataImportMode
        : dataReviewState.status === "idle" ||
            dataReviewState.status === "empty"
          ? "No confirmed imports yet"
          : undefined,
      nextAction: myProgressPreview?.canApplyVerifiedImport
        ? "High-confidence MyProgress import is auto-verified; high-impact advice still needs school or advisor confirmation."
        : dataReviewState.status === "ready"
          ? "Review warnings before applying confirmed internal records."
          : "Preview or load a staging import, then review exceptions only.",
      href: "#data-import-preview",
      actionLabel: "Open review",
      advisoryLabels: myProgressPreview?.canApplyVerifiedImport
        ? ["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"]
        : ["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"],
    },
    {
      ariaLabel: "Browser extension import status card",
      title: "Browser extension import",
      explanation: "Visible-page import source that stays in staging first.",
      status:
        dataImportState.status === "ready" && myProgressPreview
          ? myProgressPreview.realImportStatus
          : "MANUAL_REVIEW_REQUIRED",
      statusLabel:
        dataImportState.status === "ready" && myProgressPreview
          ? dataImportMode
          : "Non-official imported data",
      nextAction:
        dataImportState.status === "ready" && myProgressPreview
          ? "MyProgress summary is staged; review the validation summary and exception queue."
          : "Inspect only user-opened pages, then stage imported data for exception review.",
      href: "#data-import-preview",
      actionLabel: "Review import",
      advisoryLabels: myProgressPreview?.canApplyVerifiedImport
        ? ["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"]
        : [
            "NON_OFFICIAL_IMPORTED_DATA",
            "MANUAL_REVIEW_REQUIRED",
            "ADVISORY_ONLY",
          ],
    },
    {
      ariaLabel: "Section monitoring status card",
      title: "Section monitoring",
      explanation: "Advisory comparison of user-triggered section snapshots.",
      status:
        sectionMonitoringState.status === "ready"
          ? sectionMonitoringState.alerts.length > 0
            ? "WARNING"
            : sectionMonitoringState.targets.length > 0
              ? "READY"
              : null
          : sectionMonitoringState.status,
      statusLabel:
        sectionMonitoringState.status === "ready"
          ? sectionMonitoringState.alerts.length > 0
            ? "Advisory alerts ready"
            : sectionMonitoringState.targets.length > 0
              ? "Monitoring targets ready"
              : "No section monitoring targets"
          : undefined,
      nextAction:
        sectionMonitoringState.status === "ready" &&
        sectionMonitoringState.alerts.length > 0
          ? "Verify any section change manually in the official portal."
          : "Import section-search data and choose sections to monitor manually.",
      href: "#section-monitoring",
      actionLabel: "Review alerts",
      advisoryLabels: [
        "NON_OFFICIAL_IMPORTED_DATA",
        "ADVISORY_ONLY",
        "VERIFY_IN_OFFICIAL_PORTAL",
      ],
    },
    {
      ariaLabel: "Schedule optimization status card",
      title: "Schedule optimization",
      explanation: "Section-level schedule options separate from planning.",
      status:
        scheduleState.status === "ready"
          ? scheduleState.schedule.status
          : scheduleState.status === "idle"
            ? null
            : scheduleState.status,
      statusLabel:
        scheduleState.status === "idle" || scheduleState.status === "empty"
          ? "No generated schedule plans"
          : undefined,
      nextAction:
        scheduleState.status === "ready"
          ? "Compare advisory schedule options and warnings."
          : "Build a schedule from a manually selected course set.",
      href: "#schedule-optimization",
      actionLabel: "Build a schedule",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
    {
      ariaLabel: "What-if planning status card",
      title: "What-if planning",
      explanation: "Scenario comparison for hypothetical program changes.",
      status:
        scenarioState.status === "ready"
          ? scenarioState.detail.scenario.status
          : scenarioState.status === "idle"
            ? null
            : scenarioState.status,
      statusLabel:
        scenarioState.status === "idle" || scenarioState.status === "empty"
          ? "No what-if scenarios"
          : undefined,
      nextAction:
        scenarioState.status === "ready"
          ? "Compare saved scenario assumptions and advisor warnings."
          : "Create scenario from a candidate program.",
      href: "#what-if-planning",
      actionLabel: "Create scenario",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
  ];

  return (
    <section className="product-status" aria-label="Product status dashboard">
      {cards.map((card) => (
        <StatusCard key={card.ariaLabel} card={card} />
      ))}
    </section>
  );
}

function StatusCard({ card }: { card: ProductStatusCard }) {
  const badge = getAcademicStatusBadge(card.status);
  const displayBadge = {
    ...badge,
    label: card.statusLabel ?? badge.label,
  };
  return (
    <article className="status-card" aria-label={card.ariaLabel}>
      <div className="status-card-heading">
        <h2>{card.title}</h2>
        <StatusBadge label={displayBadge.label} tone={displayBadge.tone} />
      </div>
      <p>{card.explanation}</p>
      <p>
        <strong>Next action:</strong> {card.nextAction}
      </p>
      {card.advisoryLabels ? (
        <AdvisoryLabels keys={card.advisoryLabels} />
      ) : null}
      <a className="status-action" href={card.href}>
        {card.actionLabel}
      </a>
    </article>
  );
}

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: ReturnType<typeof getAcademicStatusBadge>["tone"];
}) {
  return <span className={`ui-status-badge tone-${tone}`}>{label}</span>;
}

function AdvisoryLabels({ keys }: { keys: AdvisoryLabelKey[] }) {
  return (
    <ul className="advisory-labels">
      {getAdvisoryLabels(keys).map((label) => (
        <li key={label.text} className={`advisory-label tone-${label.tone}`}>
          {label.text}
        </li>
      ))}
    </ul>
  );
}

function EmptyState({
  copyKey,
  ariaLabel,
}: {
  copyKey: AcademicEmptyStateKey;
  ariaLabel: string;
}) {
  const copy = getAcademicEmptyStateCopy(copyKey);
  return (
    <section className="state-panel empty-state" aria-label={ariaLabel}>
      <h2>{copy.title}</h2>
      <p>{copy.explanation}</p>
      <p>
        <strong>Reason:</strong> {copy.reason}
      </p>
      <p>
        <strong>Next step:</strong> {copy.nextAction}
      </p>
      <p className="advisory-note">{copy.disclaimer}</p>
    </section>
  );
}

function WhatIfAnalysis({
  selectedCandidateId,
  setSelectedCandidateId,
  scenarioState,
  setScenarioState,
  canUseDownstreamAnalysis,
  sourceLabel,
}: {
  selectedCandidateId: string;
  setSelectedCandidateId: (value: string) => void;
  scenarioState: ScenarioState;
  setScenarioState: Dispatch<SetStateAction<ScenarioState>>;
  canUseDownstreamAnalysis: boolean;
  sourceLabel: ImportSourceStateLabel;
}) {
  const selectedCandidate =
    candidatePrograms.find(
      (candidate) => candidate.id === selectedCandidateId,
    ) ?? candidatePrograms[0];

  async function handleCreateScenario(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setScenarioState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before running what-if analysis.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScenarioState({
        status: "failed",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setScenarioState({ status: "loading" });
    try {
      const scenario = await createAcademicScenario(
        apiBaseUrl,
        {
          student_profile_id: mockStudentId,
          scenario_name:
            selectedCandidate.relationshipType === "PRIMARY_MAJOR"
              ? `Change to ${selectedCandidate.label}`
              : `Add ${selectedCandidate.label}`,
          scenario_type: selectedCandidate.scenarioType,
          calculation_mode: "PROJECTED",
          programs:
            selectedCandidate.relationshipType === "PRIMARY_MAJOR"
              ? [
                  {
                    program_version_id: selectedCandidate.programVersionId,
                    relationship_type: "PRIMARY_MAJOR",
                    priority: 0,
                  },
                ]
              : [
                  {
                    program_version_id: mockProgramVersionId,
                    relationship_type: "PRIMARY_MAJOR",
                    priority: 0,
                  },
                  {
                    program_version_id: selectedCandidate.programVersionId,
                    relationship_type: selectedCandidate.relationshipType,
                    priority: 10,
                  },
                ],
        },
        { timeoutMs: 8_000 },
      );
      const detail = await loadScenarioDetail(apiBaseUrl, scenario);
      setScenarioState({
        status: "ready",
        detail,
        comparisons: [],
        savedScenarios: [],
      });
    } catch (error: unknown) {
      setScenarioState({
        status: "failed",
        message: describeScenarioError(error),
      });
    }
  }

  async function handleCompareSaved(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setScenarioState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before comparing scenarios.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScenarioState({
        status: "failed",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    try {
      const savedScenarios = await fetchStudentAcademicScenarios(
        apiBaseUrl,
        mockStudentId,
        { timeoutMs: 5_000 },
      );
      if (savedScenarios.length < 2) {
        setScenarioState({
          status: "empty",
          message: "At least two saved scenarios are needed.",
        });
        return;
      }
      const selectedScenarios = savedScenarios.slice(0, 2);
      const comparisons = await compareAcademicScenarios(
        apiBaseUrl,
        selectedScenarios.map((scenario) => scenario.id),
        { timeoutMs: 5_000 },
      );
      setScenarioState((current) =>
        current.status === "ready"
          ? { ...current, comparisons, savedScenarios }
          : {
              status: "empty",
              message: "Create a scenario before comparing saved results.",
            },
      );
    } catch (error: unknown) {
      setScenarioState({
        status: "failed",
        message: describeScenarioError(error),
      });
    }
  }

  return (
    <section
      className="what-if-panel"
      id="what-if-planning"
      aria-label="Explore Programs What-if Analysis"
    >
      <div className="section-heading">
        <div>
          <h2>Explore Programs / What-if Analysis</h2>
          <p className="subtle">
            Estimated additional credits do not predict graduation timing.
          </p>
        </div>
        <p className="notice compact">Advisor confirmation may be required.</p>
      </div>

      <div className="scenario-controls">
        <label>
          Candidate program
          <select
            value={selectedCandidateId}
            onChange={(event) => setSelectedCandidateId(event.target.value)}
          >
            {candidatePrograms.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCreateScenario()}
        >
          Create scenario
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCompareSaved()}
        >
          Compare saved scenarios
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="What-if source gate">
          <h2>Import required for what-if analysis</h2>
          <p>
            Current source is {sourceLabel}. What-if analysis only runs after an
            auto-verified, confirmed, or explicitly loaded sanitized MyProgress
            sample is available.
          </p>
        </section>
      ) : null}

      {scenarioState.status === "idle" ? (
        <EmptyState
          copyKey="NO_WHAT_IF_SCENARIOS"
          ariaLabel="What-if scenarios empty state"
        />
      ) : null}

      {scenarioState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Creating scenario</h2>
          <p>Running mock what-if audits and allocation.</p>
        </section>
      ) : null}

      {scenarioState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>What-if scenario unavailable</h2>
          <p>{scenarioState.message}</p>
        </section>
      ) : null}

      {scenarioState.status === "empty" ? (
        <EmptyState
          copyKey="NO_WHAT_IF_SCENARIOS"
          ariaLabel="What-if scenarios empty state"
        />
      ) : null}

      {scenarioState.status === "ready" ? (
        <ScenarioResult
          state={scenarioState}
          selectedCandidate={selectedCandidate}
        />
      ) : null}
    </section>
  );
}

function CourseEligibilityChecker({
  selectedCourseId,
  setSelectedCourseId,
  eligibilityState,
  setEligibilityState,
}: {
  selectedCourseId: string;
  setSelectedCourseId: (value: string) => void;
  eligibilityState: EligibilityState;
  setEligibilityState: Dispatch<SetStateAction<EligibilityState>>;
}) {
  const selectedCourse =
    candidateCourses.find((candidate) => candidate.id === selectedCourseId) ??
    candidateCourses[0];

  async function handleRunEligibility(): Promise<void> {
    if (!apiBaseUrl) {
      setEligibilityState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setEligibilityState({ status: "loading" });
    try {
      const result = await createCourseEligibilityCheck(
        apiBaseUrl,
        {
          student_profile_id: mockStudentId,
          course_id: selectedCourse.courseId,
          section_id: selectedCourse.sectionId ?? null,
          target_term_id: selectedCourse.termId,
          mode: selectedCourse.mode,
          planned_corequisite_course_ids:
            selectedCourse.plannedCorequisiteCourseIds ?? [],
        },
        { timeoutMs: 8_000 },
      );
      const history = await fetchStudentEligibilityChecks(
        apiBaseUrl,
        mockStudentId,
        {
          timeoutMs: 5_000,
        },
      );
      setEligibilityState({ status: "ready", result, history });
    } catch (error: unknown) {
      setEligibilityState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeEligibilityError(error),
      });
    }
  }

  async function handleLoadHistory(): Promise<void> {
    if (!apiBaseUrl) {
      setEligibilityState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setEligibilityState({ status: "loading" });
    try {
      const history = await fetchStudentEligibilityChecks(
        apiBaseUrl,
        mockStudentId,
        {
          timeoutMs: 5_000,
        },
      );
      if (history.length === 0) {
        setEligibilityState({
          status: "empty",
          message: "No course eligibility checks have been created yet.",
        });
        return;
      }
      setEligibilityState({
        status: "ready",
        result: history[0],
        history,
      });
    } catch (error: unknown) {
      setEligibilityState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeEligibilityError(error),
      });
    }
  }

  return (
    <section
      className="eligibility-panel"
      aria-label="Course Eligibility Checker"
    >
      <div className="section-heading">
        <div>
          <h2>Course Eligibility</h2>
          <p className="subtle">
            Mock estimate only; confirm official rules with the school or an
            advisor.
          </p>
        </div>
        <p className="notice compact">
          Section seats are separate from academic eligibility.
        </p>
      </div>

      <div className="scenario-controls">
        <label>
          Course check
          <select
            value={selectedCourseId}
            onChange={(event) => setSelectedCourseId(event.target.value)}
          >
            {candidateCourses.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void handleRunEligibility()}>
          Check eligibility
        </button>
        <button type="button" onClick={() => void handleLoadHistory()}>
          Load history
        </button>
      </div>

      {eligibilityState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Checking eligibility</h2>
          <p>Evaluating stored mock course rules and expression evidence.</p>
        </section>
      ) : null}

      {eligibilityState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Eligibility API offline</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Eligibility check failed</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Eligibility schema error</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>No eligibility checks</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "ready" ? (
        <EligibilityResultView state={eligibilityState} />
      ) : null}
    </section>
  );
}

function EligibilityResultView({
  state,
}: {
  state: Extract<EligibilityState, { status: "ready" }>;
}) {
  const { result } = state;
  const availability = result.registration_availability;
  return (
    <div className="eligibility-result">
      <section className="summary-grid" aria-label="Course eligibility summary">
        <SummaryMetric label="Mode" value={statusLabel(result.mode)} />
        <SummaryMetric
          label="Result"
          value={statusLabel(result.overall_result)}
        />
        <SummaryMetric
          label="Academic Result"
          value={statusLabel(result.academic_eligibility_result)}
        />
        <SummaryMetric
          label="Section Status"
          value={
            availability
              ? statusLabel(availability.section_status)
              : "Course only"
          }
        />
        <SummaryMetric
          label="Available Seats"
          value={
            availability?.available_seats === undefined ||
            availability?.available_seats === null
              ? "Not reported"
              : String(availability.available_seats)
          }
        />
        <SummaryMetric
          label="Warnings"
          value={String(result.warnings.length)}
        />
      </section>

      <section className="eligibility-columns">
        <div>
          <h2>Reasons</h2>
          <ReasonList title="Blocking" reasons={result.blocking_reasons} />
          <ReasonList
            title="Conditional"
            reasons={result.conditional_reasons}
          />
          <ReasonList
            title="Permission"
            reasons={result.permissions_required}
          />
          <ReasonList
            title="Manual Review"
            reasons={result.manual_review_reasons}
          />
        </div>
        <div>
          <h2>Rule Evidence</h2>
          {result.rule_evaluations.length > 0 ? (
            result.rule_evaluations.map((rule) => (
              <details key={rule.id} className="eligibility-rule">
                <summary>
                  <span>{statusLabel(rule.rule_type)}</span>
                  <span className={`status-pill ${rule.result.toLowerCase()}`}>
                    {statusLabel(rule.result)}
                  </span>
                </summary>
                <div className="eligibility-expression-list">
                  {rule.expressions.map((expression) => (
                    <div key={expression.id} className="eligibility-expression">
                      <strong>{statusLabel(expression.node_type)}</strong>
                      <span>{statusLabel(expression.result)}</span>
                      <p>{expression.explanation}</p>
                    </div>
                  ))}
                </div>
              </details>
            ))
          ) : (
            <p className="subtle">
              No stored rules were found for this course scope.
            </p>
          )}
        </div>
        <div>
          <h2>Warnings</h2>
          {result.warnings.length > 0 ? (
            <ul className="compact-list">
              {result.warnings.map((warning) => (
                <li key={warning.id}>
                  <strong>{warning.warning_code}</strong>
                  <span>{warning.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No eligibility warnings.</p>
          )}
        </div>
      </section>

      {state.history.length > 1 ? (
        <section className="comparison-table" aria-label="Eligibility history">
          <h2>Recent Eligibility Checks</h2>
          <div className="comparison-rows">
            {state.history.slice(0, 4).map((item) => (
              <div key={item.id} className="comparison-row">
                <strong>{statusLabel(item.overall_result)}</strong>
                <span>
                  {statusLabel(item.mode)} ·{" "}
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function ReasonList({
  title,
  reasons,
}: {
  title: string;
  reasons: CourseEligibilityCheck["blocking_reasons"];
}) {
  if (reasons.length === 0) {
    return null;
  }
  return (
    <section className="reason-group">
      <h3>{title}</h3>
      <ul className="compact-list">
        {reasons.map((reason) => (
          <li
            key={`${title}-${reason.reason_code}-${reason.course_rule_expression_id ?? ""}`}
          >
            <strong>{reason.reason_code}</strong>
            <span>{reason.explanation}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AcademicPlanner({
  selectedPlannerScopeId,
  setSelectedPlannerScopeId,
  selectedPlannerStartTermId,
  setSelectedPlannerStartTermId,
  termsToPlan,
  setTermsToPlan,
  minimumCredits,
  setMinimumCredits,
  preferredCredits,
  setPreferredCredits,
  maximumCredits,
  setMaximumCredits,
  plannerState,
  setPlannerState,
  canUseDownstreamAnalysis,
  sourceLabel,
}: {
  selectedPlannerScopeId: string;
  setSelectedPlannerScopeId: (value: string) => void;
  selectedPlannerStartTermId: string;
  setSelectedPlannerStartTermId: (value: string) => void;
  termsToPlan: number;
  setTermsToPlan: Dispatch<SetStateAction<number>>;
  minimumCredits: number;
  setMinimumCredits: Dispatch<SetStateAction<number>>;
  preferredCredits: number;
  setPreferredCredits: Dispatch<SetStateAction<number>>;
  maximumCredits: number;
  setMaximumCredits: Dispatch<SetStateAction<number>>;
  plannerState: PlannerState;
  setPlannerState: Dispatch<SetStateAction<PlannerState>>;
  canUseDownstreamAnalysis: boolean;
  sourceLabel: ImportSourceStateLabel;
}) {
  const selectedScope =
    plannerScopes.find((scope) => scope.id === selectedPlannerScopeId) ??
    plannerScopes[0];

  async function createScenarioForScope(
    scope: PlannerScope,
  ): Promise<string | null> {
    if (scope.planningMode === "CURRENT_PROGRAM") {
      return null;
    }

    const candidate = candidatePrograms.find(
      (program) => program.id === scope.candidateProgramId,
    );
    if (!candidate) {
      throw new ApiRequestError(
        "Planner what-if candidate program is not configured.",
      );
    }

    const scenario = await createAcademicScenario(
      apiBaseUrl ?? "",
      {
        student_profile_id: mockStudentId,
        scenario_name:
          candidate.relationshipType === "PRIMARY_MAJOR"
            ? `Planner change to ${candidate.label}`
            : `Planner add ${candidate.label}`,
        scenario_type: candidate.scenarioType,
        calculation_mode: "PROJECTED",
        programs:
          candidate.relationshipType === "PRIMARY_MAJOR"
            ? [
                {
                  program_version_id: candidate.programVersionId,
                  relationship_type: "PRIMARY_MAJOR",
                  priority: 0,
                },
              ]
            : [
                {
                  program_version_id: mockProgramVersionId,
                  relationship_type: "PRIMARY_MAJOR",
                  priority: 0,
                },
                {
                  program_version_id: candidate.programVersionId,
                  relationship_type: candidate.relationshipType,
                  priority: 10,
                },
              ],
      },
      { timeoutMs: 8_000 },
    );
    return scenario.id;
  }

  async function handleCreatePlan(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setPlannerState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before creating long-term plans.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setPlannerState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setPlannerState({ status: "loading" });
    try {
      const academicPlanScenarioId =
        await createScenarioForScope(selectedScope);
      const plan = await createAcademicPlan(
        apiBaseUrl,
        {
          student_profile_id: mockStudentId,
          program_version_id: mockProgramVersionId,
          academic_plan_scenario_id: academicPlanScenarioId,
          planning_mode: selectedScope.planningMode,
          start_term_id: selectedPlannerStartTermId,
          terms_to_plan: termsToPlan,
          minimum_credits_per_term: String(minimumCredits),
          maximum_credits_per_term: String(maximumCredits),
          preferred_credits_per_term: String(preferredCredits),
        },
        { timeoutMs: 10_000 },
      );
      setPlannerState({
        status: "ready",
        plan,
        comparisons: [],
        savedPlans: [],
      });
    } catch (error: unknown) {
      setPlannerState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describePlannerError(error),
      });
    }
  }

  async function handleComparePlans(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setPlannerState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before comparing plans.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setPlannerState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    try {
      const savedPlans = await fetchStudentAcademicPlans(
        apiBaseUrl,
        mockStudentId,
        {
          timeoutMs: 5_000,
        },
      );
      if (savedPlans.length < 2) {
        setPlannerState({
          status: "empty",
          message: "At least two saved academic plans are needed.",
        });
        return;
      }
      const comparisons = await compareAcademicPlans(
        apiBaseUrl,
        { academic_plan_ids: savedPlans.slice(0, 2).map((plan) => plan.id) },
        { timeoutMs: 5_000 },
      );
      setPlannerState((current) =>
        current.status === "ready"
          ? { ...current, comparisons, savedPlans }
          : {
              status: "empty",
              message: "Create an academic plan before comparing saved plans.",
            },
      );
    } catch (error: unknown) {
      setPlannerState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describePlannerError(error),
      });
    }
  }

  return (
    <section className="planner-panel" aria-label="Long-Term Academic Planner">
      <div className="section-heading">
        <div>
          <h2>Long-Term Academic Planner</h2>
          <p className="subtle">
            Generate an explainable term-by-term mock plan from remaining degree
            requirements.
          </p>
        </div>
        <p className="notice compact">This plan is not registration.</p>
      </div>

      <ul className="disclaimer-list" aria-label="Academic planner disclaimers">
        <li>Mock data — not official university policy.</li>
        <li>This plan is not registration.</li>
        <li>This plan does not check weekly schedule conflicts.</li>
        <li>Course offering predictions are estimates.</li>
        <li>Advisor confirmation may be required.</li>
      </ul>

      <div className="scenario-controls planner-controls">
        <label>
          Planning scope
          <select
            value={selectedPlannerScopeId}
            onChange={(event) => setSelectedPlannerScopeId(event.target.value)}
          >
            {plannerScopes.map((scope) => (
              <option key={scope.id} value={scope.id}>
                {scope.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Start term
          <select
            value={selectedPlannerStartTermId}
            onChange={(event) =>
              setSelectedPlannerStartTermId(event.target.value)
            }
          >
            {plannerStartTerms.map((term) => (
              <option key={term.id} value={term.id}>
                {term.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Terms
          <input
            min={1}
            max={16}
            type="number"
            value={termsToPlan}
            onChange={(event) => setTermsToPlan(Number(event.target.value))}
          />
        </label>
        <label>
          Min credits
          <input
            min={0}
            type="number"
            value={minimumCredits}
            onChange={(event) => setMinimumCredits(Number(event.target.value))}
          />
        </label>
        <label>
          Preferred credits
          <input
            min={0}
            type="number"
            value={preferredCredits}
            onChange={(event) =>
              setPreferredCredits(Number(event.target.value))
            }
          />
        </label>
        <label>
          Max credits
          <input
            min={0}
            type="number"
            value={maximumCredits}
            onChange={(event) => setMaximumCredits(Number(event.target.value))}
          />
        </label>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCreatePlan()}
        >
          Create plan
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleComparePlans()}
        >
          Compare saved plans
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="Planner source gate">
          <h2>Import required for planning</h2>
          <p>
            Current source is {sourceLabel}. Long-term planning only runs after
            an auto-verified, confirmed, or explicitly loaded sanitized
            MyProgress sample is available.
          </p>
        </section>
      ) : null}

      {plannerState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Creating academic plan</h2>
          <p>
            Evaluating degree audit gaps, prerequisite unlocks, and term
            capacity.
          </p>
        </section>
      ) : null}

      {plannerState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Academic planner API offline</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Academic planner failed</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Academic planner schema error</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>No saved plans</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "ready" ? (
        <AcademicPlanResultView state={plannerState} />
      ) : null}
    </section>
  );
}

function AcademicPlanResultView({
  state,
}: {
  state: Extract<PlannerState, { status: "ready" }>;
}) {
  const { plan } = state;
  const totalPlannedCredits = plan.planned_courses.reduce(
    (total, course) => total + Number(course.credits),
    0,
  );

  return (
    <div className="planner-result">
      <section className="summary-grid" aria-label="Academic plan summary">
        <SummaryMetric label="Plan Status" value={statusLabel(plan.status)} />
        <SummaryMetric
          label="Planning Mode"
          value={statusLabel(plan.planning_mode)}
        />
        <SummaryMetric label="Terms" value={String(plan.terms.length)} />
        <SummaryMetric
          label="Planned Courses"
          value={String(plan.planned_courses.length)}
        />
        <SummaryMetric
          label="Planned Credits"
          value={formatCredits(String(totalPlannedCredits))}
        />
        <SummaryMetric label="Warnings" value={String(plan.warnings.length)} />
      </section>

      <section
        className="planner-term-grid"
        aria-label="Term-by-term academic plan"
      >
        <h2>Term-by-Term Plan</h2>
        {plan.planned_courses.length === 0 ? (
          <p className="subtle">
            No planner courses were generated for the selected settings.
          </p>
        ) : null}
        <div className="term-columns">
          {plan.terms.map((term) => {
            const courses = plan.planned_courses.filter(
              (course) => course.term_id === term.term_id,
            );
            return (
              <section key={term.id} className="term-column">
                <div className="term-heading">
                  <h3>{term.term_code}</h3>
                  <span className={`status-pill ${term.status.toLowerCase()}`}>
                    {statusLabel(term.status)}
                  </span>
                </div>
                <p>{formatCredits(term.planned_credits)} planned credits</p>
                {courses.length > 0 ? (
                  <ul className="compact-list">
                    {courses.map((course) => (
                      <li key={course.id}>
                        <strong>{course.course_code}</strong>
                        <span>
                          {course.course_title} ·{" "}
                          {formatCredits(course.credits)} credits
                        </span>
                        <span>
                          {statusLabel(course.planning_status)} ·{" "}
                          {course.reason_code}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="subtle">No courses placed in this term.</p>
                )}
              </section>
            );
          })}
        </div>
      </section>

      <section className="planner-columns">
        <div>
          <h2>Requirement Coverage</h2>
          {plan.requirement_coverage.length > 0 ? (
            <ul className="compact-list">
              {plan.requirement_coverage.map((coverage) => (
                <li key={coverage.id}>
                  <strong>{coverage.requirement_code}</strong>
                  <span>
                    {statusLabel(coverage.coverage_type)} ·{" "}
                    {formatCredits(coverage.credits)}
                    credits
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No requirement coverage was created.</p>
          )}
        </div>
        <div>
          <h2>Planner Warnings</h2>
          {plan.warnings.length > 0 ? (
            <ul className="compact-list">
              {plan.warnings.map((warning) => (
                <li key={warning.id}>
                  <strong>{warning.warning_code}</strong>
                  <span>{warning.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No planner warnings.</p>
          )}
        </div>
      </section>

      {state.comparisons.length > 0 ? (
        <section
          className="comparison-table"
          aria-label="Saved academic plan comparison"
        >
          <h2>Saved Plan Comparison</h2>
          <div className="comparison-rows">
            {state.comparisons.map((comparison) => {
              const savedPlan = state.savedPlans.find(
                (item) => item.id === comparison.academic_plan_run_id,
              );
              return (
                <div
                  key={comparison.academic_plan_run_id}
                  className="comparison-row"
                >
                  <strong>
                    {savedPlan?.planning_mode ??
                      comparison.academic_plan_run_id}
                  </strong>
                  <span>
                    {formatCredits(comparison.total_planned_credits)} planned
                    credits · {comparison.warning_count} warnings
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function SemesterScheduleBuilder({
  selectedSchedulePresetId,
  setSelectedSchedulePresetId,
  scheduleNoFriday,
  setScheduleNoFriday,
  scheduleAvoidTuesdayBlock,
  setScheduleAvoidTuesdayBlock,
  schedulePreferOnline,
  setSchedulePreferOnline,
  schedulePreferCompact,
  setSchedulePreferCompact,
  schedulePreferFewerDays,
  setSchedulePreferFewerDays,
  schedulePreferNoGaps,
  setSchedulePreferNoGaps,
  schedulePreferMorning,
  setSchedulePreferMorning,
  schedulePreferAfternoon,
  setSchedulePreferAfternoon,
  schedulePinnedSectionChoiceId,
  setSchedulePinnedSectionChoiceId,
  scheduleExcludedSectionChoiceId,
  setScheduleExcludedSectionChoiceId,
  scheduleDiversityMode,
  setScheduleDiversityMode,
  scheduleAllowPartialOptions,
  setScheduleAllowPartialOptions,
  scheduleState,
  setScheduleState,
  canUseDownstreamAnalysis,
  sourceLabel,
}: {
  selectedSchedulePresetId: string;
  setSelectedSchedulePresetId: (value: string) => void;
  scheduleNoFriday: boolean;
  setScheduleNoFriday: Dispatch<SetStateAction<boolean>>;
  scheduleAvoidTuesdayBlock: boolean;
  setScheduleAvoidTuesdayBlock: Dispatch<SetStateAction<boolean>>;
  schedulePreferOnline: boolean;
  setSchedulePreferOnline: Dispatch<SetStateAction<boolean>>;
  schedulePreferCompact: boolean;
  setSchedulePreferCompact: Dispatch<SetStateAction<boolean>>;
  schedulePreferFewerDays: boolean;
  setSchedulePreferFewerDays: Dispatch<SetStateAction<boolean>>;
  schedulePreferNoGaps: boolean;
  setSchedulePreferNoGaps: Dispatch<SetStateAction<boolean>>;
  schedulePreferMorning: boolean;
  setSchedulePreferMorning: Dispatch<SetStateAction<boolean>>;
  schedulePreferAfternoon: boolean;
  setSchedulePreferAfternoon: Dispatch<SetStateAction<boolean>>;
  schedulePinnedSectionChoiceId: string;
  setSchedulePinnedSectionChoiceId: (value: string) => void;
  scheduleExcludedSectionChoiceId: string;
  setScheduleExcludedSectionChoiceId: (value: string) => void;
  scheduleDiversityMode: "STANDARD" | "HIGH";
  setScheduleDiversityMode: (value: "STANDARD" | "HIGH") => void;
  scheduleAllowPartialOptions: boolean;
  setScheduleAllowPartialOptions: Dispatch<SetStateAction<boolean>>;
  scheduleState: ScheduleState;
  setScheduleState: Dispatch<SetStateAction<ScheduleState>>;
  canUseDownstreamAnalysis: boolean;
  sourceLabel: ImportSourceStateLabel;
}) {
  const selectedPreset =
    schedulePresets.find((preset) => preset.id === selectedSchedulePresetId) ??
    schedulePresets[0];
  const pinnedSection = scheduleSectionChoices.find(
    (choice) => choice.id === schedulePinnedSectionChoiceId,
  );
  const excludedSection = scheduleSectionChoices.find(
    (choice) => choice.id === scheduleExcludedSectionChoiceId,
  );

  async function handleCreateSchedule(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setScheduleState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before building schedules.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScheduleState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setScheduleState({ status: "loading" });
    try {
      const schedule = await createScheduleOptimization(
        apiBaseUrl,
        {
          student_profile_id: mockStudentId,
          term_id: selectedPreset.termId,
          academic_plan_run_id: null,
          planning_mode: "CUSTOM_COURSE_SET",
          candidate_course_ids: selectedPreset.candidateCourseIds,
          minimum_credits: "3.0",
          maximum_credits: "6.0",
          preferred_credits: "6.0",
          requested_option_count: 3,
          max_options: 3,
          excluded_days: scheduleNoFriday ? ["FRIDAY"] : [],
          unavailable_time_blocks: scheduleAvoidTuesdayBlock
            ? [
                {
                  day_of_week: "TUESDAY",
                  start_time: "11:00",
                  end_time: "11:30",
                },
              ]
            : [],
          earliest_start_time: "08:00",
          latest_end_time: "18:00",
          prefer_online: schedulePreferOnline,
          prefer_compact_schedule: schedulePreferCompact,
          prefer_fewer_days: schedulePreferFewerDays,
          prefer_in_person: !schedulePreferOnline,
          preference_weights: {
            gap: schedulePreferNoGaps ? "1.5" : "1.0",
            priority: "2.0",
            time:
              schedulePreferMorning || schedulePreferAfternoon ? "1.25" : "1.0",
          },
          course_priority_weights: {
            "9413e6c7-26a0-5acf-9de4-88b132dc802d": "2.0",
          },
          section_priority_weights:
            pinnedSection?.sectionId && pinnedSection.id !== "none"
              ? { [pinnedSection.sectionId]: "5.0" }
              : {},
          required_section_ids:
            pinnedSection?.sectionId && pinnedSection.id !== "none"
              ? [pinnedSection.sectionId]
              : [],
          excluded_section_ids:
            excludedSection?.sectionId && excludedSection.id !== "none"
              ? [excludedSection.sectionId]
              : [],
          prefer_no_gaps: schedulePreferNoGaps,
          prefer_morning: schedulePreferMorning,
          prefer_afternoon: schedulePreferAfternoon,
          diversity_mode: scheduleDiversityMode,
          allow_partial_options: scheduleAllowPartialOptions,
          max_combinations: 500,
          avoid_late_end: true,
          allow_permission_required: false,
        },
        { timeoutMs: 10_000 },
      );
      setScheduleState({
        status: "ready",
        schedule,
        comparisons: [],
        savedRuns: [],
      });
    } catch (error: unknown) {
      setScheduleState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeScheduleError(error),
      });
    }
  }

  async function handleCompareSchedules(): Promise<void> {
    if (!canUseDownstreamAnalysis) {
      setScheduleState({
        status: "empty",
        message:
          "Load an auto-verified or confirmed MyProgress import before comparing schedules.",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScheduleState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    try {
      const savedRuns = await fetchStudentScheduleOptimizations(
        apiBaseUrl,
        mockStudentId,
        {
          timeoutMs: 5_000,
        },
      );
      if (savedRuns.length < 2) {
        setScheduleState({
          status: "empty",
          message: "At least two saved schedule runs are needed.",
        });
        return;
      }
      const comparisons = await compareScheduleOptimizations(
        apiBaseUrl,
        {
          schedule_optimization_run_ids: savedRuns
            .slice(0, 2)
            .map((run) => run.id),
        },
        { timeoutMs: 5_000 },
      );
      setScheduleState((current) =>
        current.status === "ready"
          ? { ...current, comparisons, savedRuns }
          : {
              status: "empty",
              message:
                "Create a schedule before comparing saved schedule runs.",
            },
      );
    } catch (error: unknown) {
      setScheduleState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeScheduleError(error),
      });
    }
  }

  return (
    <section
      className="schedule-panel"
      id="schedule-optimization"
      aria-label="Semester Schedule Builder"
    >
      <div className="section-heading">
        <div>
          <h2>Semester Schedule Builder</h2>
          <p className="subtle">
            Build explainable single-term section options from mock section
            data.
          </p>
        </div>
        <p className="notice compact">This is not registration.</p>
      </div>

      <ul className="disclaimer-list" aria-label="Schedule builder disclaimers">
        <li>Mock data — not official university policy.</li>
        <li>Generated schedules are not registration.</li>
        <li>Seat availability is separate from academic eligibility.</li>
        <li>This tool does not perform add/drop or waitlist actions.</li>
        <li>Advisor confirmation may be required.</li>
      </ul>

      <div className="scenario-controls schedule-controls">
        <label>
          Course set
          <select
            value={selectedSchedulePresetId}
            onChange={(event) =>
              setSelectedSchedulePresetId(event.target.value)
            }
          >
            {schedulePresets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.label}
              </option>
            ))}
          </select>
        </label>
        <label className="toggle-row">
          <input
            checked={scheduleNoFriday}
            type="checkbox"
            onChange={(event) => setScheduleNoFriday(event.target.checked)}
          />
          No Friday
        </label>
        <label className="toggle-row">
          <input
            checked={scheduleAvoidTuesdayBlock}
            type="checkbox"
            onChange={(event) =>
              setScheduleAvoidTuesdayBlock(event.target.checked)
            }
          />
          Tue 11:00 block
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferOnline}
            type="checkbox"
            onChange={(event) => setSchedulePreferOnline(event.target.checked)}
          />
          Prefer online
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferCompact}
            type="checkbox"
            onChange={(event) => setSchedulePreferCompact(event.target.checked)}
          />
          Compact
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferFewerDays}
            type="checkbox"
            onChange={(event) =>
              setSchedulePreferFewerDays(event.target.checked)
            }
          />
          Fewer days
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferNoGaps}
            type="checkbox"
            onChange={(event) => setSchedulePreferNoGaps(event.target.checked)}
          />
          No gaps
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferMorning}
            type="checkbox"
            onChange={(event) => setSchedulePreferMorning(event.target.checked)}
          />
          Morning
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferAfternoon}
            type="checkbox"
            onChange={(event) =>
              setSchedulePreferAfternoon(event.target.checked)
            }
          />
          Afternoon
        </label>
        <label>
          Pinned section
          <select
            value={schedulePinnedSectionChoiceId}
            onChange={(event) =>
              setSchedulePinnedSectionChoiceId(event.target.value)
            }
          >
            {scheduleSectionChoices.slice(0, 3).map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Excluded section
          <select
            value={scheduleExcludedSectionChoiceId}
            onChange={(event) =>
              setScheduleExcludedSectionChoiceId(event.target.value)
            }
          >
            {scheduleSectionChoices
              .filter(
                (choice) =>
                  choice.id === "none" || choice.id.startsWith("fin-300"),
              )
              .map((choice) => (
                <option key={choice.id} value={choice.id}>
                  {choice.label}
                </option>
              ))}
          </select>
        </label>
        <label>
          Diversity
          <select
            value={scheduleDiversityMode}
            onChange={(event) =>
              setScheduleDiversityMode(
                event.target.value === "HIGH" ? "HIGH" : "STANDARD",
              )
            }
          >
            <option value="HIGH">High</option>
            <option value="STANDARD">Standard</option>
          </select>
        </label>
        <label className="toggle-row">
          <input
            checked={scheduleAllowPartialOptions}
            type="checkbox"
            onChange={(event) =>
              setScheduleAllowPartialOptions(event.target.checked)
            }
          />
          Partial options
        </label>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCreateSchedule()}
        >
          Build schedule
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCompareSchedules()}
        >
          Compare saved schedules
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="Schedule source gate">
          <h2>Import required for schedule recommendations</h2>
          <p>
            Current source is {sourceLabel}. Schedule recommendations only run
            after an auto-verified, confirmed, or explicitly loaded sanitized
            MyProgress sample is available.
          </p>
        </section>
      ) : null}

      {scheduleState.status === "idle" ? (
        <EmptyState
          copyKey="NO_GENERATED_SCHEDULE_PLANS"
          ariaLabel="Schedule plans empty state"
        />
      ) : null}

      {scheduleState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Building semester schedule</h2>
          <p>
            Checking mock section meetings, eligibility, conflicts, and
            preferences.
          </p>
        </section>
      ) : null}

      {scheduleState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Schedule optimizer API offline</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Schedule optimizer failed</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Schedule optimizer schema error</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "empty" ? (
        <EmptyState
          copyKey="NO_GENERATED_SCHEDULE_PLANS"
          ariaLabel="Schedule plans empty state"
        />
      ) : null}

      {scheduleState.status === "ready" ? (
        <ScheduleResultView state={scheduleState} />
      ) : null}
    </section>
  );
}

function ScheduleResultView({
  state,
}: {
  state: Extract<ScheduleState, { status: "ready" }>;
}) {
  const { schedule } = state;
  const bestOption = schedule.options[0] ?? null;

  return (
    <div className="schedule-result">
      <section
        className="summary-grid"
        aria-label="Schedule optimization summary"
      >
        <SummaryMetric
          label="Run Status"
          value={statusLabel(schedule.status)}
        />
        <SummaryMetric
          label="Options"
          value={String(schedule.options.length)}
        />
        <SummaryMetric
          label="Conflicts"
          value={String(schedule.conflicts.length)}
        />
        <SummaryMetric
          label="Warnings"
          value={String(schedule.warnings.length)}
        />
        <SummaryMetric
          label="Best Credits"
          value={bestOption ? formatCredits(bestOption.total_credits) : "0.0"}
        />
        <SummaryMetric
          label="Best Score"
          value={bestOption ? Number(bestOption.score).toFixed(2) : "0.00"}
        />
      </section>

      <section className="schedule-options" aria-label="Schedule options">
        <h2>Section Options</h2>
        {schedule.options.length === 0 ? (
          <p className="subtle">No feasible section option was created.</p>
        ) : null}
        <div className="schedule-option-grid">
          {schedule.options.map((option) => (
            <section key={option.id} className="schedule-option">
              <div className="term-heading">
                <h3>Option {option.option_rank}</h3>
                <span className={`status-pill ${option.status.toLowerCase()}`}>
                  {statusLabel(option.status)}
                </span>
              </div>
              <p>
                {formatCredits(option.total_credits)} credits -{" "}
                {option.class_days_count} class days - score{" "}
                {Number(option.total_score).toFixed(2)}
              </p>
              <p className="subtle">{option.explanation}</p>
              <p className="subtle">
                Diversity {option.diversity_rank}: {option.difference_summary}
              </p>
              <div className="score-breakdown">
                <span>
                  Credits{" "}
                  {Number(option.score_breakdown.credit_score).toFixed(2)}
                </span>
                <span>
                  Compact{" "}
                  {Number(option.score_breakdown.compactness_score).toFixed(2)}
                </span>
                <span>
                  Days {Number(option.score_breakdown.days_score).toFixed(2)}
                </span>
                <span>
                  Gaps {Number(option.score_breakdown.gap_score).toFixed(2)}
                </span>
                <span>
                  Modality{" "}
                  {Number(option.score_breakdown.modality_score).toFixed(2)}
                </span>
                <span>
                  Time{" "}
                  {Number(option.score_breakdown.time_preference_score).toFixed(
                    2,
                  )}
                </span>
                <span>
                  Priority{" "}
                  {Number(option.score_breakdown.priority_score).toFixed(2)}
                </span>
                <span>
                  Penalty{" "}
                  {Number(option.score_breakdown.penalty_score).toFixed(2)}
                </span>
              </div>
              {option.score_explanation.length > 0 ? (
                <ul className="compact-list score-reasons">
                  {option.score_explanation.slice(0, 4).map((item, index) => (
                    <li key={`${option.id}-score-${index}`}>
                      <strong>{String(item.reason_code ?? "SCORE")}</strong>
                      <span>
                        {String(item.explanation ?? item.score ?? "")}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              <ul className="compact-list">
                {option.selected_sections.map((selected) => (
                  <li key={selected.id}>
                    <strong>
                      {selected.course_code} {selected.section_code}
                    </strong>
                    <span>
                      {selected.course_title} - {statusLabel(selected.modality)}{" "}
                      - {statusLabel(selected.eligibility_result)}
                    </span>
                    <span>{formatMeetingList(selected.meetings)}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>

      {schedule.options.length >= 2 ? (
        <section
          className="comparison-table"
          aria-label="Top schedule option comparison"
        >
          <h2>Top Option Comparison</h2>
          <div className="comparison-rows">
            {schedule.options.slice(0, 2).map((option) => (
              <div key={`${option.id}-top-compare`} className="comparison-row">
                <strong>Option {option.option_rank}</strong>
                <span>
                  score {Number(option.total_score).toFixed(2)} -{" "}
                  {option.shared_section_count_with_previous_option} shared with
                  previous - {option.difference_summary}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="planner-columns">
        <div>
          <h2>Conflicts</h2>
          {schedule.conflicts.length > 0 ? (
            <ul className="compact-list">
              {schedule.conflicts.map((conflict) => (
                <li key={conflict.id}>
                  <strong>{conflict.conflict_type}</strong>
                  <span>{conflict.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No conflicts were recorded.</p>
          )}
        </div>
        <div>
          <h2>Schedule Warnings</h2>
          {schedule.warnings.length > 0 ? (
            <ul className="compact-list">
              {schedule.warnings.map((warning) => (
                <li key={warning.id}>
                  <strong>{warning.warning_code}</strong>
                  <span>{warning.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No schedule warnings.</p>
          )}
        </div>
      </section>

      {schedule.repair_suggestions.length > 0 ? (
        <section
          className="comparison-table"
          aria-label="Schedule repair suggestions"
        >
          <h2>Repair Suggestions</h2>
          <div className="comparison-rows">
            {schedule.repair_suggestions.map((suggestion) => (
              <div key={suggestion.id} className="comparison-row">
                <strong>{statusLabel(suggestion.suggestion_type)}</strong>
                <span>
                  {suggestion.message}{" "}
                  {suggestion.requires_advisor_confirmation
                    ? "Advisor confirmation may be required."
                    : ""}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {state.comparisons.length > 0 ? (
        <section
          className="comparison-table"
          aria-label="Saved schedule comparison"
        >
          <h2>Saved Schedule Comparison</h2>
          <div className="comparison-rows">
            {state.comparisons.map((comparison) => {
              const savedRun = state.savedRuns.find(
                (item) => item.id === comparison.schedule_optimization_run_id,
              );
              return (
                <div
                  key={comparison.schedule_optimization_run_id}
                  className="comparison-row"
                >
                  <strong>
                    {savedRun?.planning_mode ?? comparison.status}
                  </strong>
                  <span>
                    {comparison.option_count} options -{" "}
                    {comparison.best_total_credits
                      ? formatCredits(comparison.best_total_credits)
                      : "0.0"}{" "}
                    best credits - {comparison.warning_count} warnings
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function DataImportPreviewPanel({
  selectedDataImportSampleId,
  setSelectedDataImportSampleId,
  dataImportState,
  setDataImportState,
  dataReviewState,
  setDataReviewState,
}: {
  selectedDataImportSampleId: string;
  setSelectedDataImportSampleId: (value: string) => void;
  dataImportState: DataImportPreviewState;
  setDataImportState: Dispatch<SetStateAction<DataImportPreviewState>>;
  dataReviewState: DataReviewState;
  setDataReviewState: Dispatch<SetStateAction<DataReviewState>>;
}) {
  const selectedSample =
    dataImportSamples.find(
      (sample) => sample.id === selectedDataImportSampleId,
    ) ?? dataImportSamples[0];
  const sanitizedMyProgressSample = dataImportSamples.find(
    (sample) => sample.id === sanitizedMyProgressSampleId,
  );

  async function handlePreviewImport(sample = selectedSample): Promise<void> {
    if (!apiBaseUrl) {
      setDataImportState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setDataImportState({ status: "loading" });
    try {
      const run = await createDataImport(
        apiBaseUrl,
        {
          student_profile_id: mockStudentId,
          import_type: sample.importType,
          file_name: sample.fileName,
          file_mime_type: sample.fileMimeType,
          content: sample.content,
          source_type: "STUDENT_PROVIDED",
          source_reference:
            sample.id === sanitizedMyProgressSampleId
              ? `Sanitized local test data from KEAN_STUDENT_PORTAL fixture: ${sample.label}`
              : `Built-in Phase 7A fixture: ${sample.label}`,
        },
        { timeoutMs: 8_000 },
      );
      await validateDataImport(apiBaseUrl, run.id, { timeoutMs: 5_000 });
      const savedImports = await fetchStudentDataImports(
        apiBaseUrl,
        mockStudentId,
        { timeoutMs: 5_000 },
      );
      setDataImportState(
        await loadDataImportPreviewState(apiBaseUrl, run, savedImports),
      );
    } catch (error: unknown) {
      setDataImportState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  async function handleLoadSavedImports(): Promise<void> {
    if (!apiBaseUrl) {
      setDataImportState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setDataImportState({ status: "loading" });
    try {
      const savedImports = await fetchStudentDataImports(
        apiBaseUrl,
        mockStudentId,
        { timeoutMs: 5_000 },
      );
      if (savedImports.length === 0) {
        setDataImportState({
          status: "empty",
          message: "No saved staging imports are available.",
        });
        return;
      }
      const previewState = await loadPreferredDataImportPreviewState(
        apiBaseUrl,
        savedImports,
      );
      if (!previewState) {
        setDataImportState({
          status: "empty",
          message: "No saved staging imports could be previewed.",
        });
        return;
      }
      setDataImportState(previewState);
    } catch (error: unknown) {
      setDataImportState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  return (
    <section
      className="data-import-panel"
      id="data-import-preview"
      aria-label="Data Import Preview"
    >
      <div className="section-heading">
        <div>
          <h2>Data Import Preview</h2>
          <p className="subtle">
            Staged records stay separate from official academic records.
          </p>
        </div>
        <p className="notice compact">Read-only staging boundary.</p>
      </div>

      <ul className="disclaimer-list" aria-label="Data import disclaimers">
        <li>Imported preview data is not official school policy.</li>
        <li>
          No transcript, catalog, section, registration, seat, or waitlist
          records are changed.
        </li>
        <li>
          Advisor or school confirmation is required before using imported
          records for high-impact guidance.
        </li>
      </ul>

      <section
        className="browser-extension-status"
        aria-label="Browser extension import status"
      >
        <div>
          <h2>Browser Extension Import</h2>
          <p className="subtle">
            Experimental source for visible-page academic tables.
          </p>
        </div>
        <AdvisoryLabels
          keys={[
            "NON_OFFICIAL_IMPORTED_DATA",
            "MANUAL_REVIEW_REQUIRED",
            "ADVISORY_ONLY",
          ]}
        />
        <ul className="compact-list">
          <li>
            <strong>Experimental</strong>
            <span>Extension extracts must enter staging import first.</span>
          </li>
          <li>
            <strong>Review</strong>
            <span>Phase 7B review is required before application.</span>
          </li>
          <li>
            <strong>Boundary</strong>
            <span>
              No registration automation, add/drop, swap, or waitlist actions.
            </span>
          </li>
        </ul>
      </section>

      <div className="scenario-controls data-import-controls">
        <label>
          Sample import
          <select
            value={selectedDataImportSampleId}
            onChange={(event) =>
              setSelectedDataImportSampleId(event.target.value)
            }
          >
            {dataImportSamples.map((sample) => (
              <option key={sample.id} value={sample.id}>
                {sample.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void handlePreviewImport()}>
          Preview import
        </button>
        {sanitizedMyProgressSample ? (
          <button
            type="button"
            onClick={() => void handlePreviewImport(sanitizedMyProgressSample)}
          >
            Load sanitized MyProgress sample
          </button>
        ) : null}
        <button type="button" onClick={() => void handleLoadSavedImports()}>
          Load saved imports
        </button>
      </div>
      <p className="notice compact">
        Sanitized local test data is sample-only and not official school data.
      </p>

      {dataImportState.status === "idle" ? (
        <EmptyState
          copyKey="NO_DATA_IMPORTS"
          ariaLabel="Data import empty state"
        />
      ) : null}

      {dataImportState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Parsing import</h2>
          <p>
            Creating a staging preview with mapping candidates and warnings.
          </p>
        </section>
      ) : null}

      {dataImportState.status === "offline" ||
      dataImportState.status === "failed" ||
      dataImportState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {dataImportState.status === "schema-error"
              ? "Data import schema error"
              : "Data import unavailable"}
          </h2>
          <p>{dataImportState.message}</p>
        </section>
      ) : null}

      {dataImportState.status === "empty" ? (
        <EmptyState
          copyKey="NO_DATA_IMPORTS"
          ariaLabel="Data import empty state"
        />
      ) : null}

      {dataImportState.status === "ready" ? (
        <DataImportResultView state={dataImportState} />
      ) : null}

      <DataReviewPanel
        dataImportState={dataImportState}
        dataReviewState={dataReviewState}
        setDataReviewState={setDataReviewState}
      />
    </section>
  );
}

function DataImportResultView({
  state,
}: {
  state: Extract<DataImportPreviewState, { status: "ready" }>;
}) {
  const myProgressPreview = myProgressPreviewFromSummary(state.preview);
  const selectedCandidateCount = state.candidates.filter(
    (candidate) => candidate.is_selected,
  ).length;
  return (
    <div className="data-import-result">
      <section
        className="summary-grid"
        aria-label="Data import preview summary"
      >
        <SummaryMetric
          label="Import Status"
          value={statusLabel(state.run.status)}
        />
        <SummaryMetric
          label="Data Mode"
          value={importModeLabel(myProgressPreview)}
        />
        <SummaryMetric label="Records" value={String(state.run.record_count)} />
        <SummaryMetric
          label="Mapped Candidates"
          value={String(selectedCandidateCount)}
        />
        <SummaryMetric label="Warnings" value={String(state.warnings.length)} />
        {myProgressPreview ? (
          <>
            <SummaryMetric
              label="Auto-Confirmed Fields"
              value={String(myProgressPreview.autoConfirmedFieldCount)}
            />
            <SummaryMetric
              label="Auto-Confirmed Course Rows"
              value={String(myProgressPreview.autoConfirmedCourseRowCount)}
            />
            <SummaryMetric
              label="Exceptions"
              value={String(myProgressPreview.exceptions.length)}
            />
            <SummaryMetric
              label="Downstream Analysis"
              value={
                myProgressPreview.downstreamAnalysisAllowed
                  ? "Allowed"
                  : "Blocked"
              }
            />
            <SummaryMetric
              label="Overall Confidence"
              value={`${Math.round(myProgressPreview.overallConfidenceScore * 100)}%`}
            />
          </>
        ) : null}
        <SummaryMetric
          label="Official Application"
          value={
            myProgressPreview?.canApplyVerifiedImport
              ? "Verified"
              : state.preview.official_application_ready
                ? "Ready"
                : "Disabled"
          }
        />
        <SummaryMetric
          label="Source Type"
          value={state.run.source.source_type}
        />
        <SummaryMetric
          label="Saved Imports"
          value={String(state.savedImports.length)}
        />
      </section>

      {myProgressPreview ? (
        <MyProgressImportPreview display={myProgressPreview} />
      ) : null}

      <section
        className="comparison-table"
        aria-label="Import preview disclaimers"
      >
        <h2>Preview Boundary</h2>
        <AdvisoryLabels
          keys={["NON_OFFICIAL_IMPORTED_DATA", "MANUAL_REVIEW_REQUIRED"]}
        />
        <ul className="compact-list">
          {state.preview.disclaimers.map((disclaimer) => (
            <li key={disclaimer}>
              <strong>Review</strong>
              <span>{disclaimer}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="data-import-grid">
        {myProgressPreview ? (
          <section aria-label="MyProgress exception queue">
            <h2>Exception Queue</h2>
            {myProgressPreview.exceptions.length > 0 ? (
              <div className="comparison-rows">
                {myProgressPreview.exceptions.map((exception) => (
                  <div key={exception.code} className="comparison-row">
                    <strong>{exception.code}</strong>
                    <span>
                      {exception.source ?? "MyProgress"} ·{" "}
                      {exception.severity ?? "WARNING"}
                    </span>
                    <span>{exception.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="subtle">
                No import exceptions require manual handling.
              </p>
            )}
          </section>
        ) : (
          <>
            <section aria-label="Data import records">
              <h2>Imported Records</h2>
              <div className="comparison-rows">
                {state.records.map((record) => (
                  <div key={record.id} className="comparison-row">
                    <strong>
                      {payloadValue(record.normalized_payload, "course_code") ??
                        record.raw_label}
                    </strong>
                    <span>
                      Row {record.row_number} · {statusLabel(record.status)} ·{" "}
                      {payloadValue(record.normalized_payload, "credits") ??
                        "0.0"}{" "}
                      credits
                    </span>
                  </div>
                ))}
              </div>
            </section>
            <section aria-label="Data import mapping candidates">
              <h2>Mapping Candidates</h2>
              <div className="comparison-rows">
                {state.candidates.map((candidate) => (
                  <div key={candidate.id} className="comparison-row">
                    <strong>{candidate.reason_code}</strong>
                    <span>
                      {statusLabel(candidate.target_entity_type)} · confidence{" "}
                      {candidate.confidence_score} · {candidate.explanation}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </section>

      <section className="comparison-table" aria-label="Data import warnings">
        <h2>Warnings</h2>
        {state.warnings.length > 0 ? (
          <div className="comparison-rows">
            {state.warnings.map((warning) => (
              <div key={warning.id} className="comparison-row">
                <strong>{warning.warning_code}</strong>
                <span>
                  {warning.message}{" "}
                  {warning.requires_advisor_confirmation
                    ? "Advisor confirmation required."
                    : ""}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtle">No import warnings.</p>
        )}
      </section>
    </div>
  );
}

function MyProgressImportPreview({
  display,
}: {
  display: MyProgressPreviewDisplay;
}) {
  const { programSummary, creditSummary } = display;
  const provenanceEntries = Object.entries(display.fieldProvenance).slice(0, 6);
  const visibleTextSample = stringFromUnknown(
    display.rawSnapshot.visibleTextSample,
  );
  const progressBarText = stringFromUnknown(
    display.rawSnapshot.progressBarText,
  );
  return (
    <section
      className="comparison-table"
      aria-label="MyProgress import verification summary"
    >
      <h2>MyProgress Verification Summary</h2>
      <div className="summary-grid compact-summary">
        <SummaryMetric
          label="Program"
          value={programSummary.programName ?? "Not detected"}
        />
        <SummaryMetric
          label="Degree"
          value={programSummary.degree ?? "Not detected"}
        />
        <SummaryMetric
          label="Major"
          value={programSummary.major ?? "Not detected"}
        />
        <SummaryMetric
          label="Department"
          value={programSummary.department ?? "Not detected"}
        />
        <SummaryMetric
          label="Catalog"
          value={
            programSummary.catalogYear
              ? String(programSummary.catalogYear)
              : "Not detected"
          }
        />
        <SummaryMetric
          label="GPA"
          value={
            programSummary.cumulativeGpa
              ? programSummary.cumulativeGpa.toFixed(3)
              : "Not detected"
          }
        />
        <SummaryMetric
          label="Institution GPA"
          value={
            programSummary.institutionGpa
              ? programSummary.institutionGpa.toFixed(3)
              : "Not detected"
          }
        />
        <SummaryMetric
          label="Expected Completion"
          value={programSummary.anticipatedCompletionDate ?? "Not detected"}
        />
        <SummaryMetric
          label="Total Credits"
          value={
            creditSummary.totalAppliedCredits !== undefined &&
            creditSummary.totalRequiredCredits !== undefined
              ? `${creditSummary.totalAppliedCredits} / ${creditSummary.totalRequiredCredits}`
              : "Not detected"
          }
        />
        <SummaryMetric
          label="Completed"
          value={String(creditSummary.completedCredits ?? "Not detected")}
        />
        <SummaryMetric
          label="In Progress"
          value={String(creditSummary.inProgressCredits ?? "Not detected")}
        />
        <SummaryMetric
          label="Planned"
          value={String(creditSummary.plannedCredits ?? "Not detected")}
        />
        <SummaryMetric
          label="Remaining"
          value={String(creditSummary.remainingCredits ?? "Not detected")}
        />
        <SummaryMetric
          label="Completion"
          value={
            creditSummary.completionPercent !== undefined
              ? `${creditSummary.completionPercent.toFixed(2)}%`
              : "Not detected"
          }
        />
        <SummaryMetric
          label="Requirement Groups"
          value={String(display.requirementGroups.length)}
        />
        <SummaryMetric
          label="Downstream Analysis"
          value={display.downstreamAnalysisAllowed ? "Allowed" : "Blocked"}
        />
      </div>
      <ul className="compact-list">
        <li>
          <strong>Review scope</strong>
          <span>
            {display.exceptions.length === 0
              ? "Exception count is 0; high-confidence fields and rows are auto-confirmed."
              : "Low-confidence exceptions must be reviewed before use."}
          </span>
        </li>
        <li>
          <strong>Apply path</strong>
          <span>
            {display.canApplyVerifiedImport
              ? "Verified import can be applied without manual row-by-row review."
              : "Failed or exception-bearing validation blocks degree audit and planning use."}
          </span>
        </li>
      </ul>

      <section className="comparison-rows" aria-label="MyProgress groups">
        {display.requirementGroups.map((group, index) => (
          <div
            key={`${stringFromUnknown(group.name) ?? "group"}-${index}`}
            className="comparison-row"
          >
            <strong>{stringFromUnknown(group.name) ?? "Unnamed group"}</strong>
            <span>
              {stringFromUnknown(group.statusText) ?? "No status text"}
            </span>
          </div>
        ))}
      </section>

      <section className="comparison-rows" aria-label="MyProgress source text">
        {progressBarText ? (
          <div className="comparison-row">
            <strong>Progress Bar</strong>
            <span>{progressBarText}</span>
          </div>
        ) : null}
        {visibleTextSample ? (
          <div className="comparison-row">
            <strong>Visible Text</strong>
            <span>{visibleTextSample.slice(0, 280)}</span>
          </div>
        ) : null}
        {provenanceEntries.map(([field, value]) => {
          const provenance = recordFromUnknown(value);
          return (
            <div key={field} className="comparison-row">
              <strong>{field}</strong>
              <span>
                {stringFromUnknown(provenance.source) ?? "MyProgress"} ·{" "}
                {stringFromUnknown(provenance.confidence) ?? "unknown"}
              </span>
              <span>
                {String(provenance.rawText ?? provenance.value ?? "")}
              </span>
            </div>
          );
        })}
      </section>
    </section>
  );
}

function SectionMonitoringPanel({ state }: { state: SectionMonitoringState }) {
  const targetById =
    state.status === "ready"
      ? new Map(state.targets.map((target) => [target.id, target]))
      : new Map<string, SectionMonitorTarget>();

  return (
    <section
      className="section-monitoring-panel"
      id="section-monitoring"
      aria-label="Section Monitoring"
    >
      <div className="section-heading">
        <div>
          <h2>Section Monitoring</h2>
          <p className="subtle">
            Advisory alerts from user-triggered section-search imports.
          </p>
        </div>
        <p className="notice compact">Manual review required.</p>
      </div>

      <ul
        className="disclaimer-list"
        aria-label="Section monitoring disclaimers"
      >
        <li>
          Section monitoring is based on user-triggered imported data and may
          differ from the official portal. Always verify information manually in
          the official registration portal.
        </li>
        <li>
          This system does not register, drop, swap, waitlist, submit forms, or
          perform any portal action.
        </li>
      </ul>

      <AdvisoryLabels
        keys={[
          "NON_OFFICIAL_IMPORTED_DATA",
          "ADVISORY_ONLY",
          "VERIFY_IN_OFFICIAL_PORTAL",
        ]}
      />

      {state.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Loading section monitoring</h2>
          <p>Retrieving monitored sections and advisory alerts.</p>
        </section>
      ) : null}

      {state.status === "offline" ||
      state.status === "failed" ||
      state.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {state.status === "schema-error"
              ? "Section monitoring schema error"
              : "Section monitoring unavailable"}
          </h2>
          <p>{state.message}</p>
        </section>
      ) : null}

      {state.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>No section alerts</h2>
          <p>{state.message}</p>
        </section>
      ) : null}

      {state.status === "ready" ? (
        <div className="section-monitoring-grid">
          <section className="comparison-table" aria-label="Monitored sections">
            <h2>Monitored Sections</h2>
            {state.targets.length > 0 ? (
              <div className="comparison-rows">
                {state.targets.map((target) => (
                  <div key={target.id} className="comparison-row">
                    <strong>
                      {target.course_code} {target.section_code}
                    </strong>
                    <span>
                      {target.term} · {target.title ?? "Untitled section"} ·{" "}
                      {target.status ? statusLabel(target.status) : "Unknown"}
                    </span>
                    <span>
                      Latest imported snapshot:{" "}
                      {formatAcademicTimestamp(
                        target.latest_snapshot_created_at,
                      )}
                    </span>
                    <span>
                      {target.is_active ? "Active" : "Archived"} · Advisory only
                      ·{" "}
                      {target.is_official
                        ? "Official source"
                        : "Non-official imported data"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                copyKey="NO_SECTION_MONITORING_TARGETS"
                ariaLabel="Section monitoring targets empty state"
              />
            )}
          </section>

          <section className="comparison-table" aria-label="Advisory alerts">
            <h2>Advisory Alerts</h2>
            {state.alerts.length > 0 ? (
              <div className="comparison-rows">
                {state.alerts.map((alert) => {
                  const target = targetById.get(alert.target_id);
                  return (
                    <div key={alert.id} className="comparison-row">
                      <strong>{statusLabel(alert.alert_type)}</strong>
                      <span>
                        {target
                          ? `${target.course_code} ${target.section_code}`
                          : alert.target_id}{" "}
                        · {statusLabel(alert.severity)} ·{" "}
                        {alert.is_acknowledged
                          ? "acknowledged"
                          : "manual review"}
                      </span>
                      <span>
                        {alert.field_name ?? "Unknown section change"}:{" "}
                        {formatBeforeAfterValue(
                          alert.previous_value,
                          alert.current_value,
                        )}
                      </span>
                      <span>{alert.message}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState
                copyKey="NO_SECTION_MONITORING_ALERTS"
                ariaLabel="Section monitoring alerts empty state"
              />
            )}
          </section>

          <section
            className="comparison-table"
            aria-label="Manual registration checklist"
          >
            <h2>Manual Checklist</h2>
            <ul className="compact-list">
              <li>Open the official registration portal manually.</li>
              <li>Verify the section status manually.</li>
              <li>Confirm prerequisites, restrictions, and holds manually.</li>
              <li>
                Register manually through the official portal if appropriate.
              </li>
            </ul>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function DataReviewPanel({
  dataImportState,
  dataReviewState,
  setDataReviewState,
}: {
  dataImportState: DataImportPreviewState;
  dataReviewState: DataReviewState;
  setDataReviewState: Dispatch<SetStateAction<DataReviewState>>;
}) {
  const myProgressPreview = myProgressPreviewFromState(dataImportState);
  const reviewRecordsForDisplay =
    dataReviewState.status === "ready" && myProgressPreview
      ? dataReviewState.records.filter(
          (record) =>
            record.requires_advisor_confirmation ||
            record.decision === "UNREVIEWED" ||
            record.decision === "NEEDS_ADVISOR_REVIEW",
        )
      : dataReviewState.status === "ready"
        ? dataReviewState.records
        : [];
  const autoConfirmedReviewCount =
    dataReviewState.status === "ready" && myProgressPreview
      ? dataReviewState.records.length - reviewRecordsForDisplay.length
      : 0;

  const [gradeEdits, setGradeEdits] = useState<Record<string, string>>({});

  async function loadReviewDetail(
    review: DataImportReviewSession,
    applicationResult: DataReviewApplicationResult | null = null,
  ): Promise<void> {
    if (!apiBaseUrl) {
      setDataReviewState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    const [records, warnings, applications] = await Promise.all([
      fetchDataImportReviewRecords(apiBaseUrl, review.id, {
        timeoutMs: 5_000,
      }),
      fetchDataImportReviewWarnings(apiBaseUrl, review.id, {
        timeoutMs: 5_000,
      }),
      fetchDataImportReviewApplications(apiBaseUrl, review.id, {
        timeoutMs: 5_000,
      }),
    ]);
    setDataReviewState({
      status: "ready",
      review,
      records,
      warnings,
      applications,
      applicationResult,
    });
  }

  async function handleCreateReview(): Promise<void> {
    if (!apiBaseUrl) {
      setDataReviewState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    if (dataImportState.status !== "ready") {
      setDataReviewState({
        status: "empty",
        message: "Preview or load a staging import before creating a review.",
      });
      return;
    }
    setDataReviewState({ status: "loading" });
    try {
      const review = await createDataImportReview(
        apiBaseUrl,
        {
          data_import_run_id: dataImportState.run.id,
          reviewer_label: "Mock student self-review",
        },
        { timeoutMs: 5_000 },
      );
      await loadReviewDetail(review);
    } catch (error: unknown) {
      setDataReviewState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  async function handleLoadLatestReviews(): Promise<void> {
    if (!apiBaseUrl) {
      setDataReviewState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setDataReviewState({ status: "loading" });
    try {
      const reviews = await fetchStudentDataImportReviews(
        apiBaseUrl,
        mockStudentId,
        { timeoutMs: 5_000 },
      );
      if (reviews.length === 0) {
        setDataReviewState({
          status: "empty",
          message: "No data import reviews are available for the mock student.",
        });
        return;
      }
      await loadReviewDetail(reviews[0]);
    } catch (error: unknown) {
      setDataReviewState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  async function handleDecision(
    recordReview: ImportedRecordReview,
    decision: ImportedRecordReview["decision"],
  ): Promise<void> {
    if (!apiBaseUrl || dataReviewState.status !== "ready") {
      return;
    }
    const review = dataReviewState.review;
    setDataReviewState({ status: "loading" });
    try {
      const editedGrade = gradeEdits[recordReview.id];
      const request =
        decision === "EDITED_AND_CONFIRMED"
          ? {
              decision,
              edited_normalized_payload: {
                grade:
                  editedGrade ??
                  payloadValue(
                    recordReview.imported_record.normalized_payload,
                    "grade",
                  ) ??
                  "",
              },
              review_note: "Reviewer edited a simple normalized field.",
            }
          : { decision };
      await updateImportedRecordReview(
        apiBaseUrl,
        review.id,
        recordReview.id,
        request,
        { timeoutMs: 5_000 },
      );
      await loadReviewDetail(review, dataReviewState.applicationResult);
    } catch (error: unknown) {
      setDataReviewState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  async function handleApply(dryRun: boolean): Promise<void> {
    if (!apiBaseUrl || dataReviewState.status !== "ready") {
      return;
    }
    const review = dataReviewState.review;
    setDataReviewState({ status: "loading" });
    try {
      const result = await applyDataImportReview(
        apiBaseUrl,
        review.id,
        { dry_run: dryRun, allow_advisor_review_records: false },
        { timeoutMs: 8_000 },
      );
      await loadReviewDetail(result.review_session, result);
    } catch (error: unknown) {
      setDataReviewState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  return (
    <section
      className="data-review-panel"
      aria-label="Data Review and Confirmation"
    >
      <div className="section-heading">
        <div>
          <h2>Data Review &amp; Confirmation</h2>
          <p className="subtle">
            Confirmed records apply only to internal planning data.
          </p>
        </div>
        <p className="notice compact">Explicit apply required.</p>
      </div>

      <ul className="disclaimer-list" aria-label="Data review disclaimers">
        <li>Review decisions do not create official transcript records.</li>
        <li>Dry run shows proposed writes without creating domain records.</li>
        <li>
          Rejected, deferred, duplicate, and advisor-review records are logged.
        </li>
      </ul>
      <AdvisoryLabels keys={["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"]} />

      <div className="scenario-controls data-import-controls">
        <button type="button" onClick={() => void handleCreateReview()}>
          Create review
        </button>
        <button type="button" onClick={() => void handleLoadLatestReviews()}>
          Load latest reviews
        </button>
        {dataReviewState.status === "ready" ? (
          <>
            <button type="button" onClick={() => void handleApply(true)}>
              Dry run
            </button>
            <button type="button" onClick={() => void handleApply(false)}>
              Apply confirmed
            </button>
          </>
        ) : null}
      </div>

      {dataReviewState.status === "idle" ? (
        <EmptyState
          copyKey="NO_CONFIRMED_IMPORTS"
          ariaLabel="Data review empty state"
        />
      ) : null}

      {dataReviewState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Loading review</h2>
          <p>Retrieving review records, warnings, and application logs.</p>
        </section>
      ) : null}

      {dataReviewState.status === "offline" ||
      dataReviewState.status === "failed" ||
      dataReviewState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {dataReviewState.status === "schema-error"
              ? "Data review schema error"
              : "Data review unavailable"}
          </h2>
          <p>{dataReviewState.message}</p>
        </section>
      ) : null}

      {dataReviewState.status === "empty" ? (
        <EmptyState
          copyKey="NO_CONFIRMED_IMPORTS"
          ariaLabel="Data review empty state"
        />
      ) : null}

      {dataReviewState.status === "ready" ? (
        <div className="data-import-result">
          <section className="summary-grid" aria-label="Data review summary">
            <SummaryMetric
              label="Review Status"
              value={statusLabel(dataReviewState.review.status)}
            />
            <SummaryMetric
              label="Records"
              value={String(dataReviewState.records.length)}
            />
            {myProgressPreview ? (
              <SummaryMetric
                label="Auto-Confirmed"
                value={String(autoConfirmedReviewCount)}
              />
            ) : null}
            {myProgressPreview ? (
              <SummaryMetric
                label="Exception Queue"
                value={String(reviewRecordsForDisplay.length)}
              />
            ) : null}
            <SummaryMetric
              label="Warnings"
              value={String(dataReviewState.warnings.length)}
            />
            <SummaryMetric
              label="Applications"
              value={String(dataReviewState.applications.length)}
            />
            <SummaryMetric
              label="Last Result"
              value={
                dataReviewState.applicationResult?.dry_run
                  ? "Dry run"
                  : dataReviewState.applicationResult?.application?.status
                    ? statusLabel(
                        dataReviewState.applicationResult.application.status,
                      )
                    : "None"
              }
            />
          </section>

          <section className="comparison-table" aria-label="Review records">
            <h2>
              {myProgressPreview ? "Exception Decisions" : "Record Decisions"}
            </h2>
            <div className="comparison-rows">
              {reviewRecordsForDisplay.length === 0 && myProgressPreview ? (
                <p className="subtle">
                  High-confidence MyProgress fields were auto-confirmed; there
                  are no exceptions requiring row-by-row review.
                </p>
              ) : null}
              {reviewRecordsForDisplay.map((recordReview) => {
                const courseCode =
                  payloadValue(
                    recordReview.imported_record.normalized_payload,
                    "course_code",
                  ) ?? recordReview.imported_record.raw_label;
                const grade =
                  gradeEdits[recordReview.id] ??
                  payloadValue(
                    recordReview.imported_record.normalized_payload,
                    "grade",
                  ) ??
                  "";
                return (
                  <div key={recordReview.id} className="comparison-row">
                    <strong>{courseCode}</strong>
                    <span>
                      {statusLabel(recordReview.decision)} ·{" "}
                      {recordReview.requires_advisor_confirmation
                        ? "advisor review flagged"
                        : "student-reviewable"}
                    </span>
                    <span>
                      {recordReview.selected_mapping_candidate?.explanation ??
                        "No selected mapping candidate."}
                    </span>
                    <div className="record-review-actions">
                      <label className="review-edit-field">
                        Grade
                        <input
                          value={grade}
                          onChange={(event) =>
                            setGradeEdits((current) => ({
                              ...current,
                              [recordReview.id]: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(recordReview, "CONFIRMED")
                        }
                      >
                        Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(recordReview, "REJECTED")
                        }
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(recordReview, "DEFERRED")
                        }
                      >
                        Defer
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(
                            recordReview,
                            "NEEDS_ADVISOR_REVIEW",
                          )
                        }
                      >
                        Advisor review
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(
                            recordReview,
                            "EDITED_AND_CONFIRMED",
                          )
                        }
                      >
                        Edit + confirm
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {dataReviewState.applicationResult ? (
            <section
              className="comparison-table"
              aria-label="Data application result"
            >
              <h2>Application Result</h2>
              <div className="comparison-rows">
                {dataReviewState.applicationResult.applied_records.map(
                  (appliedRecord) => (
                    <div
                      key={`${appliedRecord.imported_record_id}-${appliedRecord.reason_code}`}
                      className="comparison-row"
                    >
                      <strong>{statusLabel(appliedRecord.action)}</strong>
                      <span>
                        {appliedRecord.reason_code} · {appliedRecord.message}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </section>
          ) : null}

          <section className="comparison-table" aria-label="Review warnings">
            <h2>Review Warnings</h2>
            {dataReviewState.warnings.length > 0 ? (
              <div className="comparison-rows">
                {dataReviewState.warnings.map((warning) => (
                  <div key={warning.id} className="comparison-row">
                    <strong>{warning.warning_code}</strong>
                    <span>
                      {warning.message}{" "}
                      {warning.requires_advisor_confirmation
                        ? "Advisor confirmation required."
                        : ""}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="subtle">No review warnings.</p>
            )}
          </section>
        </div>
      ) : null}
    </section>
  );
}

function payloadValue(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return null;
}

function formatMeetingList(
  meetings: ScheduleOptimizationDetail["options"][number]["selected_sections"][number]["meetings"],
): string {
  if (meetings.length === 0) {
    return "Meeting time not available";
  }
  return meetings
    .map((meeting) => {
      if (meeting.is_online && !meeting.day_of_week) {
        return "Online async";
      }
      if (!meeting.day_of_week || !meeting.start_time || !meeting.end_time) {
        return statusLabel(meeting.meeting_type);
      }
      return `${statusLabel(meeting.day_of_week)} ${meeting.start_time}-${meeting.end_time}`;
    })
    .join("; ");
}

async function loadScenarioDetail(
  baseUrl: string,
  scenario: AcademicScenario,
): Promise<ScenarioDetail> {
  const [programs, audits, allocations, warnings, comparison] =
    await Promise.all([
      fetchAcademicScenarioPrograms(baseUrl, scenario.id, { timeoutMs: 5_000 }),
      fetchAcademicScenarioAudits(baseUrl, scenario.id, { timeoutMs: 5_000 }),
      fetchAcademicScenarioAllocations(baseUrl, scenario.id, {
        timeoutMs: 5_000,
      }),
      fetchAcademicScenarioWarnings(baseUrl, scenario.id, { timeoutMs: 5_000 }),
      fetchAcademicScenarioComparison(baseUrl, scenario.id, {
        timeoutMs: 5_000,
      }),
    ]);
  return { scenario, programs, audits, allocations, warnings, comparison };
}

function ScenarioResult({
  state,
  selectedCandidate,
}: {
  state: Extract<ScenarioState, { status: "ready" }>;
  selectedCandidate: CandidateProgram;
}) {
  const { detail } = state;
  const selectedAllocations = detail.allocations.filter(
    (allocation) => allocation.allocation_type !== "UNALLOCATED",
  );
  return (
    <div className="scenario-result">
      <section className="summary-grid" aria-label="What-if scenario summary">
        <SummaryMetric label="Candidate" value={selectedCandidate.label} />
        <SummaryMetric
          label="Scenario Status"
          value={statusLabel(detail.scenario.status)}
        />
        <SummaryMetric
          label="Shared Credits"
          value={formatCredits(detail.comparison.shared_credits)}
        />
        <SummaryMetric
          label="Unique Secondary Credits"
          value={formatCredits(detail.comparison.unique_secondary_credits)}
        />
        <SummaryMetric
          label="Estimated Additional Credits"
          value={formatCredits(detail.comparison.estimated_additional_credits)}
        />
        <SummaryMetric
          label="Manual Review"
          value={String(detail.comparison.manual_review_count)}
        />
      </section>

      <section className="scenario-columns">
        <div>
          <h2>Programs</h2>
          <ul className="compact-list">
            {detail.programs.map((program) => (
              <li key={program.id}>
                <strong>{program.program_name}</strong>
                <span>{statusLabel(program.relationship_type)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2>Course Allocation</h2>
          {selectedAllocations.length > 0 ? (
            <ul className="compact-list">
              {selectedAllocations.map((allocation) => (
                <li key={allocation.id}>
                  <strong>
                    {allocation.course_code ?? allocation.reason_code}
                  </strong>
                  <span>
                    {statusLabel(allocation.allocation_type)} ·{" "}
                    {formatCredits(allocation.credit_amount)} credits
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No course allocations are available.</p>
          )}
        </div>
        <div>
          <h2>Warnings</h2>
          {detail.warnings.length > 0 ? (
            <ul className="compact-list">
              {detail.warnings.map((warning) => (
                <li key={warning.id}>
                  <strong>{warning.warning_code}</strong>
                  <span>{warning.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">No manual review warnings.</p>
          )}
        </div>
      </section>

      {state.comparisons.length > 0 ? (
        <section
          className="comparison-table"
          aria-label="Saved scenario comparison"
        >
          <h2>Saved Scenario Comparison</h2>
          <div className="comparison-rows">
            {state.comparisons.map((comparison) => {
              const scenario = state.savedScenarios.find(
                (item) => item.id === comparison.academic_plan_scenario_id,
              );
              return (
                <div
                  key={comparison.academic_plan_scenario_id}
                  className="comparison-row"
                >
                  <strong>
                    {scenario?.name ?? comparison.academic_plan_scenario_id}
                  </strong>
                  <span>
                    {formatCredits(comparison.estimated_additional_credits)}{" "}
                    estimated additional credits
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
