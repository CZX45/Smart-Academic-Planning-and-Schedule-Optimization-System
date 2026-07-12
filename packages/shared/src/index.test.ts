import { describe, expect, it } from "vitest";
import {
  ApiRequestError,
  ApiResponseSchemaError,
  AcademicPlanDetailSchema,
  AppliedImportedRecordSchema,
  CourseEligibilityCheckSchema,
  CourseStateSnapshotDetailSchema,
  DataImportReviewSessionSchema,
  DataImportRunSchema,
  DataReviewApplicationResultSchema,
  DataReviewWarningSchema,
  isSectionMonitorRawPayloadBounded,
  MAX_SECTION_MONITOR_RAW_PAYLOAD_BYTES,
  MAX_SECTION_MONITOR_SNAPSHOT_COUNT,
  SectionMonitorAlertSchema,
  SectionMonitorSnapshotCompareResponseSchema,
  SectionMonitorSnapshotSchema,
  SectionMonitorTargetSchema,
  ImportedRecordReviewSchema,
  ImportMappingCandidateSchema,
  ImportPreviewSummarySchema,
  ImportValidationWarningSchema,
  HealthResponseSchema,
  ReadinessResponseSchema,
  AcademicScenarioSchema,
  ScenarioComparisonSnapshotSchema,
  ScenarioCourseAllocationSchema,
  ScenarioProgramSchema,
  ScenarioWarningSchema,
  DegreeAuditRunSchema,
  RequirementEvaluationSchema,
  DegreeAuditWarningSchema,
  ScheduleOptimizationDetailSchema,
  applyDataImportReview,
  createAcademicPlan,
  createCourseEligibilityCheck,
  createDataImport,
  createDataImportReview,
  createSectionMonitorTarget,
  compareSectionMonitorSnapshots,
  createScheduleOptimization,
  fetchSectionMonitorAlerts,
  fetchHealth,
  updateSectionMonitorAlert,
  updateSectionMonitorTarget,
  updateImportedRecordReview,
  formatAcademicTimestamp,
  formatBeforeAfterValue,
  getAcademicEmptyStateCopy,
  getAcademicStatusBadge,
  getAdvisoryLabels,
} from "./index.js";

describe("HealthResponseSchema", () => {
  it("validates API health payloads", () => {
    expect(
      HealthResponseSchema.parse({
        status: "ok",
        service: "api",
        database_configured: true,
      }),
    ).toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });
});

describe("ReadinessResponseSchema", () => {
  it("validates API readiness payloads", () => {
    expect(
      ReadinessResponseSchema.parse({
        status: "ready",
        service: "api",
        database_ready: true,
      }),
    ).toEqual({
      status: "ready",
      service: "api",
      database_ready: true,
    });
  });
});

describe("academic UI helpers", () => {
  it("normalizes status badges for dashboard and panel states", () => {
    expect(getAcademicStatusBadge("COMPLETED_WITH_WARNINGS")).toEqual({
      label: "Completed with warnings",
      tone: "warning",
    });
    expect(getAcademicStatusBadge("OPEN")).toEqual({
      label: "Open",
      tone: "success",
    });
    expect(getAcademicStatusBadge("schema-error")).toEqual({
      label: "Schema error",
      tone: "danger",
    });
    expect(getAcademicStatusBadge(null)).toEqual({
      label: "Not started",
      tone: "neutral",
    });
  });

  it("returns consistent advisory labels for non-official workflows", () => {
    expect(
      getAdvisoryLabels([
        "NON_OFFICIAL_IMPORTED_DATA",
        "MANUAL_REVIEW_REQUIRED",
        "ADVISORY_ONLY",
        "VERIFY_IN_OFFICIAL_PORTAL",
      ]),
    ).toEqual([
      { text: "Non-official imported data", tone: "warning" },
      { text: "Manual review required", tone: "warning" },
      { text: "Advisory only", tone: "info" },
      { text: "Verify in official portal", tone: "danger" },
    ]);
  });

  it("formats timestamps and before-after values for imported snapshots", () => {
    expect(formatAcademicTimestamp("2026-07-01T00:00:00Z")).toBe(
      "Jul 1, 2026, 12:00 AM UTC",
    );
    expect(formatAcademicTimestamp(null)).toBe("Not available");
    expect(formatBeforeAfterValue(null, "OPEN")).toBe("Unknown -> OPEN");
    expect(formatBeforeAfterValue("CLOSED", "")).toBe("CLOSED -> Unknown");
  });

  it("provides empty-state copy with reasons and next manual actions", () => {
    expect(getAcademicEmptyStateCopy("NO_SECTION_MONITORING_ALERTS")).toEqual({
      title: "No section monitoring alerts",
      explanation: "No advisory section changes have been detected yet.",
      reason:
        "There are no imported section snapshots with a detected before/after change.",
      nextAction:
        "Import a fresh section-search snapshot, then verify any change manually in the official portal.",
      disclaimer: "Advisory only. Verify in official portal.",
    });
    expect(getAcademicEmptyStateCopy("NO_GENERATED_SCHEDULE_PLANS")).toEqual({
      title: "No generated schedule plans",
      explanation: "No semester schedule optimization has been generated yet.",
      reason:
        "The schedule builder starts empty until a student manually runs an optimization.",
      nextAction:
        "Choose a course set and build a schedule to compare advisory options.",
      disclaimer: "Advisory only. This is not registration.",
    });
  });
});

describe("fetchHealth", () => {
  it("returns parsed health payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          status: "ok",
          service: "api",
          database_configured: true,
        }),
      );

    await expect(fetchHealth("http://api.test", { fetchFn })).resolves.toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });

  it("reports non-2xx health responses", async () => {
    const fetchFn = async () => new Response("nope", { status: 500 });

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiRequestError,
    );
  });

  it("reports invalid health response schemas", async () => {
    const fetchFn = async () => new Response(JSON.stringify({ status: "ok" }));

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiResponseSchemaError,
    );
  });
});

describe("degree audit schemas", () => {
  it("validates audit run summaries", () => {
    expect(
      DegreeAuditRunSchema.parse({
        id: "00000000-0000-4000-8000-000000000001",
        student_profile_id: "00000000-0000-4000-8000-000000000002",
        program_version_id: "00000000-0000-4000-8000-000000000003",
        status: "COMPLETED_WITH_WARNINGS",
        engine_version: "phase-3a-degree-audit-v1",
        calculation_mode: "PROJECTED",
        started_at: "2026-06-23T00:00:00Z",
        completed_at: "2026-06-23T00:00:01Z",
        total_required_credits: "120.0",
        completed_credits: "18.0",
        in_progress_credits: "3.0",
        planned_credits: "3.0",
        remaining_credits: "102.0",
        completion_percentage: "15.00",
        source_snapshot_hash: "hash",
        created_at: "2026-06-23T00:00:00Z",
        updated_at: "2026-06-23T00:00:01Z",
      }),
    ).toMatchObject({
      status: "COMPLETED_WITH_WARNINGS",
      calculation_mode: "PROJECTED",
    });
  });

  it("validates requirement evaluations with applications and warnings", () => {
    expect(
      RequirementEvaluationSchema.parse({
        id: "00000000-0000-4000-8000-000000000011",
        degree_audit_run_id: "00000000-0000-4000-8000-000000000001",
        requirement_node_id: "00000000-0000-4000-8000-000000000012",
        requirement_code: "BUS-REQ-A",
        requirement_name: "Required Course A",
        requirement_type: "REQUIRED_COURSE",
        status: "SATISFIED",
        required_credits: "3.0",
        satisfied_credits: "3.0",
        remaining_credits: "0.0",
        required_courses: 1,
        satisfied_courses: 1,
        remaining_courses: 0,
        minimum_grade: "C",
        explanation: "Completed by Mock BUS 101.",
        display_order: 10,
        applications: [
          {
            id: "00000000-0000-4000-8000-000000000013",
            course_id: "00000000-0000-4000-8000-000000000014",
            course_code: "BUS 101",
            course_title: "Mock Business Foundations",
            application_type: "COURSE_ATTEMPT",
            credit_amount: "3.0",
            grade: "B",
            is_completed: true,
            is_in_progress: false,
            is_planned: false,
            is_shared: false,
            explanation: "Applied completed attempt.",
          },
        ],
        warnings: [],
      }),
    ).toMatchObject({
      requirement_code: "BUS-REQ-A",
      status: "SATISFIED",
    });

    expect(
      DegreeAuditWarningSchema.parse({
        id: "00000000-0000-4000-8000-000000000015",
        degree_audit_run_id: "00000000-0000-4000-8000-000000000001",
        requirement_evaluation_id: "00000000-0000-4000-8000-000000000011",
        warning_code: "PENDING_TRANSFER",
        severity: "WARNING",
        message: "Pending transfer credit is not applied.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ warning_code: "PENDING_TRANSFER" });
  });
});

describe("data import schemas", () => {
  it("validates staging-only import runs, mappings, warnings, and previews", () => {
    const run = DataImportRunSchema.parse({
      id: "00000000-0000-4000-8000-000000000701",
      student_profile_id: "00000000-0000-4000-8000-000000000702",
      import_type: "UNOFFICIAL_TRANSCRIPT",
      status: "PARSED_WITH_WARNINGS",
      storage_strategy: "METADATA_ONLY",
      file_name: "mock-transcript.csv",
      file_mime_type: "text/csv",
      file_size_bytes: 148,
      file_sha256:
        "7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a",
      parser_version: "phase7a-data-import-v1",
      record_count: 2,
      valid_record_count: 1,
      warning_count: 2,
      error_count: 0,
      official_application_ready: false,
      started_at: "2026-06-30T00:00:00Z",
      completed_at: "2026-06-30T00:00:01Z",
      source: { source_type: "STUDENT_PROVIDED", is_official: false },
      created_at: "2026-06-30T00:00:00Z",
      updated_at: "2026-06-30T00:00:01Z",
    });
    expect(run.official_application_ready).toBe(false);

    expect(
      ImportMappingCandidateSchema.parse({
        id: "00000000-0000-4000-8000-000000000703",
        imported_record_id: "00000000-0000-4000-8000-000000000704",
        target_entity_type: "COURSE",
        target_entity_id: "00000000-0000-4000-8000-000000000705",
        match_type: "EXACT_CODE",
        confidence_score: "1.00",
        is_selected: true,
        reason_code: "EXACT_COURSE_CODE",
        explanation: "FIN 300 exactly matches mock catalog course FIN 300.",
        created_at: "2026-06-30T00:00:00Z",
      }),
    ).toMatchObject({ target_entity_type: "COURSE" });

    expect(
      ImportValidationWarningSchema.parse({
        id: "00000000-0000-4000-8000-000000000706",
        data_import_run_id: run.id,
        imported_record_id: null,
        warning_code: "STAGING_ONLY_NOT_OFFICIAL",
        severity: "WARNING",
        message: "Preview only.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-30T00:00:00Z",
      }),
    ).toMatchObject({ requires_advisor_confirmation: true });

    expect(
      ImportPreviewSummarySchema.parse({
        id: "00000000-0000-4000-8000-000000000707",
        data_import_run_id: run.id,
        record_count: 2,
        valid_record_count: 1,
        warning_count: 2,
        error_count: 0,
        official_application_ready: false,
        disclaimers: [
          "This import preview is staging-only and is not official school policy.",
        ],
        summary_payload: { staging_only: true },
        created_at: "2026-06-30T00:00:00Z",
      }),
    ).toMatchObject({ official_application_ready: false });
  });

  it("creates data import previews through the typed helper", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          id: "00000000-0000-4000-8000-000000000701",
          student_profile_id: "00000000-0000-4000-8000-000000000702",
          import_type: "UNOFFICIAL_TRANSCRIPT",
          status: "PARSED_WITH_WARNINGS",
          storage_strategy: "METADATA_ONLY",
          file_name: "mock-transcript.csv",
          file_mime_type: "text/csv",
          file_size_bytes: 148,
          file_sha256:
            "7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a",
          parser_version: "phase7a-data-import-v1",
          record_count: 2,
          valid_record_count: 1,
          warning_count: 2,
          error_count: 0,
          official_application_ready: false,
          started_at: "2026-06-30T00:00:00Z",
          completed_at: "2026-06-30T00:00:01Z",
          source: { source_type: "STUDENT_PROVIDED", is_official: false },
          created_at: "2026-06-30T00:00:00Z",
          updated_at: "2026-06-30T00:00:01Z",
        }),
      );

    await expect(
      createDataImport(
        "http://api.test",
        {
          student_profile_id: "00000000-0000-4000-8000-000000000702",
          import_type: "UNOFFICIAL_TRANSCRIPT",
          file_name: "mock-transcript.csv",
          file_mime_type: "text/csv",
          content: "term,course_code\n2024FA,FIN 300",
          source_type: "STUDENT_PROVIDED",
        },
        { fetchFn },
      ),
    ).resolves.toMatchObject({
      status: "PARSED_WITH_WARNINGS",
      official_application_ready: false,
    });
  });

  it("supports browser-extension import handoff requests as staging-only data", async () => {
    let requestBody: unknown = null;
    const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
      requestBody = JSON.parse(String(init?.body ?? "{}"));
      return new Response(
        JSON.stringify({
          id: "00000000-0000-4000-8000-000000000741",
          student_profile_id: "00000000-0000-4000-8000-000000000702",
          import_type: "SECTION_SCHEDULE",
          status: "PARSED_WITH_WARNINGS",
          storage_strategy: "METADATA_ONLY",
          file_name: "browser-extension-section-schedule.csv",
          file_mime_type: "text/csv",
          file_size_bytes: 96,
          file_sha256:
            "8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b8b",
          parser_version: "phase7a-data-import-v1",
          record_count: 1,
          valid_record_count: 1,
          warning_count: 1,
          error_count: 0,
          official_application_ready: false,
          started_at: "2026-07-01T00:00:00Z",
          completed_at: "2026-07-01T00:00:01Z",
          source: { source_type: "BROWSER_EXTENSION", is_official: false },
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:01Z",
        }),
      );
    };

    const result = await createDataImport(
      "http://api.test",
      {
        student_profile_id: "00000000-0000-4000-8000-000000000702",
        import_type: "SECTION_SCHEDULE",
        file_name: "browser-extension-section-schedule.csv",
        file_mime_type: "text/csv",
        content:
          "term_code,course_code,section_code,modality,status,credits\n2025FA,FIN 403,001,IN_PERSON,OPEN,3",
        source_type: "BROWSER_EXTENSION",
        source_reference:
          "Browser extension visible-page import: https://portal.example.edu/section-search",
      },
      { fetchFn },
    );

    expect(result.source.source_type).toBe("BROWSER_EXTENSION");
    expect(result.official_application_ready).toBe(false);
    expect(requestBody).toMatchObject({
      source_type: "BROWSER_EXTENSION",
      source_reference:
        "Browser extension visible-page import: https://portal.example.edu/section-search",
    });
  });

  it("adds a bearer token to typed API helper requests when configured", async () => {
    let authorizationHeader: string | null = null;
    const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
      authorizationHeader = new Headers(init?.headers).get("authorization");
      return new Response(
        JSON.stringify({
          id: "00000000-0000-4000-8000-000000000701",
          student_profile_id: "00000000-0000-4000-8000-000000000702",
          import_type: "UNOFFICIAL_TRANSCRIPT",
          status: "PARSED",
          storage_strategy: "METADATA_ONLY",
          file_name: "transcript.csv",
          file_mime_type: "text/csv",
          file_size_bytes: 32,
          file_sha256:
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
          parser_version: "phase7a-data-import-v1",
          record_count: 0,
          valid_record_count: 0,
          warning_count: 0,
          error_count: 0,
          official_application_ready: false,
          started_at: "2026-06-30T00:00:00Z",
          completed_at: "2026-06-30T00:00:01Z",
          source: { source_type: "STUDENT_PROVIDED", is_official: false },
          created_at: "2026-06-30T00:00:00Z",
          updated_at: "2026-06-30T00:00:01Z",
        }),
      );
    };

    await createDataImport(
      "http://api.test",
      {
        student_profile_id: "00000000-0000-4000-8000-000000000702",
        import_type: "UNOFFICIAL_TRANSCRIPT",
        file_name: "transcript.csv",
        file_mime_type: "text/csv",
        content: "",
        source_type: "STUDENT_PROVIDED",
      },
      { apiBearerToken: "typed-client-token", fetchFn },
    );

    expect(authorizationHeader).toBe("Bearer typed-client-token");
  });

  it("validates review sessions, record decisions, warnings, and dry-run results", () => {
    const review = DataImportReviewSessionSchema.parse({
      id: "00000000-0000-4000-8000-000000000731",
      data_import_run_id: "00000000-0000-4000-8000-000000000701",
      student_profile_id: "00000000-0000-4000-8000-000000000702",
      status: "IN_REVIEW",
      reviewer_label: "Mock student self-review",
      started_at: "2026-06-30T00:00:00Z",
      completed_at: null,
      created_at: "2026-06-30T00:00:00Z",
      updated_at: "2026-06-30T00:00:00Z",
    });
    expect(review.status).toBe("IN_REVIEW");

    const importedRecord = {
      id: "00000000-0000-4000-8000-000000000704",
      data_import_run_id: review.data_import_run_id,
      record_type: "COURSE_ATTEMPT",
      row_number: 2,
      status: "VALID_WITH_WARNINGS",
      external_identifier: "FIN 300",
      raw_label: "FIN 300 Mock Managerial Finance",
      normalized_payload: {
        term: "2024FA",
        course_code: "FIN 300",
        grade: "B",
        credits: "3.0",
        status: "COMPLETED",
      },
      confidence_score: "0.80",
      created_at: "2026-06-30T00:00:00Z",
    };
    const candidate = {
      id: "00000000-0000-4000-8000-000000000703",
      imported_record_id: importedRecord.id,
      target_entity_type: "COURSE",
      target_entity_id: "00000000-0000-4000-8000-000000000705",
      match_type: "EXACT_CODE",
      confidence_score: "1.00",
      is_selected: true,
      reason_code: "EXACT_COURSE_CODE",
      explanation: "FIN 300 exactly matches mock catalog course FIN 300.",
      created_at: "2026-06-30T00:00:00Z",
    };

    expect(
      ImportedRecordReviewSchema.parse({
        id: "00000000-0000-4000-8000-000000000732",
        review_session_id: review.id,
        imported_record_id: importedRecord.id,
        selected_mapping_candidate_id: candidate.id,
        decision: "CONFIRMED",
        edited_normalized_payload: null,
        review_note: "Matches student copy.",
        requires_advisor_confirmation: false,
        imported_record: importedRecord,
        selected_mapping_candidate: candidate,
        created_at: "2026-06-30T00:00:00Z",
        updated_at: "2026-06-30T00:00:01Z",
      }),
    ).toMatchObject({ decision: "CONFIRMED" });

    expect(
      AppliedImportedRecordSchema.parse({
        id: null,
        data_application_run_id: null,
        imported_record_review_id: "00000000-0000-4000-8000-000000000732",
        imported_record_id: importedRecord.id,
        target_entity_type: "STUDENT_COURSE_ATTEMPT",
        target_entity_id: null,
        action: "CREATED",
        status: "SUCCESS",
        reason_code: "WOULD_CREATE_STUDENT_COURSE_ATTEMPT",
        message: "Dry run would create an internal student course attempt.",
        created_at: null,
      }),
    ).toMatchObject({ action: "CREATED" });

    const warning = DataReviewWarningSchema.parse({
      id: "00000000-0000-4000-8000-000000000733",
      review_session_id: review.id,
      imported_record_review_id: null,
      data_application_run_id: null,
      warning_code: "STAGING_ONLY_NOT_OFFICIAL",
      severity: "WARNING",
      message: "Review remains unofficial.",
      requires_advisor_confirmation: true,
      created_at: "2026-06-30T00:00:00Z",
    });
    expect(warning.requires_advisor_confirmation).toBe(true);

    expect(
      DataReviewApplicationResultSchema.parse({
        review_session: review,
        dry_run: true,
        application: null,
        applied_records: [
          {
            id: null,
            data_application_run_id: null,
            imported_record_review_id: "00000000-0000-4000-8000-000000000732",
            imported_record_id: importedRecord.id,
            target_entity_type: "STUDENT_COURSE_ATTEMPT",
            target_entity_id: null,
            action: "CREATED",
            status: "SUCCESS",
            reason_code: "WOULD_CREATE_STUDENT_COURSE_ATTEMPT",
            message: "Dry run would create an internal student course attempt.",
            created_at: null,
          },
        ],
        warnings: [warning],
        summary: {
          source_import_id: review.data_import_run_id,
          snapshot_id: null,
          applied_count: 1,
          warning_count: 0,
          exception_count: 0,
          rejected_count: 0,
          deferred_count: 0,
          duplicate_count: 0,
        },
      }),
    ).toMatchObject({ dry_run: true });
  });

  it("validates applied non-official course-state snapshots and provenance", () => {
    const snapshotId = "00000000-0000-4000-8000-000000000741";
    const importId = "00000000-0000-4000-8000-000000000701";
    const readiness = {
      status: "READY_WITH_WARNINGS",
      reason_codes: ["ACTIVE_NON_OFFICIAL_COURSE_STATE_SNAPSHOT"],
      blocking_reasons: [],
      warnings: ["COURSE_CODE_UNMATCHED"],
      source_import_id: importId,
      source_validation_state: "AUTO_VERIFIED",
      source_bounded: false,
      source_truncated: false,
      last_applied_at: "2026-07-11T00:00:00Z",
    };
    const detail = CourseStateSnapshotDetailSchema.parse({
      snapshot: {
        id: snapshotId,
        student_profile_id: "00000000-0000-4000-8000-000000000702",
        data_import_run_id: importId,
        review_session_id: "00000000-0000-4000-8000-000000000731",
        data_application_run_id: "00000000-0000-4000-8000-000000000742",
        source_page_type: "KEAN_MY_PROGRESS_PAGE",
        source_validation_state: "AUTO_VERIFIED",
        program_mapping_state: "EXACT",
        is_active: true,
        is_advisory: true,
        official_application_ready: false,
        extraction_bounded: false,
        extraction_truncated: false,
        completed_count: 1,
        in_progress_count: 0,
        planned_count: 1,
        not_started_count: 0,
        matched_count: 2,
        unmatched_count: 0,
        exception_count: 0,
        program_summary: { programName: "Finance, BS", catalogYear: 2024 },
        credit_summary: { totalAppliedCredits: 104, totalRequiredCredits: 120 },
        requirement_summary: [{ name: "Finance Requirements" }],
        readiness: {
          summary: readiness,
          course_history: readiness,
          degree_audit: readiness,
          course_eligibility: readiness,
          long_term_planner: readiness,
          semester_schedule: { ...readiness, status: "DEMO_ONLY" },
        },
        applied_at: "2026-07-11T00:00:00Z",
        source: { source_type: "BROWSER_EXTENSION", is_official: false },
        created_at: "2026-07-11T00:00:00Z",
        updated_at: "2026-07-11T00:00:00Z",
      },
      course_states: [
        {
          id: "00000000-0000-4000-8000-000000000743",
          snapshot_id: snapshotId,
          imported_record_id: "00000000-0000-4000-8000-000000000704",
          imported_record_review_id: "00000000-0000-4000-8000-000000000732",
          matched_course_id: "00000000-0000-4000-8000-000000000705",
          student_course_attempt_id: "00000000-0000-4000-8000-000000000744",
          normalized_course_code: "FIN 300",
          source_course_code: "FIN 300",
          source_course_title: "Managerial Finance",
          status: "COMPLETED",
          term: "2024FA",
          credits: "3.0",
          grade: null,
          requirement_context: "Finance Requirements",
          source_page_type: "KEAN_MY_PROGRESS_PAGE",
          source_table_index: "1",
          source_row_index: "1",
          provenance: {
            course_code: {
              source: "sanitized table 1 row 1",
              confidence: "high",
            },
          },
          confidence_score: "1.0",
          validation_state: "RELIABLE",
          review_decision: "CONFIRMED",
          application_reason_code: "COURSE_STATE_APPLIED",
          reason_codes: ["EXACT_COURSE_CODE"],
          warnings: [],
          created_at: "2026-07-11T00:00:00Z",
        },
      ],
    });

    expect(detail).toMatchObject({
      snapshot: {
        is_active: true,
        official_application_ready: false,
        readiness: { semester_schedule: { status: "DEMO_ONLY" } },
      },
      course_states: [
        {
          normalized_course_code: "FIN 300",
          validation_state: "RELIABLE",
        },
      ],
    });
  });

  it("uses typed helpers for review creation, decisions, and dry-run apply", async () => {
    const reviewPayload = {
      id: "00000000-0000-4000-8000-000000000731",
      data_import_run_id: "00000000-0000-4000-8000-000000000701",
      student_profile_id: "00000000-0000-4000-8000-000000000702",
      status: "IN_REVIEW",
      reviewer_label: "Mock student self-review",
      started_at: "2026-06-30T00:00:00Z",
      completed_at: null,
      created_at: "2026-06-30T00:00:00Z",
      updated_at: "2026-06-30T00:00:00Z",
    };
    const recordReviewPayload = {
      id: "00000000-0000-4000-8000-000000000732",
      review_session_id: reviewPayload.id,
      imported_record_id: "00000000-0000-4000-8000-000000000704",
      selected_mapping_candidate_id: null,
      decision: "CONFIRMED",
      edited_normalized_payload: null,
      review_note: "Matches student copy.",
      requires_advisor_confirmation: false,
      imported_record: {
        id: "00000000-0000-4000-8000-000000000704",
        data_import_run_id: reviewPayload.data_import_run_id,
        record_type: "COURSE_ATTEMPT",
        row_number: 2,
        status: "VALID_WITH_WARNINGS",
        external_identifier: "FIN 300",
        raw_label: "FIN 300 Mock Managerial Finance",
        normalized_payload: { course_code: "FIN 300" },
        confidence_score: "0.80",
        created_at: "2026-06-30T00:00:00Z",
      },
      selected_mapping_candidate: null,
      created_at: "2026-06-30T00:00:00Z",
      updated_at: "2026-06-30T00:00:01Z",
    };

    const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "PATCH") {
        return new Response(JSON.stringify(recordReviewPayload));
      }
      if (init?.method === "POST" && String(init.body).includes("dry_run")) {
        return new Response(
          JSON.stringify({
            review_session: reviewPayload,
            dry_run: true,
            application: null,
            applied_records: [
              {
                id: null,
                data_application_run_id: null,
                imported_record_review_id: recordReviewPayload.id,
                imported_record_id: recordReviewPayload.imported_record_id,
                target_entity_type: "STUDENT_COURSE_ATTEMPT",
                target_entity_id: null,
                action: "CREATED",
                status: "SUCCESS",
                reason_code: "WOULD_CREATE_STUDENT_COURSE_ATTEMPT",
                message:
                  "Dry run would create an internal student course attempt.",
                created_at: null,
              },
            ],
            warnings: [],
            summary: {
              source_import_id: reviewPayload.data_import_run_id,
              snapshot_id: null,
              applied_count: 1,
              warning_count: 0,
              exception_count: 0,
              rejected_count: 0,
              deferred_count: 0,
              duplicate_count: 0,
            },
          }),
        );
      }
      return new Response(JSON.stringify(reviewPayload));
    };

    await expect(
      createDataImportReview(
        "http://api.test",
        {
          data_import_run_id: reviewPayload.data_import_run_id,
          reviewer_label: reviewPayload.reviewer_label,
        },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ status: "IN_REVIEW" });

    await expect(
      updateImportedRecordReview(
        "http://api.test",
        reviewPayload.id,
        recordReviewPayload.id,
        { decision: "CONFIRMED" },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ decision: "CONFIRMED" });

    await expect(
      applyDataImportReview(
        "http://api.test",
        reviewPayload.id,
        { dry_run: true, allow_advisor_review_records: false },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ dry_run: true });
  });
});

describe("section monitoring schemas", () => {
  const targetPayload = {
    id: "00000000-0000-4000-8000-000000000801",
    student_profile_id: "00000000-0000-4000-8000-000000000702",
    course_code: "FIN 403",
    section_code: "001",
    term: "2025FA",
    title: "Mock International Finance",
    instructor: "Mock Instructor",
    status: "OPEN",
    is_active: true,
    is_advisory: true,
    is_official: false,
    latest_snapshot_created_at: "2026-07-01T00:00:00Z",
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
  };
  const snapshotPayload = {
    id: "00000000-0000-4000-8000-000000000802",
    target_id: targetPayload.id,
    data_import_id: null,
    course_code: "FIN 403",
    section_code: "001",
    term: "2025FA",
    status: "OPEN",
    seats_available: 4,
    seats_capacity: 30,
    waitlist_available: 2,
    waitlist_capacity: 10,
    meeting_days: "MONDAY",
    meeting_time: "09:00-10:15",
    location: "Mock Hall 101",
    instructor: "Mock Instructor",
    raw_payload: { source_label: "Visible section-search table" },
    source_type: "BROWSER_EXTENSION",
    is_official: false,
    source_reference: "Browser extension visible-page import",
    source_confidence: "browser_extension",
    created_at: "2026-07-01T00:00:00Z",
  };
  const alertPayload = {
    id: "00000000-0000-4000-8000-000000000803",
    target_id: targetPayload.id,
    previous_snapshot_id: "00000000-0000-4000-8000-000000000804",
    current_snapshot_id: snapshotPayload.id,
    alert_type: "SECTION_OPENED",
    severity: "INFO",
    field_name: "status",
    previous_value: "CLOSED",
    current_value: "OPEN",
    message:
      "FIN 403 001 appears to have opened in imported data; manually verify in the official portal.",
    is_acknowledged: false,
    acknowledged_at: null,
    is_advisory: true,
    requires_manual_review: true,
    created_at: "2026-07-01T00:00:00Z",
  };

  it("validates advisory targets, non-official snapshots, and manual-review alerts", () => {
    expect(SectionMonitorTargetSchema.parse(targetPayload)).toMatchObject({
      is_active: true,
      is_advisory: true,
      is_official: false,
    });
    expect(SectionMonitorSnapshotSchema.parse(snapshotPayload)).toMatchObject({
      source_type: "BROWSER_EXTENSION",
      is_official: false,
    });
    expect(SectionMonitorAlertSchema.parse(alertPayload)).toMatchObject({
      alert_type: "SECTION_OPENED",
      is_advisory: true,
      requires_manual_review: true,
    });
    expect(
      SectionMonitorSnapshotCompareResponseSchema.parse({
        snapshots: [snapshotPayload],
        alerts: [alertPayload],
        disclaimers: [
          "Section monitoring is based on user-triggered imported data and is not official.",
        ],
      }),
    ).toMatchObject({ alerts: [{ alert_type: "SECTION_OPENED" }] });
  });

  it("bounds section monitor raw payloads and compare request size", async () => {
    expect(isSectionMonitorRawPayloadBounded({ source: "visible-table" })).toBe(
      true,
    );
    expect(
      isSectionMonitorRawPayloadBounded({
        source: "x".repeat(MAX_SECTION_MONITOR_RAW_PAYLOAD_BYTES + 1),
      }),
    ).toBe(false);

    const fetchFn = async () => new Response(JSON.stringify({}));
    await expect(
      compareSectionMonitorSnapshots(
        "http://api.test",
        {
          student_profile_id: targetPayload.student_profile_id,
          snapshots: Array.from(
            { length: MAX_SECTION_MONITOR_SNAPSHOT_COUNT + 1 },
            () => ({
              course_code: "FIN 403",
              section_code: "001",
              term: "2025FA",
            }),
          ),
        },
        { fetchFn },
      ),
    ).rejects.toThrow(ApiRequestError);
  });

  it("uses typed helpers for advisory target and alert workflows", async () => {
    const seenRequests: Array<{ url: string; method: string | undefined }> = [];
    const fetchFn = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      seenRequests.push({ url, method: init?.method });
      if (url.endsWith("/targets") && init?.method === "POST") {
        return new Response(JSON.stringify(targetPayload));
      }
      if (url.endsWith(`/targets/${targetPayload.id}`)) {
        return new Response(
          JSON.stringify({ ...targetPayload, is_active: false }),
        );
      }
      if (url.endsWith("/snapshots/compare")) {
        return new Response(
          JSON.stringify({
            snapshots: [snapshotPayload],
            alerts: [alertPayload],
            disclaimers: [
              "This system does not register, drop, swap, waitlist, submit forms, or perform any portal action.",
            ],
          }),
          { status: 201 },
        );
      }
      if (url.includes("/alerts/") && init?.method === "PATCH") {
        return new Response(
          JSON.stringify({
            ...alertPayload,
            is_acknowledged: true,
            acknowledged_at: "2026-07-01T00:00:01Z",
          }),
        );
      }
      return new Response(JSON.stringify([alertPayload]));
    };

    await expect(
      createSectionMonitorTarget(
        "http://api.test",
        {
          student_profile_id: targetPayload.student_profile_id,
          course_code: "FIN 403",
          section_code: "001",
          term: "2025FA",
          title: "Mock International Finance",
        },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ is_advisory: true });
    await expect(
      updateSectionMonitorTarget(
        "http://api.test",
        targetPayload.id,
        { is_active: false },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ is_active: false });
    await expect(
      compareSectionMonitorSnapshots(
        "http://api.test",
        {
          student_profile_id: targetPayload.student_profile_id,
          source_type: "BROWSER_EXTENSION",
          snapshots: [
            {
              course_code: "FIN 403",
              section_code: "001",
              term: "2025FA",
              status: "OPEN",
              seats_available: 4,
            },
          ],
        },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ alerts: [{ alert_type: "SECTION_OPENED" }] });
    await expect(
      fetchSectionMonitorAlerts(
        "http://api.test",
        targetPayload.student_profile_id,
        {
          fetchFn,
        },
      ),
    ).resolves.toHaveLength(1);
    await expect(
      updateSectionMonitorAlert(
        "http://api.test",
        alertPayload.id,
        { is_acknowledged: true },
        { fetchFn },
      ),
    ).resolves.toMatchObject({ is_acknowledged: true });

    expect(seenRequests.map((request) => request.url)).toContain(
      "http://api.test/api/v1/section-monitoring/snapshots/compare",
    );
  });
});

describe("academic scenario schemas", () => {
  it("validates scenario snapshots, allocations, warnings, and comparison summaries", () => {
    const scenario = AcademicScenarioSchema.parse({
      id: "00000000-0000-4000-8000-000000000101",
      student_profile_id: "00000000-0000-4000-8000-000000000102",
      name: "Add Accounting Minor",
      scenario_type: "ADD_MINOR",
      status: "COMPLETED_WITH_WARNINGS",
      base_program_version_id: "00000000-0000-4000-8000-000000000103",
      engine_version: "phase-3b-academic-scenario-v1",
      created_at: "2026-06-23T00:00:00Z",
      updated_at: "2026-06-23T00:00:01Z",
      completed_at: "2026-06-23T00:00:01Z",
    });
    expect(scenario.scenario_type).toBe("ADD_MINOR");

    expect(
      ScenarioProgramSchema.parse({
        id: "00000000-0000-4000-8000-000000000104",
        academic_plan_scenario_id: scenario.id,
        program_version_id: scenario.base_program_version_id,
        relationship_type: "PRIMARY_MAJOR",
        is_existing_program: true,
        is_hypothetical: false,
        priority: 0,
        program_code: "BSFIN",
        program_name: "Mock BS Finance",
        source: { source_type: "MOCK", is_official: false },
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ relationship_type: "PRIMARY_MAJOR" });

    expect(
      ScenarioCourseAllocationSchema.parse({
        id: "00000000-0000-4000-8000-000000000105",
        academic_plan_scenario_id: scenario.id,
        student_course_attempt_id: "00000000-0000-4000-8000-000000000106",
        transfer_credit_id: null,
        course_id: "00000000-0000-4000-8000-000000000107",
        course_code: "ACCT 300",
        course_title: "Mock Accounting Analytics",
        program_version_id: scenario.base_program_version_id,
        requirement_node_id: "00000000-0000-4000-8000-000000000108",
        requirement_code: "ACCT-MINOR-CORE",
        allocation_type: "SHARED",
        credit_amount: "3.0",
        is_shared: true,
        is_unique_to_program: false,
        allocation_rank: 1,
        reason_code: "SHARED_BY_RULE",
        explanation: "Shared by mock rule.",
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ allocation_type: "SHARED", credit_amount: "3.0" });

    expect(
      ScenarioWarningSchema.parse({
        id: "00000000-0000-4000-8000-000000000109",
        academic_plan_scenario_id: scenario.id,
        scenario_program_id: null,
        warning_code: "MISSING_PROGRAM_COMBINATION_RULE",
        severity: "WARNING",
        message: "Advisor review is required.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ requires_advisor_confirmation: true });

    expect(
      ScenarioComparisonSnapshotSchema.parse({
        academic_plan_scenario_id: scenario.id,
        completed_credits: "18.0",
        in_progress_credits: "3.0",
        planned_credits: "3.0",
        remaining_requirement_credits: "12.0",
        shared_credits: "3.0",
        unique_secondary_credits: "6.0",
        estimated_additional_credits: "9.0",
        unresolved_requirements: 4,
        manual_review_count: 1,
        completion_percentage: "82.50",
        is_estimate: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ is_estimate: true });
  });
});

describe("course eligibility schemas", () => {
  const eligibilityPayload = {
    id: "00000000-0000-4000-8000-000000000301",
    institution_id: "00000000-0000-4000-8000-000000000302",
    student_profile_id: "00000000-0000-4000-8000-000000000303",
    course_id: "00000000-0000-4000-8000-000000000304",
    section_id: "00000000-0000-4000-8000-000000000305",
    target_term_id: "00000000-0000-4000-8000-000000000306",
    mode: "REGISTRATION",
    status: "COMPLETED_WITH_WARNINGS",
    engine_version: "phase-4-course-eligibility-v1",
    overall_result: "PERMISSION_REQUIRED",
    academic_eligibility_result: "PERMISSION_REQUIRED",
    started_at: "2026-06-24T00:00:00Z",
    completed_at: "2026-06-24T00:00:01Z",
    source_snapshot_hash: "hash",
    rule_evaluations: [
      {
        id: "00000000-0000-4000-8000-000000000307",
        eligibility_check_run_id: "00000000-0000-4000-8000-000000000301",
        course_rule_id: "00000000-0000-4000-8000-000000000308",
        result: "PERMISSION_REQUIRED",
        rule_type: "PERMISSION",
        explanation: "Permission rule evaluated as PERMISSION_REQUIRED.",
        display_order: 0,
        expressions: [
          {
            id: "00000000-0000-4000-8000-000000000309",
            rule_evaluation_id: "00000000-0000-4000-8000-000000000307",
            course_rule_expression_id: "00000000-0000-4000-8000-000000000310",
            node_type: "PERMISSION_REQUIRED",
            result: "PERMISSION_REQUIRED",
            actual_value: null,
            expected_value: "DEPARTMENT_APPROVAL",
            matched_course_id: null,
            matched_attempt_id: null,
            reason_code: "PERMISSION_REQUIRED",
            explanation: "Permission is required.",
            created_at: "2026-06-24T00:00:01Z",
          },
        ],
        created_at: "2026-06-24T00:00:01Z",
      },
    ],
    blocking_reasons: [],
    conditional_reasons: [],
    permissions_required: [
      {
        reason_code: "PERMISSION_REQUIRED",
        explanation: "Permission is required.",
        course_rule_id: "00000000-0000-4000-8000-000000000308",
        course_rule_expression_id: "00000000-0000-4000-8000-000000000310",
        referenced_entity_type: null,
        referenced_entity_id: null,
        expected_value: "DEPARTMENT_APPROVAL",
        actual_value: null,
      },
    ],
    manual_review_reasons: [],
    corequisites_to_add: [],
    corequisite_summary: null,
    registration_availability: {
      section_status: "WAITLIST",
      available_seats: 0,
      waitlist_available: 4,
      availability_note: "Section availability is separate.",
    },
    warnings: [
      {
        id: "00000000-0000-4000-8000-000000000311",
        eligibility_check_run_id: "00000000-0000-4000-8000-000000000301",
        rule_evaluation_id: null,
        warning_code: "MOCK_ELIGIBILITY_ESTIMATE",
        severity: "INFO",
        message: "Mock non-official result.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-24T00:00:01Z",
      },
    ],
    created_at: "2026-06-24T00:00:00Z",
    updated_at: "2026-06-24T00:00:01Z",
  };

  it("validates eligibility check snapshots with expression evidence", () => {
    expect(
      CourseEligibilityCheckSchema.parse(eligibilityPayload),
    ).toMatchObject({
      overall_result: "PERMISSION_REQUIRED",
      registration_availability: { section_status: "WAITLIST" },
    });
  });

  it("rejects malformed course eligibility API payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          ...eligibilityPayload,
          overall_result: "READY_FOR_SCHEDULING",
        }),
      );

    await expect(
      createCourseEligibilityCheck(
        "http://api.test",
        {
          student_profile_id: eligibilityPayload.student_profile_id,
          course_id: eligibilityPayload.course_id,
          section_id: eligibilityPayload.section_id,
          target_term_id: eligibilityPayload.target_term_id,
          mode: "REGISTRATION",
        },
        { fetchFn },
      ),
    ).rejects.toThrow(ApiResponseSchemaError);
  });
});

describe("academic plan schemas", () => {
  const planPayload = {
    id: "00000000-0000-4000-8000-000000000401",
    student_profile_id: "00000000-0000-4000-8000-000000000001",
    program_version_id: "00000000-0000-4000-8000-000000000002",
    academic_plan_scenario_id: null,
    planning_mode: "CURRENT_PROGRAM",
    status: "COMPLETED_WITH_WARNINGS",
    engine_version: "phase-5a-academic-planner-v1",
    start_term_id: "00000000-0000-4000-8000-000000000101",
    target_completion_term_id: "00000000-0000-4000-8000-000000000102",
    minimum_credits_per_term: "3.0",
    maximum_credits_per_term: "6.0",
    preferred_credits_per_term: "6.0",
    completed_at: "2026-06-29T00:00:01Z",
    created_at: "2026-06-29T00:00:00Z",
    updated_at: "2026-06-29T00:00:01Z",
    terms: [
      {
        id: "00000000-0000-4000-8000-000000000402",
        academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
        term_id: "00000000-0000-4000-8000-000000000101",
        term_code: "2024FA",
        sequence_index: 0,
        planned_credits: "4.0",
        status: "PLANNED",
        explanation: "Term is planned.",
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    planned_courses: [
      {
        id: "00000000-0000-4000-8000-000000000403",
        academic_plan_term_id: "00000000-0000-4000-8000-000000000402",
        term_id: "00000000-0000-4000-8000-000000000101",
        term_code: "2024FA",
        course_id: "00000000-0000-4000-8000-000000000301",
        course_code: "FIN 400",
        course_title: "Mock Advanced Finance",
        requirement_node_id: "00000000-0000-4000-8000-000000000201",
        requirement_code: "CAPSTONE-DEMO",
        source: "DEGREE_AUDIT_REMAINING",
        priority_rank: 0,
        credits: "3.0",
        eligibility_result: "CONDITIONALLY_ELIGIBLE",
        planning_status: "CONDITIONALLY_PLANNED",
        reason_code: "REQUIREMENT_REMAINING",
        explanation: "Placed for a remaining requirement.",
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    requirement_coverage: [
      {
        id: "00000000-0000-4000-8000-000000000404",
        academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
        academic_plan_course_id: "00000000-0000-4000-8000-000000000403",
        requirement_node_id: "00000000-0000-4000-8000-000000000201",
        requirement_code: "CAPSTONE-DEMO",
        coverage_type: "DIRECT_REQUIREMENT",
        credits: "3.0",
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    warnings: [
      {
        id: "00000000-0000-4000-8000-000000000405",
        academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
        academic_plan_term_id: null,
        academic_plan_course_id: null,
        warning_code: "MOCK_PLAN_NOT_OFFICIAL",
        severity: "INFO",
        message: "Mock plan is not official.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
  };

  it("validates academic plan snapshots with terms, courses, coverage, and warnings", () => {
    expect(AcademicPlanDetailSchema.parse(planPayload)).toMatchObject({
      planning_mode: "CURRENT_PROGRAM",
      planned_courses: [{ course_code: "FIN 400" }],
    });
  });

  it("rejects malformed academic plan API payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          ...planPayload,
          planned_courses: [
            {
              ...planPayload.planned_courses[0],
              planning_status: "REGISTERED",
            },
          ],
        }),
      );

    await expect(
      createAcademicPlan(
        "http://api.test",
        {
          student_profile_id: planPayload.student_profile_id,
          program_version_id: planPayload.program_version_id,
          academic_plan_scenario_id: null,
          planning_mode: "CURRENT_PROGRAM",
          start_term_id: planPayload.start_term_id,
          terms_to_plan: 2,
          minimum_credits_per_term: "3.0",
          maximum_credits_per_term: "6.0",
          preferred_credits_per_term: "6.0",
        },
        { fetchFn },
      ),
    ).rejects.toThrow(ApiResponseSchemaError);
  });
});

describe("schedule optimizer schemas", () => {
  const schedulePayload = {
    id: "00000000-0000-4000-8000-000000000501",
    student_profile_id: "00000000-0000-4000-8000-000000000001",
    term_id: "00000000-0000-4000-8000-000000000101",
    academic_plan_run_id: null,
    planning_mode: "CUSTOM_COURSE_SET",
    status: "COMPLETED_WITH_WARNINGS",
    engine_version: "phase-6b-schedule-optimizer-v1",
    minimum_credits: "3.0",
    maximum_credits: "6.0",
    preferred_credits: "6.0",
    requested_option_count: 2,
    completed_at: "2026-06-29T00:00:01Z",
    created_at: "2026-06-29T00:00:00Z",
    updated_at: "2026-06-29T00:00:01Z",
    constraint_set: {
      id: "00000000-0000-4000-8000-000000000502",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000501",
      excluded_days: ["FRIDAY"],
      unavailable_time_blocks: [
        { day_of_week: "TUESDAY", start_time: "11:00", end_time: "11:30" },
      ],
      earliest_start_time: "08:00",
      latest_end_time: "18:00",
      minimum_gap_minutes: null,
      maximum_gap_minutes: null,
      candidate_course_ids: ["00000000-0000-4000-8000-000000000301"],
      allowed_modalities: [],
      excluded_modalities: [],
      required_course_ids: [],
      excluded_course_ids: [],
      required_section_ids: [],
      excluded_section_ids: [],
      prefer_online: false,
      prefer_compact_schedule: true,
      prefer_fewer_days: true,
      prefer_in_person: true,
      avoid_early_start: false,
      avoid_late_end: true,
      allow_permission_required: false,
      preference_weights: { priority: "2.0" },
      course_priority_weights: {},
      section_priority_weights: {
        "00000000-0000-4000-8000-000000000505": "5.0",
      },
      prefer_no_gaps: true,
      prefer_morning: true,
      prefer_afternoon: false,
      diversity_mode: "HIGH",
      allow_partial_options: true,
      max_combinations: 500,
      created_at: "2026-06-29T00:00:00Z",
    },
    options: [
      {
        id: "00000000-0000-4000-8000-000000000503",
        schedule_optimization_run_id: "00000000-0000-4000-8000-000000000501",
        option_rank: 1,
        status: "FEASIBLE_WITH_WARNINGS",
        total_credits: "6.0",
        class_days_count: 2,
        earliest_start_time: "09:00",
        latest_end_time: "12:15",
        total_gap_minutes: 45,
        score: "86.00",
        total_score: "86.00",
        credit_score: "30.00",
        compactness_score: "17.00",
        days_score: "12.00",
        gap_score: "10.50",
        modality_score: "8.00",
        time_preference_score: "3.00",
        priority_score: "20.00",
        penalty_score: "-5.00",
        score_explanation: [
          {
            reason_code: "SECTION_PRIORITY_WEIGHT",
            score: "20.00",
            explanation: "Pinned mock section is preferred.",
          },
        ],
        score_breakdown: {
          total_score: "86.00",
          credit_score: "30.00",
          compactness_score: "17.00",
          days_score: "12.00",
          gap_score: "10.50",
          modality_score: "8.00",
          time_preference_score: "3.00",
          priority_score: "20.00",
          penalty_score: "-5.00",
          score_explanation: [
            {
              reason_code: "SECTION_PRIORITY_WEIGHT",
              score: "20.00",
              explanation: "Pinned mock section is preferred.",
            },
          ],
        },
        diversity_rank: 1,
        difference_summary: "Top ranked option.",
        shared_section_count_with_previous_option: 0,
        explanation:
          "Selected deterministic mock sections with traceable warnings.",
        selected_sections: [
          {
            id: "00000000-0000-4000-8000-000000000504",
            schedule_option_id: "00000000-0000-4000-8000-000000000503",
            section_id: "00000000-0000-4000-8000-000000000505",
            course_id: "00000000-0000-4000-8000-000000000301",
            course_code: "FIN 300",
            course_title: "Mock Corporate Finance",
            section_code: "001",
            section_status: "OPEN",
            modality: "IN_PERSON",
            credits: "3.0",
            eligibility_result: "ELIGIBLE",
            selection_reason: "MANUAL_CANDIDATE",
            meetings: [
              {
                id: "00000000-0000-4000-8000-000000000506",
                section_id: "00000000-0000-4000-8000-000000000505",
                meeting_type: "LECTURE",
                day_of_week: "MONDAY",
                start_time: "09:00",
                end_time: "10:15",
                start_date: null,
                end_date: null,
                building: "MOCK",
                room: "101",
                timezone: "America/New_York",
                is_arranged: false,
                is_online: false,
                display_order: 1,
              },
            ],
            created_at: "2026-06-29T00:00:00Z",
          },
        ],
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    conflicts: [
      {
        id: "00000000-0000-4000-8000-000000000507",
        schedule_optimization_run_id: "00000000-0000-4000-8000-000000000501",
        schedule_option_id: null,
        conflict_type: "UNAVAILABLE_TIME",
        section_id: "00000000-0000-4000-8000-000000000505",
        other_section_id: null,
        day_of_week: "TUESDAY",
        start_time: "11:00",
        end_time: "11:30",
        message: "Mock section conflicts with an unavailable time block.",
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    warnings: [
      {
        id: "00000000-0000-4000-8000-000000000508",
        schedule_optimization_run_id: "00000000-0000-4000-8000-000000000501",
        schedule_option_id: null,
        warning_code: "MOCK_SECTION_DATA_NOT_OFFICIAL",
        severity: "INFO",
        message: "Mock schedule data is not official.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    repair_suggestions: [
      {
        id: "00000000-0000-4000-8000-000000000509",
        schedule_optimization_run_id: "00000000-0000-4000-8000-000000000501",
        suggestion_type: "RELAX_UNAVAILABLE_BLOCK",
        affected_constraint: "unavailable_time_blocks",
        affected_course_id: null,
        affected_section_id: "00000000-0000-4000-8000-000000000505",
        estimated_impact: "Could make a blocked section selectable.",
        message: "Relax the unavailable time block.",
        requires_advisor_confirmation: false,
        created_at: "2026-06-29T00:00:00Z",
      },
    ],
    hard_constraint_results: [
      { constraint: "excluded_days", result: "APPLIED", value: ["FRIDAY"] },
    ],
    soft_preference_results: [{ preference: "prefer_no_gaps", value: true }],
  };

  it("validates schedule optimizer snapshots with options, conflicts, and warnings", () => {
    expect(
      ScheduleOptimizationDetailSchema.parse(schedulePayload),
    ).toMatchObject({
      planning_mode: "CUSTOM_COURSE_SET",
      options: [{ selected_sections: [{ course_code: "FIN 300" }] }],
      conflicts: [{ conflict_type: "UNAVAILABLE_TIME" }],
      repair_suggestions: [{ suggestion_type: "RELAX_UNAVAILABLE_BLOCK" }],
      soft_preference_results: [{ preference: "prefer_no_gaps" }],
    });
  });

  it("rejects malformed schedule optimizer API payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          ...schedulePayload,
          options: [
            { ...schedulePayload.options[0], status: "AUTO_REGISTERED" },
          ],
        }),
      );

    await expect(
      createScheduleOptimization(
        "http://api.test",
        {
          student_profile_id: schedulePayload.student_profile_id,
          term_id: schedulePayload.term_id,
          academic_plan_run_id: null,
          planning_mode: "CUSTOM_COURSE_SET",
          candidate_course_ids:
            schedulePayload.constraint_set.candidate_course_ids,
          minimum_credits: "3.0",
          maximum_credits: "6.0",
          preferred_credits: "6.0",
          requested_option_count: 2,
          excluded_days: ["FRIDAY"],
        },
        { fetchFn },
      ),
    ).rejects.toThrow(ApiResponseSchemaError);
  });
});
