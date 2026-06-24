"use client";

import {
  ApiRequestError,
  ApiResponseSchemaError,
  compareAcademicScenarios,
  createAcademicScenario,
  createDegreeAudit,
  fetchAcademicScenarioAllocations,
  fetchAcademicScenarioAudits,
  fetchAcademicScenarioComparison,
  fetchAcademicScenarioPrograms,
  fetchAcademicScenarioWarnings,
  fetchDegreeAuditRequirements,
  fetchHealth,
  fetchLatestDegreeAudit,
  fetchStudentAcademicScenarios,
  type AcademicScenario,
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

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const mockStudentId = "74874476-4024-5e2d-807a-fbb4ab620249";
const mockProgramVersionId = "f65bee76-6061-515f-a3df-cdf5567514af";
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
