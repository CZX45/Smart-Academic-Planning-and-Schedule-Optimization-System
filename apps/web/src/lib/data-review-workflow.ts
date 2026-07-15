export type ReviewDecision =
  | "CONFIRMED"
  | "EDITED_AND_CONFIRMED"
  | "REJECTED"
  | "DEFERRED"
  | "NEEDS_ADVISOR_REVIEW";

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
