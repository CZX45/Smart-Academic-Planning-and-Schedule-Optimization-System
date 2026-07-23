import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  ApiRequestError,
  ApiResponseSchemaError,
  fetchActiveCourseStateSnapshot,
  type CourseStateSnapshotDetail,
} from "@sapsos/shared";
import { createWorkflowRequestGuard } from "./workflow-module-guards";

export type CourseStateWorkflowState =
  | { status: "loading" }
  | { status: "ready"; detail: CourseStateSnapshotDetail }
  | {
      status: "empty" | "offline" | "failed" | "schema-error";
      message: string;
    };

export function useCourseStateWorkflow(
  apiBaseUrl: string | undefined,
  studentId: string | undefined,
): readonly [
  CourseStateWorkflowState,
  Dispatch<SetStateAction<CourseStateWorkflowState>>,
] {
  const [state, setState] = useState<CourseStateWorkflowState>(() =>
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
      setState({
        status: "empty",
        message: "尚未导入学生数据或启用演示工作流。",
      });
      return () => {
        guard.begin();
      };
    }
    void fetchActiveCourseStateSnapshot(apiBaseUrl, studentId, {
      timeoutMs: 5_000,
    })
      .then((detail) => {
        if (guard.isCurrent(requestId)) setState({ status: "ready", detail });
      })
      .catch((error: unknown) => {
        if (!guard.isCurrent(requestId)) return;
        const notFound =
          error instanceof ApiRequestError &&
          error.message.includes("status 404");
        setState({
          status: notFound
            ? "empty"
            : error instanceof ApiResponseSchemaError
              ? "schema-error"
              : "failed",
          message: notFound
            ? "尚未应用经过审核的 MyProgress 课程状态快照。"
            : error instanceof Error
              ? error.message
              : "无法加载课程状态。",
        });
      });
    return () => {
      guard.begin();
    };
  }, [apiBaseUrl, studentId]);
  return [state, setState] as const;
}
