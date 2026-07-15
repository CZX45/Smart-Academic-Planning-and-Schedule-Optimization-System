import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  ApiResponseSchemaError,
  fetchActiveCourseStateSnapshot,
  type CourseStateSnapshotDetail,
} from "@sapsos/shared";
import { createWorkflowRequestGuard } from "./workflow-module-guards";

export type CourseStateWorkflowState =
  | { status: "loading" }
  | { status: "ready"; detail: CourseStateSnapshotDetail }
  | { status: "empty" | "offline" | "failed" | "schema-error"; message: string };

export function useCourseStateWorkflow(
  apiBaseUrl: string | undefined,
  studentId: string,
): readonly [CourseStateWorkflowState, Dispatch<SetStateAction<CourseStateWorkflowState>>] {
  const [state, setState] = useState<CourseStateWorkflowState>(() =>
    apiBaseUrl
      ? { status: "loading" }
      : { status: "offline", message: "NEXT_PUBLIC_API_BASE_URL 未配置。" },
  );
  useEffect(() => {
    const guard = createWorkflowRequestGuard();
    const requestId = guard.begin();
    if (!apiBaseUrl) {
      return;
    }
    void fetchActiveCourseStateSnapshot(apiBaseUrl, studentId, { timeoutMs: 5_000 })
      .then((detail) => {
        if (guard.isCurrent(requestId)) setState({ status: "ready", detail });
      })
      .catch((error: unknown) => {
        if (!guard.isCurrent(requestId)) return;
        const notFound =
          typeof error === "object" &&
          error !== null &&
          "status" in error &&
          error.status === 404;
        setState({
          status: notFound ? "empty" : error instanceof ApiResponseSchemaError ? "schema-error" : "failed",
          message: notFound ? "尚未应用经过审核的 MyProgress 课程状态快照。" : error instanceof Error ? error.message : "无法加载课程状态。",
        });
      });
  }, [apiBaseUrl, studentId]);
  return [state, setState] as const;
}
