"use client";

import {
  ApiRequestError,
  ApiResponseSchemaError,
  compareAcademicPlans,
  compareAcademicScenarios,
  createAcademicPlan,
  createAcademicScenario,
  createCourseEligibilityCheck,
  createDegreeAudit,
  fetchAcademicScenarioAllocations,
  fetchAcademicScenarioAudits,
  fetchAcademicScenarioComparison,
  fetchAcademicScenarioPrograms,
  fetchAcademicScenarioWarnings,
  fetchDegreeAuditRequirements,
  fetchHealth,
  fetchLatestDegreeAudit,
  fetchStudentAcademicPlans,
  fetchStudentEligibilityChecks,
  fetchStudentAcademicScenarios,
  type AcademicPlanComparison,
  type AcademicPlanDetail,
  type AcademicPlanRun,
  type AcademicScenario,
  type CourseEligibilityCheck,
  type DegreeAuditRun,
  type HealthResponse,
  type RequirementEvaluation,
  type ScenarioComparisonSnapshot,
  type ScenarioCourseAllocation,
  type ScenarioProgram,
  type ScenarioProgramAudit,
  type ScenarioWarning,
} from "@sapsos/shared";
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

type HealthState =
  | { status: "loading" }
  | { status: "online"; payload: HealthResponse }
  | { status: "offline"; message: string };

type AuditState =
  | { status: "loading" }
  | { status: "empty"; message: string }
  | { status: "ready"; audit: DegreeAuditRun; requirements: RequirementEvaluation[] }
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
  | { status: "ready"; result: CourseEligibilityCheck; history: CourseEligibilityCheck[] }
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

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
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

function describeHealthError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected health response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown API health error";
}

function describeAuditError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected degree audit response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown degree audit error";
}

function describeScenarioError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected academic scenario response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown what-if scenario error";
}

function describeEligibilityError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected course eligibility response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown course eligibility error";
}

function describePlannerError(error: unknown): string {
  if (error instanceof ApiResponseSchemaError) {
    return "API returned an unexpected academic plan response shape.";
  }
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown academic planner error";
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiRequestError && error.message.includes("status 404");
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

export default function Home() {
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
  const [selectedCandidateId, setSelectedCandidateId] = useState(candidatePrograms[0].id);
  const [scenarioState, setScenarioState] = useState<ScenarioState>({ status: "idle" });
  const [selectedCourseId, setSelectedCourseId] = useState(candidateCourses[0].id);
  const [eligibilityState, setEligibilityState] = useState<EligibilityState>(() =>
    apiBaseUrl
      ? { status: "idle" }
      : {
          status: "offline",
          message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
        },
  );
  const [selectedPlannerScopeId, setSelectedPlannerScopeId] = useState(plannerScopes[0].id);
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

        const requirements = await fetchDegreeAuditRequirements(baseUrl, audit.id, {
          timeoutMs: 5_000,
        });
        if (!cancelled) {
          setAuditState(
            requirements.length === 0
              ? {
                  status: "empty",
                  message: "No degree audit snapshot results are available yet.",
                }
              : { status: "ready", audit, requirements },
          );
        }
      } catch (error: unknown) {
        if (!cancelled) {
          const message = describeAuditError(error);
          setAuditState({ status: "failed", message });
          if (health.status !== "online") {
            setHealth({ status: "offline", message: describeHealthError(error) });
          }
        }
      }
    }

    void loadDegreeProgress(apiBaseUrl);

    return () => {
      cancelled = true;
    };
  }, [health.status]);

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
              ? "API checking"
              : health.status === "online"
                ? "API connected"
                : "API unavailable"}
          </p>
          <p className="notice compact">Mock data — not official university policy.</p>
        </div>

        <h1>Degree Progress</h1>
        <p className="subtle">
          Advisor confirmation is required for high-impact academic guidance.
        </p>

        {auditState.status === "ready" ? (
          <DegreeProgress audit={auditState.audit} requirements={auditState.requirements} />
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
}: {
  audit: DegreeAuditRun;
  requirements: RequirementEvaluation[];
}) {
  return (
    <>
      <section className="summary-grid" aria-label="Degree audit summary">
        <SummaryMetric label="Program" value="Mock BS Finance" />
        <SummaryMetric label="Catalog Year" value="2024" />
        <SummaryMetric label="Audit Mode" value={audit.calculation_mode} />
        <SummaryMetric
          label="Completed Credits"
          value={formatCredits(audit.completed_credits)}
        />
        <SummaryMetric
          label="In-Progress Credits"
          value={formatCredits(audit.in_progress_credits)}
        />
        <SummaryMetric
          label="Planned Credits"
          value={formatCredits(audit.planned_credits)}
        />
        <SummaryMetric
          label="Remaining Credits"
          value={formatCredits(audit.remaining_credits)}
        />
        <SummaryMetric
          label="Completion"
          value={`${Number(audit.completion_percentage).toFixed(2)}%`}
        />
      </section>

      <section className="requirement-tree" aria-label="Requirement Tree">
        <h2>Requirement Tree</h2>
        {requirements.map((requirement) => (
          <details key={requirement.id} className="requirement-row">
            <summary>
              <span>{requirement.requirement_name}</span>
              <span className={`status-pill ${requirement.status.toLowerCase()}`}>
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
                      <strong>{application.course_code ?? application.application_type}</strong>
                      <span>
                        {statusLabel(application.application_type)} ·{" "}
                        {formatCredits(application.credit_amount)} credits
                        {application.grade ? ` · grade ${application.grade}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {requirement.warnings.some(
                (warning) => warning.requires_advisor_confirmation,
              ) ? (
                <p className="advisor-note">Advisor confirmation required.</p>
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
    candidatePrograms.find((candidate) => candidate.id === selectedCandidateId) ??
    candidatePrograms[0];

  async function handleCreateScenario(): Promise<void> {
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
        setScenarioState({ status: "empty", message: "At least two saved scenarios are needed." });
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
    <section className="what-if-panel" aria-label="Explore Programs What-if Analysis">
      <div className="section-heading">
        <div>
          <h2>Explore Programs / What-if Analysis</h2>
          <p className="subtle">Estimated additional credits do not predict graduation timing.</p>
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
        <button type="button" onClick={() => void handleCreateScenario()}>
          Create scenario
        </button>
        <button type="button" onClick={() => void handleCompareSaved()}>
          Compare saved scenarios
        </button>
      </div>

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
        <section className="state-panel" aria-live="polite">
          <h2>No comparison yet</h2>
          <p>{scenarioState.message}</p>
        </section>
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
      const history = await fetchStudentEligibilityChecks(apiBaseUrl, mockStudentId, {
        timeoutMs: 5_000,
      });
      setEligibilityState({ status: "ready", result, history });
    } catch (error: unknown) {
      setEligibilityState({
        status: error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
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
      const history = await fetchStudentEligibilityChecks(apiBaseUrl, mockStudentId, {
        timeoutMs: 5_000,
      });
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
        status: error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describeEligibilityError(error),
      });
    }
  }

  return (
    <section className="eligibility-panel" aria-label="Course Eligibility Checker">
      <div className="section-heading">
        <div>
          <h2>Course Eligibility</h2>
          <p className="subtle">
            Mock estimate only; confirm official rules with the school or an advisor.
          </p>
        </div>
        <p className="notice compact">Section seats are separate from academic eligibility.</p>
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
        <SummaryMetric label="Result" value={statusLabel(result.overall_result)} />
        <SummaryMetric
          label="Academic Result"
          value={statusLabel(result.academic_eligibility_result)}
        />
        <SummaryMetric
          label="Section Status"
          value={availability ? statusLabel(availability.section_status) : "Course only"}
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
        <SummaryMetric label="Warnings" value={String(result.warnings.length)} />
      </section>

      <section className="eligibility-columns">
        <div>
          <h2>Reasons</h2>
          <ReasonList
            title="Blocking"
            reasons={result.blocking_reasons}
          />
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
            <p className="subtle">No stored rules were found for this course scope.</p>
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
                  {statusLabel(item.mode)} · {new Date(item.created_at).toLocaleString()}
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
          <li key={`${title}-${reason.reason_code}-${reason.course_rule_expression_id ?? ""}`}>
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
    plannerScopes.find((scope) => scope.id === selectedPlannerScopeId) ?? plannerScopes[0];

  async function createScenarioForScope(scope: PlannerScope): Promise<string | null> {
    if (scope.planningMode === "CURRENT_PROGRAM") {
      return null;
    }

    const candidate = candidatePrograms.find(
      (program) => program.id === scope.candidateProgramId,
    );
    if (!candidate) {
      throw new ApiRequestError("Planner what-if candidate program is not configured.");
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
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    setPlannerState({ status: "loading" });
    try {
      const academicPlanScenarioId = await createScenarioForScope(selectedScope);
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
        status: error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
        message: describePlannerError(error),
      });
    }
  }

  async function handleComparePlans(): Promise<void> {
    if (!apiBaseUrl) {
      setPlannerState({
        status: "offline",
        message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      });
      return;
    }
    try {
      const savedPlans = await fetchStudentAcademicPlans(apiBaseUrl, mockStudentId, {
        timeoutMs: 5_000,
      });
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
        status: error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
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
            onChange={(event) => setSelectedPlannerStartTermId(event.target.value)}
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
            onChange={(event) => setPreferredCredits(Number(event.target.value))}
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
        <button type="button" onClick={() => void handleCreatePlan()}>
          Create plan
        </button>
        <button type="button" onClick={() => void handleComparePlans()}>
          Compare saved plans
        </button>
      </div>

      {plannerState.status === "loading" ? (
        <section className="state-panel" aria-live="polite">
          <h2>Creating academic plan</h2>
          <p>Evaluating degree audit gaps, prerequisite unlocks, and term capacity.</p>
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
        <SummaryMetric label="Planning Mode" value={statusLabel(plan.planning_mode)} />
        <SummaryMetric label="Terms" value={String(plan.terms.length)} />
        <SummaryMetric label="Planned Courses" value={String(plan.planned_courses.length)} />
        <SummaryMetric
          label="Planned Credits"
          value={formatCredits(String(totalPlannedCredits))}
        />
        <SummaryMetric label="Warnings" value={String(plan.warnings.length)} />
      </section>

      <section className="planner-term-grid" aria-label="Term-by-term academic plan">
        <h2>Term-by-Term Plan</h2>
        {plan.planned_courses.length === 0 ? (
          <p className="subtle">No planner courses were generated for the selected settings.</p>
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
                          {course.course_title} · {formatCredits(course.credits)} credits
                        </span>
                        <span>
                          {statusLabel(course.planning_status)} · {course.reason_code}
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
                    {statusLabel(coverage.coverage_type)} · {formatCredits(coverage.credits)}
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
        <section className="comparison-table" aria-label="Saved academic plan comparison">
          <h2>Saved Plan Comparison</h2>
          <div className="comparison-rows">
            {state.comparisons.map((comparison) => {
              const savedPlan = state.savedPlans.find(
                (item) => item.id === comparison.academic_plan_run_id,
              );
              return (
                <div key={comparison.academic_plan_run_id} className="comparison-row">
                  <strong>{savedPlan?.planning_mode ?? comparison.academic_plan_run_id}</strong>
                  <span>
                    {formatCredits(comparison.total_planned_credits)} planned credits ·{" "}
                    {comparison.warning_count} warnings
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

async function loadScenarioDetail(
  baseUrl: string,
  scenario: AcademicScenario,
): Promise<ScenarioDetail> {
  const [programs, audits, allocations, warnings, comparison] = await Promise.all([
    fetchAcademicScenarioPrograms(baseUrl, scenario.id, { timeoutMs: 5_000 }),
    fetchAcademicScenarioAudits(baseUrl, scenario.id, { timeoutMs: 5_000 }),
    fetchAcademicScenarioAllocations(baseUrl, scenario.id, { timeoutMs: 5_000 }),
    fetchAcademicScenarioWarnings(baseUrl, scenario.id, { timeoutMs: 5_000 }),
    fetchAcademicScenarioComparison(baseUrl, scenario.id, { timeoutMs: 5_000 }),
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
        <SummaryMetric label="Scenario Status" value={statusLabel(detail.scenario.status)} />
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
                  <strong>{allocation.course_code ?? allocation.reason_code}</strong>
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
        <section className="comparison-table" aria-label="Saved scenario comparison">
          <h2>Saved Scenario Comparison</h2>
          <div className="comparison-rows">
            {state.comparisons.map((comparison) => {
              const scenario = state.savedScenarios.find(
                (item) => item.id === comparison.academic_plan_scenario_id,
              );
              return (
                <div key={comparison.academic_plan_scenario_id} className="comparison-row">
                  <strong>{scenario?.name ?? comparison.academic_plan_scenario_id}</strong>
                  <span>
                    {formatCredits(comparison.estimated_additional_credits)} estimated
                    additional credits
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
