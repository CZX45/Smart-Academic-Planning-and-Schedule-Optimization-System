import { describe, expect, it } from "vitest";
import { extractAcademicPageFromTables } from "../src/content/extractors.js";
import { KEAN_STUDENT_PORTAL_PREFIX } from "../src/shared/kean.js";

function summary(text: string) {
  const extraction = extractAcademicPageFromTables({
    title: "MyProgress",
    url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
    tables: [],
    visibleText: text,
    headings: ["My Progress"],
  });
  return JSON.parse(extraction.content) as {
    programSummary: Record<string, unknown>;
    fieldProvenance: Record<
      string,
      { confidence: string; requiresReview: boolean; source: string }
    >;
    validation: {
      exceptions: Array<{ code: string }>;
      overallConfidenceScore: number;
    };
  };
}

describe("MyProgress summary field boundaries", () => {
  it("does not silently select the first of conflicting program labels", () => {
    const content = summary(
      "Program: Mock Finance, BS Degree: Bachelor of Science Program: Mock Biology, BS Catalog: 2024",
    );
    expect(content.programSummary).not.toHaveProperty("programName");
    expect(content.validation.exceptions).toContainEqual(
      expect.objectContaining({ code: "MY_PROGRESS_SUMMARY_FIELD_CONFLICT" }),
    );
  });

  it("accepts compact colon labels and repeated identical fields", () => {
    const content = summary(
      "Program:Mock Finance, BS Degree:Bachelor of Science Program:Mock Finance, BS Catalog Year:2024 Cumulative GPA:3.5 Institution GPA:3.4 Total Credits 0 of 120",
    );
    expect(content.programSummary).toMatchObject({
      programName: "Mock Finance, BS",
      degree: "Bachelor of Science",
      catalogYear: 2024,
      cumulativeGpa: 3.5,
    });
  });

  it("rejects short navigation and announcement text in degree fields", () => {
    const content = summary(
      "Program: Mock Finance, BS Degree: Home Announcements Help Catalog: 2024",
    );
    expect(content.programSummary).not.toHaveProperty("degree");
  });

  it("keeps extracted summary values unreviewed with field-specific locations", () => {
    const content = summary(
      "Program: Mock Finance, BS Degree: Bachelor of Science Catalog: 2024",
    );
    expect(content.fieldProvenance.programName).toMatchObject({
      confidence: "medium",
      requiresReview: true,
    });
    expect(content.fieldProvenance.programName?.source).toContain("Program");
    expect(content.fieldProvenance.degree?.source).toContain("Degree");
    expect(content.validation.overallConfidenceScore).toBeLessThan(1);
  });
});
