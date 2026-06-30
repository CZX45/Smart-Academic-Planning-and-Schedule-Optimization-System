import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  createDataImportRequestFromExtraction,
  extractAcademicPageFromTables,
} from "../src/content/extractors.js";
import type { TableSnapshot } from "../src/shared/types.js";

const fixturesDir = join(process.cwd(), "tests", "fixtures");

function fixture(name: string): string {
  return readFileSync(join(fixturesDir, name), "utf8");
}

function textOnly(value: string): string {
  return value
    .replace(/<input\b[^>]*type=["']password["'][^>]*>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cells(rowHtml: string, tagName: "td" | "th"): string[] {
  const pattern = new RegExp(
    `<${tagName}\\b[^>]*>([\\s\\S]*?)<\\/${tagName}>`,
    "gi",
  );
  return [...rowHtml.matchAll(pattern)].map((match) =>
    textOnly(match[1] ?? ""),
  );
}

function tablesFromFixture(name: string): TableSnapshot[] {
  const html = fixture(name);
  const tableMatches = html.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/gi);
  return [...tableMatches].map((match, index) => {
    const tableHtml = match[1] ?? "";
    const captionMatch = tableHtml.match(
      /<caption\b[^>]*>([\s\S]*?)<\/caption>/i,
    );
    const rowMatches = [...tableHtml.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)];
    const headerRow = rowMatches.find((rowMatch) =>
      /<th\b/i.test(rowMatch[1] ?? ""),
    );
    const headers = headerRow ? cells(headerRow[1] ?? "", "th") : [];
    const rows = rowMatches
      .filter((rowMatch) => /<td\b/i.test(rowMatch[1] ?? ""))
      .map((rowMatch) => cells(rowMatch[1] ?? "", "td"));
    return {
      caption: captionMatch ? textOnly(captionMatch[1] ?? "") : "",
      index,
      headers,
      rows,
    };
  });
}

function extractFixture(name: string) {
  return extractAcademicPageFromTables({
    title: `Fixture ${name}`,
    url: `https://portal.example.edu/${name}`,
    tables: tablesFromFixture(name),
  });
}

describe("browser extension academic table extractors", () => {
  it("extracts transcript tables into Phase 7A-compatible unofficial transcript content", () => {
    const extraction = extractFixture("transcript-table.html");

    expect(extraction.pageType).toBe("TRANSCRIPT_TABLE");
    expect(extraction.importType).toBe("UNOFFICIAL_TRANSCRIPT");
    expect(extraction.sourceType).toBe("BROWSER_EXTENSION");
    expect(extraction.isOfficial).toBe(false);
    expect(extraction.records).toHaveLength(2);
    expect(extraction.records[0]).toMatchObject({
      term_code: "2024FA",
      course_code: "FIN 300",
      course_title: "Mock Managerial Finance",
      credits: "3.0",
      grade: "B",
      attempt_status: "COMPLETED",
      source_label: "Visible transcript table",
    });
    expect(extraction.content).toContain(
      "term_code,course_code,course_title,credits,grade,attempt_status,source_label",
    );
  });

  it("extracts degree audit tables with requirements and manual-review warnings", () => {
    const extraction = extractFixture("degree-audit-table.html");

    expect(extraction.pageType).toBe("DEGREE_AUDIT_TABLE");
    expect(extraction.importType).toBe("DEGREE_AUDIT_EXPORT");
    expect(extraction.records[0]).toMatchObject({
      program_code: "BSFIN",
      catalog_year: "2024",
      requirements: "Major Core",
      completed_courses: "FIN 300",
      remaining_requirements: "FIN 403",
    });
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "DEGREE_AUDIT_REQUIRES_MANUAL_REVIEW",
    );
  });

  it("extracts course catalog tables", () => {
    const extraction = extractFixture("course-catalog-table.html");

    expect(extraction.pageType).toBe("COURSE_CATALOG_TABLE");
    expect(extraction.importType).toBe("COURSE_CATALOG");
    expect(extraction.records[0]).toMatchObject({
      course_code: "FIN 403",
      course_title: "Mock Investments",
      credits: "3",
      course_level: "400",
      department: "Finance",
      description: "Mock catalog description.",
    });
  });

  it("extracts section search tables", () => {
    const extraction = extractFixture("section-search-table.html");

    expect(extraction.pageType).toBe("SECTION_SEARCH_TABLE");
    expect(extraction.importType).toBe("SECTION_SCHEDULE");
    expect(extraction.records[0]).toMatchObject({
      term_code: "2025FA",
      course_code: "FIN 403",
      section_code: "001",
      modality: "IN_PERSON",
      status: "OPEN",
      credits: "3",
      day_of_week: "MONDAY",
      start_time: "09:00",
      end_time: "10:15",
      building: "Mock Hall",
      room: "101",
      instructor_display: "Mock Instructor",
    });
  });

  it("returns a no-data result for unknown pages and empty tables", () => {
    const unknown = extractFixture("unknown-page.html");
    const empty = extractFixture("empty-table.html");

    expect(unknown.pageType).toBe("UNKNOWN_PAGE");
    expect(unknown.records).toHaveLength(0);
    expect(unknown.warnings.map((warning) => warning.code)).toContain(
      "NO_ACADEMIC_TABLE_FOUND",
    );
    expect(empty.records).toHaveLength(0);
    expect(empty.warnings.map((warning) => warning.code)).toContain(
      "NO_IMPORTABLE_ROWS",
    );
  });

  it("warns instead of crashing on malformed rows and unknown columns", () => {
    const malformed = extractFixture("malformed-row.html");
    const extraColumns = extractFixture("extra-columns.html");

    expect(malformed.records).toHaveLength(0);
    expect(malformed.warnings.map((warning) => warning.code)).toContain(
      "MALFORMED_ROW",
    );
    expect(extraColumns.records).toHaveLength(1);
    expect(extraColumns.warnings.map((warning) => warning.code)).toContain(
      "UNKNOWN_COLUMNS",
    );
  });

  it("produces deterministic output for the same visible page", () => {
    const first = extractFixture("section-search-table.html");
    const second = extractFixture("section-search-table.html");

    expect(second).toEqual(first);
  });

  it("does not extract password field values", () => {
    const extraction = extractFixture("transcript-table.html");

    expect(JSON.stringify(extraction)).not.toContain("do-not-read");
  });

  it("builds a confirmed browser-extension handoff request for the existing import API", () => {
    const extraction = extractFixture("section-search-table.html");
    const request = createDataImportRequestFromExtraction(
      "00000000-0000-4000-8000-000000000702",
      extraction,
    );

    expect(request).toMatchObject({
      student_profile_id: "00000000-0000-4000-8000-000000000702",
      import_type: "SECTION_SCHEDULE",
      file_name: "browser-extension-section-schedule.csv",
      file_mime_type: "text/csv",
      source_type: "BROWSER_EXTENSION",
    });
    expect(request.content).toBe(extraction.content);
    expect(request.source_reference).toContain(
      "https://portal.example.edu/section-search-table.html",
    );
  });
});
