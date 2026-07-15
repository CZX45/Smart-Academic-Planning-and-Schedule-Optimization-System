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
