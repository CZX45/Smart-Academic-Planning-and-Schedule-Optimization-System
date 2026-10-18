import { describe, expect, it } from "vitest";
import {
  createMutationReplayGuard,
  createWorkflowRequestGuard,
} from "./workflow-module-guards";
import {
  canApplyReview,
  reviewDisplayScope,
  reviewMappingLabel,
  reviewWorkflowKey,
} from "./data-review-workflow";
import {
  eligibilityWorkflowKey,
  preservesUnknownEligibility,
} from "./eligibility-workflow";
import {
  hypotheticalScenarioKey,
  isHypotheticalOnly,
} from "./what-if-workflow";
import {
  canUseSectionForRealOptimizer,
  sectionCrnAvailabilityLabel,
} from "./reviewed-sections-workflow";

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
    expect(
      eligibilityWorkflowKey({ studentId: "s1", courseId: "c1" }),
    ).not.toBe(eligibilityWorkflowKey({ studentId: "s2", courseId: "c1" }));
    expect(preservesUnknownEligibility("UNKNOWN")).toBe(true);
    expect(
      hypotheticalScenarioKey({ studentId: "s1", scenarioId: "x1" }),
    ).toContain("WHAT_IF");
    expect(isHypotheticalOnly("WHAT_IF")).toBe(true);
    expect(
      canUseSectionForRealOptimizer("REVIEWED_IMPORTED", {
        reviewStatus: "REVIEWED",
        applied: true,
      }),
    ).toBe(true);
    expect(
      canUseSectionForRealOptimizer("DEMO_MOCK", {
        reviewStatus: "REVIEWED",
        applied: true,
      }),
    ).toBe(false);
  });

  it("shows unavailable CRN only when the reviewed source explicitly omitted it", () => {
    expect(
      sectionCrnAvailabilityLabel({ crn_source_status: "NOT_PROVIDED" }),
    ).toBe("CRN：当前来源未提供");
    expect(
      sectionCrnAvailabilityLabel({ crn_source_status: "PROVIDED" }),
    ).toBeNull();
    expect(sectionCrnAvailabilityLabel(null)).toBeNull();
  });

  it("derives the loaded review display from its records instead of an unrelated staging preview", () => {
    const catalogScope = reviewDisplayScope([
      {
        decision: "CONFIRMED",
        requires_advisor_confirmation: false,
        imported_record: {
          normalized_payload: {
            record_kind: "CATALOG_COURSE",
            course_code: "ACCT 2200",
          },
        },
      },
      {
        decision: "EDITED_AND_CONFIRMED",
        requires_advisor_confirmation: false,
        imported_record: {
          normalized_payload: {
            record_kind: "CATALOG_COURSE",
            course_code: "FIN 3310",
          },
        },
      },
    ]);

    expect(catalogScope.isMyProgressReview).toBe(false);
    expect(catalogScope.records).toHaveLength(2);
    expect(catalogScope.confirmedCount).toBe(2);
    expect(catalogScope.advisorReviewCount).toBe(0);
    expect(reviewMappingLabel(false, null)).toBe("Catalog identity：已审核");

    const myProgressScope = reviewDisplayScope([
      {
        decision: "UNREVIEWED",
        requires_advisor_confirmation: true,
        imported_record: {
          normalized_payload: { record_kind: "MY_PROGRESS_PROGRAM_SUMMARY" },
        },
      },
      {
        decision: "CONFIRMED",
        requires_advisor_confirmation: false,
        imported_record: {
          normalized_payload: { record_kind: "MY_PROGRESS_COURSE_ROW" },
        },
      },
      {
        decision: "NEEDS_ADVISOR_REVIEW",
        requires_advisor_confirmation: true,
        imported_record: {
          normalized_payload: { record_kind: "MY_PROGRESS_COURSE_ROW" },
        },
      },
    ]);

    expect(myProgressScope.isMyProgressReview).toBe(true);
    expect(myProgressScope.records).toHaveLength(2);
    expect(myProgressScope.confirmedCount).toBe(1);
    expect(myProgressScope.advisorReviewCount).toBe(1);
    expect(
      reviewMappingLabel(true, "00000000-0000-4000-8000-000000000001"),
    ).toBe("Catalog：已匹配");
    expect(reviewMappingLabel(true, null)).toBe("Catalog：未匹配 / 外部证据");
  });
});
