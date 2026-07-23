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
  fetchLocalBackupStatus,
  downloadLocalBackup,
  prepareLocalDataRemoval,
  cancelLocalDataRemoval,
  validateLocalRestore,
  confirmLocalRestore,
  cancelLocalRestore,
  fetchLatestDegreeAudit,
  fetchStudentDataImports,
  fetchStudentScheduleOptimizations,
  fetchStudentAcademicPlans,
  fetchStudentEligibilityChecks,
  fetchStudentAcademicScenarios,
  fetchActiveCourseStateSnapshot,
  formatAcademicTimestamp,
  updateImportedRecordReview,
  validateDataImport,
  type AcademicPlanComparison,
  type AcademicPlanDetail,
  type AcademicPlanRun,
  type AcademicScenario,
  type AcademicEmptyStateKey,
  type AdvisoryLabelKey,
  type CourseEligibilityCheck,
  type CourseStateSnapshotDetail,
  type DataApplicationRun,
  type DataImportRun,
  type DataImportReviewSession,
  type DataReviewApplicationResult,
  type DataReviewWarning,
  type DegreeAuditRun,
  type HealthResponse,
  type BackupStatus,
  type RestorePreview,
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
  startTransition,
  useEffect,
  useState,
  useSyncExternalStore,
} from "react";
import { parsePublicEnv, parseRuntimeApiBaseUrl } from "../lib/env";
import {
  isUsableMyProgressPreviewSummary,
  savedImportOptionFromRun,
  selectPreferredLoadedDataImport,
} from "../lib/data-import-preview";
import {
  formatZhCnBeforeAfterValue,
  getZhCnAdvisoryLabels,
  getZhCnEmptyStateCopy,
  localizeDemoOptionLabel,
  localizeStatusBadge,
  localizeStatusLabel,
} from "../lib/zh-cn";
import {
  useActiveWorkflow,
  WorkflowShell,
} from "../components/workflow-shell";
import { useCourseStateWorkflow } from "../lib/course-state-workflow";
import { useSectionMonitoringWorkflow } from "../lib/section-monitoring-workflow";
import { usePairingWorkflow } from "../lib/pairing-workflow";
import { DiagnosticsWorkflow } from "../components/diagnostics-workflow";

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
  | "真实导入数据 - 已自动验证"
  | "真实导入数据 - 需要审核"
  | "真实导入数据 - 等待审核"
  | "演示 / 模拟数据"
  | "尚未加载导入";
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
type CourseStateState =
  | { status: "loading" }
  | { status: "ready"; detail: CourseStateSnapshotDetail }
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
type MyProgressCourseRow = {
  rowNumber: number;
  courseCode: string;
  courseTitle: string;
  term: string;
  status: string;
  requirementGroupContext: string;
  rawRowText: string;
  sourceTableIndex: string;
  sourceRowIndex: string;
  confidence: string;
  warnings: string[];
  reasonCodes: string[];
  requiresReview: boolean;
};
type MyProgressReadinessKey =
  | "summary"
  | "requirement_summary"
  | "course_rows"
  | "planner"
  | "course_eligibility"
  | "schedule_builder";
type MyProgressReadinessItem = {
  status: string;
  reasonCodes: string[];
};
type MyProgressPreviewDisplay = {
  realImportStatus: string;
  programSummary: MyProgressProgramSummary;
  creditSummary: MyProgressCreditSummary;
  requirementGroups: Record<string, unknown>[];
  courseRows: MyProgressCourseRow[];
  exceptions: MyProgressException[];
  extractedDegreeAuditRowCount: number;
  parsedCourseLikeRowCount: number;
  parsedRequirementRowCount: number;
  ignoredRowCount: number;
  exceptionRowCount: number;
  extractionBounded: boolean;
  extractionTruncated: boolean;
  autoConfirmedFieldCount: number;
  autoConfirmedCourseRowCount: number;
  overallConfidenceScore: number;
  downstreamAnalysisAllowed: boolean;
  canApplyVerifiedImport: boolean;
  readiness: Record<MyProgressReadinessKey, MyProgressReadinessItem>;
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

let apiBaseUrl: string | undefined;

function setConfiguredApiBaseUrl(value: string | undefined): string | undefined {
  apiBaseUrl = value;
  return value;
}

function getConfiguredBrowserApiBaseUrl(): string | undefined {
  try {
    return setConfiguredApiBaseUrl(
      parseRuntimeApiBaseUrl(window.location.search) ?? configuredApiBaseUrl(),
    );
  } catch {
    return setConfiguredApiBaseUrl(undefined);
  }
}

function getServerApiBaseUrl(): string | undefined {
  return configuredApiBaseUrl();
}

function subscribeToStableBrowserValue(): () => void {
  return () => undefined;
}

function getBrowserOrigin(): string {
  return window.location.origin;
}

function getServerOrigin(): string {
  return "正在检测网页来源";
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
    return "API 返回了意外的健康检查响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知 API 健康检查错误";
}

function describeAuditError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的学业审核响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知学业审核错误";
}

function describeScenarioError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的假设方案响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知假设方案错误";
}

function describeEligibilityError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的课程资格响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知课程资格错误";
}

function describePlannerError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的学业规划响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知学业规划错误";
}

function describeScheduleError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的课表优化响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知课表优化错误";
}

function describeDataImportError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的数据导入响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return describeApiRequestFailure(error);
  }
  return error instanceof Error ? error.message : "未知数据导入错误";
}

function localApiRestartGuidance(): string {
  return `API 可能未重启或仍是旧版本。请重启 API 和 web dev server，确认浏览器端口已被 CORS 允许，并核对当前 API 基础地址：${
    apiBaseUrl ?? "未配置"
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
  return localizeStatusLabel(status);
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

function stringsFromUnknown(value: unknown): string[] {
  return Array.isArray(value)
    ? value
        .map((item) => (typeof item === "string" ? item : null))
        .filter((item): item is string => item !== null)
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

function readinessItemFromUnknown(value: unknown): MyProgressReadinessItem {
  const record = recordFromUnknown(value);
  return {
    status: stringFromUnknown(record.status) ?? "UNKNOWN",
    reasonCodes: stringsFromUnknown(record.reason_codes),
  };
}

function readinessFromUnknown(
  value: unknown,
): Record<MyProgressReadinessKey, MyProgressReadinessItem> {
  const record = recordFromUnknown(value);
  return {
    summary: readinessItemFromUnknown(record.summary),
    requirement_summary: readinessItemFromUnknown(record.requirement_summary),
    course_rows: readinessItemFromUnknown(record.course_rows),
    planner: readinessItemFromUnknown(record.planner),
    course_eligibility: readinessItemFromUnknown(record.course_eligibility),
    schedule_builder: readinessItemFromUnknown(record.schedule_builder),
  };
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
  const courseRows = recordsFromUnknown(payload.course_rows).map((row) => ({
    rowNumber: numberFromUnknown(row.row_number) ?? 0,
    courseCode: stringFromUnknown(row.course_code) ?? "",
    courseTitle: stringFromUnknown(row.course_title) ?? "",
    term: stringFromUnknown(row.term) ?? "",
    status: stringFromUnknown(row.status) ?? "UNKNOWN",
    requirementGroupContext:
      stringFromUnknown(row.requirement_group_context) ?? "",
    rawRowText: stringFromUnknown(row.raw_row_text) ?? "",
    sourceTableIndex: stringFromUnknown(row.source_table_index) ?? "",
    sourceRowIndex: stringFromUnknown(row.source_row_index) ?? "",
    confidence: stringFromUnknown(row.confidence) ?? "",
    warnings: stringsFromUnknown(row.warnings),
    reasonCodes: stringsFromUnknown(row.reason_codes),
    requiresReview: row.requires_review === true,
  }));
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
    courseRows,
    exceptions,
    extractedDegreeAuditRowCount:
      numberFromUnknown(payload.extracted_degree_audit_row_count) ?? 0,
    parsedCourseLikeRowCount:
      numberFromUnknown(payload.parsed_course_like_row_count) ?? 0,
    parsedRequirementRowCount:
      numberFromUnknown(payload.parsed_requirement_row_count) ?? 0,
    ignoredRowCount: numberFromUnknown(payload.ignored_row_count) ?? 0,
    exceptionRowCount: numberFromUnknown(payload.exception_row_count) ?? 0,
    extractionBounded: payload.extraction_bounded === true,
    extractionTruncated: payload.extraction_truncated === true,
    autoConfirmedFieldCount:
      numberFromUnknown(payload.auto_confirmed_field_count) ?? 0,
    autoConfirmedCourseRowCount:
      numberFromUnknown(payload.auto_confirmed_course_row_count) ?? 0,
    overallConfidenceScore:
      numberFromUnknown(payload.overall_confidence_score) ?? 0,
    downstreamAnalysisAllowed: payload.downstream_analysis_allowed === true,
    canApplyVerifiedImport: payload.can_apply_verified_import === true,
    readiness: readinessFromUnknown(payload.readiness),
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
  const states: ReadyDataImportPreviewState[] = [];
  for (const run of preferMyProgressImports(savedImports)) {
    const previewState = await loadDataImportPreviewState(
      baseUrl,
      run,
      savedImports,
    );
    states.push(previewState);
  }
  return selectPreferredLoadedDataImport(states);
}

function importModeLabel(
  display: MyProgressPreviewDisplay | null,
): ImportSourceStateLabel {
  if (!display) {
    return "演示 / 模拟数据";
  }
  if (
    display.realImportStatus === "REAL_IMPORTED_DATA_AUTO_VERIFIED" &&
    display.downstreamAnalysisAllowed &&
    display.canApplyVerifiedImport &&
    display.exceptions.length === 0
  ) {
    return "真实导入数据 - 已自动验证";
  }
  if (
    display.exceptions.length > 0 ||
    !display.downstreamAnalysisAllowed ||
    !display.canApplyVerifiedImport
  ) {
    return "真实导入数据 - 需要审核";
  }
  return "真实导入数据 - 等待审核";
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
    return "尚未加载导入";
  }
  return auditState.status === "ready" ? "演示 / 模拟数据" : "尚未加载导入";
}

function readinessAllows(status: string | undefined): boolean {
  return status === "READY" || status === "READY_WITH_WARNINGS";
}

const readinessLabels: Record<MyProgressReadinessKey, string> = {
  summary: "汇总数据",
  requirement_summary: "毕业要求摘要",
  course_rows: "课程行数据",
  planner: "长期规划",
  course_eligibility: "课程资格",
  schedule_builder: "课表优化",
};

const readinessStatusCopy: Record<string, string> = {
  APPLIED_OR_READY: "已应用 / 可应用",
  AUTO_VERIFIED: "已自动验证",
  BLOCKED: "已阻止",
  DEMO_ONLY: "演示模式",
  MISSING: "缺失",
  PARTIAL_REQUIRES_REVIEW: "部分解析 / 需要审核",
  PARTIAL: "部分就绪",
  READY: "就绪",
  READY_WITH_WARNINGS: "就绪但有警告",
  NEEDS_REVIEW: "需要审核",
  REQUIRES_REVIEW: "需要审核",
  WARNING: "警告",
};

function readinessStatusLabel(status: string): string {
  return readinessStatusCopy[status] ?? statusLabel(status);
}

function readinessReasonLabel(reasonCode: string): string {
  const copy: Record<string, string> = {
    BOUNDED_OR_TRUNCATED_EXTRACTION: "浏览器提取有边界或被截断",
    COURSE_ROW_EXCEPTIONS_PRESENT: "仍有课程行异常需要审核",
    IMPORTED_ROWS_NEED_ADVISOR_CONFIRMATION: "导入课程行仍需顾问或学校确认",
    MY_PROGRESS_REQUIREMENTS_MISSING: "未检测到 MyProgress 要求摘要",
    MY_PROGRESS_SUMMARY_NOT_VERIFIED: "MyProgress 汇总未通过自动验证",
    NO_COURSE_ROWS_PARSED: "尚未解析真实课程行",
    REAL_COURSE_HISTORY_NOT_READY: "尚未接入可靠真实课程历史",
    REAL_SECTION_SEARCH_DATA_NOT_IMPORTED: "尚未导入真实课节搜索数据",
    SOURCE_BOUNDED_OR_TRUNCATED: "来源提取有边界或被截断",
    PROGRAM_VERSION_UNMATCHED: "导入项目与内部 Catalog 版本尚未可靠匹配",
    REQUIREMENT_TREE_INCOMPLETE: "毕业要求树覆盖仍不完整",
    COURSE_HISTORY_NOT_RELIABLE: "尚无可靠的已匹配课程历史",
    NO_CATALOG_MATCHED_COURSE_HISTORY: "没有可用于下游的 Catalog 匹配课程历史",
    RELIABLE_PREREQUISITE_EVIDENCE_MISSING: "缺少可靠的已完成或进行中先修证据",
    UNMATCHED_COURSES_LIMIT_ELIGIBILITY: "未匹配课程限制课程资格判断",
    CRITICAL_COURSE_STATE_EXCEPTIONS: "仍有关键课程状态异常",
    COURSE_CODE_UNMATCHED: "存在未匹配的课程代码",
    COURSE_STATE_EXCEPTIONS_PRESENT: "存在课程状态异常记录",
    WAITING_FOR_RELIABLE_MYPROGRESS_COURSE_ROWS:
      "等待完整可靠的 MyProgress 课程行",
  };
  return copy[reasonCode] ?? reasonCode;
}

const courseStateReadinessLabels: Record<string, string> = {
  summary: "汇总数据",
  requirement_summary: "毕业要求摘要",
  course_history: "课程历史",
  degree_audit: "学业审核",
  course_eligibility: "课程资格",
  long_term_planner: "长期规划",
  semester_schedule: "学期课表",
};

export default function Home() {
  const activeWorkflow = useActiveWorkflow();
  const apiBaseUrl = useSyncExternalStore(
    subscribeToStableBrowserValue,
    getConfiguredBrowserApiBaseUrl,
    getServerApiBaseUrl,
  );
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
          message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
        },
  );
  const [auditState, setAuditState] = useState<AuditState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : {
          status: "failed",
          message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
            message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
            message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
          },
    );
  const [dataReviewState, setDataReviewState] = useState<DataReviewState>(() =>
    apiBaseUrl
      ? { status: "idle" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
        },
  );
  const [demoModeEnabled, setDemoModeEnabled] = useState(false);
  const activeStudentId = demoModeEnabled ? mockStudentId : undefined;
  const sectionMonitoringState = useSectionMonitoringWorkflow(
    apiBaseUrl,
    activeStudentId,
  );
  const [courseStateState, setCourseStateState] = useCourseStateWorkflow(
    apiBaseUrl,
    activeStudentId,
  );

  useEffect(() => {
    if (!apiBaseUrl) {
      return;
    }

    startTransition(() => {
      setEligibilityState((current) =>
        current.status === "offline" ? { status: "idle" } : current,
      );
      setPlannerState((current) =>
        current.status === "offline" ? { status: "idle" } : current,
      );
      setScheduleState((current) =>
        current.status === "offline" ? { status: "idle" } : current,
      );
      setDataImportState((current) =>
        current.status === "offline" ? { status: "idle" } : current,
      );
      setDataReviewState((current) =>
        current.status === "offline" ? { status: "idle" } : current,
      );
    });
  }, [apiBaseUrl]);

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

        if (!activeStudentId) {
          setAuditState({
            status: "empty",
            message: "尚未导入学生数据；请先导入并审核数据，或显式启用演示工作流。",
          });
          return;
        }
        const studentId = activeStudentId;

        let audit: DegreeAuditRun;
        try {
          audit = await fetchLatestDegreeAudit(baseUrl, studentId, {
            timeoutMs: 5_000,
          });
        } catch (error: unknown) {
          if (!isNotFound(error)) {
            throw error;
          }
          audit = await createDegreeAudit(
            baseUrl,
            {
              student_profile_id: studentId,
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
                  message: "还没有可用的学业审核快照。",
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
  }, [apiBaseUrl, activeStudentId]);

  useEffect(() => {
    let cancelled = false;

    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }

    if (!activeStudentId) {
      setDataImportState({
        status: "empty",
        message: "尚未导入学生数据；没有可加载的学生导入记录。",
      });
      return () => {
        cancelled = true;
      };
    }
    const studentId = activeStudentId;

    async function loadLatestImportPreview(baseUrl: string): Promise<void> {
      try {
        const savedImports = await fetchStudentDataImports(
          baseUrl,
          studentId,
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
  }, [apiBaseUrl, activeStudentId]);

  const myProgressPreview = myProgressPreviewFromState(dataImportState);
  const warnings =
    auditState.status === "ready" && !myProgressPreview
      ? auditState.requirements.flatMap((requirement) => requirement.warnings)
      : [];
  const currentImportMode = dashboardSourceLabel(
    myProgressPreview,
    dataReviewState,
    auditState,
    dataImportState,
  );
  const longTermReadiness =
    courseStateState.status === "ready"
      ? courseStateState.detail.snapshot.readiness.long_term_planner
      : null;
  const eligibilityReadiness =
    courseStateState.status === "ready"
      ? courseStateState.detail.snapshot.readiness.course_eligibility
      : null;
  const scheduleReadiness =
    courseStateState.status === "ready"
      ? courseStateState.detail.snapshot.readiness.semester_schedule
      : null;
  const downstreamAnalysisAllowed =
    activeStudentId && courseStateState.status === "ready"
      ? readinessAllows(longTermReadiness?.status)
      : Boolean(activeStudentId) && demoModeEnabled && !myProgressPreview;
  const eligibilityAnalysisAllowed =
    activeStudentId && courseStateState.status === "ready"
      ? readinessAllows(eligibilityReadiness?.status)
      : Boolean(activeStudentId) && demoModeEnabled && !myProgressPreview;
  const scheduleAnalysisAllowed =
    activeStudentId && courseStateState.status === "ready"
      ? readinessAllows(scheduleReadiness?.status)
      : Boolean(activeStudentId) && demoModeEnabled && !myProgressPreview;

  return (
    <WorkflowShell
      activeWorkflow={activeWorkflow}
      apiStatus={
        health.status === "loading"
          ? "API 检查中"
          : health.status === "online"
            ? "API 已连接"
            : "API 不可用"
      }
      sourceLabel={currentImportMode}
    >
      <main>
        <DiagnosticsWorkflow
          apiBaseUrl={apiBaseUrl}
          active={activeWorkflow === "diagnostics"}
        />
        <section id="overview" className="progress-shell">
        <div className="topbar">
          <p className={`badge ${health.status === "online" ? "ok" : "warn"}`}>
            {health.status === "loading"
              ? "API 检查中"
              : health.status === "online"
                ? "API 已连接"
                : "API 不可用"}
          </p>
          <p className="notice compact">{currentImportMode}</p>
          <button
            type="button"
            aria-pressed={demoModeEnabled}
            onClick={() => setDemoModeEnabled((enabled) => !enabled)}
            disabled={
              courseStateState.status === "ready" || Boolean(myProgressPreview)
            }
          >
            {demoModeEnabled ? "关闭演示工作流" : "启用演示工作流"}
          </button>
        </div>

        {demoModeEnabled ? (
          <p className="notice compact" role="status">
            演示工作流已显式启用；所有结果仅使用模拟数据，不代表真实学业状态。
          </p>
        ) : null}

        <DevelopmentDiagnostics
          apiBaseUrl={apiBaseUrl}
          webOrigin={webOrigin}
          health={health}
          dataImportState={dataImportState}
          sourceLabel={currentImportMode}
          downstreamAnalysisAllowed={downstreamAnalysisAllowed}
        />

        <LocalPairingPanel apiBaseUrl={apiBaseUrl} />

        <BackupPanel apiBaseUrl={apiBaseUrl} />

        <h1>学业进度</h1>
        <p className="subtle">
          高风险学业建议需要 advisor / registrar / 学校确认。
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
            courseStateState={courseStateState}
          />
        ) : (
          <AuditFallback state={auditState} health={health} />
        )}

        <CourseStateSnapshotPanel state={courseStateState} />

        {warnings.length > 0 ? (
          <section className="warning-panel" aria-label="顾问警告">
            <h2>警告</h2>
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
          courseStateState={courseStateState}
          canUseRealEligibility={eligibilityAnalysisAllowed}
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
          canUseDownstreamAnalysis={scheduleAnalysisAllowed}
          sourceLabel={currentImportMode}
        />

        <DataImportPreviewPanel
          selectedDataImportSampleId={selectedDataImportSampleId}
          setSelectedDataImportSampleId={setSelectedDataImportSampleId}
          dataImportState={dataImportState}
          setDataImportState={setDataImportState}
          dataReviewState={dataReviewState}
          setDataReviewState={setDataReviewState}
          courseStateState={courseStateState}
          setCourseStateState={setCourseStateState}
        />

        <SectionMonitoringPanel state={sectionMonitoringState} />
        </section>
      </main>
    </WorkflowShell>
  );
}

function BackupPanel({ apiBaseUrl }: { apiBaseUrl: string | undefined }) {
  const [status, setStatus] = useState<
    | { state: "loading" }
    | { state: "ready"; payload: BackupStatus }
    | { state: "failed"; message: string }
  >(
    apiBaseUrl
      ? { state: "loading" }
      : { state: "failed", message: "API 基础地址未配置。" },
  );
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [restorePreview, setRestorePreview] = useState<RestorePreview | null>(null);
  const [restoreBusy, setRestoreBusy] = useState(false);
  const [restoreConfirmation, setRestoreConfirmation] = useState("");
  const [backupReceipt, setBackupReceipt] = useState<string | null>(null);
  const [removalConfirmation, setRemovalConfirmation] = useState("");
  const [removalBusy, setRemovalBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!apiBaseUrl) {
      return () => {
        cancelled = true;
      };
    }
    void fetchLocalBackupStatus(apiBaseUrl, { timeoutMs: 5_000 })
      .then((payload) => {
        if (!cancelled) setStatus({ state: "ready", payload });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setStatus({
            state: "failed",
            message: error instanceof Error ? error.message : "备份状态不可用。",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  async function createBackup(): Promise<void> {
    if (
      !apiBaseUrl ||
      creating ||
      status.state !== "ready" ||
      !status.payload.available
    ) {
      return;
    }
    setCreating(true);
    setResult(null);
    try {
      const downloaded = await downloadLocalBackup(apiBaseUrl, {
        timeoutMs: 60_000,
      });
      setBackupReceipt(downloaded.backupReceipt);
      const url = URL.createObjectURL(downloaded.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = downloaded.filename ?? "SAPSOS-backup.sapsos-backup";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
      setResult(`已创建并下载 ${link.download}。`);
    } catch (error: unknown) {
      setResult(
        error instanceof Error ? error.message : "创建备份失败。请稍后重试。",
      );
    } finally {
      setCreating(false);
    }
  }

  async function validateRestore(): Promise<void> {
    if (!apiBaseUrl || !selectedFile || restoreBusy) return;
    setRestoreBusy(true);
    setResult(null);
    try {
      setRestorePreview(await validateLocalRestore(apiBaseUrl, selectedFile, { timeoutMs: 60_000 }));
    } catch (error: unknown) {
      setResult(error instanceof Error ? error.message : "恢复文件验证失败。");
    } finally {
      setRestoreBusy(false);
    }
  }

  async function stageRestore(): Promise<void> {
    if (!apiBaseUrl || !restorePreview || restoreBusy) return;
    setRestoreBusy(true);
    try {
      const staged = await confirmLocalRestore(apiBaseUrl, restorePreview.session_id, restoreConfirmation);
      setResult(staged.message);
    } catch (error: unknown) {
      setResult(error instanceof Error ? error.message : "恢复暂存失败。");
    } finally {
      setRestoreBusy(false);
    }
  }

  async function cancelRestore(): Promise<void> {
    if (!apiBaseUrl || !restorePreview || restoreBusy) return;
    setRestoreBusy(true);
    try {
      await cancelLocalRestore(apiBaseUrl, restorePreview.session_id);
      setRestorePreview(null);
      setSelectedFile(null);
      setRestoreConfirmation("");
      setResult("已取消未确认的恢复。" );
    } catch (error: unknown) {
      setResult(error instanceof Error ? error.message : "取消恢复失败。");
    } finally {
      setRestoreBusy(false);
    }
  }

  async function prepareRemovalPlan(): Promise<void> {
    if (!apiBaseUrl || !backupReceipt || removalBusy) return;
    setRemovalBusy(true);
    setResult(null);
    try {
      const prepared = await prepareLocalDataRemoval(
        apiBaseUrl,
        removalConfirmation,
        backupReceipt,
        { timeoutMs: 10_000 },
      );
      setResult(`${prepared.message} 关闭应用后才会执行。`);
    } catch (error: unknown) {
      setResult(error instanceof Error ? error.message : "无法准备本地数据删除。");
    } finally {
      setRemovalBusy(false);
    }
  }

  async function cancelRemovalPlan(): Promise<void> {
    if (!apiBaseUrl || removalBusy) return;
    setRemovalBusy(true);
    try {
      await cancelLocalDataRemoval(apiBaseUrl, { timeoutMs: 10_000 });
      setRemovalConfirmation("");
      setResult("已取消本地数据删除计划。");
    } catch (error: unknown) {
      setResult(error instanceof Error ? error.message : "无法取消本地数据删除计划。" );
    } finally {
      setRemovalBusy(false);
    }
  }

  return (
    <section
      id="backup-restore"
      className="diagnostics-panel"
      aria-label="备份与恢复"
    >
      <h2>备份与恢复</h2>
      <p>备份仅在 LOCAL_DESKTOP 中手动创建，包含完整本地 SQLite 学业数据。</p>
      <ul className="disclaimer-list">
        <li>备份文件包含个人学业数据；备份文件未加密，请存放在可信位置。</li>
        <li>
          不会包含浏览器扩展配对凭据、runtime.json、日志、缓存或其他运行时文件。
        </li>
        <li>
          备份不会上传，也不会修改学校门户。恢复功能将在依赖门控的后续 PR 中提供。
        </li>
      </ul>
      {status.state === "loading" ? (
        <p role="status">正在检查本地备份状态…</p>
      ) : null}
      {status.state === "failed" ? (
        <p role="alert">备份不可用：{status.message}</p>
      ) : null}
      {status.state === "ready" ? (
        <>
          <p role="status">
            {status.payload.message} · Schema {status.payload.schema_version}
          </p>
          <button
            type="button"
            onClick={() => void createBackup()}
            disabled={creating || !status.payload.available}
          >
            {creating ? "正在创建备份…" : "创建备份"}
          </button>
        </>
      ) : null}
      {result ? <p role="status">{result}</p> : null}
      <hr />
      <h3>完整删除本地应用数据</h3>
      <p>
        默认卸载只删除应用文件并保留本地数据；下面是独立的不可撤销操作。
        它不会删除外部备份、诊断 ZIP 或 Documents、Downloads、Desktop 文件。
      </p>
      <ul className="disclaimer-list">
        <li>必须先创建并验证一个保存在应用数据目录之外的备份。</li>
        <li>将删除数据库、配对状态、偏好设置、恢复/迁移状态和应用缓存。</li>
        <li>不会删除学校门户数据、浏览器 profile 或任意外部路径。</li>
      </ul>
      <label htmlFor="local-data-removal-confirmation">输入 DELETE SAPSOS LOCAL DATA</label>
      <input
        id="local-data-removal-confirmation"
        value={removalConfirmation}
        onChange={(event) => setRemovalConfirmation(event.target.value)}
        autoComplete="off"
        spellCheck={false}
      />
      <div className="diagnostics-actions">
        <button
          type="button"
          onClick={() => void prepareRemovalPlan()}
          disabled={removalBusy || !backupReceipt || removalConfirmation !== "DELETE SAPSOS LOCAL DATA"}
        >
          {removalBusy ? "正在准备…" : "准备完整删除"}
        </button>
        <button type="button" onClick={() => void cancelRemovalPlan()} disabled={removalBusy}>
          取消删除计划
        </button>
      </div>
      <hr />
      <h3>恢复（需要重启）</h3>
      <p>选择文件不会上传；点击“验证恢复文件”后才会进行严格验证。</p>
      <input
        type="file"
        accept=".sapsos-backup,application/vnd.sapsos.backup+zip"
        onChange={(event) => {
          setSelectedFile(event.target.files?.[0] ?? null);
          setRestorePreview(null);
          setRestoreConfirmation("");
        }}
      />
      <button type="button" onClick={() => void validateRestore()} disabled={!selectedFile || restoreBusy}>
        {restoreBusy ? "正在处理…" : "验证恢复文件"}
      </button>
      {restorePreview ? (
        <section aria-label="恢复预览" className="state-panel">
          <h4>恢复预览</h4>
          <p>{restorePreview.full_replacement_warning}</p>
          <p>{restorePreview.pairing_notice}</p>
          <p>{restorePreview.restart_notice}</p>
          {restorePreview.warnings.map((warning) => <p key={warning}>{warning}</p>)}
          <label>
            输入 RESTORE 以确认
            <input value={restoreConfirmation} onChange={(event) => setRestoreConfirmation(event.target.value)} />
          </label>
          <button type="button" onClick={() => void stageRestore()} disabled={restoreBusy || restoreConfirmation !== "RESTORE"}>暂存恢复并要求重启</button>
          <button type="button" onClick={() => void cancelRestore()} disabled={restoreBusy}>取消</button>
        </section>
      ) : null}
    </section>
  );
}

function CourseStateSnapshotPanel({ state }: { state: CourseStateState }) {
  if (state.status === "loading") {
    return (
      <section
        className="state-panel"
        aria-label="已应用课程状态"
        aria-live="polite"
      >
        <h2>正在加载已应用课程状态</h2>
        <p>正在读取最新有效的内部非官方课程状态快照。</p>
      </section>
    );
  }
  if (state.status !== "ready") {
    return (
      <section className="state-panel" aria-label="已应用课程状态">
        <h2>已应用课程状态</h2>
        <p>{state.message}</p>
        <p className="subtle">未应用真实快照时不会静默使用演示课程历史。</p>
      </section>
    );
  }
  const { snapshot, course_states: courseStates } = state.detail;
  const readinessEntries = Object.entries(snapshot.readiness);
  return (
    <section className="course-state-panel" aria-label="已应用课程状态">
      <div className="section-heading">
        <div>
          <h2>内部课程状态快照</h2>
          <p className="subtle">
            来源 import：{snapshot.data_import_run_id} · 应用时间：
            {formatAcademicTimestamp(snapshot.applied_at)}
          </p>
        </div>
        <p className="notice compact">非官方导入 · 仅供内部规划与建议。</p>
      </div>
      <section className="summary-grid" aria-label="课程状态统计">
        <SummaryMetric
          label="已完成"
          value={String(snapshot.completed_count)}
        />
        <SummaryMetric
          label="进行中"
          value={String(snapshot.in_progress_count)}
        />
        <SummaryMetric label="已规划" value={String(snapshot.planned_count)} />
        <SummaryMetric
          label="未开始要求/选项"
          value={String(snapshot.not_started_count)}
        />
        <SummaryMetric
          label="已匹配 Catalog"
          value={String(snapshot.matched_count)}
        />
        <SummaryMetric
          label="未匹配课程"
          value={String(snapshot.unmatched_count)}
        />
        <SummaryMetric
          label="异常记录"
          value={String(snapshot.exception_count)}
        />
        <SummaryMetric
          label="来源范围"
          value={
            snapshot.extraction_bounded || snapshot.extraction_truncated
              ? "有边界 / 被截断"
              : "未检测到截断"
          }
        />
      </section>
      <section className="comparison-table" aria-label="下游就绪状态">
        <h2>分项 readiness</h2>
        <div className="comparison-rows">
          {readinessEntries.map(([key, item]) => (
            <div key={key} className="comparison-row">
              <strong>{courseStateReadinessLabels[key] ?? key}</strong>
              <span>{readinessStatusLabel(item.status)}</span>
              <span>
                {item.blocking_reasons.length > 0
                  ? `阻塞：${item.blocking_reasons
                      .map(readinessReasonLabel)
                      .join("；")}`
                  : "没有阻塞原因"}
              </span>
              {item.warnings.length > 0 ? (
                <span>
                  警告：{item.warnings.map(readinessReasonLabel).join("；")}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      </section>
      <section className="comparison-table" aria-label="已应用课程状态记录">
        <h2>课程状态记录</h2>
        <div className="comparison-rows">
          {courseStates.slice(0, 12).map((courseState) => (
            <div key={courseState.id} className="comparison-row">
              <strong>
                {courseState.normalized_course_code || "缺少课程代码"} ·{" "}
                {courseState.source_course_title || "未提供标题"}
              </strong>
              <span>
                {statusLabel(courseState.status)} ·{" "}
                {statusLabel(courseState.validation_state)} ·{" "}
                {courseState.term ?? "学期未知"}
              </span>
              <span>
                {courseState.matched_course_id
                  ? "已匹配 Catalog"
                  : "外部未匹配证据"}{" "}
                · {courseState.application_reason_code}
              </span>
              {courseState.reason_codes.length > 0 ? (
                <span>
                  原因：
                  {courseState.reason_codes
                    .map(readinessReasonLabel)
                    .join("；")}
                </span>
              ) : null}
            </div>
          ))}
        </div>
        {courseStates.length > 12 ? (
          <p className="subtle">
            其余 {courseStates.length - 12} 条状态已保留在快照中。
          </p>
        ) : null}
      </section>
      <AdvisoryLabels keys={["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"]} />
    </section>
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
      ? `${sourceLabel} · ${statusLabel(dataImportState.run.source.source_type)}`
      : `${sourceLabel}；导入加载状态 ${statusLabel(dataImportState.status)}`;

  return (
    <section className="diagnostics-panel" aria-label="本地诊断">
      <h2>本地诊断</h2>
      <dl>
        <div>
          <dt>API 基础地址</dt>
          <dd>{apiBaseUrl ?? "未配置"}</dd>
        </div>
        <div>
          <dt>网页来源</dt>
          <dd>{webOrigin}</dd>
        </div>
        <div>
          <dt>API 连接状态</dt>
          <dd>{statusLabel(health.status)}</dd>
        </div>
        <div>
          <dt>导入来源状态</dt>
          <dd>{importStatus}</dd>
        </div>
        <div>
          <dt>长期规划就绪状态</dt>
          <dd>{downstreamAnalysisAllowed ? "可谨慎继续" : "已阻止"}</dd>
        </div>
      </dl>
      {shouldShowGuidance ? (
        <p className="advisor-note">{localApiRestartGuidance()}</p>
      ) : null}
    </section>
  );
}

function LocalPairingPanel({ apiBaseUrl }: { apiBaseUrl: string | undefined }) {
  const { state, createCode, revoke } = usePairingWorkflow(apiBaseUrl);

  return (
    <section className="diagnostics-panel" aria-label="本地浏览器扩展配对">
      <h2>本地扩展配对</h2>
      <p>配对凭据仅用于本地应用与浏览器扩展通信，不是学校登录凭据，也不会发送到学校门户。</p>
      <p>
        状态：{state.status === "paired" ? "已配对" : state.status === "code" ? "等待扩展确认" : state.status === "unpaired" ? "未配对" : state.status === "loading" ? "检查中" : state.message}
      </p>
      {state.status === "code" ? <p>配对码：<strong>{state.code}</strong>（截至 {new Date(state.expiresAt).toLocaleTimeString()}）</p> : null}
      <button type="button" onClick={() => void createCode()} disabled={!apiBaseUrl}>生成 / 重新生成配对码</button>
      <button type="button" onClick={() => void revoke()} disabled={state.status !== "paired"}>撤销扩展凭据</button>
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
      ? "正在加载学业审核"
      : state.status === "empty"
        ? "还没有学业审核快照"
        : "学业审核不可用";
  const message =
    state.status === "loading"
      ? "正在检查最新的模拟学业审核快照。"
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
  courseStateState,
}: {
  audit: DegreeAuditRun;
  requirements: RequirementEvaluation[];
  myProgressPreview: MyProgressPreviewDisplay | null;
  courseStateState: CourseStateState;
}) {
  const snapshot =
    courseStateState.status === "ready"
      ? courseStateState.detail.snapshot
      : null;
  const program =
    snapshot?.program_summary ?? myProgressPreview?.programSummary;
  const credits = snapshot?.credit_summary ?? myProgressPreview?.creditSummary;
  const hasAppliedCourseState = snapshot !== null;
  const hasRealMyProgress = hasAppliedCourseState || myProgressPreview !== null;
  const myProgressRequirementGroups = snapshot
    ? snapshot.requirement_summary
    : (myProgressPreview?.requirementGroups ?? []);
  const programName = stringFromUnknown(program?.programName);
  const catalogYear = numberFromUnknown(program?.catalogYear);
  const degree = stringFromUnknown(program?.degree);
  const department = stringFromUnknown(program?.department);
  const cumulativeGpa = numberFromUnknown(program?.cumulativeGpa);
  const institutionGpa = numberFromUnknown(program?.institutionGpa);
  const totalAppliedCredits = numberFromUnknown(credits?.totalAppliedCredits);
  const totalRequiredCredits = numberFromUnknown(credits?.totalRequiredCredits);
  const completedCredits = numberFromUnknown(credits?.completedCredits) ?? 0;
  const inProgressCredits = numberFromUnknown(credits?.inProgressCredits) ?? 0;
  const plannedCredits = numberFromUnknown(credits?.plannedCredits) ?? 0;
  const remainingCredits = numberFromUnknown(credits?.remainingCredits) ?? 0;
  const completionPercent = numberFromUnknown(credits?.completionPercent) ?? 0;
  const anticipatedCompletionDate = stringFromUnknown(
    program?.anticipatedCompletionDate,
  );
  const auditReadiness = snapshot?.readiness.degree_audit;
  return (
    <>
      <section
        className="summary-grid"
        id="degree-audit"
        aria-label="学业审核汇总"
      >
        <SummaryMetric
          label="数据模式"
          value={
            hasAppliedCourseState
              ? "已应用非官方课程状态快照"
              : importModeLabel(myProgressPreview)
          }
        />
        <SummaryMetric
          label="项目"
          value={programName ?? "尚未加载真实 MyProgress 导入"}
        />
        <SummaryMetric
          label="审核模式"
          value={statusLabel(audit.calculation_mode)}
        />
        {hasRealMyProgress ? (
          <>
            <SummaryMetric
              label="Catalog 年份"
              value={catalogYear ? String(catalogYear) : "未加载"}
            />
            {degree ? <SummaryMetric label="学位" value={degree} /> : null}
            {department ? (
              <SummaryMetric label="院系" value={department} />
            ) : null}
            {cumulativeGpa !== undefined ? (
              <SummaryMetric label="GPA" value={cumulativeGpa.toFixed(3)} />
            ) : null}
            {institutionGpa !== undefined ? (
              <SummaryMetric
                label="本校 GPA"
                value={institutionGpa.toFixed(3)}
              />
            ) : null}
            {totalAppliedCredits !== undefined &&
            totalRequiredCredits !== undefined ? (
              <SummaryMetric
                label="总学分"
                value={`${formatCredits(String(totalAppliedCredits))} / ${formatCredits(
                  String(totalRequiredCredits),
                )}`}
              />
            ) : null}
            <SummaryMetric
              label="已完成"
              value={formatCredits(String(completedCredits))}
            />
            <SummaryMetric
              label="进行中"
              value={formatCredits(String(inProgressCredits))}
            />
            <SummaryMetric
              label="已规划"
              value={formatCredits(String(plannedCredits))}
            />
            <SummaryMetric
              label="剩余"
              value={formatCredits(String(remainingCredits))}
            />
            <SummaryMetric
              label="完成度"
              value={`${completionPercent.toFixed(2)}%`}
            />
            {anticipatedCompletionDate ? (
              <SummaryMetric
                label="预计完成"
                value={anticipatedCompletionDate}
              />
            ) : null}
          </>
        ) : (
          <>
            <SummaryMetric label="当前 MyProgress 导入" value="未加载" />
            <SummaryMetric label="模拟值" value="仅示例数据" />
          </>
        )}
      </section>

      {!hasRealMyProgress ? (
        <section
          className="state-panel"
          aria-label="尚未加载真实 MyProgress 导入"
        >
          <h2>尚未加载真实 MyProgress 导入</h2>
          <p>
            演示 / 模拟数据仅用于本地示例，不代表当前真实学业状态，
            不应用于真实学业决策。
          </p>
          <ul className="compact-list">
            <li>从已打开并已登录的 Kean MyProgress 页面触发浏览器插件导入。</li>
            <li>从本地数据库加载已保存的 staging 导入。</li>
            <li>加载脱敏 MyProgress 示例仅用于本地测试，不是官方学校数据。</li>
          </ul>
        </section>
      ) : null}

      <section className="requirement-tree" aria-label="毕业要求摘要">
        <h2>
          {hasAppliedCourseState
            ? "已应用 MyProgress 要求摘要"
            : hasRealMyProgress
              ? "MyProgress staging 要求摘要"
              : "演示毕业要求树"}
        </h2>
        {hasRealMyProgress ? (
          <>
            <p className="subtle">
              {hasAppliedCourseState
                ? `以下内容来自 active snapshot ${snapshot.id}；旧的模拟要求不会作为真实学业状态使用。`
                : "以下内容仍是 staging 预览，只有审核并应用后才会成为内部课程状态。"}
            </p>
            {auditReadiness ? (
              <ul className="compact-list">
                <li>
                  <strong>Degree audit readiness</strong>
                  <span>{readinessStatusLabel(auditReadiness.status)}</span>
                </li>
                {auditReadiness.blocking_reasons.map((reason) => (
                  <li key={reason}>{readinessReasonLabel(reason)}</li>
                ))}
              </ul>
            ) : null}
            <ul className="compact-list">
              <li>
                <strong>课程行数据</strong>
                <span>
                  {hasAppliedCourseState
                    ? readinessStatusLabel(
                        snapshot.readiness.course_history.status,
                      )
                    : readinessStatusLabel(
                        myProgressPreview?.readiness.course_rows.status ??
                          "MISSING",
                      )}
                </span>
              </li>
              <li>
                <strong>审核范围</strong>
                <span>
                  解析器会报告高置信度字段；每条导入记录仍必须经过人工 Review，异常队列和截断/边界警告需要重点核对。
                </span>
              </li>
            </ul>
            {myProgressRequirementGroups.length > 0 ? (
              myProgressRequirementGroups.map((group, index) => {
                const groupRecord =
                  typeof group === "object" && group !== null
                    ? (group as Record<string, unknown>)
                    : {};
                const name =
                  stringFromUnknown(groupRecord.name) ??
                  stringFromUnknown(groupRecord.requirements) ??
                  `MyProgress requirement group ${index + 1}`;
                const statusText =
                  stringFromUnknown(groupRecord.statusText) ??
                  stringFromUnknown(groupRecord.status_text) ??
                  "高置信度要求组。";
                const confidence =
                  stringFromUnknown(groupRecord.confidence) ?? "high";
                return (
                  <article key={`${name}-${index}`} className="requirement-row">
                    <div className="requirement-detail">
                      <h3>{name}</h3>
                      <p>{statusText}</p>
                      <p className="advisor-note">
                        待人工 Review · 解析器置信度 {statusLabel(confidence)}
                      </p>
                    </div>
                  </article>
                );
              })
            ) : (
              <section className="state-panel">
                <h3>没有 MyProgress 要求组</h3>
                <p>
                  汇总仍会保留项目、GPA 与学分字段；缺失的要求组会进入异常审核。
                </p>
              </section>
            )}
          </>
        ) : (
          <>
            <p className="subtle">
              在加载或确认真实 MyProgress 导入前，这些要求行仅作为开发示例显示。
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
                      <dt>要求</dt>
                      <dd>
                        {requirement.required_courses ?? "—"} courses /{" "}
                        {requirement.required_credits
                          ? formatCredits(requirement.required_credits)
                          : "—"}{" "}
                        学分
                      </dd>
                    </div>
                    <div>
                      <dt>已满足</dt>
                      <dd>
                        {requirement.satisfied_courses} courses /{" "}
                        {formatCredits(requirement.satisfied_credits)} 学分
                      </dd>
                    </div>
                    <div>
                      <dt>剩余</dt>
                      <dd>
                        {requirement.remaining_courses} courses /{" "}
                        {formatCredits(requirement.remaining_credits)} 学分
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
                            {formatCredits(application.credit_amount)} 学分
                            {application.grade
                              ? ` · 成绩 ${application.grade}`
                              : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {requirement.warnings.some(
                    (warning) => warning.requires_advisor_confirmation,
                  ) ? (
                    <p className="advisor-note">需要 advisor 确认。</p>
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
      ariaLabel: "学业审核状态卡片",
      title: "学业审核",
      explanation: "最新的确定性审核快照与毕业要求树。",
      status:
        auditState.status === "ready"
          ? auditState.audit.status
          : auditState.status,
      nextAction:
        auditState.status === "ready"
          ? "查看要求警告，并与 advisor 确认高风险学业建议。"
          : "加载或生成学业审核快照。",
      href: "#degree-audit",
      actionLabel: "查看学业审核",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
    {
      ariaLabel: "数据导入审核状态卡片",
      title: "数据导入审核",
      explanation: "staging 导入记录的异常审核入口。",
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
          ? "尚无已确认导入"
          : undefined,
      nextAction: myProgressPreview?.canApplyVerifiedImport
        ? "高置信度 MyProgress 导入已自动验证；高风险建议仍需学校或 advisor 确认。"
        : dataReviewState.status === "ready"
          ? "应用已确认内部记录前先查看警告。"
          : "先预览或加载 staging 导入，再审核异常队列。",
      href: "#data-import-preview",
      actionLabel: "打开审核",
      advisoryLabels: myProgressPreview?.canApplyVerifiedImport
        ? ["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"]
        : ["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"],
    },
    {
      ariaLabel: "浏览器插件导入状态卡片",
      title: "浏览器插件导入",
      explanation: "只读取用户已打开页面的导入来源，必须先进入 staging。",
      status:
        dataImportState.status === "ready" && myProgressPreview
          ? myProgressPreview.realImportStatus
          : "MANUAL_REVIEW_REQUIRED",
      statusLabel:
        dataImportState.status === "ready" && myProgressPreview
          ? dataImportMode
          : "非官方导入数据",
      nextAction:
        dataImportState.status === "ready" && myProgressPreview
          ? "MyProgress 汇总已进入 staging；请查看验证摘要和异常队列。"
          : "仅检查用户已打开页面，然后把导入数据放入 staging 异常审核。",
      href: "#data-import-preview",
      actionLabel: "查看导入",
      advisoryLabels: myProgressPreview?.canApplyVerifiedImport
        ? ["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"]
        : [
            "NON_OFFICIAL_IMPORTED_DATA",
            "MANUAL_REVIEW_REQUIRED",
            "ADVISORY_ONLY",
          ],
    },
    {
      ariaLabel: "课节监控状态卡片",
      title: "课节监控",
      explanation: "用户触发的课节快照对比，仅供参考。",
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
            ? "参考性提醒已就绪"
            : sectionMonitoringState.targets.length > 0
              ? "监控目标已就绪"
              : "没有课节监控目标"
          : undefined,
      nextAction:
        sectionMonitoringState.status === "ready" &&
        sectionMonitoringState.alerts.length > 0
          ? "任何课节变化都必须在官方门户人工核对。"
          : "导入 section-search 数据，并手动选择要监控的课节。",
      href: "#section-monitoring",
      actionLabel: "查看提醒",
      advisoryLabels: [
        "NON_OFFICIAL_IMPORTED_DATA",
        "ADVISORY_ONLY",
        "VERIFY_IN_OFFICIAL_PORTAL",
      ],
    },
    {
      ariaLabel: "课表优化状态卡片",
      title: "课表优化",
      explanation: "课节级课表选项，与长期学业规划分离。",
      status:
        scheduleState.status === "ready"
          ? scheduleState.schedule.status
          : scheduleState.status === "idle"
            ? null
            : scheduleState.status,
      statusLabel:
        scheduleState.status === "idle" || scheduleState.status === "empty"
          ? "等待真实课节数据 / 演示模式"
          : undefined,
      nextAction:
        scheduleState.status === "ready"
          ? "比较仅供参考的课表选项和警告。"
          : "只有导入真实课节数据后才能用于真实课表判断；当前为演示模式。",
      href: "#schedule-optimization",
      actionLabel: "生成课表",
      advisoryLabels: ["NON_OFFICIAL_IMPORTED_DATA", "ADVISORY_ONLY"],
    },
    {
      ariaLabel: "假设规划状态卡片",
      title: "假设规划",
      explanation: "用于比较假设项目变更的场景。",
      status:
        scenarioState.status === "ready"
          ? scenarioState.detail.scenario.status
          : scenarioState.status === "idle"
            ? null
            : scenarioState.status,
      statusLabel:
        scenarioState.status === "idle" || scenarioState.status === "empty"
          ? "没有假设方案"
          : undefined,
      nextAction:
        scenarioState.status === "ready"
          ? "比较已保存方案的假设和 advisor 警告。"
          : "从候选项目创建假设方案。",
      href: "#what-if-planning",
      actionLabel: "创建假设方案",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
  ];

  return (
    <section className="product-status" aria-label="产品状态概览">
      {cards.map((card) => (
        <StatusCard key={card.ariaLabel} card={card} />
      ))}
    </section>
  );
}

function StatusCard({ card }: { card: ProductStatusCard }) {
  const badge = localizeStatusBadge(card.status);
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
        <strong>下一步：</strong> {card.nextAction}
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
  tone: ReturnType<typeof localizeStatusBadge>["tone"];
}) {
  return <span className={`ui-status-badge tone-${tone}`}>{label}</span>;
}

function AdvisoryLabels({ keys }: { keys: AdvisoryLabelKey[] }) {
  return (
    <ul className="advisory-labels">
      {getZhCnAdvisoryLabels(keys).map((label) => (
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
  const copy = getZhCnEmptyStateCopy(copyKey);
  return (
    <section className="state-panel empty-state" aria-label={ariaLabel}>
      <h2>{copy.title}</h2>
      <p>{copy.explanation}</p>
      <p>
        <strong>原因：</strong> {copy.reason}
      </p>
      <p>
        <strong>下一步：</strong> {copy.nextAction}
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
          "运行假设分析前，请先加载已自动验证或已确认的 MyProgress 导入。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScenarioState({
        status: "failed",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
        message: "比较方案前，请先加载已自动验证或已确认的 MyProgress 导入。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScenarioState({
        status: "failed",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "至少需要两个已保存方案。",
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
              message: "比较已保存结果前，请先创建方案。",
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
      aria-label="假设规划"
    >
      <div className="section-heading">
        <div>
          <h2>假设规划</h2>
          <p className="subtle">额外学分估算不会预测毕业时间。</p>
        </div>
        <p className="notice compact">可能需要 advisor 确认。</p>
      </div>

      <div className="scenario-controls">
        <label>
          候选项目
          <select
            value={selectedCandidateId}
            onChange={(event) => setSelectedCandidateId(event.target.value)}
          >
            {candidatePrograms.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {localizeDemoOptionLabel(
                  "candidateProgram",
                  candidate.id,
                  candidate.label,
                )}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCreateScenario()}
        >
          创建假设方案
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCompareSaved()}
        >
          比较已保存方案
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="假设规划来源门禁">
          <h2>假设规划已阻止</h2>
          <p>
            当前来源是 {sourceLabel}。需要完整可靠的真实 MyProgress 课程行后，
            才能用于真实学业决策；当前不应用于真实学业决策。
          </p>
        </section>
      ) : null}

      {scenarioState.status === "idle" ? (
        <EmptyState copyKey="NO_WHAT_IF_SCENARIOS" ariaLabel="假设方案空状态" />
      ) : null}

      {scenarioState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在创建方案</h2>
          <p>正在运行模拟假设审核和分配。</p>
        </section>
      ) : null}

      {scenarioState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>假设方案不可用</h2>
          <p>{scenarioState.message}</p>
        </section>
      ) : null}

      {scenarioState.status === "empty" ? (
        <EmptyState copyKey="NO_WHAT_IF_SCENARIOS" ariaLabel="假设方案空状态" />
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
  courseStateState,
  canUseRealEligibility,
}: {
  selectedCourseId: string;
  setSelectedCourseId: (value: string) => void;
  eligibilityState: EligibilityState;
  setEligibilityState: Dispatch<SetStateAction<EligibilityState>>;
  courseStateState: CourseStateState;
  canUseRealEligibility: boolean;
}) {
  const selectedCourse =
    candidateCourses.find((candidate) => candidate.id === selectedCourseId) ??
    candidateCourses[0];

  async function handleRunEligibility(): Promise<void> {
    if (courseStateState.status === "ready" && !canUseRealEligibility) {
      const readiness =
        courseStateState.detail.snapshot.readiness.course_eligibility;
      setEligibilityState({
        status: "empty",
        message: `真实课程资格已阻止：${readiness.blocking_reasons
          .map(readinessReasonLabel)
          .join("；")}`,
      });
      return;
    }
    if (!apiBaseUrl) {
      setEligibilityState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "还没有创建课程资格检查。",
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
      id="eligibility"
      className="eligibility-panel"
      aria-label="课程资格检查"
    >
      <div className="section-heading">
        <div>
          <h2>课程资格</h2>
          <p className="subtle">
            {courseStateState.status === "ready"
              ? `真实导入模式：使用 active snapshot ${courseStateState.detail.snapshot.id} 的已完成/进行中证据。`
              : "演示模式：仅在用户明确使用演示数据时运行，不应用于真实学业决策。"}
          </p>
        </div>
        <p className="notice compact">课节座位状态必须在官方门户人工核对。</p>
      </div>

      <div className="scenario-controls">
        <label>
          课程检查
          <select
            value={selectedCourseId}
            onChange={(event) => setSelectedCourseId(event.target.value)}
          >
            {candidateCourses.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {courseStateState.status === "ready"
                  ? candidate.label.split(" · ")[0]
                  : localizeDemoOptionLabel(
                      "candidateCourse",
                      candidate.id,
                      candidate.label,
                    )}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={
            courseStateState.status === "ready" && !canUseRealEligibility
          }
          onClick={() => void handleRunEligibility()}
        >
          检查资格
        </button>
        <button type="button" onClick={() => void handleLoadHistory()}>
          加载历史
        </button>
      </div>

      {courseStateState.status === "ready" && !canUseRealEligibility ? (
        <section className="state-panel" aria-label="课程资格来源门禁">
          <h2>真实课程资格已阻止</h2>
          <p>
            {courseStateState.detail.snapshot.readiness.course_eligibility.blocking_reasons
              .map(readinessReasonLabel)
              .join("；")}
          </p>
        </section>
      ) : null}

      {eligibilityState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在检查资格</h2>
          <p>正在评估已保存的模拟课程规则和表达式证据。</p>
        </section>
      ) : null}

      {eligibilityState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课程资格 API 离线</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课程资格检查失败</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课程资格结构错误</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>没有课程资格检查</h2>
          <p>{eligibilityState.message}</p>
        </section>
      ) : null}

      {eligibilityState.status === "ready" ? (
        <EligibilityResultView
          state={eligibilityState}
          usesRealSnapshot={courseStateState.status === "ready"}
        />
      ) : null}
    </section>
  );
}

function EligibilityResultView({
  state,
  usesRealSnapshot,
}: {
  state: Extract<EligibilityState, { status: "ready" }>;
  usesRealSnapshot: boolean;
}) {
  const { result } = state;
  const availability = result.registration_availability;
  return (
    <div className="eligibility-result">
      <section className="summary-grid" aria-label="课程资格汇总">
        <SummaryMetric label="模式" value={statusLabel(result.mode)} />
        <SummaryMetric
          label="结果"
          value={statusLabel(result.overall_result)}
        />
        <SummaryMetric
          label="学业结果"
          value={statusLabel(result.academic_eligibility_result)}
        />
        <SummaryMetric
          label="课节状态"
          value={
            availability ? statusLabel(availability.section_status) : "仅课程"
          }
        />
        <SummaryMetric
          label="可用座位"
          value={
            availability?.available_seats === undefined ||
            availability?.available_seats === null
              ? "未报告"
              : String(availability.available_seats)
          }
        />
        <SummaryMetric label="警告" value={String(result.warnings.length)} />
      </section>
      <p className="notice compact">
        {usesRealSnapshot
          ? "使用已审核的非官方 active course-state snapshot；结果仅供建议，仍需学校或 advisor 确认。"
          : "演示数据：不应用于真实学业决策。"}
      </p>

      <section className="eligibility-columns">
        <div>
          <h2>原因</h2>
          <ReasonList title="阻止原因" reasons={result.blocking_reasons} />
          <ReasonList title="有条件原因" reasons={result.conditional_reasons} />
          <ReasonList title="需要许可" reasons={result.permissions_required} />
          <ReasonList title="人工审核" reasons={result.manual_review_reasons} />
        </div>
        <div>
          <h2>规则证据</h2>
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
            <p className="subtle">当前课程范围没有已保存规则。</p>
          )}
        </div>
        <div>
          <h2>警告</h2>
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
            <p className="subtle">没有课程资格警告。</p>
          )}
        </div>
      </section>

      {state.history.length > 1 ? (
        <section className="comparison-table" aria-label="课程资格历史">
          <h2>最近课程资格检查</h2>
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
  const isDemoMode = sourceLabel === "演示 / 模拟数据";
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
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
        message: "比较规划前，请先加载已自动验证或已确认的 MyProgress 导入。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setPlannerState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "至少需要两个已保存学业规划。",
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
              message: "比较已保存规划前，请先创建学业规划。",
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
    <section
      id="academic-plan"
      className="planner-panel"
      aria-label="长期学业规划"
    >
      <div className="section-heading">
        <div>
          <h2>长期学业规划</h2>
          <p className="subtle">
            {isDemoMode
              ? "演示模式：不应用于真实学业决策。"
              : "真实导入模式只在课程历史、要求树和项目映射均达到 readiness 阈值后启用。"}
          </p>
        </div>
        <p className="notice compact">这不是注册课程。</p>
      </div>

      <ul className="disclaimer-list" aria-label="长期学业规划边界">
        <li>
          {isDemoMode
            ? "演示数据 / 模拟数据，不是官方学校政策。"
            : "使用非官方内部规划快照，不代表官方毕业审核或完成日期。"}
        </li>
        <li>不会注册课程，不会 add/drop/swap。</li>
        <li>长期规划不检查每周课表冲突。</li>
        <li>课程开设预测只是估算。</li>
        <li>高风险学业建议需要 advisor / registrar / 学校确认。</li>
      </ul>

      <div className="scenario-controls planner-controls">
        <label>
          规划范围
          <select
            value={selectedPlannerScopeId}
            onChange={(event) => setSelectedPlannerScopeId(event.target.value)}
          >
            {plannerScopes
              .filter((scope) => isDemoMode || scope.id === "current-program")
              .map((scope) => (
                <option key={scope.id} value={scope.id}>
                  {isDemoMode
                    ? localizeDemoOptionLabel(
                        "plannerScope",
                        scope.id,
                        scope.label,
                      )
                    : "已应用项目 / Catalog 内部规划范围"}
                </option>
              ))}
          </select>
        </label>
        <label>
          开始学期
          <select
            value={selectedPlannerStartTermId}
            onChange={(event) =>
              setSelectedPlannerStartTermId(event.target.value)
            }
          >
            {plannerStartTerms.map((term) => (
              <option key={term.id} value={term.id}>
                {localizeDemoOptionLabel("term", term.label, term.label)}
              </option>
            ))}
          </select>
        </label>
        <label>
          学期数
          <input
            min={1}
            max={16}
            type="number"
            value={termsToPlan}
            onChange={(event) => setTermsToPlan(Number(event.target.value))}
          />
        </label>
        <label>
          最低学分
          <input
            min={0}
            type="number"
            value={minimumCredits}
            onChange={(event) => setMinimumCredits(Number(event.target.value))}
          />
        </label>
        <label>
          偏好学分
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
          最高学分
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
          创建规划
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleComparePlans()}
        >
          比较已保存规划
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="长期规划来源门禁">
          <h2>长期规划已阻止</h2>
          <p>
            当前来源是 {sourceLabel}。长期规划等待完整可靠的真实 MyProgress
            课程行；当前演示/模拟规划不应用于真实学业决策。
          </p>
        </section>
      ) : null}

      {plannerState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在创建学业规划</h2>
          <p>正在评估毕业要求缺口、先修解锁和学期容量。</p>
        </section>
      ) : null}

      {plannerState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>学业规划 API 离线</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>学业规划失败</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>学业规划结构错误</h2>
          <p>{plannerState.message}</p>
        </section>
      ) : null}

      {plannerState.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>没有已保存规划</h2>
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
      <section className="summary-grid" aria-label="学业规划汇总">
        <SummaryMetric label="规划状态" value={statusLabel(plan.status)} />
        <SummaryMetric
          label="规划模式"
          value={statusLabel(plan.planning_mode)}
        />
        <SummaryMetric label="学期数" value={String(plan.terms.length)} />
        <SummaryMetric
          label="规划课程"
          value={String(plan.planned_courses.length)}
        />
        <SummaryMetric
          label="规划学分"
          value={formatCredits(String(totalPlannedCredits))}
        />
        <SummaryMetric label="警告" value={String(plan.warnings.length)} />
      </section>
      <p className="notice compact">
        演示数据：尚未接入完整真实 MyProgress 课程行，不应用于真实学业决策。
      </p>

      <section className="planner-term-grid" aria-label="逐学期学业规划">
        <h2>逐学期规划</h2>
        {plan.planned_courses.length === 0 ? (
          <p className="subtle">当前设置没有生成规划课程。</p>
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
                <p>{formatCredits(term.planned_credits)} 规划学分</p>
                {courses.length > 0 ? (
                  <ul className="compact-list">
                    {courses.map((course) => (
                      <li key={course.id}>
                        <strong>{course.course_code}</strong>
                        <span>
                          {course.course_title} ·{" "}
                          {formatCredits(course.credits)} 学分
                        </span>
                        <span>
                          {statusLabel(course.planning_status)} ·{" "}
                          {course.reason_code}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="subtle">本学期没有放置课程。</p>
                )}
              </section>
            );
          })}
        </div>
      </section>

      <section className="planner-columns">
        <div>
          <h2>要求覆盖</h2>
          {plan.requirement_coverage.length > 0 ? (
            <ul className="compact-list">
              {plan.requirement_coverage.map((coverage) => (
                <li key={coverage.id}>
                  <strong>{coverage.requirement_code}</strong>
                  <span>
                    {statusLabel(coverage.coverage_type)} ·{" "}
                    {formatCredits(coverage.credits)}
                    学分
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">没有创建要求覆盖。</p>
          )}
        </div>
        <div>
          <h2>规划警告</h2>
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
            <p className="subtle">没有规划警告。</p>
          )}
        </div>
      </section>

      {state.comparisons.length > 0 ? (
        <section className="comparison-table" aria-label="已保存学业规划比较">
          <h2>已保存规划比较</h2>
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
                    {formatCredits(comparison.total_planned_credits)} 规划学分 ·{" "}
                    {comparison.warning_count} 个警告
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
        message: "生成课表前，请先导入真实课节数据并确认可靠课程行。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScheduleState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          section_data_mode: "REVIEWED_IMPORTED",
          source_age_max_minutes: 1440,
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
        message: "比较课表前，请先导入真实课节数据并确认可靠课程行。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setScheduleState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "至少需要两个已保存课表运行。",
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
              message: "比较已保存课表运行前，请先生成课表。",
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
      aria-label="学期课表生成器"
    >
      <span id="sections" className="workflow-anchor" aria-hidden="true" />
      <div className="section-heading">
        <div>
          <h2 id="schedule-builder">学期课表生成器</h2>
          <p className="subtle">
            真实导入模式：仅使用已 Review/Apply 的课节；来源年龄上限为 24 小时。
          </p>
        </div>
        <p className="notice compact">这不是注册课程。</p>
      </div>

      <ul className="disclaimer-list" aria-label="课表生成器边界">
        <li>仅使用已 Review/Apply 的导入课节；不会回退到演示课节。</li>
        <li>生成课表不是注册课程。</li>
        <li>课节座位状态必须在官方门户人工核对。</li>
        <li>不会 add/drop/swap，不会加入 waitlist。</li>
        <li>不会抢课或占座，不会提交官方门户表单。</li>
        <li>高风险学业建议需要 advisor / registrar / 学校确认。</li>
      </ul>

      <div className="scenario-controls schedule-controls">
        <label>
          课程集合
          <select
            value={selectedSchedulePresetId}
            onChange={(event) =>
              setSelectedSchedulePresetId(event.target.value)
            }
          >
            {schedulePresets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {localizeDemoOptionLabel(
                  "schedulePreset",
                  preset.id,
                  preset.label,
                )}
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
          不排周五
        </label>
        <label className="toggle-row">
          <input
            checked={scheduleAvoidTuesdayBlock}
            type="checkbox"
            onChange={(event) =>
              setScheduleAvoidTuesdayBlock(event.target.checked)
            }
          />
          周二 11:00 不可用
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferOnline}
            type="checkbox"
            onChange={(event) => setSchedulePreferOnline(event.target.checked)}
          />
          偏好线上
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferCompact}
            type="checkbox"
            onChange={(event) => setSchedulePreferCompact(event.target.checked)}
          />
          紧凑课表
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferFewerDays}
            type="checkbox"
            onChange={(event) =>
              setSchedulePreferFewerDays(event.target.checked)
            }
          />
          更少上课日
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferNoGaps}
            type="checkbox"
            onChange={(event) => setSchedulePreferNoGaps(event.target.checked)}
          />
          减少空档
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferMorning}
            type="checkbox"
            onChange={(event) => setSchedulePreferMorning(event.target.checked)}
          />
          上午
        </label>
        <label className="toggle-row">
          <input
            checked={schedulePreferAfternoon}
            type="checkbox"
            onChange={(event) =>
              setSchedulePreferAfternoon(event.target.checked)
            }
          />
          下午
        </label>
        <label>
          固定课节
          <select
            value={schedulePinnedSectionChoiceId}
            onChange={(event) =>
              setSchedulePinnedSectionChoiceId(event.target.value)
            }
          >
            {scheduleSectionChoices.slice(0, 3).map((choice) => (
              <option key={choice.id} value={choice.id}>
                {localizeDemoOptionLabel(
                  "scheduleSectionChoice",
                  choice.id,
                  choice.label,
                )}
              </option>
            ))}
          </select>
        </label>
        <label>
          排除课节
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
                  {localizeDemoOptionLabel(
                    "scheduleSectionChoice",
                    choice.id,
                    choice.label,
                  )}
                </option>
              ))}
          </select>
        </label>
        <label>
          差异度
          <select
            value={scheduleDiversityMode}
            onChange={(event) =>
              setScheduleDiversityMode(
                event.target.value === "HIGH" ? "HIGH" : "STANDARD",
              )
            }
          >
            <option value="HIGH">高</option>
            <option value="STANDARD">标准</option>
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
          允许部分选项
        </label>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCreateSchedule()}
        >
          生成课表
        </button>
        <button
          type="button"
          disabled={!canUseDownstreamAnalysis}
          onClick={() => void handleCompareSchedules()}
        >
          比较已保存课表
        </button>
      </div>

      {!canUseDownstreamAnalysis ? (
        <section className="state-panel" aria-label="课表来源门禁">
          <h2>课表优化等待真实课节数据</h2>
          <p>
            当前来源是 {sourceLabel}。课表优化需要真实课节搜索数据；
            当前演示/模拟课表不应用于真实学业决策。
          </p>
        </section>
      ) : null}

      {scheduleState.status === "idle" ? (
        <EmptyState
          copyKey="NO_GENERATED_SCHEDULE_PLANS"
          ariaLabel="课表方案空状态"
        />
      ) : null}

      {scheduleState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在生成学期课表</h2>
          <p>正在检查模拟课节时间、资格、冲突和偏好。</p>
        </section>
      ) : null}

      {scheduleState.status === "offline" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课表优化 API 离线</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "failed" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课表优化失败</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>课表优化结构错误</h2>
          <p>{scheduleState.message}</p>
        </section>
      ) : null}

      {scheduleState.status === "empty" ? (
        <EmptyState
          copyKey="NO_GENERATED_SCHEDULE_PLANS"
          ariaLabel="课表方案空状态"
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
      <section className="summary-grid" aria-label="课表优化汇总">
        <SummaryMetric label="运行状态" value={statusLabel(schedule.status)} />
        <SummaryMetric label="选项" value={String(schedule.options.length)} />
        <SummaryMetric label="冲突" value={String(schedule.conflicts.length)} />
        <SummaryMetric label="警告" value={String(schedule.warnings.length)} />
        <SummaryMetric
          label="最佳学分"
          value={bestOption ? formatCredits(bestOption.total_credits) : "0.0"}
        />
        <SummaryMetric
          label="最佳分数"
          value={bestOption ? Number(bestOption.score).toFixed(2) : "0.00"}
        />
      </section>
      <p className="notice compact">
        演示数据：尚未导入真实课节数据；课节座位状态必须在官方门户人工核对。
      </p>

      <section className="schedule-options" aria-label="课表选项">
        <h2>课节选项</h2>
        {schedule.options.length === 0 ? (
          <p className="subtle">没有创建可行课节选项。</p>
        ) : null}
        <div className="schedule-option-grid">
          {schedule.options.map((option) => (
            <section key={option.id} className="schedule-option">
              <div className="term-heading">
                <h3>选项 {option.option_rank}</h3>
                <span className={`status-pill ${option.status.toLowerCase()}`}>
                  {statusLabel(option.status)}
                </span>
              </div>
              <p>
                {formatCredits(option.total_credits)} 学分 -{" "}
                {option.class_days_count} 个上课日 - 分数{" "}
                {Number(option.total_score).toFixed(2)}
              </p>
              <p className="subtle">{option.explanation}</p>
              <p className="subtle">
                差异度 {option.diversity_rank}: {option.difference_summary}
              </p>
              <div className="score-breakdown">
                <span>
                  学分 {Number(option.score_breakdown.credit_score).toFixed(2)}
                </span>
                <span>
                  紧凑{" "}
                  {Number(option.score_breakdown.compactness_score).toFixed(2)}
                </span>
                <span>
                  上课日 {Number(option.score_breakdown.days_score).toFixed(2)}
                </span>
                <span>
                  空档 {Number(option.score_breakdown.gap_score).toFixed(2)}
                </span>
                <span>
                  模式{" "}
                  {Number(option.score_breakdown.modality_score).toFixed(2)}
                </span>
                <span>
                  时间{" "}
                  {Number(option.score_breakdown.time_preference_score).toFixed(
                    2,
                  )}
                </span>
                <span>
                  优先级{" "}
                  {Number(option.score_breakdown.priority_score).toFixed(2)}
                </span>
                <span>
                  惩罚 {Number(option.score_breakdown.penalty_score).toFixed(2)}
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
                    <span>
                      来源 · {selected.drift_status === "CHANGED"
                        ? "已变化，请重新生成"
                        : selected.drift_status === "UNCHANGED"
                          ? "快照一致"
                          : "未捕获快照"}
                      {selected.source_age_minutes !== null
                        ? ` · ${selected.source_age_minutes} 分钟前`
                        : " · 来源年龄未知"}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>

      {schedule.options.length >= 2 ? (
        <section className="comparison-table" aria-label="课表选项比较">
          <h2>前两个选项比较</h2>
          <div className="comparison-rows">
            {schedule.options.slice(0, 2).map((option) => (
              <div key={`${option.id}-top-compare`} className="comparison-row">
                <strong>选项 {option.option_rank}</strong>
                <span>
                  分数 {Number(option.total_score).toFixed(2)} - 与上一选项共享{" "}
                  {option.shared_section_count_with_previous_option} 个课节 -{" "}
                  {option.difference_summary}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="planner-columns">
        <div>
          <h2>冲突</h2>
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
            <p className="subtle">没有记录冲突。</p>
          )}
        </div>
        <div>
          <h2>课表警告</h2>
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
            <p className="subtle">没有课表警告。</p>
          )}
        </div>
      </section>

      {schedule.repair_suggestions.length > 0 ? (
        <section className="comparison-table" aria-label="课表修复建议">
          <h2>修复建议</h2>
          <div className="comparison-rows">
            {schedule.repair_suggestions.map((suggestion) => (
              <div key={suggestion.id} className="comparison-row">
                <strong>{statusLabel(suggestion.suggestion_type)}</strong>
                <span>
                  {suggestion.message}{" "}
                  {suggestion.requires_advisor_confirmation
                    ? "可能需要 advisor 确认。"
                    : ""}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {state.comparisons.length > 0 ? (
        <section className="comparison-table" aria-label="已保存课表比较">
          <h2>已保存课表比较</h2>
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
                    {comparison.option_count} 个选项 -{" "}
                    {comparison.best_total_credits
                      ? formatCredits(comparison.best_total_credits)
                      : "0.0"}{" "}
                    最佳学分 - {comparison.warning_count} 个警告
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
  courseStateState,
  setCourseStateState,
}: {
  selectedDataImportSampleId: string;
  setSelectedDataImportSampleId: (value: string) => void;
  dataImportState: DataImportPreviewState;
  setDataImportState: Dispatch<SetStateAction<DataImportPreviewState>>;
  dataReviewState: DataReviewState;
  setDataReviewState: Dispatch<SetStateAction<DataReviewState>>;
  courseStateState: CourseStateState;
  setCourseStateState: Dispatch<SetStateAction<CourseStateState>>;
}) {
  const selectedSample =
    dataImportSamples.find(
      (sample) => sample.id === selectedDataImportSampleId,
    ) ?? dataImportSamples[0];
  const sanitizedMyProgressSample = dataImportSamples.find(
    (sample) => sample.id === sanitizedMyProgressSampleId,
  );

  async function handlePreviewImport(sample = selectedSample): Promise<void> {
    if (!activeStudentId) {
      setDataImportState({
        status: "empty",
        message: "请先导入真实学生数据，或显式启用演示工作流。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setDataImportState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    setDataImportState({ status: "loading" });
    try {
      const run = await createDataImport(
        apiBaseUrl,
        {
          student_profile_id: activeStudentId,
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
        activeStudentId,
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
    if (!activeStudentId) {
      setDataImportState({
        status: "empty",
        message: "请先导入真实学生数据，或显式启用演示工作流。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setDataImportState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    setDataImportState({ status: "loading" });
    try {
      const savedImports = await fetchStudentDataImports(
        apiBaseUrl,
        activeStudentId,
        { timeoutMs: 5_000 },
      );
      if (savedImports.length === 0) {
        setDataImportState({
          status: "empty",
          message: "没有可用的已保存 staging 导入。",
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
          message: "无法预览任何已保存 staging 导入。",
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

  async function handleSelectSavedImport(runId: string): Promise<void> {
    if (!activeStudentId) {
      setDataImportState({
        status: "empty",
        message: "请先导入真实学生数据，或显式启用演示工作流。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setDataImportState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    const currentSavedImports =
      dataImportState.status === "ready" ? dataImportState.savedImports : [];
    const selectedRun = currentSavedImports.find((run) => run.id === runId);
    if (!selectedRun) {
      setDataImportState({
        status: "failed",
        message: "无法找到所选 staging 导入。",
      });
      return;
    }
    setDataImportState({ status: "loading" });
    try {
      const savedImports = await fetchStudentDataImports(
        apiBaseUrl,
        activeStudentId,
        { timeoutMs: 5_000 },
      );
      const run = savedImports.find((savedRun) => savedRun.id === runId);
      if (!run) {
        setDataImportState({
          status: "failed",
          message: "所选 staging 导入不再可用。",
        });
        return;
      }
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

  return (
    <section
      className="data-import-panel"
      id="data-import-preview"
      aria-label="数据导入预览"
    >
      <div className="section-heading">
        <div>
          <h2>数据导入预览</h2>
          <p className="subtle">staging 记录与官方学业记录保持分离。</p>
        </div>
        <p className="notice compact">只读 staging 边界。</p>
      </div>

      <ul className="disclaimer-list" aria-label="数据导入边界">
        <li>导入预览数据不是官方学校政策。</li>
        <li>不会修改成绩单、目录、课节、注册、座位或 waitlist 记录。</li>
        <li>高风险学业建议需要 advisor / registrar / 学校确认。</li>
      </ul>

      <section
        className="browser-extension-status"
        aria-label="浏览器插件导入状态"
      >
        <div>
          <h2>浏览器插件导入</h2>
          <p className="subtle">
            只检查用户已登录并主动打开的页面；导入后先进入 staging。
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
            <strong>只读</strong>
            <span>浏览器插件提取结果必须先进入 staging 导入。</span>
          </li>
          <li>
            <strong>审核</strong>
            <span>应用前需要明确点击应用并查看异常队列。</span>
          </li>
          <li>
            <strong>安全边界</strong>
            <span>
              不会注册课程，不会 add/drop/swap，不会加入
              waitlist，不会抢课或占座。
            </span>
          </li>
        </ul>
      </section>

      <div className="scenario-controls data-import-controls">
        <label>
          示例导入
          <select
            value={selectedDataImportSampleId}
            onChange={(event) =>
              setSelectedDataImportSampleId(event.target.value)
            }
          >
            {dataImportSamples.map((sample) => (
              <option key={sample.id} value={sample.id}>
                {localizeDemoOptionLabel(
                  "dataImportSample",
                  sample.id,
                  sample.label,
                )}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void handlePreviewImport()}>
          预览导入
        </button>
        {sanitizedMyProgressSample ? (
          <button
            type="button"
            onClick={() => void handlePreviewImport(sanitizedMyProgressSample)}
          >
            加载脱敏 MyProgress 示例
          </button>
        ) : null}
        <button type="button" onClick={() => void handleLoadSavedImports()}>
          加载已保存导入
        </button>
      </div>
      <p className="notice compact">
        脱敏本地测试数据仅为示例，不是官方学校数据。
      </p>

      {dataImportState.status === "idle" ? (
        <EmptyState copyKey="NO_DATA_IMPORTS" ariaLabel="数据导入空状态" />
      ) : null}

      {dataImportState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在解析导入</h2>
          <p>正在创建包含映射候选项和警告的 staging 预览。</p>
        </section>
      ) : null}

      {dataImportState.status === "offline" ||
      dataImportState.status === "failed" ||
      dataImportState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {dataImportState.status === "schema-error"
              ? "数据导入结构错误"
              : "数据导入不可用"}
          </h2>
          <p>{dataImportState.message}</p>
        </section>
      ) : null}

      {dataImportState.status === "empty" ? (
        <EmptyState copyKey="NO_DATA_IMPORTS" ariaLabel="数据导入空状态" />
      ) : null}

      {dataImportState.status === "ready" ? (
        <>
          <SavedImportSelector
            state={dataImportState}
            onSelectImport={(runId) => {
              void handleSelectSavedImport(runId);
            }}
          />
          <DataImportResultView state={dataImportState} />
        </>
      ) : null}

      <DataReviewPanel
        dataImportState={dataImportState}
        dataReviewState={dataReviewState}
        setDataReviewState={setDataReviewState}
        courseStateState={courseStateState}
        setCourseStateState={setCourseStateState}
      />
    </section>
  );
}

function SavedImportSelector({
  state,
  onSelectImport,
}: {
  state: ReadyDataImportPreviewState;
  onSelectImport: (runId: string) => void;
}) {
  const newestRun = state.savedImports[0];
  const showingOlderUsableImport =
    newestRun !== undefined && newestRun.id !== state.run.id;
  const selectedUsable = isUsableMyProgressPreviewSummary(state.preview);
  return (
    <section className="saved-import-selector" aria-label="已保存导入选择器">
      <div>
        <h2>已保存 staging 导入</h2>
        <p>选择要预览的导入；列表显示时间、来源、验证状态、行数和置信度。</p>
      </div>
      <label>
        <span>当前导入</span>
        <select
          value={state.run.id}
          onChange={(event) => {
            onSelectImport(event.currentTarget.value);
          }}
        >
          {state.savedImports.map((run) => {
            const option = savedImportOptionFromRun(run);
            return (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            );
          })}
        </select>
      </label>
      {showingOlderUsableImport ? (
        <p className="notice compact">
          最新保存的导入没有自动替换当前可用的 MyProgress
          预览；可在上方选择器中检查。
        </p>
      ) : null}
      {!selectedUsable && myProgressPreviewFromSummary(state.preview) ? (
        <p className="notice compact danger">
          当前 MyProgress 导入缺少可用行或汇总数据，需要重新提取或人工检查。
        </p>
      ) : null}
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
      <section className="summary-grid" aria-label="数据导入预览汇总">
        <SummaryMetric label="导入状态" value={statusLabel(state.run.status)} />
        <SummaryMetric
          label="数据模式"
          value={importModeLabel(myProgressPreview)}
        />
        <SummaryMetric label="记录数" value={String(state.run.record_count)} />
        <SummaryMetric
          label="映射候选项"
          value={String(selectedCandidateCount)}
        />
        <SummaryMetric label="警告" value={String(state.warnings.length)} />
        {myProgressPreview ? (
          <>
            <SummaryMetric
              label="提取的 MyProgress 行"
              value={String(myProgressPreview.extractedDegreeAuditRowCount)}
            />
            <SummaryMetric
              label="已解析课程行"
              value={String(myProgressPreview.parsedCourseLikeRowCount)}
            />
            <SummaryMetric
              label="要求摘要行"
              value={String(myProgressPreview.parsedRequirementRowCount)}
            />
            <SummaryMetric
              label="异常行"
              value={String(myProgressPreview.exceptionRowCount)}
            />
            <SummaryMetric
              label="忽略行"
              value={String(myProgressPreview.ignoredRowCount)}
            />
            <SummaryMetric
              label="提取有边界 / 截断"
              value={
                myProgressPreview.extractionBounded ||
                myProgressPreview.extractionTruncated
                  ? "是"
                  : "否"
              }
            />
            <SummaryMetric
              label="解析器确认字段"
              value={String(myProgressPreview.autoConfirmedFieldCount)}
            />
            <SummaryMetric
              label="解析器确认课程行"
              value={String(myProgressPreview.autoConfirmedCourseRowCount)}
            />
            <SummaryMetric
              label="异常"
              value={String(myProgressPreview.exceptions.length)}
            />
            <SummaryMetric
              label="总体置信度"
              value={`${Math.round(myProgressPreview.overallConfidenceScore * 100)}%`}
            />
          </>
        ) : null}
        <SummaryMetric
          label="内部验证"
          value={
            myProgressPreview?.canApplyVerifiedImport
              ? "已通过"
              : myProgressPreview
                ? "需 Review"
                : state.preview.official_application_ready
                  ? "可应用"
                  : "已禁用"
          }
        />
        <SummaryMetric
          label="来源类型"
          value={statusLabel(state.run.source.source_type)}
        />
        <SummaryMetric
          label="已保存导入"
          value={String(state.savedImports.length)}
        />
      </section>

      {myProgressPreview ? (
        <>
          <MyProgressReadinessPanel display={myProgressPreview} />
          <MyProgressImportPreview display={myProgressPreview} />
        </>
      ) : null}

      <section className="comparison-table" aria-label="导入预览边界">
        <h2>预览边界</h2>
        <AdvisoryLabels
          keys={["NON_OFFICIAL_IMPORTED_DATA", "MANUAL_REVIEW_REQUIRED"]}
        />
        <ul className="compact-list">
          {state.preview.disclaimers.map((disclaimer) => (
            <li key={disclaimer}>
              <strong>审核</strong>
              <span>{disclaimer}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="data-import-grid">
        {myProgressPreview ? (
          <section aria-label="MyProgress 异常队列">
            <h2>异常队列</h2>
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
              <p className="subtle">没有需要人工处理的导入异常。</p>
            )}
          </section>
        ) : (
          <>
            <section aria-label="导入记录">
              <h2>导入记录</h2>
              <div className="comparison-rows">
                {state.records.map((record) => (
                  <div key={record.id} className="comparison-row">
                    <strong>
                      {payloadValue(record.normalized_payload, "course_code") ??
                        record.raw_label}
                    </strong>
                    <span>
                      行 {record.row_number} · {statusLabel(record.status)} ·{" "}
                      {payloadValue(record.normalized_payload, "credits") ??
                        "0.0"}{" "}
                      学分
                    </span>
                  </div>
                ))}
              </div>
            </section>
            <section aria-label="导入映射候选项">
              <h2>映射候选项</h2>
              <div className="comparison-rows">
                {state.candidates.map((candidate) => (
                  <div key={candidate.id} className="comparison-row">
                    <strong>{candidate.reason_code}</strong>
                    <span>
                      {statusLabel(candidate.target_entity_type)} · 置信度{" "}
                      {candidate.confidence_score} · {candidate.explanation}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </section>

      <section className="comparison-table" aria-label="数据导入警告">
        <h2>警告</h2>
        {state.warnings.length > 0 ? (
          <div className="comparison-rows">
            {state.warnings.map((warning) => (
              <div key={warning.id} className="comparison-row">
                <strong>{warning.warning_code}</strong>
                <span>
                  {warning.message}{" "}
                  {warning.requires_advisor_confirmation
                    ? "需要 advisor 确认。"
                    : ""}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtle">没有导入警告。</p>
        )}
      </section>
    </div>
  );
}

function MyProgressReadinessPanel({
  display,
}: {
  display: MyProgressPreviewDisplay;
}) {
  const readinessEntries: MyProgressReadinessKey[] = [
    "summary",
    "requirement_summary",
    "course_rows",
    "planner",
    "course_eligibility",
    "schedule_builder",
  ];
  return (
    <section className="comparison-table" aria-label="MyProgress 分项就绪状态">
      <h2>分项就绪状态</h2>
      <div className="comparison-rows">
        {readinessEntries.map((key) => {
          const item = display.readiness[key];
          return (
            <div key={key} className="comparison-row">
              <strong>{readinessLabels[key]}</strong>
              <span>{readinessStatusLabel(item.status)}</span>
              <span>
                {item.reasonCodes.length > 0
                  ? item.reasonCodes.map(readinessReasonLabel).join("；")
                  : "没有额外阻止原因。"}
              </span>
            </div>
          );
        })}
      </div>
    </section>
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
    <section className="comparison-table" aria-label="MyProgress 导入验证摘要">
      <h2>MyProgress 验证摘要</h2>
      <div className="summary-grid compact-summary">
        <SummaryMetric
          label="项目"
          value={programSummary.programName ?? "未检测到"}
        />
        <SummaryMetric
          label="学位"
          value={programSummary.degree ?? "未检测到"}
        />
        <SummaryMetric
          label="专业"
          value={programSummary.major ?? "未检测到"}
        />
        <SummaryMetric
          label="院系"
          value={programSummary.department ?? "未检测到"}
        />
        <SummaryMetric
          label="Catalog 年份"
          value={
            programSummary.catalogYear
              ? String(programSummary.catalogYear)
              : "未检测到"
          }
        />
        <SummaryMetric
          label="GPA"
          value={
            programSummary.cumulativeGpa
              ? programSummary.cumulativeGpa.toFixed(3)
              : "未检测到"
          }
        />
        <SummaryMetric
          label="本校 GPA"
          value={
            programSummary.institutionGpa
              ? programSummary.institutionGpa.toFixed(3)
              : "未检测到"
          }
        />
        <SummaryMetric
          label="预计完成"
          value={programSummary.anticipatedCompletionDate ?? "未检测到"}
        />
        <SummaryMetric
          label="总学分"
          value={
            creditSummary.totalAppliedCredits !== undefined &&
            creditSummary.totalRequiredCredits !== undefined
              ? `${creditSummary.totalAppliedCredits} / ${creditSummary.totalRequiredCredits}`
              : "未检测到"
          }
        />
        <SummaryMetric
          label="已完成"
          value={String(creditSummary.completedCredits ?? "未检测到")}
        />
        <SummaryMetric
          label="进行中"
          value={String(creditSummary.inProgressCredits ?? "未检测到")}
        />
        <SummaryMetric
          label="已规划"
          value={String(creditSummary.plannedCredits ?? "未检测到")}
        />
        <SummaryMetric
          label="剩余"
          value={String(creditSummary.remainingCredits ?? "未检测到")}
        />
        <SummaryMetric
          label="完成度"
          value={
            creditSummary.completionPercent !== undefined
              ? `${creditSummary.completionPercent.toFixed(2)}%`
              : "未检测到"
          }
        />
        <SummaryMetric
          label="要求组"
          value={String(display.requirementGroups.length)}
        />
        <SummaryMetric
          label="课程行就绪"
          value={readinessStatusLabel(display.readiness.course_rows.status)}
        />
      </div>
      <ul className="compact-list">
        <li>
          <strong>审核范围</strong>
          <span>
            {display.exceptions.length === 0
              ? "解析器未发现异常；记录仍必须逐条经过人工 Review。"
              : "低置信度异常必须先审核再使用。"}
          </span>
        </li>
        <li>
          <strong>应用路径</strong>
          <span>
            {display.canApplyVerifiedImport
              ? "已验证导入可通过明确点击应用进入内部快照。"
              : "解析器验证不会跳过 Review；只有已确认记录才能应用到内部快照。"}
          </span>
        </li>
      </ul>

      <section className="comparison-rows" aria-label="MyProgress 要求组">
        {display.requirementGroups.map((group, index) => (
          <div
            key={`${stringFromUnknown(group.name) ?? "group"}-${index}`}
            className="comparison-row"
          >
            <strong>{stringFromUnknown(group.name) ?? "未命名要求组"}</strong>
            <span>{stringFromUnknown(group.statusText) ?? "没有状态文本"}</span>
          </div>
        ))}
      </section>

      <section className="comparison-rows" aria-label="MyProgress 课程行">
        {display.courseRows.slice(0, 8).map((row) => (
          <div
            key={`${row.rowNumber}-${row.rawRowText}`}
            className="comparison-row"
          >
            <strong>
              {row.courseCode || row.rawRowText || `课程行 ${row.rowNumber}`}
            </strong>
            <span>
              {row.courseTitle || "缺少课程标题"} · {statusLabel(row.status)}
              {row.term ? ` · ${row.term}` : ""}
            </span>
            <span>
              表 {row.sourceTableIndex || "?"} / 行 {row.sourceRowIndex || "?"}
              {row.requiresReview
                ? ` · ${row.reasonCodes.map(readinessReasonLabel).join("；")}`
                : " · 待人工 Review"}
            </span>
          </div>
        ))}
      </section>

      <section className="comparison-rows" aria-label="MyProgress 来源文本">
        {progressBarText ? (
          <div className="comparison-row">
            <strong>进度条</strong>
            <span>{progressBarText}</span>
          </div>
        ) : null}
        {visibleTextSample ? (
          <div className="comparison-row">
            <strong>可见文本</strong>
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
                {statusLabel(
                  stringFromUnknown(provenance.confidence) ?? "unknown",
                )}
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
      aria-label="课节监控"
    >
      <div className="section-heading">
        <div>
          <h2>课节监控</h2>
          <p className="subtle">
            来自用户触发的 section-search 导入，仅供参考。
          </p>
        </div>
        <p className="notice compact">需要人工审核。</p>
      </div>

      <ul className="disclaimer-list" aria-label="课节监控边界">
        <li>
          课节监控基于用户触发的导入数据，可能与官方门户不同。
          必须在官方注册门户人工核对。
        </li>
        <li>
          本系统不会注册、drop、swap、waitlist、提交表单或执行任何门户操作。
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
          <h2>正在加载课节监控</h2>
          <p>正在获取已监控课节和参考性提醒。</p>
        </section>
      ) : null}

      {state.status === "offline" ||
      state.status === "failed" ||
      state.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {state.status === "schema-error"
              ? "课节监控结构错误"
              : "课节监控不可用"}
          </h2>
          <p>{state.message}</p>
        </section>
      ) : null}

      {state.status === "empty" ? (
        <section className="state-panel" aria-live="polite">
          <h2>没有课节提醒</h2>
          <p>{state.message}</p>
        </section>
      ) : null}

      {state.status === "ready" ? (
        <div className="section-monitoring-grid">
          <section className="comparison-table" aria-label="已监控课节">
            <h2>已监控课节</h2>
            {state.targets.length > 0 ? (
              <div className="comparison-rows">
                {state.targets.map((target) => (
                  <div key={target.id} className="comparison-row">
                    <strong>
                      {target.course_code} {target.section_code}
                    </strong>
                    <span>
                      {target.term} · {target.title ?? "未命名课节"} ·{" "}
                      {target.status ? statusLabel(target.status) : "未知"}
                    </span>
                    <span>
                      最新导入快照：{" "}
                      {formatAcademicTimestamp(
                        target.latest_snapshot_created_at,
                      )}
                    </span>
                    <span>
                      {target.is_active ? "启用中" : "已归档"} · 仅供参考 ·{" "}
                      {target.is_official ? "官方来源" : "非官方导入数据"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                copyKey="NO_SECTION_MONITORING_TARGETS"
                ariaLabel="课节监控目标空状态"
              />
            )}
          </section>

          <section className="comparison-table" aria-label="参考性提醒">
            <h2>参考性提醒</h2>
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
                        {alert.is_acknowledged ? "已确认" : "人工审核"}
                      </span>
                      <span>
                        {alert.field_name ?? "未知课节变化"}:{" "}
                        {formatZhCnBeforeAfterValue(
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
                ariaLabel="课节监控提醒空状态"
              />
            )}
          </section>

          <section className="comparison-table" aria-label="人工注册核对清单">
            <h2>人工核对清单</h2>
            <ul className="compact-list">
              <li>手动打开官方注册门户。</li>
              <li>手动核对课节状态。</li>
              <li>手动确认先修、限制和 hold。</li>
              <li>如适合，必须由学生本人通过官方门户手动注册。</li>
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
  courseStateState,
  setCourseStateState,
}: {
  dataImportState: DataImportPreviewState;
  dataReviewState: DataReviewState;
  setDataReviewState: Dispatch<SetStateAction<DataReviewState>>;
  courseStateState: CourseStateState;
  setCourseStateState: Dispatch<SetStateAction<CourseStateState>>;
}) {
  const myProgressPreview = myProgressPreviewFromState(dataImportState);
  const reviewRecordsForDisplay =
    dataReviewState.status === "ready" && myProgressPreview
      ? dataReviewState.records.filter(
          (record) =>
            payloadValue(
              record.imported_record.normalized_payload,
              "record_kind",
            ) === "MY_PROGRESS_COURSE_ROW",
        )
      : dataReviewState.status === "ready"
        ? dataReviewState.records
        : [];
  const autoConfirmedReviewCount =
    dataReviewState.status === "ready" && myProgressPreview
      ? reviewRecordsForDisplay.filter(
          (record) =>
            record.decision === "CONFIRMED" ||
            record.decision === "EDITED_AND_CONFIRMED",
        ).length
      : 0;

  const [gradeEdits, setGradeEdits] = useState<Record<string, string>>({});

  async function loadActiveCourseStates(): Promise<void> {
    if (!activeStudentId) {
      setCourseStateState({
        status: "empty",
        message: "请先导入真实学生数据，或显式启用演示工作流。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setCourseStateState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    setCourseStateState({ status: "loading" });
    try {
      const detail = await fetchActiveCourseStateSnapshot(
        apiBaseUrl,
        activeStudentId,
        { timeoutMs: 5_000 },
      );
      setCourseStateState({ status: "ready", detail });
    } catch (error: unknown) {
      if (isNotFound(error)) {
        setCourseStateState({
          status: "empty",
          message: "尚未应用经过审核的 MyProgress 课程状态快照。",
        });
        return;
      }
      setCourseStateState({
        status:
          error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeDataImportError(error),
      });
    }
  }

  async function loadReviewDetail(
    review: DataImportReviewSession,
    applicationResult: DataReviewApplicationResult | null = null,
  ): Promise<void> {
    if (!apiBaseUrl) {
      setDataReviewState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    if (dataImportState.status !== "ready") {
      setDataReviewState({
        status: "empty",
        message: "创建审核前，请先预览或加载 staging 导入。",
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
    if (!activeStudentId) {
      setDataReviewState({
        status: "empty",
        message: "请先导入真实学生数据，或显式启用演示工作流。",
      });
      return;
    }
    if (!apiBaseUrl) {
      setDataReviewState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
      });
      return;
    }
    setDataReviewState({ status: "loading" });
    try {
      const reviews = await fetchStudentDataImportReviews(
        apiBaseUrl,
        activeStudentId,
        { timeoutMs: 5_000 },
      );
      if (reviews.length === 0) {
        setDataReviewState({
          status: "empty",
          message: "当前模拟学生没有可用的数据导入审核。",
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
      if (!dryRun && result.course_state_snapshot) {
        await loadActiveCourseStates();
      }
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
      id="data-review"
      className="data-review-panel"
      aria-label="数据审核与确认"
    >
      <div className="section-heading">
        <div>
          <h2>数据审核与确认</h2>
          <p className="subtle">已确认记录只会应用到内部规划数据。</p>
        </div>
        <p className="notice compact">需要明确点击应用。</p>
      </div>

      <ul className="disclaimer-list" aria-label="数据审核边界">
        <li>审核决定不会创建官方成绩单记录。</li>
        <li>试运行只显示拟写入内容，不创建领域记录。</li>
        <li>拒绝、暂缓、重复以及需要 advisor 审核的记录都会留下日志。</li>
      </ul>
      <AdvisoryLabels keys={["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"]} />

      <div className="scenario-controls data-import-controls">
        <button type="button" onClick={() => void handleCreateReview()}>
          创建审核
        </button>
        <button type="button" onClick={() => void handleLoadLatestReviews()}>
          加载最新审核
        </button>
        <button type="button" onClick={() => void loadActiveCourseStates()}>
          {courseStateState.status === "ready"
            ? "刷新课程状态"
            : "加载已应用课程状态"}
        </button>
        {dataReviewState.status === "ready" ? (
          <>
            <button type="button" onClick={() => void handleApply(true)}>
              试运行
            </button>
            <button type="button" onClick={() => void handleApply(false)}>
              应用已确认记录
            </button>
          </>
        ) : null}
      </div>

      {dataReviewState.status === "idle" ? (
        <EmptyState copyKey="NO_CONFIRMED_IMPORTS" ariaLabel="数据审核空状态" />
      ) : null}

      {dataReviewState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在加载审核</h2>
          <p>正在获取审核记录、警告和应用日志。</p>
        </section>
      ) : null}

      {dataReviewState.status === "offline" ||
      dataReviewState.status === "failed" ||
      dataReviewState.status === "schema-error" ? (
        <section className="state-panel" aria-live="polite">
          <h2>
            {dataReviewState.status === "schema-error"
              ? "数据审核结构错误"
              : "数据审核不可用"}
          </h2>
          <p>{dataReviewState.message}</p>
        </section>
      ) : null}

      {dataReviewState.status === "empty" ? (
        <EmptyState copyKey="NO_CONFIRMED_IMPORTS" ariaLabel="数据审核空状态" />
      ) : null}

      {dataReviewState.status === "ready" ? (
        <div className="data-import-result">
          <section className="summary-grid" aria-label="数据审核汇总">
            <SummaryMetric
              label="审核状态"
              value={statusLabel(dataReviewState.review.status)}
            />
            <SummaryMetric
              label="记录数"
              value={String(dataReviewState.records.length)}
            />
            {myProgressPreview ? (
              <SummaryMetric
                label="已确认记录"
                value={String(autoConfirmedReviewCount)}
              />
            ) : null}
            {myProgressPreview ? (
              <SummaryMetric
                label="异常队列"
                value={String(
                  reviewRecordsForDisplay.filter(
                    (record) => record.requires_advisor_confirmation,
                  ).length,
                )}
              />
            ) : null}
            <SummaryMetric
              label="警告"
              value={String(dataReviewState.warnings.length)}
            />
            <SummaryMetric
              label="应用次数"
              value={String(dataReviewState.applications.length)}
            />
            <SummaryMetric
              label="上次结果"
              value={
                dataReviewState.applicationResult?.dry_run
                  ? "试运行"
                  : dataReviewState.applicationResult?.application?.status
                    ? statusLabel(
                        dataReviewState.applicationResult.application.status,
                      )
                    : "无"
              }
            />
          </section>

          <section className="comparison-table" aria-label="审核记录">
            <h2>{myProgressPreview ? "课程状态审核与应用" : "记录处理决定"}</h2>
            <div className="comparison-rows">
              {reviewRecordsForDisplay.length === 0 && myProgressPreview ? (
                <p className="subtle">
                  当前导入没有可审核的 MyProgress 课程状态行。
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
                const payload = recordReview.imported_record.normalized_payload;
                const courseTitle =
                  payloadValue(payload, "title") ?? "未提供标题";
                const courseStatus =
                  payloadValue(payload, "status") ?? "UNKNOWN";
                const term = payloadValue(payload, "term") ?? "学期未知";
                const credits = payloadValue(payload, "credits") ?? "学分未知";
                const tableIndex =
                  payloadValue(payload, "source_table_index") ?? "未知表";
                const rowIndex =
                  payloadValue(payload, "source_row_index") ?? "未知行";
                return (
                  <div key={recordReview.id} className="comparison-row">
                    <strong>
                      {courseCode} · {courseTitle}
                    </strong>
                    <span>
                      {statusLabel(courseStatus)} · {term} · {credits} 学分 ·{" "}
                      {statusLabel(recordReview.decision)}
                    </span>
                    <span>
                      {recordReview.requires_advisor_confirmation
                        ? "已标记 advisor 审核"
                        : "学生可审核"}
                    </span>
                    <span>
                      Catalog：
                      {recordReview.selected_mapping_candidate?.target_entity_id
                        ? "已匹配"
                        : "未匹配 / 外部证据"}
                      · 置信度{" "}
                      {String(recordReview.imported_record.confidence_score)} ·
                      来源表 {tableIndex} 行 {rowIndex}
                    </span>
                    <span>
                      {recordReview.selected_mapping_candidate?.explanation ??
                        "没有已选映射候选项；不会根据标题猜测课程代码。"}
                    </span>
                    <div className="record-review-actions">
                      <label className="review-edit-field">
                        成绩
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
                        确认
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(recordReview, "REJECTED")
                        }
                      >
                        拒绝
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDecision(recordReview, "DEFERRED")
                        }
                      >
                        暂缓
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
                        Advisor 审核
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
                        编辑并确认
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {dataReviewState.applicationResult ? (
            <section className="comparison-table" aria-label="数据应用结果">
              <h2>应用结果</h2>
              <section className="summary-grid" aria-label="数据应用汇总">
                <SummaryMetric
                  label="已应用"
                  value={String(
                    dataReviewState.applicationResult.summary.applied_count,
                  )}
                />
                <SummaryMetric
                  label="警告"
                  value={String(
                    dataReviewState.applicationResult.summary.warning_count,
                  )}
                />
                <SummaryMetric
                  label="异常"
                  value={String(
                    dataReviewState.applicationResult.summary.exception_count,
                  )}
                />
                <SummaryMetric
                  label="已拒绝"
                  value={String(
                    dataReviewState.applicationResult.summary.rejected_count,
                  )}
                />
                <SummaryMetric
                  label="已暂缓"
                  value={String(
                    dataReviewState.applicationResult.summary.deferred_count,
                  )}
                />
                <SummaryMetric
                  label="重复跳过"
                  value={String(
                    dataReviewState.applicationResult.summary.duplicate_count,
                  )}
                />
              </section>
              <p className="subtle">
                来源 import：
                {dataReviewState.applicationResult.summary.source_import_id}
                {dataReviewState.applicationResult.summary.snapshot_id
                  ? ` · snapshot：${dataReviewState.applicationResult.summary.snapshot_id}`
                  : " · dry run 尚未创建 snapshot"}
              </p>
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

          <section className="comparison-table" aria-label="审核警告">
            <h2>审核警告</h2>
            {dataReviewState.warnings.length > 0 ? (
              <div className="comparison-rows">
                {dataReviewState.warnings.map((warning) => (
                  <div key={warning.id} className="comparison-row">
                    <strong>{warning.warning_code}</strong>
                    <span>
                      {warning.message}{" "}
                      {warning.requires_advisor_confirmation
                        ? "需要 advisor 确认。"
                        : ""}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="subtle">没有审核警告。</p>
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
    return "上课时间不可用";
  }
  return meetings
    .map((meeting) => {
      if (meeting.is_online && !meeting.day_of_week) {
        return "在线异步";
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
      <section className="summary-grid" aria-label="假设方案汇总">
        <SummaryMetric
          label="候选项目"
          value={localizeDemoOptionLabel(
            "candidateProgram",
            selectedCandidate.id,
            selectedCandidate.label,
          )}
        />
        <SummaryMetric
          label="方案状态"
          value={statusLabel(detail.scenario.status)}
        />
        <SummaryMetric
          label="共享学分"
          value={formatCredits(detail.comparison.shared_credits)}
        />
        <SummaryMetric
          label="第二项目独有学分"
          value={formatCredits(detail.comparison.unique_secondary_credits)}
        />
        <SummaryMetric
          label="预计额外学分"
          value={formatCredits(detail.comparison.estimated_additional_credits)}
        />
        <SummaryMetric
          label="人工审核"
          value={String(detail.comparison.manual_review_count)}
        />
      </section>

      <section className="scenario-columns">
        <div>
          <h2>项目</h2>
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
          <h2>课程分配</h2>
          {selectedAllocations.length > 0 ? (
            <ul className="compact-list">
              {selectedAllocations.map((allocation) => (
                <li key={allocation.id}>
                  <strong>
                    {allocation.course_code ?? allocation.reason_code}
                  </strong>
                  <span>
                    {statusLabel(allocation.allocation_type)} ·{" "}
                    {formatCredits(allocation.credit_amount)} 学分
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="subtle">没有可用课程分配。</p>
          )}
        </div>
        <div>
          <h2>警告</h2>
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
            <p className="subtle">没有人工审核警告。</p>
          )}
        </div>
      </section>

      {state.comparisons.length > 0 ? (
        <section className="comparison-table" aria-label="已保存方案比较">
          <h2>已保存方案比较</h2>
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
                    预计额外学分
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
