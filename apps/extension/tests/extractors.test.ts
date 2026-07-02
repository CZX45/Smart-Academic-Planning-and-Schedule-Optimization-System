import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  createDataImportRequestsFromExtractions,
  createDataImportRequestFromExtraction,
  extractAcademicPageFromTables,
} from "../src/content/extractors.js";
import {
  KEAN_SOURCE_LABEL,
  KEAN_STUDENT_PORTAL_PREFIX,
} from "../src/shared/kean.js";
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

function extractFixture(
  name: string,
  options: { title?: string; url?: string } = {},
) {
  return extractAcademicPageFromTables({
    title: options.title ?? `Fixture ${name}`,
    url: options.url ?? `https://portal.example.edu/${name}`,
    tables: tablesFromFixture(name),
  });
}

function rowLikeBlocksFromFixture(name: string) {
  const html = fixture(name);
  return textOnly(html)
    .split(
      /(Status Course Grade Term Credits|Completed |Registered |Planned |Not Started )/,
    )
    .reduce<string[]>((blocks, segment, index, parts) => {
      if (
        segment === "Completed " ||
        segment === "Registered " ||
        segment === "Planned " ||
        segment === "Not Started "
      ) {
        blocks.push(`${segment}${parts[index + 1] ?? ""}`.trim());
        return blocks;
      }
      if (segment === "Status Course Grade Term Credits") {
        blocks.push(segment);
      }
      return blocks;
    }, [])
    .map((text, index) => ({ index, text }));
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
      seats_available: "4",
      seats_capacity: "30",
      waitlist_available: "2",
      waitlist_capacity: "10",
      credits: "3",
      day_of_week: "MONDAY",
      start_time: "09:00",
      end_time: "10:15",
      meeting_days: "MONDAY",
      meeting_time: "09:00-10:15",
      location: "Mock Hall 101",
      instructor_display: "Mock Instructor",
    });
    expect(extraction.records[0]).not.toHaveProperty("registration_action");
    expect(extraction.content).toContain("seats_available");
    expect(extraction.content).toContain("waitlist_available");
    expect(extraction.content).toContain("meeting_time");
    expect(extraction.content).toContain("location");
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

  it("detects Kean transcript pages under the Student portal prefix", () => {
    const extraction = extractFixture("kean-transcript-page.html", {
      title: "Kean Student Planning - Unofficial Transcript",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
    });

    expect(extraction.pageType).toBe("KEAN_TRANSCRIPT_PAGE");
    expect(extraction.importType).toBe("UNOFFICIAL_TRANSCRIPT");
    expect(extraction.sourceType).toBe("BROWSER_EXTENSION");
    expect(extraction.isOfficial).toBe(false);
    expect(extraction.requiresReview).toBe(true);
    expect(extraction.records).toHaveLength(2);
    expect(extraction.records[0]).toMatchObject({
      term_code: "2024FA",
      course_code: "CPS 2231",
      course_title: "Mock Computer Organization",
      credits: "3",
      grade: "B+",
      attempt_status: "COMPLETED",
    });
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "KEAN_IMPORT_NON_OFFICIAL_REVIEW_REQUIRED",
    );
    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
      detectedPageType: "KEAN_TRANSCRIPT_PAGE",
      matchedPageMarker: "AcademicHistory",
      tablesFound: 1,
      rowsFound: 2,
      extractedAcademicFieldCount: 12,
      ignoredSensitiveFieldCount: 0,
    });
  });

  it("detects Kean MyProgress, catalog, section search, planning, and schedule pages", () => {
    const myProgress = extractFixture("kean-my-progress-page.html", {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/MyProgress`,
    });
    const catalog = extractFixture("kean-course-catalog-page.html", {
      title: "Course Catalog",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/CourseCatalog`,
    });
    const sections = extractFixture("kean-section-search-page.html", {
      title: "Section Search",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/SectionSearch`,
    });
    const planning = extractFixture("kean-student-planning-page.html", {
      title: "Student Planning",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/StudentPlanning`,
    });
    const schedule = extractFixture("kean-schedule-page.html", {
      title: "Student Schedule",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Schedule`,
    });

    expect(myProgress.pageType).toBe("KEAN_MY_PROGRESS_PAGE");
    expect(myProgress.importType).toBe("DEGREE_AUDIT_EXPORT");
    expect(catalog.pageType).toBe("KEAN_COURSE_CATALOG_PAGE");
    expect(catalog.importType).toBe("COURSE_CATALOG");
    expect(sections.pageType).toBe("KEAN_SECTION_SEARCH_PAGE");
    expect(sections.importType).toBe("SECTION_SCHEDULE");
    expect(planning.pageType).toBe("KEAN_STUDENT_PLANNING_PAGE");
    expect(planning.importType).toBe("SECTION_SCHEDULE");
    expect(schedule.pageType).toBe("KEAN_SCHEDULE_PAGE");
    expect(schedule.importType).toBe("SECTION_SCHEDULE");
  });

  it("parses sanitized Kean MyProgress row-like blocks without real tables", () => {
    const extraction = extractAcademicPageFromTables({
      title: "My Progress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
      visibleText: textOnly(fixture("kean-my-progress-row-blocks.html")),
      rowLikeBlocks: rowLikeBlocksFromFixture(
        "kean-my-progress-row-blocks.html",
      ),
      snapshotMetadata: {
        directSnapshotRan: true,
        visibleTextLength: textOnly(fixture("kean-my-progress-row-blocks.html"))
          .length,
        rowLikeBlocksFound: 5,
      },
    });

    expect(extraction.pageType).toBe("KEAN_MY_PROGRESS_PAGE");
    expect(extraction.importType).toBe("DEGREE_AUDIT_EXPORT");
    expect(extraction.records).toHaveLength(4);
    expect(extraction.records[0]).toMatchObject({
      status: "COMPLETED",
      course_code: "ACCT 2200",
      course_title: "Principles of Accounting I",
      grade: "A-",
      term_code: "2025FAW",
      credits: "3",
    });
    expect(extraction.records[1]).toMatchObject({
      status: "REGISTERED",
      course_code: "FIN 3311",
      course_title: "Corporate Finance II",
      term_code: "2026FAW",
      credits: "3",
    });
    expect(extraction.records[3]).toMatchObject({
      status: "NOT_STARTED",
      course_code: "MGS 3040",
      course_title: "Management Information Systems",
    });
    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
      detectedPageType: "KEAN_MY_PROGRESS_PAGE",
      matchedPageMarker: "MyProgress",
      tablesFound: 0,
      rowsFound: 5,
      visibleTextLength: textOnly(fixture("kean-my-progress-row-blocks.html"))
        .length,
      rowLikeBlocksFound: 5,
      directSnapshotRan: true,
      bounded: false,
    });
  });

  it("preserves direct snapshot diagnostics when MyProgress parsing finds no rows", () => {
    const visibleText = "My Progress Requirements Cumulative GPA Total Credits";
    const extraction = extractAcademicPageFromTables({
      title: "My Progress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
      visibleText,
      rowLikeBlocks: [{ index: 0, text: "Requirements" }],
      snapshotMetadata: {
        directSnapshotRan: true,
        visibleTextLength: visibleText.length,
        rowLikeBlocksFound: 1,
      },
    });

    expect(extraction.pageType).toBe("UNKNOWN_PAGE");
    expect(extraction.records).toHaveLength(0);
    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
      tablesFound: 0,
      rowsFound: 1,
      visibleTextLength: visibleText.length,
      rowLikeBlocksFound: 1,
      directSnapshotRan: true,
    });
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "KEAN_WHITELISTED_PAGE_NO_ACADEMIC_TABLE_FOUND",
    );
  });

  it("creates confirmed guided Kean import requests without cookies or session data", () => {
    const extractions = [
      extractFixture("kean-transcript-page.html", {
        title: "Unofficial Transcript",
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
      }),
      extractFixture("kean-my-progress-page.html", {
        title: "MyProgress",
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/MyProgress`,
      }),
      extractFixture("kean-section-search-page.html", {
        title: "Section Search",
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/SectionSearch`,
      }),
    ];

    const requests = createDataImportRequestsFromExtractions(
      "00000000-0000-4000-8000-000000000702",
      extractions,
    );

    expect(requests).toHaveLength(3);
    expect(requests.map((request) => request.import_type)).toEqual([
      "UNOFFICIAL_TRANSCRIPT",
      "DEGREE_AUDIT_EXPORT",
      "SECTION_SCHEDULE",
    ]);
    expect(
      requests.every((request) => request.source_type === "BROWSER_EXTENSION"),
    ).toBe(true);
    expect(
      requests.every((request) =>
        request.source_reference.includes(KEAN_SOURCE_LABEL),
      ),
    ).toBe(true);
    expect(JSON.stringify(requests).toLowerCase()).not.toMatch(
      /cookie|session|token|secret|hidden-field-value/,
    );
  });

  it("does not scan Kean host pages outside the Student portal prefix", () => {
    const extraction = extractFixture("kean-transcript-page.html", {
      title: "Kean Billing",
      url: "https://kean-ss.colleague.elluciancloud.com/Finance/Billing",
    });

    expect(extraction.pageType).toBe("UNKNOWN_PAGE");
    expect(extraction.records).toHaveLength(0);
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "OUTSIDE_KEAN_STUDENT_PORTAL",
    );
  });

  it("ignores Kean login, hidden, personal, financial, and action-only data", () => {
    const login = extractFixture("kean-login-page.html", {
      title: "Kean Login",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Account/Login`,
    });
    const hidden = extractFixture("kean-hidden-credential-fields.html", {
      title: "Unofficial Transcript",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
    });
    const personal = extractFixture("kean-personal-financial-columns.html", {
      title: "Unofficial Transcript",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
    });
    const actions = extractFixture("kean-registration-actions-page.html", {
      title: "Section Search",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/SectionSearch`,
    });

    expect(login.pageType).toBe("UNKNOWN_PAGE");
    expect(login.records).toHaveLength(0);
    expect(hidden.records[0]).toMatchObject({
      course_code: "MATH 1054",
      course_title: "Mock Precalculus",
    });
    const serialized = JSON.stringify([login, hidden, personal, actions]);
    expect(serialized).not.toContain("do-not-read-password");
    expect(serialized).not.toContain("hidden-field-value");
    expect(serialized).not.toContain("mock.student@example.edu");
    expect(serialized).not.toContain("$500.00");
    expect(serialized).not.toContain("Add Section");
    expect(serialized).not.toContain("Drop Section");
    expect(actions.records[0]).not.toHaveProperty("registration_action");
    expect(actions.records[0]).not.toHaveProperty("form_action");
  });

  it("keeps diagnostic metadata free of credentials, cookies, tokens, and row payloads", () => {
    const extraction = extractFixture("kean-hidden-credential-fields.html", {
      title: "Unofficial Transcript",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory?session=do-not-copy`,
    });

    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
      detectedPageType: "KEAN_TRANSCRIPT_PAGE",
      matchedPageMarker: "AcademicHistory",
      tablesFound: 1,
      rowsFound: 1,
      ignoredSensitiveFieldCount: 0,
    });
    expect(JSON.stringify(extraction.diagnostics).toLowerCase()).not.toMatch(
      /password|cookie|token|session|hidden-field-value|do-not-read-password/,
    );
  });

  it("preserves bounded extraction warnings in diagnostics", () => {
    const extraction = extractAcademicPageFromTables({
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: tablesFromFixture("kean-my-progress-page.html"),
      warnings: [
        {
          code: "EXTRACTION_LIMIT_REACHED",
          severity: "WARNING",
          message:
            "Extraction stopped early because the page is large. Try expanding only the relevant section or use a more specific supported page.",
        },
      ],
    });

    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "EXTRACTION_LIMIT_REACHED",
    );
    expect(extraction.diagnostics.warningCodes).toContain(
      "EXTRACTION_LIMIT_REACHED",
    );
    expect(extraction.diagnostics.bounded).toBe(true);
  });
});
