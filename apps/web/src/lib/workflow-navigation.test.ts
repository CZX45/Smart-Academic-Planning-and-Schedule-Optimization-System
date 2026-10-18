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
      "backup-restore",
      "diagnostics",
    ]);
    expect(workflowDefinitions.map((workflow) => workflow.label)).toContain(
      "备份与恢复",
    );
  });

  it("resolves hashes without requiring a server route", () => {
    expect(workflowIdFromHash("#degree-audit")).toBe("degree-audit");
    expect(workflowIdFromHash("degree-audit")).toBe("degree-audit");
    expect(workflowIdFromHash("#unknown-workflow")).toBe("overview");
    expect(workflowHref(workflowDefinitions[0])).toBe("#overview");
    expect(workflowIdFromHash("#diagnostics")).toBe("diagnostics");
  });
});
