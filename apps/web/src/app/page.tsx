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
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { parsePublicEnv } from "../lib/env";
import {
  formatZhCnBeforeAfterValue,
  getZhCnAdvisoryLabels,
  getZhCnEmptyStateCopy,
  localizeDemoOptionLabel,
  localizeStatusBadge,
  localizeStatusLabel,
} from "../lib/zh-cn";

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
];

function describeHealthError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的健康检查响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知 API 健康检查错误";
}

function describeAuditError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的学业审核响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知学业审核错误";
}

function describeScenarioError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的假设方案响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知假设方案错误";
}

function describeEligibilityError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的课程资格响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知课程资格错误";
}

function describePlannerError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的学业规划响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知学业规划错误";
}

function describeScheduleError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的课表优化响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知课表优化错误";
}

function describeDataImportError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的数据导入响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知数据导入错误";
}

function describeSectionMonitoringError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API 返回了意外的课节监控响应结构。";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "未知课节监控错误";
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

function formatDisplayTimestamp(value: string | null | undefined): string {
  const formatted = formatAcademicTimestamp(value);
  if (formatted === "Not available") {
    return "不可用";
  }
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.valueOf())) {
    return "不可用";
  }
  return `${new Intl.DateTimeFormat("zh-CN", {
    day: "numeric",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(date)} UTC`;
}

export default function Home() {
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
  const [sectionMonitoringState, setSectionMonitoringState] =
    useState<SectionMonitoringState>(() =>
      apiBaseUrl
        ? { status: "loading" }
        : {
            status: "offline",
            message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
                  message: "还没有可用的学业审核快照结果。",
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

  const warnings =
    auditState.status === "ready"
      ? auditState.requirements.flatMap((requirement) => requirement.warnings)
      : [];

  return (
    <main>
      <section className="progress-shell">
        <div className="topbar">
          <p className={`badge ${health.status === "online" ? "ok" : "warn"}`}>
            {health.status === "loading"
              ? "正在检查 API"
              : health.status === "online"
                ? "API 已连接"
                : "API 不可用"}
          </p>
          <p className="notice compact">模拟数据 — 不是官方学校政策。</p>
        </div>

        <h1>学业进度</h1>
        <p className="subtle">高风险学业建议需要学校或顾问确认。</p>

        <ProductStatusDashboard
          auditState={auditState}
          dataReviewState={dataReviewState}
          scenarioState={scenarioState}
          scheduleState={scheduleState}
          sectionMonitoringState={sectionMonitoringState}
        />

        {auditState.status === "ready" ? (
          <DegreeProgress
            audit={auditState.audit}
            requirements={auditState.requirements}
          />
        ) : (
          <AuditFallback state={auditState} health={health} />
        )}

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
}: {
  audit: DegreeAuditRun;
  requirements: RequirementEvaluation[];
}) {
  return (
    <>
      <section
        className="summary-grid"
        id="degree-audit"
        aria-label="学业审核摘要"
      >
        <SummaryMetric label="项目" value="Mock BS Finance" />
        <SummaryMetric label="目录年份" value="2024" />
        <SummaryMetric
          label="审核模式"
          value={statusLabel(audit.calculation_mode)}
        />
        <SummaryMetric
          label="已完成学分"
          value={formatCredits(audit.completed_credits)}
        />
        <SummaryMetric
          label="进行中学分"
          value={formatCredits(audit.in_progress_credits)}
        />
        <SummaryMetric
          label="已规划学分"
          value={formatCredits(audit.planned_credits)}
        />
        <SummaryMetric
          label="剩余学分"
          value={formatCredits(audit.remaining_credits)}
        />
        <SummaryMetric
          label="完成度"
          value={`${Number(audit.completion_percentage).toFixed(2)}%`}
        />
      </section>

      <section className="requirement-tree" aria-label="毕业要求树">
        <h2>毕业要求树</h2>
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
                    {requirement.required_courses ?? "—"} 门课程 /{" "}
                    {requirement.required_credits
                      ? formatCredits(requirement.required_credits)
                      : "—"}{" "}
                    学分
                  </dd>
                </div>
                <div>
                  <dt>已满足</dt>
                  <dd>
                    {requirement.satisfied_courses} 门课程 /{" "}
                    {formatCredits(requirement.satisfied_credits)} 学分
                  </dd>
                </div>
                <div>
                  <dt>剩余</dt>
                  <dd>
                    {requirement.remaining_courses} 门课程 /{" "}
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
                <p className="advisor-note">需要顾问确认。</p>
              ) : null}
            </div>
          </details>
        ))}
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
  dataReviewState,
  scenarioState,
  scheduleState,
  sectionMonitoringState,
}: {
  auditState: AuditState;
  dataReviewState: DataReviewState;
  scenarioState: ScenarioState;
  scheduleState: ScheduleState;
  sectionMonitoringState: SectionMonitoringState;
}) {
  const cards: ProductStatusCard[] = [
    {
      ariaLabel: "学业审核状态卡片",
      title: "学业审核",
      explanation: "最新的确定性学业审核快照和毕业要求树。",
      status:
        auditState.status === "ready"
          ? auditState.audit.status
          : auditState.status,
      nextAction:
        auditState.status === "ready"
          ? "查看毕业要求警告，并与顾问确认高风险学业建议。"
          : "加载或生成学业审核快照。",
      href: "#degree-audit",
      actionLabel: "查看学业审核",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
    {
      ariaLabel: "数据导入审核状态卡片",
      title: "数据导入审核",
      explanation: "staging 导入记录进入正式应用前的人工确认入口。",
      status:
        dataReviewState.status === "ready"
          ? dataReviewState.review.status
          : dataReviewState.status === "idle"
            ? null
            : dataReviewState.status,
      statusLabel:
        dataReviewState.status === "idle" || dataReviewState.status === "empty"
          ? "还没有已确认的导入"
          : undefined,
      nextAction:
        dataReviewState.status === "ready"
          ? "应用已确认的内部记录前，先查看警告。"
          : "预览或加载 staging 导入，然后人工审核记录。",
      href: "#data-import-preview",
      actionLabel: "打开审核",
      advisoryLabels: ["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"],
    },
    {
      ariaLabel: "浏览器插件导入状态卡片",
      title: "浏览器插件导入",
      explanation: "仅从用户已打开页面读取；导入数据先进入 staging。",
      status: "MANUAL_REVIEW_REQUIRED",
      statusLabel: "非官方导入数据",
      nextAction:
        "只检查用户已打开并明确要求检查的页面，然后进入 staging 等待人工审核。",
      href: "#data-import-preview",
      actionLabel: "查看导入",
      advisoryLabels: [
        "NON_OFFICIAL_IMPORTED_DATA",
        "MANUAL_REVIEW_REQUIRED",
        "ADVISORY_ONLY",
      ],
    },
    {
      ariaLabel: "课节监控状态卡片",
      title: "课节监控",
      explanation: "对用户触发导入的课节快照进行仅供参考的比较。",
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
            ? "参考提醒已就绪"
            : sectionMonitoringState.targets.length > 0
              ? "监控目标已就绪"
              : "还没有课节监控目标"
          : undefined,
      nextAction:
        sectionMonitoringState.status === "ready" &&
        sectionMonitoringState.alerts.length > 0
          ? "在官方门户人工核对任何课节变化。"
          : "导入课节搜索数据，并手动选择要监控的课节。",
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
      explanation: "独立于长期规划的课节级课表选项。",
      status:
        scheduleState.status === "ready"
          ? scheduleState.schedule.status
          : scheduleState.status === "idle"
            ? null
            : scheduleState.status,
      statusLabel:
        scheduleState.status === "idle" || scheduleState.status === "empty"
          ? "还没有生成课表方案"
          : undefined,
      nextAction:
        scheduleState.status === "ready"
          ? "比较仅供参考的课表选项和警告。"
          : "从手动选择的课程集合生成课表。",
      href: "#schedule-optimization",
      actionLabel: "生成课表",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
    {
      ariaLabel: "假设规划状态卡片",
      title: "假设规划",
      explanation: "用于比较假设项目变更的方案。",
      status:
        scenarioState.status === "ready"
          ? scenarioState.detail.scenario.status
          : scenarioState.status === "idle"
            ? null
            : scenarioState.status,
      statusLabel:
        scenarioState.status === "idle" || scenarioState.status === "empty"
          ? "还没有假设方案"
          : undefined,
      nextAction:
        scenarioState.status === "ready"
          ? "比较已保存方案的假设和顾问警告。"
          : "从候选项目创建假设方案。",
      href: "#what-if-planning",
      actionLabel: "创建假设方案",
      advisoryLabels: ["ADVISORY_ONLY"],
    },
  ];

  return (
    <section className="product-status" aria-label="产品状态仪表盘">
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
}: {
  selectedCandidateId: string;
  setSelectedCandidateId: (value: string) => void;
  scenarioState: ScenarioState;
  setScenarioState: Dispatch<SetStateAction<ScenarioState>>;
}) {
  const selectedCandidate =
    candidatePrograms.find(
      (candidate) => candidate.id === selectedCandidateId,
    ) ?? candidatePrograms[0];

  async function handleCreateScenario(): Promise<void> {
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
          message: "至少需要两个已保存的假设方案。",
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
              message: "请先创建一个假设方案，再比较已保存结果。",
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
      aria-label="项目探索与假设分析"
    >
      <div className="section-heading">
        <div>
          <h2>项目探索 / 假设分析</h2>
          <p className="subtle">预计额外学分不等同于毕业时间预测。</p>
        </div>
        <p className="notice compact">可能需要顾问确认。</p>
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
        <button type="button" onClick={() => void handleCreateScenario()}>
          创建假设方案
        </button>
        <button type="button" onClick={() => void handleCompareSaved()}>
          比较已保存方案
        </button>
      </div>

      {scenarioState.status === "idle" ? (
        <EmptyState copyKey="NO_WHAT_IF_SCENARIOS" ariaLabel="假设方案空状态" />
      ) : null}

      {scenarioState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在创建假设方案</h2>
          <p>正在运行模拟假设审核和课程分配。</p>
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
    <section className="eligibility-panel" aria-label="课程资格检查">
      <div className="section-heading">
        <div>
          <h2>课程资格</h2>
          <p className="subtle">仅为模拟估算；官方规则请向学校或顾问确认。</p>
        </div>
        <p className="notice compact">课节座位状态与学业资格分开判断。</p>
      </div>

      <div className="scenario-controls">
        <label>
          检查课程
          <select
            value={selectedCourseId}
            onChange={(event) => setSelectedCourseId(event.target.value)}
          >
            {candidateCourses.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {localizeDemoOptionLabel(
                  "candidateCourse",
                  candidate.id,
                  candidate.label,
                )}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => void handleRunEligibility()}>
          检查资格
        </button>
        <button type="button" onClick={() => void handleLoadHistory()}>
          加载历史
        </button>
      </div>

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
          <h2>还没有资格检查</h2>
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
      <section className="summary-grid" aria-label="课程资格摘要">
        <SummaryMetric label="模式" value={statusLabel(result.mode)} />
        <SummaryMetric
          label="结果"
          value={statusLabel(result.overall_result)}
        />
        <SummaryMetric
          label="学业资格结果"
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

      <section className="eligibility-columns">
        <div>
          <h2>原因</h2>
          <ReasonList title="阻塞原因" reasons={result.blocking_reasons} />
          <ReasonList title="条件原因" reasons={result.conditional_reasons} />
          <ReasonList title="许可要求" reasons={result.permissions_required} />
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
            <p className="subtle">当前课程范围没有找到已保存的规则。</p>
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
            <p className="subtle">没有资格警告。</p>
          )}
        </div>
      </section>

      {state.history.length > 1 ? (
        <section className="comparison-table" aria-label="资格检查历史">
          <h2>最近的资格检查</h2>
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
      throw new ApiRequestError("规划器的假设候选项目未配置。");
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
          message: "至少需要两个已保存的学业规划。",
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
              message: "请先创建学业规划，再比较已保存规划。",
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
    <section className="planner-panel" aria-label="长期学业规划">
      <div className="section-heading">
        <div>
          <h2>长期学业规划</h2>
          <p className="subtle">根据剩余毕业要求生成可解释的逐学期模拟规划。</p>
        </div>
        <p className="notice compact">此规划不会注册课程。</p>
      </div>

      <ul className="disclaimer-list" aria-label="学业规划免责声明">
        <li>模拟数据 — 不是官方学校政策。</li>
        <li>此规划不会注册课程，也不会 add/drop/swap/waitlist。</li>
        <li>此规划不会检查每周课表冲突。</li>
        <li>课程开设预测仅为估算。</li>
        <li>可能需要顾问确认。</li>
      </ul>

      <div className="scenario-controls planner-controls">
        <label>
          规划范围
          <select
            value={selectedPlannerScopeId}
            onChange={(event) => setSelectedPlannerScopeId(event.target.value)}
          >
            {plannerScopes.map((scope) => (
              <option key={scope.id} value={scope.id}>
                {localizeDemoOptionLabel("plannerScope", scope.id, scope.label)}
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
        <button type="button" onClick={() => void handleCreatePlan()}>
          创建规划
        </button>
        <button type="button" onClick={() => void handleComparePlans()}>
          比较已保存规划
        </button>
      </div>

      {plannerState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在创建学业规划</h2>
          <p>正在评估学业审核缺口、先修解锁情况和学期容量。</p>
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
          <h2>还没有已保存规划</h2>
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
      <section className="summary-grid" aria-label="学业规划摘要">
        <SummaryMetric label="规划状态" value={statusLabel(plan.status)} />
        <SummaryMetric
          label="规划模式"
          value={statusLabel(plan.planning_mode)}
        />
        <SummaryMetric label="学期数" value={String(plan.terms.length)} />
        <SummaryMetric
          label="已规划课程"
          value={String(plan.planned_courses.length)}
        />
        <SummaryMetric
          label="已规划学分"
          value={formatCredits(String(totalPlannedCredits))}
        />
        <SummaryMetric label="警告" value={String(plan.warnings.length)} />
      </section>

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
                <p>{formatCredits(term.planned_credits)} 已规划学分</p>
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
                  <p className="subtle">此学期没有放入课程。</p>
                )}
              </section>
            );
          })}
        </div>
      </section>

      <section className="planner-columns">
        <div>
          <h2>毕业要求覆盖</h2>
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
            <p className="subtle">还没有生成毕业要求覆盖。</p>
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
                    {formatCredits(comparison.total_planned_credits)} 已规划学分
                    · {comparison.warning_count} 个警告
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
          message: "至少需要两个已保存的课表运行结果。",
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
              message: "请先生成课表，再比较已保存的课表运行结果。",
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
      aria-label="学期课表优化"
    >
      <div className="section-heading">
        <div>
          <h2>学期课表优化</h2>
          <p className="subtle">根据模拟课节数据生成可解释的单学期课表选项。</p>
        </div>
        <p className="notice compact">这不是选课注册。</p>
      </div>

      <ul className="disclaimer-list" aria-label="课表优化免责声明">
        <li>模拟数据 — 不是官方学校政策。</li>
        <li>生成的课表不是选课注册。</li>
        <li>座位可用性与学业资格分开判断。</li>
        <li>此工具不会 add/drop/swap/waitlist。</li>
        <li>此工具不会抢课或占座。</li>
        <li>可能需要顾问确认。</li>
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
          避开周五
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
          偏好在线
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
          更少上课天数
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
          多样性
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
          允许部分方案
        </label>
        <button type="button" onClick={() => void handleCreateSchedule()}>
          生成课表
        </button>
        <button type="button" onClick={() => void handleCompareSchedules()}>
          比较已保存课表
        </button>
      </div>

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
      <section className="summary-grid" aria-label="课表优化摘要">
        <SummaryMetric label="运行状态" value={statusLabel(schedule.status)} />
        <SummaryMetric label="方案数" value={String(schedule.options.length)} />
        <SummaryMetric label="冲突" value={String(schedule.conflicts.length)} />
        <SummaryMetric label="警告" value={String(schedule.warnings.length)} />
        <SummaryMetric
          label="最佳方案学分"
          value={bestOption ? formatCredits(bestOption.total_credits) : "0.0"}
        />
        <SummaryMetric
          label="最佳分数"
          value={bestOption ? Number(bestOption.score).toFixed(2) : "0.00"}
        />
      </section>

      <section className="schedule-options" aria-label="课表方案">
        <h2>课节方案</h2>
        {schedule.options.length === 0 ? (
          <p className="subtle">没有生成可行的课节方案。</p>
        ) : null}
        <div className="schedule-option-grid">
          {schedule.options.map((option) => (
            <section key={option.id} className="schedule-option">
              <div className="term-heading">
                <h3>方案 {option.option_rank}</h3>
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
                多样性 {option.diversity_rank}：{option.difference_summary}
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
                  天数 {Number(option.score_breakdown.days_score).toFixed(2)}
                </span>
                <span>
                  空档 {Number(option.score_breakdown.gap_score).toFixed(2)}
                </span>
                <span>
                  授课形式{" "}
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
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>

      {schedule.options.length >= 2 ? (
        <section className="comparison-table" aria-label="前两个课表方案比较">
          <h2>前两个方案比较</h2>
          <div className="comparison-rows">
            {schedule.options.slice(0, 2).map((option) => (
              <div key={`${option.id}-top-compare`} className="comparison-row">
                <strong>方案 {option.option_rank}</strong>
                <span>
                  分数 {Number(option.total_score).toFixed(2)} -{" "}
                  与前一个方案共享{" "}
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
            <p className="subtle">没有记录到冲突。</p>
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
                    ? "可能需要顾问确认。"
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
                    {comparison.option_count} 个方案 -{" "}
                    {comparison.best_total_credits
                      ? formatCredits(comparison.best_total_credits)
                      : "0.0"}{" "}
                    最佳方案学分 - {comparison.warning_count} 个警告
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

  async function handlePreviewImport(): Promise<void> {
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
          student_profile_id: mockStudentId,
          import_type: selectedSample.importType,
          file_name: selectedSample.fileName,
          file_mime_type: selectedSample.fileMimeType,
          content: selectedSample.content,
          source_type: "STUDENT_PROVIDED",
          source_reference: `Built-in Phase 7A fixture: ${selectedSample.label}`,
        },
        { timeoutMs: 8_000 },
      );
      const [records, candidates, warnings, preview, savedImports] =
        await Promise.all([
          fetchDataImportRecords(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
          fetchDataImportMappingCandidates(apiBaseUrl, run.id, {
            timeoutMs: 5_000,
          }),
          fetchDataImportWarnings(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
          validateDataImport(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
          fetchStudentDataImports(apiBaseUrl, mockStudentId, {
            timeoutMs: 5_000,
          }),
        ]);
      setDataImportState({
        status: "ready",
        run,
        records,
        candidates,
        warnings,
        preview,
        savedImports,
      });
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
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "没有可用的已保存 staging 导入。",
        });
        return;
      }
      const run = savedImports[0];
      const [records, candidates, warnings, preview] = await Promise.all([
        fetchDataImportRecords(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
        fetchDataImportMappingCandidates(apiBaseUrl, run.id, {
          timeoutMs: 5_000,
        }),
        fetchDataImportWarnings(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
        fetchDataImportPreview(apiBaseUrl, run.id, { timeoutMs: 5_000 }),
      ]);
      setDataImportState({
        status: "ready",
        run,
        records,
        candidates,
        warnings,
        preview,
        savedImports,
      });
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
          <p className="subtle">staging 记录与正式学业记录保持分离。</p>
        </div>
        <p className="notice compact">只读 staging 边界。</p>
      </div>

      <ul className="disclaimer-list" aria-label="数据导入免责声明">
        <li>导入预览数据不是官方学校政策。</li>
        <li>不会更改成绩单、目录、课节、注册、座位或候补名单记录。</li>
        <li>导入数据先进入 staging，不直接写入正式记录。</li>
        <li>将导入记录用于高风险学业指导前，需要顾问或学校确认。</li>
      </ul>

      <section
        className="browser-extension-status"
        aria-label="浏览器插件导入状态"
      >
        <div>
          <h2>浏览器插件导入</h2>
          <p className="subtle">用于当前可见页面学业表格的实验性来源。</p>
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
            <strong>实验功能</strong>
            <span>插件提取的数据必须先进入 staging 导入。</span>
          </li>
          <li>
            <strong>人工审核</strong>
            <span>应用前必须先完成人工审核。</span>
          </li>
          <li>
            <strong>边界</strong>
            <span>只检查用户已经登录、主动打开并明确要求检查的页面。</span>
          </li>
          <li>
            <strong>不会操作门户</strong>
            <span>
              不会自动注册课程，不会 add/drop/swap/waitlist，也不会抢课或占座。
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
        <button type="button" onClick={() => void handleLoadSavedImports()}>
          加载已保存导入
        </button>
      </div>

      {dataImportState.status === "idle" ? (
        <EmptyState copyKey="NO_DATA_IMPORTS" ariaLabel="数据导入空状态" />
      ) : null}

      {dataImportState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>正在解析导入</h2>
          <p>正在创建包含映射候选和警告的 staging 预览。</p>
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
  const selectedCandidateCount = state.candidates.filter(
    (candidate) => candidate.is_selected,
  ).length;
  return (
    <div className="data-import-result">
      <section className="summary-grid" aria-label="数据导入预览摘要">
        <SummaryMetric label="导入状态" value={statusLabel(state.run.status)} />
        <SummaryMetric label="记录数" value={String(state.run.record_count)} />
        <SummaryMetric
          label="已映射候选"
          value={String(selectedCandidateCount)}
        />
        <SummaryMetric label="警告" value={String(state.warnings.length)} />
        <SummaryMetric
          label="正式应用"
          value={state.preview.official_application_ready ? "就绪" : "已禁用"}
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
        <section aria-label="数据导入记录">
          <h2>导入记录</h2>
          <div className="comparison-rows">
            {state.records.map((record) => (
              <div key={record.id} className="comparison-row">
                <strong>
                  {payloadValue(record.normalized_payload, "course_code") ??
                    record.raw_label}
                </strong>
                <span>
                  第 {record.row_number} 行 · {statusLabel(record.status)} ·{" "}
                  {payloadValue(record.normalized_payload, "credits") ?? "0.0"}{" "}
                  学分
                </span>
              </div>
            ))}
          </div>
        </section>
        <section aria-label="数据导入映射候选">
          <h2>映射候选</h2>
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
                    ? "需要顾问确认。"
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
          <p className="subtle">来自用户触发的课节搜索导入的仅供参考提醒。</p>
        </div>
        <p className="notice compact">需要人工审核。</p>
      </div>

      <ul className="disclaimer-list" aria-label="课节监控免责声明">
        <li>
          课节监控基于用户触发的导入数据，可能不同于官方门户。请始终在官方注册门户人工核对信息。
        </li>
        <li>
          本系统不会注册课程、drop、swap、waitlist、提交表单，也不会执行任何门户操作。
        </li>
        <li>本系统不会抢课或占座；所有提醒仅供参考。</li>
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
          <p>正在获取监控课节和参考提醒。</p>
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
          <h2>还没有课节提醒</h2>
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
                      {formatDisplayTimestamp(
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

          <section className="comparison-table" aria-label="参考提醒">
            <h2>参考提醒</h2>
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
                        {alert.field_name ?? "未知课节变化"}：{" "}
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

          <section className="comparison-table" aria-label="人工注册检查清单">
            <h2>人工检查清单</h2>
            <ul className="compact-list">
              <li>手动打开官方注册门户。</li>
              <li>手动核对课节状态。</li>
              <li>手动确认先修、限制和 hold。</li>
              <li>如确实合适，请通过官方门户手动注册。</li>
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
  const [gradeEdits, setGradeEdits] = useState<Record<string, string>>({});

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
        message: "创建人工审核前，请先预览或加载 staging 导入。",
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
        message: "NEXT_PUBLIC_API_BASE_URL 未配置。",
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
          message: "该模拟学生没有可用的数据导入审核。",
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
    <section className="data-review-panel" aria-label="数据审核与确认">
      <div className="section-heading">
        <div>
          <h2>数据审核与确认</h2>
          <p className="subtle">已确认记录只应用到内部规划数据。</p>
        </div>
        <p className="notice compact">必须明确点击应用。</p>
      </div>

      <ul className="disclaimer-list" aria-label="数据审核免责声明">
        <li>审核决定不会创建官方成绩单记录。</li>
        <li>试运行只显示拟写入内容，不会创建正式领域记录。</li>
        <li>已拒绝、暂缓、重复和顾问审核记录会被记录下来。</li>
      </ul>
      <AdvisoryLabels keys={["MANUAL_REVIEW_REQUIRED", "ADVISORY_ONLY"]} />

      <div className="scenario-controls data-import-controls">
        <button type="button" onClick={() => void handleCreateReview()}>
          创建人工审核
        </button>
        <button type="button" onClick={() => void handleLoadLatestReviews()}>
          加载最新审核
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
          <section className="summary-grid" aria-label="数据审核摘要">
            <SummaryMetric
              label="审核状态"
              value={statusLabel(dataReviewState.review.status)}
            />
            <SummaryMetric
              label="记录数"
              value={String(dataReviewState.records.length)}
            />
            <SummaryMetric
              label="警告"
              value={String(dataReviewState.warnings.length)}
            />
            <SummaryMetric
              label="已应用记录"
              value={String(dataReviewState.applications.length)}
            />
            <SummaryMetric
              label="最近结果"
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
            <h2>记录决定</h2>
            <div className="comparison-rows">
              {dataReviewState.records.map((recordReview) => {
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
                        ? "已标记顾问审核"
                        : "学生可审核"}
                    </span>
                    <span>
                      {recordReview.selected_mapping_candidate?.explanation ??
                        "没有选中的映射候选。"}
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
                        顾问审核
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
                        ? "需要顾问确认。"
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
    return "会议时间不可用";
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
      <section className="summary-grid" aria-label="假设方案摘要">
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
            <p className="subtle">没有可用的课程分配。</p>
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
