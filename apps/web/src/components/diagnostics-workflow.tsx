"use client";

import {
  downloadLocalDiagnosticsBundle,
  fetchLocalDiagnostics,
  type DiagnosticsSnapshot,
} from "@sapsos/shared";
import { useCallback, useEffect, useRef, useState } from "react";

type SnapshotState =
  | {
      status: "idle" | "loading";
      snapshot: DiagnosticsSnapshot | null;
      stale: boolean;
    }
  | { status: "ready"; snapshot: DiagnosticsSnapshot; stale: boolean }
  | { status: "failed"; snapshot: DiagnosticsSnapshot | null; stale: boolean };

type ComponentKey =
  | "runtime_health"
  | "api_health"
  | "database_health"
  | "schema_status"
  | "restore_status"
  | "pairing_status"
  | "recent_startup_status";

const COMPONENTS: readonly { key: ComponentKey; title: string }[] = [
  { key: "runtime_health", title: "Application & Runtime" },
  { key: "api_health", title: "Local API" },
  { key: "database_health", title: "Local Database" },
  { key: "schema_status", title: "Schema & Migration" },
  { key: "restore_status", title: "Backup & Restore" },
  { key: "pairing_status", title: "Browser Extension Pairing" },
  { key: "recent_startup_status", title: "Recent Startup Status" },
];

const OVERALL_COPY: Record<
  DiagnosticsSnapshot["overall_status"],
  {
    title: string;
    explanation: string;
    impact: string;
    nextStep: string;
  }
> = {
  HEALTHY: {
    title: "Diagnostics look healthy",
    explanation: "The local checks completed without a reported problem.",
    impact: "Normal local use is not currently blocked by diagnostics.",
    nextStep: "Continue using the application; refresh if something changes.",
  },
  DEGRADED: {
    title: "Some checks need attention",
    explanation:
      "The application can usually continue, but one or more components reported a warning.",
    impact: "Normal use may continue with limitations.",
    nextStep:
      "Review the warning cards and create a manual backup before recovery work.",
  },
  ACTION_REQUIRED: {
    title: "A user action is required",
    explanation:
      "A component needs review before a related recovery workflow can continue.",
    impact: "Some actions may be unavailable until you review the issue.",
    nextStep:
      "Follow the read-only guidance, then use the existing controlled workflow if needed.",
  },
  BLOCKED: {
    title: "A blocking condition was detected",
    explanation:
      "At least one local component reported a condition that prevents safe continuation.",
    impact: "Related application actions may be blocked.",
    nextStep:
      "Do not make data-changing changes here; close and reopen the application or review Backup/Restore.",
  },
  UNKNOWN: {
    title: "Status could not be determined",
    explanation: "The application could not determine this component’s status.",
    impact:
      "Do not treat this result as healthy or as confirmation of school data.",
    nextStep:
      "Refresh once, then close and reopen the application if the uncertainty remains.",
  },
};

const CODE_COPY: Record<
  string,
  { title: string; action: string; restart: boolean; avoidChanges: boolean }
> = {
  RUNTIME_MANIFEST_MISSING: {
    title: "Application runtime details are unavailable",
    action: "Close and reopen the application.",
    restart: true,
    avoidChanges: false,
  },
  RUNTIME_MANIFEST_STALE: {
    title: "The application runtime may be stale",
    action: "Close and reopen the application before continuing.",
    restart: true,
    avoidChanges: true,
  },
  API_NOT_READY: {
    title: "The local API is not ready",
    action: "Close and reopen the application, then refresh diagnostics.",
    restart: true,
    avoidChanges: false,
  },
  DATABASE_INTEGRITY_FAILED: {
    title: "Database integrity needs review",
    action: "Avoid data-changing actions and review Backup/Restore.",
    restart: false,
    avoidChanges: true,
  },
  FOREIGN_KEY_CHECK_FAILED: {
    title: "Database relationships need review",
    action:
      "Avoid data-changing actions and contact an advisor or support person.",
    restart: false,
    avoidChanges: true,
  },
  SCHEMA_UPGRADE_REQUIRED: {
    title: "A schema upgrade is required",
    action:
      "Close and reopen the application, then follow the normal recovery flow.",
    restart: true,
    avoidChanges: true,
  },
  SCHEMA_NEWER_THAN_APP: {
    title: "The database is newer than this application",
    action:
      "Do not modify data; use the matching application version or seek support.",
    restart: false,
    avoidChanges: true,
  },
  MIGRATION_INTERRUPTED: {
    title: "A schema change was interrupted",
    action:
      "Close and reopen the application before taking any recovery action.",
    restart: true,
    avoidChanges: true,
  },
  RESTORE_PENDING: {
    title: "A restore is waiting for review",
    action: "Open Backup/Restore to review the pending restore.",
    restart: false,
    avoidChanges: true,
  },
  RESTORE_ROLLED_BACK: {
    title: "The last restore was rolled back",
    action: "Review Backup/Restore before trying another data-changing action.",
    restart: false,
    avoidChanges: true,
  },
  PAIRING_REQUIRED: {
    title: "The browser extension needs pairing",
    action:
      "Re-pair the browser extension through the existing pairing workflow.",
    restart: false,
    avoidChanges: false,
  },
  PAIRING_INVALID: {
    title: "Browser extension pairing needs review",
    action:
      "Re-pair the browser extension through the existing pairing workflow.",
    restart: false,
    avoidChanges: false,
  },
  STARTUP_LOCK_CONFLICT: {
    title: "Another application start may be in progress",
    action: "Close and reopen the application after the other start finishes.",
    restart: true,
    avoidChanges: false,
  },
  RUNTIME_MANIFEST_UNAVAILABLE: {
    title: "Application runtime details are unavailable",
    action: "Close and reopen the application.",
    restart: true,
    avoidChanges: false,
  },
  RUNTIME_MANIFEST_INVALID: {
    title: "Application runtime details could not be read",
    action: "Close and reopen the application before continuing.",
    restart: true,
    avoidChanges: true,
  },
  DATABASE_MISSING: {
    title: "The local database is unavailable",
    action:
      "Avoid data-changing actions and review the normal recovery workflow.",
    restart: false,
    avoidChanges: true,
  },
  DATABASE_UNREADABLE: {
    title: "The local database could not be read",
    action: "Avoid data-changing actions and review Backup/Restore.",
    restart: false,
    avoidChanges: true,
  },
  MIGRATION_STATE_UNAVAILABLE: {
    title: "Schema status could not be determined",
    action: "Close and reopen the application; do not start a migration here.",
    restart: true,
    avoidChanges: true,
  },
  RESTORE_STATE_REQUIRES_REVIEW: {
    title: "Restore state requires review",
    action: "Open Backup/Restore to review the pending state.",
    restart: false,
    avoidChanges: true,
  },
  PAIRING_RECORD_INVALID: {
    title: "Browser extension pairing needs review",
    action:
      "Re-pair the browser extension through the existing pairing workflow.",
    restart: false,
    avoidChanges: false,
  },
};

function safeCode(code: string | null): string {
  return code && /^[A-Za-z0-9_.-]{1,80}$/.test(code)
    ? code.toUpperCase()
    : "UNKNOWN_STATUS";
}

function statusText(status: string): string {
  return status === "HEALTHY"
    ? "Healthy"
    : status === "DEGRADED"
      ? "Warning"
      : status === "ACTION_REQUIRED"
        ? "Action required"
        : status === "BLOCKED"
          ? "Blocked"
          : "Unknown";
}

function formatCheckedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Time unavailable"
    : date.toLocaleString();
}

function guidanceFor(code: string | null) {
  return (
    CODE_COPY[safeCode(code)] ?? {
      title: "The application could not determine this component’s status.",
      action:
        "Refresh diagnostics once; if the result remains unknown, close and reopen the application.",
      restart: true,
      avoidChanges: true,
    }
  );
}

function statusTone(status: string): string {
  return status === "HEALTHY"
    ? "healthy"
    : status === "DEGRADED"
      ? "warning"
      : "blocking";
}

function safeTechnicalDetails(value: Record<string, unknown>): string[] {
  return Object.entries(value)
    .filter(
      ([key, entry]) =>
        key !== "summary" &&
        (typeof entry === "string" ||
          typeof entry === "boolean" ||
          typeof entry === "number" ||
          entry === null),
    )
    .map(
      ([key, entry]) => `${key}: ${entry === null ? "unknown" : String(entry)}`,
    )
    .slice(0, 12);
}

function DiagnosticsCard({
  title,
  value,
  checkedAt,
}: {
  title: string;
  value: Record<string, unknown>;
  checkedAt: string;
}) {
  const status = typeof value.status === "string" ? value.status : "UNKNOWN";
  const reasonCode =
    typeof value.reason_code === "string" ? value.reason_code : null;
  const guidance = guidanceFor(reasonCode);
  return (
    <article
      className={`diagnostics-card ${statusTone(status)}`}
      aria-label={`${title}: ${statusText(status)}`}
    >
      <div className="diagnostics-card-heading">
        <h3>{title}</h3>
        <span className="diagnostics-status" role="status">
          {statusText(status)}
        </span>
      </div>
      <p>{guidance.title}</p>
      <p className="subtle">Last checked: {formatCheckedAt(checkedAt)}</p>
      {status !== "HEALTHY" ? (
        <p className="advisor-note">Next step: {guidance.action}</p>
      ) : null}
      {status !== "HEALTHY" ? (
        <p className="subtle">
          Restart may help: {guidance.restart ? "Yes" : "No"}
        </p>
      ) : null}
      {reasonCode ? (
        <p className="subtle">Warning/blocking code: {safeCode(reasonCode)}</p>
      ) : null}
      {guidance.avoidChanges ? (
        <p className="subtle">
          Avoid data-changing actions until this is reviewed.
        </p>
      ) : null}
      <details>
        <summary>Technical details</summary>
        <ul className="compact-list">
          {safeTechnicalDetails(value).map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
      </details>
    </article>
  );
}

export function DiagnosticsWorkflow({
  apiBaseUrl,
  active,
}: {
  apiBaseUrl: string | undefined;
  active: boolean;
}) {
  const [state, setState] = useState<SnapshotState>({
    status: "idle",
    snapshot: null,
    stale: false,
  });
  const [exportState, setExportState] = useState<
    "idle" | "loading" | "success" | "failed"
  >("idle");
  const requestInFlight = useRef(false);
  const requestSequence = useRef(0);
  const loaded = useRef(false);

  const refresh = useCallback(async (): Promise<void> => {
    if (!apiBaseUrl || requestInFlight.current) return;
    requestInFlight.current = true;
    const sequence = ++requestSequence.current;
    setState((current) => ({
      status: "loading",
      snapshot: current.snapshot,
      stale: Boolean(current.snapshot),
    }));
    try {
      const snapshot = await fetchLocalDiagnostics(apiBaseUrl, {
        timeoutMs: 10_000,
      });
      if (sequence !== requestSequence.current) return;
      loaded.current = true;
      setState({ status: "ready", snapshot, stale: false });
    } catch {
      if (sequence !== requestSequence.current) return;
      setState((current) => ({
        status: "failed",
        snapshot: current.snapshot,
        stale: true,
      }));
    } finally {
      if (sequence === requestSequence.current) requestInFlight.current = false;
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    if (active && !loaded.current) void refresh();
    return () => {
      requestSequence.current += 1;
      requestInFlight.current = false;
    };
  }, [active, refresh]);

  async function exportBundle(): Promise<void> {
    if (!apiBaseUrl || exportState === "loading") return;
    setExportState("loading");
    try {
      const downloaded = await downloadLocalDiagnosticsBundle(apiBaseUrl, {
        timeoutMs: 30_000,
      });
      const url = URL.createObjectURL(downloaded.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = downloaded.filename ?? "sapsos-diagnostics.zip";
      link.click();
      URL.revokeObjectURL(url);
      setExportState("success");
    } catch {
      setExportState("failed");
    }
  }

  const snapshot = state.snapshot;
  const overall = snapshot
    ? OVERALL_COPY[snapshot.overall_status]
    : OVERALL_COPY.UNKNOWN;
  return (
    <section
      id="diagnostics"
      className="diagnostics-workflow"
      aria-labelledby="diagnostics-title"
    >
      <header className="workflow-page-header">
        <h1 id="diagnostics-title">Diagnostics</h1>
        <p className="subtle">
          Read-only local health checks and privacy-safe recovery guidance.
        </p>
      </header>
      <div className="diagnostics-actions">
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={!apiBaseUrl || state.status === "loading"}
        >
          {state.status === "loading"
            ? "Checking diagnostics…"
            : "Refresh diagnostics"}
        </button>
        <button
          type="button"
          onClick={() => void exportBundle()}
          disabled={!apiBaseUrl || exportState === "loading"}
        >
          {exportState === "loading"
            ? "Generating bundle…"
            : "Export diagnostics bundle"}
        </button>
      </div>
      <p className="subtle" aria-live="polite">
        {state.status === "loading"
          ? "Diagnostics are being checked."
          : state.status === "failed"
            ? "The latest check failed; the previous snapshot is shown as stale."
            : exportState === "success"
              ? "Bundle generated locally. Check it before sharing."
              : exportState === "failed"
                ? "The bundle could not be generated. No upload was attempted."
                : "No background polling or automatic repair is performed."}
      </p>
      <section
        className={`diagnostics-summary ${statusTone(snapshot?.overall_status ?? "UNKNOWN")}`}
        role="status"
        aria-label={`Overall diagnostics status: ${snapshot?.overall_status ?? "UNKNOWN"}`}
      >
        <h2>{overall.title}</h2>
        <p>{overall.explanation}</p>
        <p>
          <strong>Impact:</strong> {overall.impact}
        </p>
        <p>
          <strong>Next step:</strong> {overall.nextStep}
        </p>
        {state.stale ? (
          <p className="advisor-note">
            This is a stale snapshot from the last successful check.
          </p>
        ) : null}
      </section>
      {snapshot ? (
        <div className="diagnostics-card-grid">
          {COMPONENTS.map(({ key, title }) => (
            <DiagnosticsCard
              key={key}
              title={title}
              value={snapshot[key] as unknown as Record<string, unknown>}
              checkedAt={snapshot.generated_at}
            />
          ))}
        </div>
      ) : (
        <p className="state-panel">
          Diagnostics are unavailable until the local API responds. No repair or
          migration was started.
        </p>
      )}
      {snapshot?.warnings.length ? (
        <section className="warning-panel" aria-label="Diagnostics warnings">
          <h2>Warnings</h2>
          <ul>
            {snapshot.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
