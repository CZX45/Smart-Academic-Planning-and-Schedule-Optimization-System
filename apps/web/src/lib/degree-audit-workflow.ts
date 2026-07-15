export type AuditSourceReadiness =
  | "loading"
  | "ready"
  | "empty"
  | "unknown"
  | "manual-review"
  | "failed";

export function auditUsesReviewedSource(
  source: { reviewStatus?: string; confidence?: string } | null,
): boolean {
  return source?.reviewStatus === "REVIEWED" && source.confidence !== "UNKNOWN";
}
