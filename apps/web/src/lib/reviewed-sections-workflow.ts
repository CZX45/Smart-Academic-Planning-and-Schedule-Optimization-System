export type ReviewedSectionMode = "DEMO_MOCK" | "REVIEWED_IMPORTED";

export function canUseSectionForRealOptimizer(
  mode: ReviewedSectionMode,
  section: { reviewStatus?: string; applied?: boolean },
): boolean {
  return (
    mode === "REVIEWED_IMPORTED" &&
    section.reviewStatus === "REVIEWED" &&
    section.applied === true
  );
}

export function sectionCrnAvailabilityLabel(
  sourceProvenance: Record<string, unknown> | null | undefined,
): string | null {
  return sourceProvenance?.crn_source_status === "NOT_PROVIDED"
    ? "CRN：当前来源未提供"
    : null;
}
