import { describe, expect, it } from "vitest";

import {
  beginCatalogSubject,
  handleAuthorizedCatalogTabClosed,
  handleCatalogPageSignal,
  handleCatalogSubjectNavigationSignal,
  handleCatalogTabLoaded,
  recordCatalogTabUpdate,
  resumeCatalogBatchEventDriven,
  type CatalogBatchEventDriver,
} from "../src/background/catalog-batch-controller.js";
import {
  catalogPreparationCheckpointToken,
  createCatalogBatchState,
  pauseCatalogBatch,
  type CatalogBatchPage,
  type CatalogBatchState,
} from "../src/content/catalog-batch.js";
import type {
  CatalogPageSignal,
  CatalogSubjectNavigationSignal,
} from "../src/content/catalog-batch-page.js";
import type { BrowserExtensionExtraction } from "../src/shared/types.js";

const landingUrl =
  "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses";
const resultUrl = `${landingUrl}/SearchResult`;
const subjectNavigationDiagnostics = {
  documentReady: true,
  subjectControlPresent: true,
  expectedSubjectSelected: true,
  catalogListingControlPresent: true,
  catalogListingChecked: true,
  submitControlPresent: true,
  submitControlEnabled: true,
  preparationSignalObserved: true,
  resultSurfacePresent: false,
  resultListPresent: false,
  courseCardCount: 0,
  validCourseIdentityCount: 0,
  sectionResultPresent: false,
} as const;

function page(
  subjectCode: string,
  pageNumber: number,
  totalPages: number,
  courseCodes: string[],
): CatalogBatchPage {
  const extraction: BrowserExtensionExtraction = {
    pageType: "KEAN_COURSE_CATALOG_PAGE",
    importType: "COURSE_CATALOG",
    sourceType: "BROWSER_EXTENSION",
    sourceLabel: "KEAN_STUDENT_PORTAL",
    isOfficial: false,
    title: "Course Catalog",
    url: resultUrl,
    fileName: "catalog.csv",
    fileMimeType: "text/csv",
    content: "",
    records: courseCodes.map((code) => ({
      course_code: code,
      course_title: `Visible ${code}`,
      credits: "3",
      raw_requisites: "None",
      rule_review_status: "REVIEW_REQUIRED",
    })),
    warnings: [],
    diagnostics: {
      currentUrl: resultUrl,
      detectedPageType: "KEAN_COURSE_CATALOG_PAGE",
      matchedPageMarker: "/Student/Student/Courses/SearchResult",
      tablesFound: 0,
      rowsFound: courseCodes.length,
      visibleTextLength: 0,
      rowLikeBlocksFound: courseCodes.length,
      extractedAcademicFieldCount: courseCodes.length * 4,
      ignoredSensitiveFieldCount: 0,
      directSnapshotRan: true,
      bounded: false,
      warningCodes: [],
      academicTablesDetected: 1,
      academicTablesParsed: 1,
      academicRowsParsed: courseCodes.length,
      academicRowsSkipped: 0,
      academicRowsCapped: 0,
      parserWarningCodes: [],
    },
    requiresReview: true,
    extractedAt: `2026-08-27T09:00:0${pageNumber}.000Z`,
  };
  return { subjectCode, pageNumber, totalPages, fatalSignal: null, extraction };
}

function initialState(): CatalogBatchState {
  return createCatalogBatchState({
    apiBaseUrl: "http://127.0.0.1:8000",
    studentProfileId: "00000000-0000-4000-8000-000000000702",
    tabId: 41,
    landingUrl,
    subjects: [
      { code: "ACCT", label: "Accounting" },
      { code: "AD", label: "Advertising" },
      { code: "ART", label: "Art" },
    ],
    startedAt: "2026-08-27T09:00:00.000Z",
    mode: "BOUNDED_ACCEPTANCE",
    subjectLimit: 2,
  });
}

function readySignal(
  state: CatalogBatchState,
  pageNumber: number,
  totalPages: number,
  marker: string,
): CatalogPageSignal {
  const secondMarker = marker.replace(/-[^-]+$/, "-TAIL");
  return {
    type: "SAPSOS_CATALOG_PAGE_SIGNAL",
    batchId: state.batchId,
    signal: "READY",
    navigationRevision: state.expectedNavigationRevision,
    subjectCode: state.subjects[state.currentSubjectIndex]?.code ?? null,
    pageNumber,
    totalPages,
    visibleCourseCount: 2,
    firstCourseMarker: marker,
    lastCourseMarker: secondMarker,
    resultFingerprint: `${marker}\u001f${secondMarker}`,
    diagnostics: {
      expectedSubject:
        state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN",
      expectedPage: pageNumber,
      searchResultNavigationReceived: true,
      searchResultUrlMatch: true,
      searchResultDomReady: true,
      visibleSubject:
        state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN",
      visibleSubjectSource: "COURSE_CARD_ID",
      pageNumber,
      pageNumberSource: "CURRENT_PAGE_INPUT",
      courseCardCount: 2,
      validCourseIdentityCount: 2,
      courseResultContainerPresent: true,
      resultContainerConnected: true,
      spinnerPresent: false,
      spinnerVisible: false,
      spinnerSelector:
        '[aria-busy="true"], .loading, .spinner, .esg-spinner-container',
      spinnerNodeCount: 0,
      spinnerComputedDisplay: null,
      spinnerComputedVisibility: null,
      spinnerComputedOpacity: null,
      spinnerClientRect: null,
      spinnerAriaHidden: null,
      spinnerBlocksResultInteraction: false,
      spinnerIsCatalogResultsSpinner: false,
      spinnerHardGateValid: false,
      spinnerClassification: "NON_BLOCKING",
      resultHeading: "Course Catalog",
      resultSummary: null,
      pageFingerprint: `${marker}\u001f${secondMarker}`,
      previousPageFingerprint: null,
      knockoutReady: true,
      domStable: true,
      domStableDurationMs: 300,
      contentStable: true,
      contentStabilityDurationMs: 300,
      contentScriptRevision: "phase15b-main-world-checkpoint-v9",
      runnerRevision: state.runnerRevision,
      expectedRevision: state.expectedNavigationRevision,
      pageReadyGateFailedOn: null,
      readyPredicatesPassing: [
        "RESULT_CONTAINER",
        "VALID_COURSE_IDENTITY_COUNT",
        "CONTENT_STABLE",
      ],
      failedPredicate: null,
      currentPageTimeoutRootCause: null,
    },
    providerActionsWritten: "NO",
  };
}

function driver(): CatalogBatchEventDriver & {
  state: CatalogBatchState;
  events: string[];
  tabUrl: string | null;
  watchSubjectNavigation: (
    state: CatalogBatchState,
    navigationRevision: number,
  ) => Promise<void>;
} {
  const events: string[] = [];
  const value: CatalogBatchEventDriver & {
    state: CatalogBatchState;
    events: string[];
    tabUrl: string | null;
    watchSubjectNavigation: (
      state: CatalogBatchState,
      navigationRevision: number,
    ) => Promise<void>;
  } = {
    state: initialState(),
    events,
    tabUrl: landingUrl,
    now: () => "2026-08-27T09:00:30.000Z",
    loadState: async () => value.state,
    persistState: async (state) => {
      value.state = state;
      events.push(`persist:${state.lastTransition}`);
    },
    getAuthorizedTabUrl: async () => value.tabUrl,
    navigateToLanding: async () => {
      value.tabUrl = landingUrl;
      events.push("navigate:landing");
    },
    watchSubjectNavigation: async (_state, navigationRevision) => {
      events.push(`watch-subject:${navigationRevision}`);
    },
    startSubjectSearch: async (_state, subject) => {
      value.tabUrl = resultUrl;
      value.state = {
        ...value.state,
        preparationCheckpointRevision: value.state.expectedNavigationRevision,
        stateMachineCheckpoint: "SEARCH_SUBMIT_STARTED",
        lastSuccessfulCheckpoint: "CATALOG_LISTING_VERIFIED",
      };
      events.push(`search:${subject.code}`);
      return {
        preparation: {
          action: "CATALOG_SEARCH_PREPARED",
          subjectCode: subject.code,
          completedCheckpoints: [
            "LANDING_DOM_READY",
            "KNOCKOUT_READY",
            "SUBJECT_SELECTED",
            "SUBJECT_SELECTION_VERIFIED",
            "CATALOG_LISTING_SELECTED",
            "CATALOG_LISTING_VERIFIED",
          ],
          providerActionsWritten: "NO",
        },
        preparationResultKind: "VALUE",
        submissionResultKind: "VALUE",
      };
    },
    watchResultPage: async (_state, expectedPage) => {
      events.push(`watch:${expectedPage}`);
    },
    capturePage: async (state, subject, expectedPage, expectedFingerprint) => {
      events.push(`capture:${expectedPage}:${expectedFingerprint}`);
      const totalPages = state.totalPagesForCurrentSubject ?? 2;
      return subject.code === "ACCT"
        ? page(
            subject.code,
            expectedPage,
            totalPages,
            expectedPage === 1 ? ["ACCT 2200"] : ["ACCT 2200", "ACCT 3300"],
          )
        : page(subject.code, 1, 1, ["AD 1000"]);
    },
    advancePage: async (_state, targetPage) => {
      events.push(`page:${targetPage}`);
    },
    processSubject: async (state, extraction) => {
      events.push(`process:${state.subjects[state.currentSubjectIndex]?.code}`);
      return {
        importRunId: `import-${state.currentSubjectIndex}`,
        reviewSessionId: `review-${state.currentSubjectIndex}`,
        createdCount: extraction.records.length,
        updatedCount: 0,
        processingStagesCompleted: [
          "LOCAL_STAGING",
          "LOCAL_VALIDATION",
          "LOCAL_REVIEW",
          "LOCAL_DRY_RUN",
          "LOCAL_APPLY",
          "MYPROGRESS_REMAP",
        ],
        stagedRecordCount: extraction.records.length,
        reviewValidCount: extraction.records.length,
        reviewWarningCount: 0,
        appliedRecordCount: extraction.records.length,
        myprogressRunId: "myprogress-1",
        myprogressTotalCount: 118,
        myprogressMappedBeforeCount: 34,
        myprogressMappedCount: 35,
        myprogressUnmatchedCount: 83,
        myprogressRemapExecuted: true,
        reasonCodes: [],
        providerActionsWritten: "NO",
        completedAt: "2026-08-27T09:00:30.000Z",
      };
    },
  };
  return value;
}

describe("event-driven Catalog batch controller", () => {
  it("starts ACCT from a fresh 116-subject v7 run and records the startup checkpoint", async () => {
    const value = driver();
    const subjects = Array.from({ length: 116 }, (_, index) =>
      index === 0
        ? { code: "ACCT", label: "Accounting" }
        : {
            code: `S${String(index).padStart(3, "0")}`,
            label: `Subject ${index}`,
          },
    );
    value.state = createCatalogBatchState({
      batchId: "fresh-v7-116-subjects",
      apiBaseUrl: "http://127.0.0.1:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      subjects,
      startedAt: "2026-08-31T10:00:00.000Z",
      extensionVersion: "0.1.7",
      mode: "BOUNDED_ACCEPTANCE",
      subjectLimit: 2,
    });

    await beginCatalogSubject(value.state, value);

    expect(value.events).toContain("watch-subject:1");
    expect(value.events).toContain("search:ACCT");
    expect(value.state).toMatchObject({
      status: "RUNNING",
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      currentSubjectIndex: 0,
      expectedNavigationRevision: 1,
      navigationTimeoutRevision: 1,
      contentReadyRevision: 1,
      stateMachineCheckpoint: "SEARCH_SUBMITTED",
      lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
      failedOperation: null,
      lastFailureDiagnostic: null,
    });
  });

  it("persists the exact safe diagnostic when first-subject startup throws an unexpected Error", async () => {
    const value = driver();
    value.startSubjectSearch = async () => {
      const error = new TypeError(
        "Cannot read landing control at https://portal.example/private?token=redacted",
      );
      error.name = "TypeError at C:\\Users\\student\\private.txt";
      error.stack =
        "TypeError: Cannot read landing control\n    at chrome-extension://abcdefghijklmnopabcdefghijklmnop/dist/background/service-worker.js:42:7";
      throw error;
    };

    await beginCatalogSubject(value.state, value);

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_SEARCH_TRIGGER_FAILED",
      lastSuccessfulCheckpoint: "LANDING_READY",
      failedOperation: "START_SUBJECT_SEARCH",
      stateMachineCheckpoint: "FAILED",
      lastFailureDiagnostic: {
        safeErrorName: "TypeError at [PATH_REDACTED]",
        safeErrorMessage: "Cannot read landing control at [URL_REDACTED]",
        phase: "SUBJECT_SELECTION_STARTED",
        operation: "START_SUBJECT_SEARCH",
        checkpoint: "LANDING_READY",
        runRevision: "phase15b-main-world-checkpoint-v9",
        navigationRevision: 1,
        timestamp: "2026-08-27T09:00:30.000Z",
      },
      providerActionsWritten: "NO",
    });
    expect(
      (
        value.state as unknown as {
          lastFailureDiagnostic: { safeStack: string };
        }
      ).lastFailureDiagnostic.safeStack,
    ).not.toContain("chrome-extension://abcdefghijklmnopabcdefghijklmnop");
  });

  it("maps a startup storage write failure without losing the last durable checkpoint", async () => {
    const value = driver();
    const persist = value.persistState;
    let failedOnce = false;
    value.persistState = async (state) => {
      if (
        !failedOnce &&
        state.stateMachineCheckpoint === "SUBJECT_SELECTION_STARTED"
      ) {
        failedOnce = true;
        throw new Error("BATCH_CATALOG_STORAGE_UNAVAILABLE");
      }
      await persist(state);
    };

    await beginCatalogSubject(value.state, value);

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_STATE_PERSIST_FAILED",
      lastSuccessfulCheckpoint: "LANDING_READY",
      failedOperation: "PERSIST_STATE",
      lastFailureDiagnostic: {
        safeErrorName: "Error",
        safeErrorMessage: "BATCH_CATALOG_STORAGE_UNAVAILABLE",
        operation: "PERSIST_STATE",
      },
    });
    expect(value.events).not.toContain("search:ACCT");
  });

  it("starts the first subject after discovery without depending on the popup", async () => {
    const value = driver();

    await beginCatalogSubject(value.state, value);

    expect(value.events).toEqual([
      "persist:SUBJECTS_DISCOVERED",
      "persist:SUBJECT_NAVIGATION_REQUESTED",
      "watch-subject:1",
      "persist:SUBJECT_NAVIGATION_REQUESTED",
      "search:ACCT",
      "persist:SUBJECT_NAVIGATION_REQUESTED",
    ]);
    expect(value.state.currentPage).toBe(1);
    expect(value.state).toMatchObject({
      expectedNavigationRevision: 1,
      contentReadyRevision: 1,
      navigationTimeoutRevision: 1,
    });
  });

  it("continues from a tab-load event after the popup response lifecycle ended", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.events.length = 0;

    await handleCatalogTabLoaded(41, resultUrl, value);

    expect(value.events).toEqual([
      "persist:WAITING_FOR_RESULT_PAGE",
      "watch:1",
    ]);
  });

  it("ignores a duplicate SearchResult completion event for the same revision", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    value.events.length = 0;

    await handleCatalogTabLoaded(41, resultUrl, value);

    expect(value.events).toEqual([]);
    expect(value.state).toMatchObject({
      status: "RUNNING",
      lastTransition: "WAITING_FOR_RESULT_PAGE",
      expectedNavigationRevision: 1,
    });
  });

  it("records the authorized tab loading revision without changing the lifecycle transition", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.events.length = 0;

    await recordCatalogTabUpdate(41, "loading", value);

    expect(value.state).toMatchObject({
      expectedNavigationRevision: 1,
      currentNavigationRevision: 1,
      lastTabUpdateStatus: "loading",
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      stateMachineCheckpoint: "SEARCH_SUBMITTED",
    });
  });

  it("persists a current-revision preparation checkpoint before navigation is allowed", async () => {
    const value = driver();
    value.state = {
      ...value.state,
      expectedNavigationRevision: 1,
      navigationTimeoutRevision: 1,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      stateMachineCheckpoint: "SUBJECT_SELECTION_STARTED",
      lastSuccessfulCheckpoint: "LANDING_READY",
    };

    await handleCatalogSubjectNavigationSignal(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: value.state.batchId,
        navigationRevision: 1,
        signal: "PREPARATION_VERIFIED",
        checkpointToken: catalogPreparationCheckpointToken(
          value.state.batchId,
          1,
          "ACCT",
        ),
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        completedCheckpoints: [
          "LANDING_DOM_READY",
          "KNOCKOUT_READY",
          "SUBJECT_SELECTED",
          "SUBJECT_SELECTION_VERIFIED",
          "CATALOG_LISTING_SELECTED",
          "CATALOG_LISTING_VERIFIED",
        ],
        providerActionsWritten: "NO",
      } as unknown as CatalogSubjectNavigationSignal,
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "RUNNING",
      preparationCheckpointRevision: 1,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      stateMachineCheckpoint: "SEARCH_SUBMIT_STARTED",
      lastSuccessfulCheckpoint: "CATALOG_LISTING_VERIFIED",
    });
  });

  it("pauses when the current revision remains on the landing page until the navigation watchdog expires", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.tabUrl = landingUrl;

    await handleCatalogSubjectNavigationSignal(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: value.state.batchId,
        navigationRevision: 1,
        signal: "TIMEOUT",
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        diagnostics: subjectNavigationDiagnostics,
        providerActionsWritten: "NO",
      },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "PAUSED",
      pauseReason: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      lastErrorCode: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      expectedNavigationRevision: 1,
    });
  });

  it("ignores a stale navigation timeout revision", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.tabUrl = landingUrl;
    value.events.length = 0;

    await handleCatalogSubjectNavigationSignal(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: value.state.batchId,
        navigationRevision: 0,
        signal: "TIMEOUT",
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        diagnostics: subjectNavigationDiagnostics,
        providerActionsWritten: "NO",
      },
      41,
      value,
    );

    expect(value.events).toEqual([]);
    expect(value.state.status).toBe("RUNNING");
  });

  it("ignores a tab switch or unrelated tab update", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.events.length = 0;

    await handleCatalogTabLoaded(99, "https://example.com/", value);

    expect(value.events).toEqual([]);
    expect(value.state.status).toBe("RUNNING");
  });

  it("keeps the authorized SearchResult tab valid while a running batch waits for page 2", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    await handleCatalogPageSignal(
      readySignal(value.state, 1, 2, "course-ACCT-2200"),
      41,
      value,
    );
    value.events.length = 0;

    await handleCatalogTabLoaded(41, resultUrl, value);

    expect(value.state).toMatchObject({
      status: "RUNNING",
      currentPage: 2,
      expectedNavigationRevision: 2,
      lastTransition: "PAGE_NAVIGATION_REQUESTED",
      pauseReason: null,
    });
    expect(value.events).toEqual([]);
  });

  it("pauses safely for manual reauthentication when the authorized tab reaches login", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    value.events.length = 0;

    await handleCatalogTabLoaded(
      41,
      "https://kean-ss.colleague.elluciancloud.com/Account/Login",
      value,
    );

    expect(value.state).toMatchObject({
      status: "PAUSED",
      pauseReason: "MANUAL_REAUTH_REQUIRED",
      lastErrorCode: "BATCH_CATALOG_AUTH_REDIRECT",
    });
    expect(value.events).not.toContain("search:ACCT");
  });

  it("pauses when the authorized tab leaves the reviewed Catalog scope", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);

    await handleCatalogTabLoaded(
      41,
      "https://kean-ss.colleague.elluciancloud.com/Student/Planning/DegreePlans",
      value,
    );

    expect(value.state).toMatchObject({
      status: "PAUSED",
      pauseReason: "AUTHORIZED_TAB_OUT_OF_SCOPE",
      lastErrorCode: "BATCH_CATALOG_TAB_OUT_OF_SCOPE",
    });
  });

  it("fails closed when SearchResult belongs to a different subject", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    value.events.length = 0;

    await handleCatalogPageSignal(
      {
        ...readySignal(value.state, 1, 1, "course-AD-1000"),
        subjectCode: "AD",
      },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_PAGE_SUBJECT_MISMATCH",
      providerActionsWritten: "NO",
    });
    expect(value.events.some((event) => event.startsWith("capture:"))).toBe(
      false,
    );
  });

  it("attributes an unexpected page capture exception to the capture operation", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    value.capturePage = async () => {
      throw new TypeError("capture bridge unavailable");
    };

    await handleCatalogPageSignal(
      readySignal(value.state, 1, 1, "course-ACCT-2200"),
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_CONTENT_SCRIPT_UNAVAILABLE",
      failedOperation: "CAPTURE_PAGE",
      lastFailureDiagnostic: {
        safeErrorName: "TypeError",
        safeErrorMessage: "capture bridge unavailable",
        operation: "CAPTURE_PAGE",
      },
      providerActionsWritten: "NO",
    });
  });

  it("fails closed when the visible page number mismatches the checkpoint", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    await handleCatalogPageSignal(
      {
        ...readySignal(value.state, 1, 2, "course-ACCT-2200"),
        signal: "PAGE_NUMBER_MISMATCH",
        pageNumber: 2,
        diagnostics: {
          ...readySignal(value.state, 1, 2, "course-ACCT-2200").diagnostics,
          pageNumber: 2,
          pageReadyGateFailedOn: "PAGE_NUMBER_MISMATCH",
        },
      },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_PAGE_NUMBER_MISMATCH",
      currentPage: 1,
      providerActionsWritten: "NO",
    });
  });

  it("ignores a stale page-ready signal from an older navigation revision", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    value.events.length = 0;
    const staleSignal = {
      ...readySignal(value.state, 1, 2, "course-ACCT-2200"),
      navigationRevision: value.state.expectedNavigationRevision - 1,
    } as CatalogPageSignal & { navigationRevision: number };

    await handleCatalogPageSignal(staleSignal, 41, value);

    expect(value.state).toMatchObject({
      status: "RUNNING",
      lastTransition: "WAITING_FOR_RESULT_PAGE",
      coursesCaptured: 0,
    });
    expect(value.events).toEqual([]);
  });

  it("captures a stable checkpoint-bound page before requesting page 2", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    const signal = readySignal(value.state, 1, 2, "course-card01");
    signal.subjectCode = "ACCT";
    signal.diagnostics = {
      ...signal.diagnostics,
      visibleSubject: null,
      visibleSubjectSource: "CHECKPOINT_BOUND",
      knockoutReady: false,
    };

    await handleCatalogPageSignal(signal, 41, value);

    expect(value.events).toContain("capture:1:course-card01\u001fcourse-TAIL");
    expect(value.events).toContain("persist:PAGE_CAPTURED");
    expect(value.events).toContain("page:2");
    expect(value.state).toMatchObject({
      status: "RUNNING",
      lastTransition: "PAGE_NAVIGATION_REQUESTED",
      currentPage: 2,
      providerActionsWritten: "NO",
    });
  });

  it("advances a multi-page subject, deduplicates overlap, then starts the next subject", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    await handleCatalogPageSignal(
      readySignal(value.state, 1, 2, "course-ACCT-2200"),
      41,
      value,
    );
    expect(value.events).toContain(
      "capture:1:course-ACCT-2200\u001fcourse-ACCT-TAIL",
    );
    expect(value.events).toContain("page:2");

    await handleCatalogPageSignal(
      readySignal(value.state, 2, 2, "course-ACCT-3300"),
      41,
      value,
    );
    expect(value.events).toContain(
      "capture:2:course-ACCT-3300\u001fcourse-ACCT-TAIL",
    );
    expect(value.state).toMatchObject({
      completedSubjects: ["ACCT"],
      coursesCaptured: 3,
      uniqueCourses: 2,
      duplicatesIgnored: 1,
      status: "RUNNING",
      lastTransition: "LANDING_NAVIGATION_REQUESTED",
    });

    await handleCatalogTabLoaded(41, landingUrl, value);
    expect(value.events).toContain("watch-subject:3");
    expect(value.events).toContain("search:AD");
    expect(value.state).toMatchObject({
      currentSubjectIndex: 1,
      expectedNavigationRevision: 3,
      contentReadyRevision: 3,
      navigationTimeoutRevision: 3,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
    });

    value.tabUrl = landingUrl;
    value.events.length = 0;
    await handleCatalogTabLoaded(41, landingUrl, value);
    expect(value.events).toEqual([]);
    expect(value.state).toMatchObject({
      status: "RUNNING",
      expectedNavigationRevision: 3,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
    });

    await handleCatalogSubjectNavigationSignal(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: value.state.batchId,
        navigationRevision: 1,
        signal: "TIMEOUT",
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        diagnostics: subjectNavigationDiagnostics,
        providerActionsWritten: "NO",
      },
      41,
      value,
    );
    expect(value.events).toEqual([]);
    expect(value.state.status).toBe("RUNNING");
  });

  it("captures all four pages once and confirms the final page before completing", async () => {
    const value = driver();
    value.state = { ...value.state, subjectLimit: 1 };
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    for (let pageNumber = 1; pageNumber <= 4; pageNumber += 1) {
      await handleCatalogPageSignal(
        readySignal(value.state, pageNumber, 4, `course-ACCT-${pageNumber}000`),
        41,
        value,
      );
    }

    expect(value.state).toMatchObject({
      status: "COMPLETED",
      completedSubjects: ["ACCT"],
      pagesCaptured: 4,
      expectedNavigationRevision: 4,
      processingStage: "COMPLETED",
      leaseStatus: "RELEASED",
    });
    expect(value.state.acceptedPageKeys).toEqual([
      "ACCT:1",
      "ACCT:2",
      "ACCT:3",
      "ACCT:4",
    ]);
    expect(
      value.events.filter((event) => event === "persist:LAST_PAGE_CONFIRMED"),
    ).toHaveLength(1);
  });

  it("completes the bounded two-subject acceptance before unlocking full capture", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    await handleCatalogPageSignal(
      readySignal(value.state, 1, 2, "course-ACCT-2200"),
      41,
      value,
    );
    await handleCatalogPageSignal(
      readySignal(value.state, 2, 2, "course-ACCT-3300"),
      41,
      value,
    );
    await handleCatalogTabLoaded(41, landingUrl, value);
    await handleCatalogTabLoaded(41, resultUrl, value);
    await handleCatalogPageSignal(
      readySignal(value.state, 1, 1, "course-AD-1000"),
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "COMPLETED",
      completedSubjects: ["ACCT", "AD"],
      boundedAcceptancePassed: true,
      providerActionsWritten: "NO",
    });
    expect(value.state.boundedAcceptanceRevision).toBe(
      "phase15b-main-world-checkpoint-v9",
    );
    expect(value.events).not.toContain("search:ART");
  });

  it("pauses on a bounded navigation timeout", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    await handleCatalogPageSignal(
      { ...readySignal(value.state, 1, 1, "unused"), signal: "TIMEOUT" },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "PAUSED",
      pauseReason: "BATCH_CATALOG_PAGE_TIMEOUT",
      lastTransition: "PAUSED",
    });
  });

  it("pauses when the authorized tab closes and retains resumable progress", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);

    await handleAuthorizedCatalogTabClosed(41, value);

    expect(value.state).toMatchObject({
      status: "PAUSED",
      pauseReason: "AUTHORIZED_CATALOG_TAB_CLOSED",
      lastErrorCode: "BATCH_CATALOG_TAB_CLOSED",
      currentSubjectIndex: 0,
      currentPage: 1,
    });
  });

  it("fails closed on a school rate-limit signal", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    await handleCatalogPageSignal(
      { ...readySignal(value.state, 1, 1, "unused"), signal: "RATE_LIMIT" },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_RATE_LIMIT",
      providerActionsWritten: "NO",
    });
    expect(value.events.some((event) => event.startsWith("process:"))).toBe(
      false,
    );
  });

  it("stops safely on a school provider-error signal", async () => {
    const value = driver();
    await beginCatalogSubject(value.state, value);
    await handleCatalogTabLoaded(41, resultUrl, value);

    await handleCatalogPageSignal(
      {
        ...readySignal(value.state, 1, 1, "unused"),
        signal: "PROVIDER_ERROR",
      },
      41,
      value,
    );

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_PROVIDER_ERROR",
      providerActionsWritten: "NO",
    });
    expect(value.events.some((event) => event.startsWith("process:"))).toBe(
      false,
    );
  });

  it("resumes by returning the same authorized tab to the landing page", async () => {
    const value = driver();
    value.state = {
      ...pauseCatalogBatch(value.state),
      currentSubjectIndex: 1,
      completedSubjects: ["ACCT"],
      expectedNavigationRevision: 2,
      contentReadyRevision: 2,
      navigationTimeoutRevision: 2,
    };
    value.tabUrl = resultUrl;

    await resumeCatalogBatchEventDriven(value.state, value);

    expect(value.state).toMatchObject({
      status: "RUNNING",
      lastTransition: "LANDING_NAVIGATION_REQUESTED",
      currentSubjectIndex: 1,
      completedSubjects: ["ACCT"],
      expectedNavigationRevision: 2,
    });
    expect(value.events).toContain("navigate:landing");

    value.events.length = 0;
    await handleCatalogTabLoaded(41, landingUrl, value);
    expect(value.events).toContain("watch-subject:3");
    expect(value.events).toContain("search:AD");
    expect(value.state).toMatchObject({
      status: "RUNNING",
      currentSubjectIndex: 1,
      completedSubjects: ["ACCT"],
      expectedNavigationRevision: 3,
      contentReadyRevision: 3,
      navigationTimeoutRevision: 3,
    });
  });

  it("fails checkpoint validation before resuming an older runner revision", async () => {
    const value = driver();
    value.state = {
      ...pauseCatalogBatch(value.state),
      runnerRevision: "phase15b-subject-transition-v2",
    };
    value.tabUrl = resultUrl;

    await resumeCatalogBatchEventDriven(value.state, value);

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_CHECKPOINT_INVALID",
    });
    expect(value.events).not.toContain("navigate:landing");
  });

  it("fails checkpoint validation before resuming accepted pages without fingerprints", async () => {
    const value = driver();
    value.state = {
      ...pauseCatalogBatch(value.state),
      currentPage: 1,
      acceptedPageKeys: ["ACCT:1"],
      acceptedPageFingerprints: {},
    };
    value.tabUrl = resultUrl;

    await resumeCatalogBatchEventDriven(value.state, value);

    expect(value.state).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_CHECKPOINT_INVALID",
    });
    expect(value.events).not.toContain("navigate:landing");
  });
});
