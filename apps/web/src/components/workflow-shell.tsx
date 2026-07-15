"use client";

import { useSyncExternalStore } from "react";
import {
  workflowDefinitions,
  workflowHref,
  workflowIdFromHash,
  type WorkflowId,
} from "../lib/workflow-navigation";

function subscribeToHashChanges(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function getBrowserHash(): string {
  return window.location.hash;
}

function getServerHash(): string {
  return "";
}

export function useActiveWorkflow(): WorkflowId {
  const hash = useSyncExternalStore(
    subscribeToHashChanges,
    getBrowserHash,
    getServerHash,
  );
  return workflowIdFromHash(hash);
}

export function WorkflowPageHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <header className="workflow-page-header">
      <h2>{title}</h2>
      {description ? <p className="subtle">{description}</p> : null}
    </header>
  );
}

export function WorkflowStatus({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "neutral" | "ok" | "warn";
}) {
  return <span className={`workflow-status ${tone}`}>{label}</span>;
}

export function WorkflowShell({
  activeWorkflow,
  apiStatus,
  sourceLabel,
  children,
}: {
  activeWorkflow: WorkflowId;
  apiStatus: string;
  sourceLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="app-shell-header">
        <div>
          <p className="app-shell-title">智能学业规划</p>
          <p className="app-shell-subtitle">本地优先、可解释的学业进度工作区</p>
        </div>
        <div className="app-shell-context" aria-label="当前应用上下文">
          <WorkflowStatus
            label={`连接状态：${apiStatus.replace(/^API\s*/, "")}`}
          />
          <span className="app-shell-context-label">当前学生：演示学生</span>
          <span className="app-shell-context-label">数据：{sourceLabel}</span>
        </div>
      </header>
      <nav className="workflow-nav" aria-label="主要工作流">
        <ul>
          {workflowDefinitions.map((workflow) => (
            <li key={workflow.id}>
              <a
                href={workflowHref(workflow)}
                aria-current={
                  activeWorkflow === workflow.id ? "page" : undefined
                }
                className={
                  activeWorkflow === workflow.id
                    ? "workflow-link active"
                    : "workflow-link"
                }
              >
                {workflow.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <div className="app-shell-content">{children}</div>
    </div>
  );
}
