import { useEffect, useRef, useState } from "react";
import {
  ApiResponseSchemaError,
  fetchSectionMonitorAlerts,
  fetchSectionMonitorTargets,
  type SectionMonitorAlert,
  type SectionMonitorTarget,
} from "@sapsos/shared";
import { createWorkflowRequestGuard } from "./workflow-module-guards";

export type SectionMonitoringWorkflowState =
  | { status: "loading" }
  | {
      status: "ready";
      targets: SectionMonitorTarget[];
      alerts: SectionMonitorAlert[];
    }
  | { status: "empty"; message: string }
  | { status: "offline"; message: string }
  | { status: "failed" | "schema-error"; message: string };

export function useSectionMonitoringWorkflow(
  apiBaseUrl: string | undefined,
  studentId: string | undefined,
): SectionMonitoringWorkflowState {
  const [state, setState] = useState<SectionMonitoringWorkflowState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : { status: "offline", message: "NEXT_PUBLIC_API_BASE_URL 未配置。" },
  );
  const guardRef = useRef(createWorkflowRequestGuard());

  useEffect(() => {
    const guard = guardRef.current;
    const requestId = guard.begin();
    if (!apiBaseUrl) {
      return () => {
        guard.begin();
      };
    }
    if (!studentId) {
      queueMicrotask(() => {
        if (guard.isCurrent(requestId)) {
          setState({
            status: "empty",
            message: "尚未导入学生数据或启用演示工作流。",
          });
        }
      });
      return () => {
        guard.begin();
      };
    }
    void Promise.all([
      fetchSectionMonitorTargets(apiBaseUrl, studentId, { timeoutMs: 5_000 }),
      fetchSectionMonitorAlerts(apiBaseUrl, studentId, { timeoutMs: 5_000 }),
    ])
      .then(([targets, alerts]) => {
        if (guard.isCurrent(requestId)) {
          setState({ status: "ready", targets, alerts });
        }
      })
      .catch((error: unknown) => {
        if (!guard.isCurrent(requestId)) return;
        setState({
          status:
            error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
          message:
            error instanceof Error ? error.message : "无法加载监控状态。",
        });
      });
    return () => {
      guard.begin();
    };
  }, [apiBaseUrl, studentId]);

  return state;
}
