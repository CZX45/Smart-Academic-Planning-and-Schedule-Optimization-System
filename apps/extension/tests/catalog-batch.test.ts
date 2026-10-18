import { describe, expect, it } from "vitest";

import {
  acceptCatalogPage,
  buildCatalogSubjectExtraction,
  cancelCatalogBatch,
  catalogBatchErrorDetails,
  completeCatalogSubject,
  createCatalogBatchState,
  pauseCatalogBatch,
  restoreCatalogBatchState,
  resumeCatalogBatch,
  type CatalogBatchPage,
} from "../src/content/catalog-batch.js";
import type { BrowserExtensionExtraction } from "../src/shared/types.js";

const subjectOptions = [
  { code: "ACCT", label: "Accounting" },
  { code: "FIN", label: "Finance" },
];

function extraction(
  records: BrowserExtensionExtraction["records"],
  options: {
    bounded?: boolean;
    warningCodes?: string[];
  } = {},
): BrowserExtensionExtraction {
  return {
    pageType: "KEAN_COURSE_CATALOG_PAGE",
    importType: "COURSE_CATALOG",
    sourceType: "BROWSER_EXTENSION",
    sourceLabel: "KEAN_STUDENT_PORTAL",
    isOfficial: false,
    title: "Course Catalog",
    url: "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
    fileName: "kean-student-portal-course-catalog.csv",
    fileMimeType: "text/csv",
    content: "",
    records,
    warnings: (options.warningCodes ?? []).map((code) => ({
      code,
      severity: "WARNING" as const,
      message: "Sanitized batch fixture warning.",
    })),
    diagnostics: {
      currentUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
      detectedPageType: "KEAN_COURSE_CATALOG_PAGE",
      matchedPageMarker: "/Student/Student/Courses",
      tablesFound: 0,
      rowsFound: records.length,
      visibleTextLength: 0,
      rowLikeBlocksFound: records.length,
      extractedAcademicFieldCount: records.length * 4,
      ignoredSensitiveFieldCount: 0,
      directSnapshotRan: true,
      bounded: options.bounded ?? false,
      warningCodes: options.warningCodes ?? [],
      academicTablesDetected: 1,
      academicTablesParsed: 1,
      academicRowsParsed: records.length,
      academicRowsSkipped: 0,
      academicRowsCapped: 0,
      parserWarningCodes: [],
    },
    requiresReview: true,
    extractedAt: "2026-08-26T02:00:00.000Z",
  };
}

function page(
  pageNumber: number,
  totalPages: number,
  records: BrowserExtensionExtraction["records"],
  options: {
    bounded?: boolean;
    fatalSignal?: CatalogBatchPage["fatalSignal"];
    warningCodes?: string[];
  } = {},
): CatalogBatchPage {
  return {
    subjectCode: "ACCT",
    pageNumber,
    totalPages,
    fatalSignal: options.fatalSignal ?? null,
    extraction: extraction(records, options),
  };
}

function accountingRecord(overrides: Record<string, string> = {}) {
  return {
    course_code: "ACCT 2200",
    course_title: "Financial Accounting",
    credits: "3",
    description: "Visible sanitized description.",
    raw_requisites: "Minimum grade of C required.",
    rule_review_status: "MANUAL_CONFIRMATION_REQUIRED",
    source_label: "Visible course catalog cards",
    ...overrides,
  };
}

describe("read-only Course Catalog batch state", () => {
  it("redacts authentication secrets from persisted failure diagnostics", () => {
    const jwt =
      "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzdGFjay1qd3Qtc2VjcmV0In0.signaturesecret";
    const error = new Error(
      "request failed Authorization: Bearer message-secret\nCookie: session=message-cookie\npassword=message-password\naccess_token=message-token",
      {
        cause:
          '{"pairingCredential":"cause-secret","client_secret":"client-secret","Authorization":"Basic json-basic-secret","Cookie":"session=json-cookie-secret"}',
      },
    );
    error.stack = `Error: api_key=stack-api-key\n    at worker (token=stack-token)\nBearer standalone-bearer-secret\n${jwt}`;

    const details = catalogBatchErrorDetails(error, "START_SUBJECT_SEARCH");
    const persistedDiagnostic = [
      details.message,
      details.safeErrorMessage,
      details.safeStack,
      details.safeCause,
    ].join("\n");

    expect(persistedDiagnostic).toContain("[SECRET_REDACTED]");
    for (const secret of [
      "message-secret",
      "message-cookie",
      "message-password",
      "message-token",
      "stack-api-key",
      "stack-token",
      "standalone-bearer-secret",
      jwt,
      "cause-secret",
      "client-secret",
      "json-basic-secret",
      "json-cookie-secret",
    ]) {
      expect(persistedDiagnostic).not.toContain(secret);
    }
  });

  it("classifies an invalid stored payload as an exact state-schema failure", () => {
    expect(() =>
      restoreCatalogBatchState(
        { batchId: "invalid", status: "RUNNING" },
        "2026-08-31T10:01:00.000Z",
      ),
    ).toThrow(/BATCH_CATALOG_STATE_SCHEMA_INVALID/);
  });

  it("iterates discovered subjects and deduplicates overlapping pagination by normalized identity", () => {
    let state = createCatalogBatchState({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-26T02:00:00.000Z",
    });

    state = acceptCatalogPage(
      state,
      page(1, 2, [
        accountingRecord(),
        accountingRecord({
          course_code: "ACCT*2210",
          course_title: "Managerial Accounting",
        }),
      ]),
    );
    state = acceptCatalogPage(
      state,
      page(2, 2, [
        accountingRecord(),
        accountingRecord({
          course_code: "ACCT 3300",
          course_title: "Cost Accounting",
          raw_requisites: "",
        }),
      ]),
    );

    expect(state.pendingRecords.map((record) => record.course_code)).toEqual([
      "ACCT 2200",
      "ACCT 2210",
      "ACCT 3300",
    ]);
    expect(state.coursesCaptured).toBe(4);
    expect(state.uniqueCourses).toBe(3);
    expect(state.duplicatesIgnored).toBe(1);
    expect(state.pagesCaptured).toBe(2);
    expect(state.pendingRecords[0]).toMatchObject({
      normalized_code: "ACCT 2200",
      raw_visible_title: "Financial Accounting",
      department: "NOT_PROVIDED",
      course_level: "NOT_PROVIDED",
      source_subject: "ACCT",
      source_page_number: "1",
      source_page:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
      capture_timestamp: "2026-08-26T02:00:00.000Z",
    });

    const combined = buildCatalogSubjectExtraction(state);
    expect(combined.records).toHaveLength(3);
    expect(combined.content).toContain("normalized_code");
    expect(combined.content).toContain("NOT_PROVIDED");
    expect(combined.warnings.map((warning) => warning.code)).toContain(
      "KEAN_CATALOG_RULE_REQUIRES_REVIEW",
    );
  });

  it("fails closed when duplicate search results disagree", () => {
    const initial = acceptCatalogPage(
      createCatalogBatchState({
        apiBaseUrl: "http://localhost:8000",
        studentProfileId: "00000000-0000-4000-8000-000000000702",
        tabId: 41,
        landingUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
        subjects: subjectOptions,
        startedAt: "2026-08-26T02:00:00.000Z",
      }),
      page(1, 2, [accountingRecord()]),
    );

    expect(() =>
      acceptCatalogPage(
        initial,
        page(2, 2, [accountingRecord({ credits: "4" })]),
      ),
    ).toThrowError(/CONFLICTING_DUPLICATE_COURSE/);
  });

  it.each([
    {
      name: "bounded page",
      options: { bounded: true },
      code: "BATCH_CATALOG_TRUNCATED_PAGE",
    },
    {
      name: "rate limit",
      options: { fatalSignal: "RATE_LIMIT" as const },
      code: "BATCH_CATALOG_RATE_LIMIT",
    },
    {
      name: "parser drift",
      options: { warningCodes: ["NO_IMPORTABLE_ROWS"] },
      code: "BATCH_CATALOG_PARSER_DRIFT",
    },
  ])("fails closed for $name", ({ options, code }) => {
    const state = createCatalogBatchState({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-26T02:00:00.000Z",
    });

    expect(() =>
      acceptCatalogPage(state, page(1, 1, [accountingRecord()], options)),
    ).toThrowError(new RegExp(code));
  });

  it("rejects malformed courses while allowing explicit missing optional fields", () => {
    const state = createCatalogBatchState({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-26T02:00:00.000Z",
    });

    expect(() =>
      acceptCatalogPage(
        state,
        page(1, 1, [accountingRecord({ course_title: "" })]),
      ),
    ).toThrowError(/BATCH_CATALOG_MALFORMED_COURSE/);

    const accepted = acceptCatalogPage(
      state,
      page(1, 1, [
        accountingRecord({
          description: "",
          raw_requisites: "",
          rule_review_status: "NO_REQUISITES_VISIBLE",
        }),
      ]),
    );
    expect(accepted.pendingRecords[0]).toMatchObject({
      description: "NOT_PROVIDED",
      raw_requisites: "NOT_PROVIDED",
      department: "NOT_PROVIDED",
      course_level: "NOT_PROVIDED",
    });
  });

  it("serializes restart-safe progress and supports explicit pause, resume, and cancellation", () => {
    const running = acceptCatalogPage(
      createCatalogBatchState({
        apiBaseUrl: "http://localhost:8000",
        studentProfileId: "00000000-0000-4000-8000-000000000702",
        tabId: 41,
        landingUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
        subjects: subjectOptions,
        startedAt: "2026-08-26T02:00:00.000Z",
      }),
      page(1, 2, [accountingRecord()]),
    );
    const restored = JSON.parse(JSON.stringify(pauseCatalogBatch(running)));

    expect(restored.status).toBe("PAUSED");
    expect(resumeCatalogBatch(restored).status).toBe("RUNNING");
    expect(resumeCatalogBatch(restored).pendingRecords).toHaveLength(1);

    const cancelled = cancelCatalogBatch(restored);
    expect(cancelled.status).toBe("CANCELLED");
    expect(cancelled.pendingRecords).toEqual([]);
    expect(cancelled.providerActionsWritten).toBe("NO");
  });

  it("defaults omitted v6 diagnostics and round-trips a fresh state without schema contamination", () => {
    const fresh = createCatalogBatchState({
      batchId: "fresh-v6-state",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-31T10:00:00.000Z",
      extensionVersion: "0.1.7",
      mode: "BOUNDED_ACCEPTANCE",
      subjectLimit: 2,
    });
    const serialized = structuredClone(
      JSON.parse(JSON.stringify(fresh)) as Record<string, unknown>,
    );
    delete serialized.lastSuccessfulCheckpoint;
    delete serialized.failedOperation;
    delete serialized.lastFailureDiagnostic;
    serialized.lastPageDiagnostics = null;

    const restored = restoreCatalogBatchState(
      serialized,
      "2026-08-31T10:01:00.000Z",
    );

    expect(restored).toMatchObject({
      status: "PAUSED",
      lastSuccessfulCheckpoint: "SUBJECT_DISCOVERY_COMPLETED",
      failedOperation: null,
      lastFailureDiagnostic: null,
      lastPageDiagnostics: null,
      providerActionsWritten: "NO",
    });
    expect(() => structuredClone(restored)).not.toThrow();
  });

  it("re-redacts valid diagnostics restored from extension storage", () => {
    const fresh = createCatalogBatchState({
      batchId: "stored-v6-diagnostics",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-31T10:00:00.000Z",
      extensionVersion: "0.1.7",
      mode: "BOUNDED_ACCEPTANCE",
      subjectLimit: 2,
    });
    const stored = JSON.parse(JSON.stringify(fresh)) as Record<string, unknown>;
    stored.status = "FAILED";
    stored.stateMachineCheckpoint = "FAILED";
    stored.expectedNavigationRevision = 1;
    stored.lastErrorMessage = "Cookie: session=stored-summary-secret";
    stored.lastFailureDiagnostic = {
      safeErrorName: "Error",
      safeErrorMessage: "Authorization: Bearer stored-message-secret",
      safeStack: "Error: api_key=stored-stack-secret",
      safeCause: "pairingCredential=stored-cause-secret",
      phase: "SUBJECT_SELECTION_STARTED",
      operation: "START_SUBJECT_SEARCH",
      checkpoint: "LANDING_READY",
      runRevision: "phase15b-main-world-checkpoint-v9",
      navigationRevision: 1,
      timestamp: "2026-08-31T10:00:01.000Z",
    };

    const restored = restoreCatalogBatchState(
      stored,
      "2026-08-31T10:01:00.000Z",
    );
    const diagnostic = JSON.stringify({
      lastErrorMessage: restored.lastErrorMessage,
      lastFailureDiagnostic: restored.lastFailureDiagnostic,
    });

    expect(diagnostic).toContain("[SECRET_REDACTED]");
    expect(diagnostic).not.toMatch(
      /stored-(?:summary|message|stack|cause)-secret/,
    );
  });

  it("drops invalid v6 diagnostic enum values when restoring stored state", () => {
    const fresh = createCatalogBatchState({
      batchId: "invalid-v6-diagnostics",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-31T10:00:00.000Z",
      extensionVersion: "0.1.7",
      mode: "BOUNDED_ACCEPTANCE",
      subjectLimit: 2,
    });
    const stored = JSON.parse(JSON.stringify(fresh)) as Record<string, unknown>;
    stored.lastSuccessfulCheckpoint = "NOT_A_CHECKPOINT";
    stored.failedOperation = "NOT_AN_OPERATION";
    stored.lastFailureDiagnostic = {
      safeErrorName: "Error",
      safeErrorMessage: "safe",
      safeStack: "",
      safeCause: null,
      phase: "NOT_A_CHECKPOINT",
      operation: "NOT_AN_OPERATION",
      checkpoint: "NOT_A_CHECKPOINT",
      runRevision: "phase15b-main-world-checkpoint-v9",
      navigationRevision: 1,
      timestamp: "2026-08-31T10:00:01.000Z",
    };

    const restored = restoreCatalogBatchState(
      stored,
      "2026-08-31T10:01:00.000Z",
    );

    expect(restored.lastSuccessfulCheckpoint).toBe(
      "SUBJECT_DISCOVERY_COMPLETED",
    );
    expect(restored.failedOperation).toBeNull();
    expect(restored.lastFailureDiagnostic).toBeNull();
  });

  it("records local-only apply counts and advances each discovered subject deterministically", () => {
    const accepted = acceptCatalogPage(
      createCatalogBatchState({
        apiBaseUrl: "http://localhost:8000",
        studentProfileId: "00000000-0000-4000-8000-000000000702",
        tabId: 41,
        landingUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Courses",
        subjects: subjectOptions,
        startedAt: "2026-08-26T02:00:00.000Z",
      }),
      page(1, 1, [accountingRecord()]),
    );

    const next = completeCatalogSubject(accepted, {
      importRunId: "11111111-1111-4111-8111-111111111111",
      reviewSessionId: "22222222-2222-4222-8222-222222222222",
      createdCount: 1,
      updatedCount: 0,
      processingStagesCompleted: [
        "LOCAL_STAGING",
        "LOCAL_VALIDATION",
        "LOCAL_REVIEW",
        "LOCAL_DRY_RUN",
        "LOCAL_APPLY",
        "MYPROGRESS_REMAP",
      ],
      stagedRecordCount: 1,
      reviewValidCount: 1,
      reviewWarningCount: 0,
      appliedRecordCount: 1,
      myprogressRunId: "33333333-3333-4333-8333-333333333333",
      myprogressTotalCount: 118,
      myprogressMappedBeforeCount: 34,
      myprogressMappedCount: 35,
      myprogressUnmatchedCount: 83,
      myprogressRemapExecuted: true,
      reasonCodes: [],
      providerActionsWritten: "NO",
      completedAt: "2026-08-26T02:01:00.000Z",
    });

    expect(next).toMatchObject({
      status: "RUNNING",
      currentSubjectIndex: 1,
      completedSubjects: ["ACCT"],
      pendingRecords: [],
      localImportsApplied: 1,
      localCoursesCreated: 1,
      localCoursesUpdated: 0,
      localStagedCount: 1,
      localReviewValidCount: 1,
      localReviewWarningCount: 0,
      localAppliedCount: 1,
      myprogressTotalCount: 118,
      myprogressMappedBeforeCount: 34,
      myprogressMappedCount: 35,
      myprogressUnmatchedCount: 83,
      myprogressRemapExecuted: true,
      providerActionsWritten: "NO",
    });
  });

  it("restores an interrupted running batch as paused instead of resuming secretly", () => {
    const running = createCatalogBatchState({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl: "https://kean-ss.colleague.elluciancloud.com/Student/Courses",
      subjects: subjectOptions,
      startedAt: "2026-08-26T02:00:00.000Z",
    });

    const restored = restoreCatalogBatchState(
      JSON.parse(JSON.stringify(running)),
      "2026-08-26T02:02:00.000Z",
    );

    expect(restored).toMatchObject({
      status: "PAUSED",
      lastErrorCode: "BATCH_CATALOG_WORKER_RESTART",
      providerActionsWritten: "NO",
    });
    expect(restored.warnings).toContain("BATCH_CATALOG_WORKER_RESTART");
  });
});
