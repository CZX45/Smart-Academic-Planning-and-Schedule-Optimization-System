import { describe, expect, it } from "vitest";
import {
  workflowDefinitions,
  workflowHref,
  workflowIdFromHash,
} from "./workflow-navigation";

describe("workflow navigation", () => {
  it("exposes only implemented workflows", () => {
    expect(workflowDefinitions.map((workflow) => workflow.id)).toEqual([
      "overview",
      "data-import",
      "review-apply",
      "degree-audit",
      "eligibility",
      "academic-plan",
      "what-if",
      "sections",
      "schedule-builder",
      "section-monitoring",
    ]);
    expect(workflowDefinitions.map((workflow) => workflow.label)).not.toContain(
      "备份",
    );
  });

  it("resolves hashes without requiring a server route", () => {
    expect(workflowIdFromHash("#degree-audit")).toBe("degree-audit");
    expect(workflowIdFromHash("degree-audit")).toBe("degree-audit");
    expect(workflowIdFromHash("#unknown-workflow")).toBe("overview");
    expect(workflowHref(workflowDefinitions[0])).toBe("#overview");
  });
});
