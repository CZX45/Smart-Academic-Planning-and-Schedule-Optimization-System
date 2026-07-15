import { describe, expect, it } from "vitest";
import { createMutationReplayGuard, createWorkflowRequestGuard } from "./workflow-module-guards";
import { canApplyReview, reviewWorkflowKey } from "./data-review-workflow";
import { eligibilityWorkflowKey, preservesUnknownEligibility } from "./eligibility-workflow";
import { hypotheticalScenarioKey, isHypotheticalOnly } from "./what-if-workflow";
import { canUseSectionForRealOptimizer } from "./reviewed-sections-workflow";

describe("workflow module isolation guards", () => {
  it("ignores stale reads after a newer request starts", () => {
    const guard = createWorkflowRequestGuard();
    const first = guard.begin();
    const second = guard.begin();
    expect(guard.isCurrent(first)).toBe(false);
    expect(guard.isCurrent(second)).toBe(true);
  });

  it("does not replay a mutation while the original is running", () => {
    const beginMutation = createMutationReplayGuard();
    expect(beginMutation()).toBe(true);
    expect(beginMutation()).toBe(false);
  });

  it("keeps review, eligibility, What-If, and reviewed Section state scoped", () => {
    expect(reviewWorkflowKey({ importId: "i1", reviewId: "r1" })).not.toBe(
      reviewWorkflowKey({ importId: "i2", reviewId: "r1" }),
    );
    expect(canApplyReview(["DEFERRED", "EDITED_AND_CONFIRMED"])).toBe(true);
    expect(eligibilityWorkflowKey({ studentId: "s1", courseId: "c1" })).not.toBe(
      eligibilityWorkflowKey({ studentId: "s2", courseId: "c1" }),
    );
    expect(preservesUnknownEligibility("UNKNOWN")).toBe(true);
    expect(hypotheticalScenarioKey({ studentId: "s1", scenarioId: "x1" })).toContain("WHAT_IF");
    expect(isHypotheticalOnly("WHAT_IF")).toBe(true);
    expect(canUseSectionForRealOptimizer("REVIEWED_IMPORTED", { reviewStatus: "REVIEWED", applied: true })).toBe(true);
    expect(canUseSectionForRealOptimizer("DEMO_MOCK", { reviewStatus: "REVIEWED", applied: true })).toBe(false);
  });
});
