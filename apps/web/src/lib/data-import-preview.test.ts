import { describe, expect, it } from "vitest";

import type { DataImportRun, ImportPreviewSummary } from "@sapsos/shared";
import {
  isUsableMyProgressPreviewSummary,
  savedImportOptionFromRun,
  selectPreferredLoadedDataImport,
  type LoadedDataImportPreview,
} from "./data-import-preview";

function run(overrides: Partial<DataImportRun>): DataImportRun {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    student_profile_id: "00000000-0000-4000-8000-000000000101",
    import_type: "DEGREE_AUDIT_EXPORT",
    status: "PARSED",
    storage_strategy: "METADATA_ONLY",
    file_name: "kean-student-portal-my-progress.json",
    file_mime_type: "application/json",
    file_size_bytes: 1000,
    file_sha256: "0".repeat(64),
    parser_version: "phase7a-data-import-v1",
    record_count: 87,
    valid_record_count: 86,
    warning_count: 1,
    error_count: 1,
    official_application_ready: false,
    started_at: "2026-07-04T12:00:00Z",
    completed_at: "2026-07-04T12:00:10Z",
    source: {
      source_type: "BROWSER_EXTENSION",
      is_official: false,
      source_reference:
        "KEAN_STUDENT_PORTAL browser extension import: https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress",
      source_confidence: "browser_extension",
    },
    created_at: "2026-07-04T12:00:00Z",
    updated_at: "2026-07-04T12:00:10Z",
    ...overrides,
  };
}

function preview(
  runId: string,
  summaryPayload: Record<string, unknown>,
): ImportPreviewSummary {
  return {
    id: `10000000-0000-4000-8000-${runId.slice(-12)}`,
    data_import_run_id: runId,
    record_count: 87,
    valid_record_count: 86,
    warning_count: 1,
    error_count: 1,
    official_application_ready: false,
    disclaimers: [],
    summary_payload: summaryPayload,
    created_at: "2026-07-04T12:00:10Z",
  };
}

describe("saved data import preview helpers", () => {
  it("formats saved import selector metadata with timestamp, source, counts, validation, and confidence", () => {
    const option = savedImportOptionFromRun(
      run({
        record_count: 87,
        valid_record_count: 86,
        warning_count: 2,
        error_count: 1,
      }),
    );

    expect(option).toMatchObject({
      validationStatus: "PARSED",
      sourceType: "BROWSER_EXTENSION",
      recordCount: 87,
      confidence: "browser_extension",
    });
    expect(option.label).toContain("Jul 4, 2026");
    expect(option.label).toContain("BROWSER_EXTENSION");
    expect(option.label).toContain("87 records");
    expect(option.label).toContain("86 valid");
    expect(option.label).toContain("2 warnings");
    expect(option.label).toContain("1 error");
  });

  it("treats an empty MyProgress payload as unusable even when it is newest", () => {
    const brokenPreview = preview("000000000002", {
      real_import_status: "REAL_IMPORTED_DATA_REQUIRES_EXCEPTION_REVIEW",
      extracted_degree_audit_row_count: 0,
      parsed_course_like_row_count: 0,
      parsed_requirement_row_count: 0,
      exception_row_count: 0,
      overall_confidence_score: 0,
      program_summary: {},
      course_rows: [],
    });

    expect(isUsableMyProgressPreviewSummary(brokenPreview)).toBe(false);
  });

  it("prefers the latest usable MyProgress import over a newer broken one", () => {
    const latestBroken: LoadedDataImportPreview = {
      run: run({
        id: "00000000-0000-4000-8000-000000000002",
        created_at: "2026-07-04T13:00:00Z",
        record_count: 1,
        valid_record_count: 0,
        error_count: 1,
      }),
      preview: preview("000000000002", {
        real_import_status: "REAL_IMPORTED_DATA_REQUIRES_EXCEPTION_REVIEW",
        extracted_degree_audit_row_count: 0,
        parsed_course_like_row_count: 0,
        parsed_requirement_row_count: 0,
        overall_confidence_score: 0,
        program_summary: {},
        course_rows: [],
      }),
    };
    const previousValid: LoadedDataImportPreview = {
      run: run({
        id: "00000000-0000-4000-8000-000000000001",
        created_at: "2026-07-04T12:00:00Z",
      }),
      preview: preview("000000000001", {
        real_import_status: "REAL_IMPORTED_DATA_AUTO_VERIFIED",
        extracted_degree_audit_row_count: 85,
        parsed_course_like_row_count: 84,
        parsed_requirement_row_count: 1,
        exception_row_count: 1,
        overall_confidence_score: 1,
        program_summary: { programName: "Finance, BS" },
        course_rows: [{ course_code: "MATH 1044" }],
      }),
    };

    expect(
      selectPreferredLoadedDataImport([latestBroken, previousValid])?.run.id,
    ).toBe(previousValid.run.id);
  });
});
