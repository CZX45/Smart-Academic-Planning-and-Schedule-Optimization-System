export type ReviewDecision =
  | "UNREVIEWED"
  | "CONFIRMED"
  | "EDITED_AND_CONFIRMED"
  | "REJECTED"
  | "DEFERRED"
  | "NEEDS_ADVISOR_REVIEW";

export type ReviewDisplayRecord = {
  decision: ReviewDecision;
  requires_advisor_confirmation: boolean;
  imported_record: {
    normalized_payload: Record<string, unknown>;
  };
};

export type ReviewWorkflowIdentity = { importId: string; reviewId: string };

export function reviewWorkflowKey(identity: ReviewWorkflowIdentity): string {
  return `${identity.importId}:${identity.reviewId}`;
}

export function canApplyReview(decisions: readonly ReviewDecision[]): boolean {
  return decisions.some(
    (decision) =>
      decision === "CONFIRMED" || decision === "EDITED_AND_CONFIRMED",
  );
}

export function reviewDisplayScope<T extends ReviewDisplayRecord>(
  records: readonly T[],
): {
  isMyProgressReview: boolean;
  records: T[];
  confirmedCount: number;
  advisorReviewCount: number;
} {
  const myProgressRecords = records.filter(
    (record) =>
      record.imported_record.normalized_payload.record_kind ===
      "MY_PROGRESS_COURSE_ROW",
  );
  const isMyProgressReview = myProgressRecords.length > 0;
  const recordsForDisplay = isMyProgressReview
    ? myProgressRecords
    : [...records];

  return {
    isMyProgressReview,
    records: recordsForDisplay,
    confirmedCount: recordsForDisplay.filter(
      (record) =>
        record.decision === "CONFIRMED" ||
        record.decision === "EDITED_AND_CONFIRMED",
    ).length,
    advisorReviewCount: recordsForDisplay.filter(
      (record) => record.requires_advisor_confirmation,
    ).length,
  };
}

export function reviewMappingLabel(
  isMyProgressReview: boolean,
  targetEntityId: string | null | undefined,
): string {
  if (!isMyProgressReview) {
    return "Catalog identity：已审核";
  }
  return targetEntityId ? "Catalog：已匹配" : "Catalog：未匹配 / 外部证据";
}
