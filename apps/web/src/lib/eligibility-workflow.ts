export type EligibilityWorkflowKey = { studentId: string; courseId: string };

export function eligibilityWorkflowKey(
  key: EligibilityWorkflowKey,
): string {
  return `${key.studentId}:${key.courseId}`;
}

export function preservesUnknownEligibility(status: string): boolean {
  return status === "UNKNOWN" || status === "MANUAL_REVIEW";
}
