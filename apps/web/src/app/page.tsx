"use client";

import {
  ApiRequestError,
  ApiResponseSchemaError,
  createDegreeAudit,
  fetchDegreeAuditRequirements,
  fetchHealth,
  fetchLatestDegreeAudit,
  type DegreeAuditRun,
  type HealthResponse,
  type RequirementEvaluation,
} from "@sapsos/shared";
import { useEffect, useState } from "react";

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

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const mockStudentId = "74874476-4024-5e2d-807a-fbb4ab620249";
const mockProgramVersionId = "f65bee76-6061-515f-a3df-cdf5567514af";

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
