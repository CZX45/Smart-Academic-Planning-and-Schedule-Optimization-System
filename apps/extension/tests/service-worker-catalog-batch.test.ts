import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createCatalogBatchState,
  type CatalogBatchState,
  type CatalogSubject,
} from "../src/content/catalog-batch.js";
import type { AcademicPageSnapshot } from "../src/shared/types.js";

type MessageSender = { id?: string; tab?: { id?: number } };
type MessageListener = (
  message: unknown,
  sender: MessageSender,
  sendResponse: (response: unknown) => void,
) => boolean;
type UpdatedListener = (
  tabId: number,
  changeInfo: { status?: string; url?: string },
  tab: { id?: number; url?: string; title?: string },
) => void;

type StoredCatalogBatchArchive = {
  batchRunId: string;
  archiveStatus: "SUPERSEDED" | "COMPLETED" | "CANCELLED" | "FAILED";
  reason: string;
  originalStatus: CatalogBatchState["status"];
  runnerRevision: string;
  completedSubjects: string[];
  coursesCaptured: number;
  localImportRunIds: string[];
  providerActionsWritten: "NO";
};

type StoredCatalogBatchLifecycleNotice = {
  kind: "SUPERSEDED";
  batchRunId: string;
  previousStatus: CatalogBatchState["status"];
  previousRunnerRevision: string;
  currentRunnerRevision: string;
  reason: "SUPERSEDED_BY_NEW_REVISION";
  providerActionsWritten: "NO";
};

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

function pageSignalDiagnostics(
  expectedSubject: string,
  expectedPage: number,
  navigationRevision: number,
) {
  return {
    expectedSubject,
    expectedPage,
    searchResultNavigationReceived: true,
    searchResultUrlMatch: true,
    searchResultDomReady: true,
    visibleSubject: expectedSubject,
    visibleSubjectSource: "COURSE_CARD_ID" as const,
    pageNumber: expectedPage,
    pageNumberSource: "CURRENT_PAGE_INPUT" as const,
    courseCardCount: 1,
    validCourseIdentityCount: 1,
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
    spinnerClassification: "NON_BLOCKING" as const,
    resultHeading: "Course Catalog",
    resultSummary: null,
    pageFingerprint: `course-${expectedSubject}-2200`,
    previousPageFingerprint: null,
    knockoutReady: true,
    domStable: true,
    domStableDurationMs: 300,
    contentStable: true,
    contentStabilityDurationMs: 300,
    contentScriptRevision: "phase15b-main-world-checkpoint-v9",
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    expectedRevision: navigationRevision,
    pageReadyGateFailedOn: null,
    readyPredicatesPassing: [
      "RESULT_CONTAINER",
      "VALID_COURSE_IDENTITY_COUNT",
      "CONTENT_STABLE",
    ],
    failedPredicate: null,
    currentPageTimeoutRootCause: null,
  };
}

function runningStoredBatch(): CatalogBatchState {
  return createCatalogBatchState({
    apiBaseUrl: "http://localhost:8000",
    studentProfileId: "00000000-0000-4000-8000-000000000702",
    tabId: 41,
    landingUrl,
    subjects: [
      { code: "ACCT", label: "Accounting" },
      { code: "ANTH", label: "Anthropology" },
    ],
    startedAt: "2026-08-27T09:00:00.000Z",
    mode: "BOUNDED_ACCEPTANCE",
    subjectLimit: 2,
  });
}

function completedBoundedBatch(): CatalogBatchState {
  return {
    ...runningStoredBatch(),
    status: "COMPLETED",
    boundedAcceptancePassed: true,
    currentSubjectIndex: 2,
    completedSubjects: ["ACCT", "ANTH"],
    lastTransition: "COMPLETED",
  };
}

function currentCompletedBoundedBatch(): CatalogBatchState {
  return {
    ...completedBoundedBatch(),
    boundedAcceptanceRevision: "phase15b-main-world-checkpoint-v9",
  };
}

function catalogSnapshot(subject: string): AcademicPageSnapshot {
  return {
    title: "Course Catalog",
    url: resultUrl,
    visibleText: `${subject}*2200 Visible course (3 Credits) Requisites: None`,
    tables: [],
    headings: ["Course Catalog"],
    rowLikeBlocks: [
      {
        index: 0,
        section: "COURSE_CATALOG_CARD",
        text: `${subject}*2200 Visible course (3 Credits) Requisites: None`,
        cells: [
          `${subject}*2200 Visible course (3 Credits)`,
          "Visible sanitized description.",
          "Requisites: None",
        ],
      },
    ],
    warnings: [],
    snapshotMetadata: {
      directSnapshotRan: true,
      visibleTextLength: 64,
      rowLikeBlocksFound: 1,
      bounded: false,
    },
  };
}

async function loadWorker(
  options: {
    storedBatch?: CatalogBatchState;
    sessionLease?: { batchId: string };
    sidePanelFails?: boolean;
    fallbackTabFails?: boolean;
    tabReloadFails?: boolean;
    subjectSearchNavigates?: boolean;
    subjectSearchResult?: "VALUE" | "NULL" | "EMPTY";
    subjectSearchSignalsLoadingBeforeResult?: boolean;
    subjectSearchError?: Error;
    discoveredSubjects?: CatalogSubject[];
    storedArchives?: StoredCatalogBatchArchive[];
  } = {},
) {
  vi.resetModules();
  let messageListener: MessageListener | undefined;
  let updatedListener: UpdatedListener | undefined;
  let removedListener: ((tabId: number) => void) | undefined;
  let tabUrl = landingUrl;
  let currentSubject = "ACCT";
  let currentPage = 1;
  let localStored: {
    sapsosPairing: {
      apiBaseUrl: string;
      credential: string;
      protocolVersion: number;
    };
    catalogBatch?: CatalogBatchState;
    catalogBatchArchives?: StoredCatalogBatchArchive[];
    catalogBatchLifecycleNotice?: StoredCatalogBatchLifecycleNotice;
  } = {
    sapsosPairing: {
      apiBaseUrl: "http://localhost:8000",
      credential: "worker-only-credential",
      protocolVersion: 1,
    },
    ...(options.storedBatch ? { catalogBatch: options.storedBatch } : {}),
    ...(options.storedArchives
      ? { catalogBatchArchives: options.storedArchives }
      : {}),
  };
  let sessionStored: { catalogBatchLease?: { batchId: string } } = {
    ...(options.sessionLease
      ? { catalogBatchLease: options.sessionLease }
      : {}),
  };
  const executedFunctions: string[] = [];
  const scriptCalls: Array<{
    name: string;
    world: string | null;
    args: Record<string, unknown>;
  }> = [];
  const createdTabs: string[] = [];
  const reloadedTabs: number[] = [];
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/v1/data-imports")) {
      return Response.json({
        id: `11111111-1111-4111-8111-${currentSubject === "ACCT" ? "111111111111" : "222222222222"}`,
        record_count: 1,
      });
    }
    if (url.endsWith("/catalog-batch-process")) {
      return Response.json({
        status: "APPLIED",
        review_session: {
          id: `22222222-2222-4222-8222-${currentSubject === "ACCT" ? "111111111111" : "222222222222"}`,
        },
        application_result: {
          applied_records: [{ action: "CREATED", status: "SUCCESS" }],
        },
        confirmed_record_count: 1,
        blocked_record_count: 0,
        reason_codes: [],
        processing_stages_completed: [
          "LOCAL_STAGING",
          "LOCAL_VALIDATION",
          "LOCAL_REVIEW",
          "LOCAL_DRY_RUN",
          "LOCAL_APPLY",
          "MYPROGRESS_REMAP",
        ],
        staged_record_count: 1,
        review_valid_count: 1,
        review_warning_count: 0,
        applied_record_count: 1,
        myprogress_run_id: "33333333-3333-4333-8333-333333333333",
        myprogress_total_count: 118,
        myprogress_mapped_before_count: 34,
        myprogress_mapped_count: 35,
        myprogress_unmatched_count: 83,
        myprogress_remap_executed: true,
        already_processed: false,
        provider_actions_written: "NO",
      });
    }
    return Response.json({}, { status: 404 });
  });
  const runtimeApi: {
    id: string;
    lastError?: { message?: string };
    getURL: (path: string) => string;
    onInstalled: { addListener: ReturnType<typeof vi.fn> };
    onMessage: { addListener: (listener: MessageListener) => void };
  } = {
    id: "extension-id",
    getURL: (path: string) => `chrome-extension://extension-id/${path}`,
    onInstalled: { addListener: vi.fn() },
    onMessage: {
      addListener: (listener: MessageListener) => {
        messageListener = listener;
      },
    },
  };
  const chromeApi = {
    runtime: runtimeApi,
    storage: {
      local: {
        get: (_keys: string[], callback: (value: typeof localStored) => void) =>
          callback(localStored),
        set: (value: Partial<typeof localStored>, callback?: () => void) => {
          localStored = { ...localStored, ...value };
          callback?.();
        },
        remove: (keys: string[], callback?: () => void) => {
          if (keys.includes("catalogBatch")) delete localStored.catalogBatch;
          if (keys.includes("catalogBatchLifecycleNotice")) {
            delete localStored.catalogBatchLifecycleNotice;
          }
          callback?.();
        },
      },
      session: {
        get: (
          _keys: string[],
          callback: (value: typeof sessionStored) => void,
        ) => callback(sessionStored),
        set: (value: typeof sessionStored, callback?: () => void) => {
          sessionStored = { ...sessionStored, ...value };
          callback?.();
        },
        remove: (_keys: string[], callback?: () => void) => {
          sessionStored = {};
          callback?.();
        },
      },
    },
    tabs: {
      get: (
        tabId: number,
        callback: (tab: {
          id: number;
          url: string;
          title: string;
          windowId: number;
        }) => void,
      ) =>
        callback({
          id: tabId,
          url: tabUrl,
          title: "Course Catalog",
          windowId: 7,
        }),
      update: (
        tabId: number,
        update: { url: string },
        callback: (tab: { id: number; url: string }) => void,
      ) => {
        tabUrl = update.url;
        currentPage = 1;
        callback({ id: tabId, url: tabUrl });
      },
      reload: (
        tabId: number,
        _reloadProperties: Record<string, never>,
        callback: () => void,
      ) => {
        reloadedTabs.push(tabId);
        if (options.tabReloadFails) {
          runtimeApi.lastError = { message: "Edge refused Catalog navigation" };
        }
        callback();
        delete runtimeApi.lastError;
      },
      create: (input: { url: string }, callback?: () => void) => {
        createdTabs.push(input.url);
        if (options.fallbackTabFails) {
          runtimeApi.lastError = { message: "Edge refused extension tab" };
        }
        callback?.();
        delete runtimeApi.lastError;
      },
      onUpdated: {
        addListener: (listener: UpdatedListener) => {
          updatedListener = listener;
        },
      },
      onRemoved: {
        addListener: (listener: (tabId: number) => void) => {
          removedListener = listener;
        },
      },
    },
    scripting: {
      executeScript: (
        details: {
          func: { name: string };
          args: [Record<string, unknown>];
          world?: string;
        },
        callback: (results: Array<{ result: unknown }>) => void,
      ) => {
        executedFunctions.push(details.func.name);
        scriptCalls.push({
          name: details.func.name,
          world: details.world ?? null,
          args: details.args[0] ?? {},
        });
        if (details.func.name === "discoverCatalogSubjects") {
          callback([
            {
              result: {
                landingUrl,
                subjects: options.discoveredSubjects ?? [
                  { code: "ACCT", label: "Accounting" },
                  { code: "ANTH", label: "Anthropology" },
                  { code: "ART", label: "Art" },
                ],
                providerActionsWritten: "NO",
              },
            },
          ]);
          return;
        }
        if (details.func.name === "prepareCatalogSubjectSearch") {
          if (options.subjectSearchError) throw options.subjectSearchError;
          currentSubject = String(details.args[0]?.subjectCode ?? "ACCT");
          const submitCheckpoint = details.args[0]?.submitCheckpoint as
            | {
                batchId?: unknown;
                navigationRevision?: unknown;
                checkpointToken?: unknown;
              }
            | undefined;
          if (submitCheckpoint) {
            if (!messageListener) {
              throw new Error("Missing preparation checkpoint listener");
            }
            messageListener(
              {
                type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
                batchId: submitCheckpoint.batchId,
                navigationRevision: submitCheckpoint.navigationRevision,
                signal: "PREPARATION_VERIFIED",
                checkpointToken: submitCheckpoint.checkpointToken,
                currentPath: "/Student/Student/Courses",
                subjectCode: currentSubject,
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
              { id: "extension-id", tab: { id: 41 } },
              (response) => {
                if (
                  typeof response !== "object" ||
                  response === null ||
                  (response as { ok?: unknown }).ok !== true
                ) {
                  throw new Error("Preparation checkpoint was not accepted");
                }
                if (options.subjectSearchNavigates !== false)
                  tabUrl = resultUrl;
                currentPage = 1;
                if (options.subjectSearchSignalsLoadingBeforeResult) {
                  updatedListener?.(
                    41,
                    { status: "loading" },
                    { id: 41, url: resultUrl },
                  );
                }
                if (options.subjectSearchResult === "NULL") {
                  callback([{ result: null }]);
                  return;
                }
                if (options.subjectSearchResult === "EMPTY") {
                  callback([]);
                  return;
                }
                callback([
                  {
                    result: {
                      action: "CATALOG_SEARCH_PREPARED_AND_SUBMITTED",
                      subjectCode: currentSubject,
                      completedCheckpoints: [
                        "LANDING_DOM_READY",
                        "KNOCKOUT_READY",
                        "SUBJECT_SELECTED",
                        "SUBJECT_SELECTION_VERIFIED",
                        "CATALOG_LISTING_SELECTED",
                        "CATALOG_LISTING_VERIFIED",
                        "SEARCH_SUBMITTED",
                      ],
                      providerActionsWritten: "NO",
                    },
                  },
                ]);
              },
            );
            return;
          }
          callback([
            {
              result: {
                action: "CATALOG_SEARCH_PREPARED",
                subjectCode: currentSubject,
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
            },
          ]);
          return;
        }
        if (details.func.name === "watchCatalogSubjectNavigation") {
          callback([
            {
              result: {
                action: "CATALOG_SUBJECT_NAVIGATION_WATCH_STARTED",
                providerActionsWritten: "NO",
              },
            },
          ]);
          return;
        }
        if (details.func.name === "watchCatalogResultPage") {
          callback([
            {
              result: {
                action: "CATALOG_RESULT_WATCH_STARTED",
                providerActionsWritten: "NO",
              },
            },
          ]);
          return;
        }
        if (details.func.name === "inspectCatalogResultPage") {
          callback([
            {
              result: {
                ready: true,
                pageNumber: currentPage,
                totalPages: 1,
                visibleCourseCount: 1,
                subjectCode: currentSubject,
                firstCourseMarker: `course-${currentSubject}-2200`,
                lastCourseMarker: `course-${currentSubject}-2200`,
                resultFingerprint: `course-${currentSubject}-2200`,
                fatalSignal: null,
                providerActionsWritten: "NO",
              },
            },
          ]);
          return;
        }
        if (details.func.name === "snapshotVisibleAcademicPage") {
          callback([{ result: catalogSnapshot(currentSubject) }]);
          return;
        }
        if (details.func.name === "advanceCatalogResultPage") {
          currentPage = Number(details.args[0]?.targetPage ?? 2);
          callback([
            {
              result: {
                action: "CATALOG_PAGE_REQUESTED",
                targetPage: currentPage,
                previousFirstCourseMarker: `course-${currentSubject}-2200`,
                previousResultFingerprint: `course-${currentSubject}-2200`,
                providerActionsWritten: "NO",
              },
            },
          ]);
          return;
        }
        throw new Error(`Unexpected injected function ${details.func.name}`);
      },
    },
    sidePanel: {
      open: options.sidePanelFails
        ? vi.fn(async () => Promise.reject(new Error("unsupported")))
        : vi.fn(async () => undefined),
    },
  };
  vi.stubGlobal("chrome", chromeApi);
  vi.stubGlobal("fetch", fetchMock);
  await import("../src/background/service-worker.js");
  await Promise.resolve();
  if (!messageListener || !updatedListener || !removedListener) {
    throw new Error("Service worker event listeners were not registered.");
  }
  return {
    messageListener,
    updatedListener,
    removedListener,
    fetchMock,
    executedFunctions,
    scriptCalls,
    createdTabs,
    reloadedTabs,
    getStoredBatch: () => localStored.catalogBatch,
    getStoredArchives: () => localStored.catalogBatchArchives ?? [],
    getLifecycleNotice: () => localStored.catalogBatchLifecycleNotice,
    getSessionLease: () => sessionStored.catalogBatchLease,
  };
}

async function dispatch(
  listener: MessageListener,
  message: unknown,
  sender: MessageSender = { id: "extension-id" },
): Promise<unknown> {
  return await new Promise((resolve) => {
    listener(message, sender, resolve);
  });
}

async function settleEvents(): Promise<void> {
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("service worker event-driven Course Catalog batch", () => {
  it("completes the bounded run after handing discovery off from the popup", async () => {
    const worker = await loadWorker();

    const started = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    expect(started).toMatchObject({
      ok: true,
      status: 202,
      payload: {
        batchStatus: "RUNNING",
        currentSubject: "ACCT",
        currentPage: 1,
        lastTransition: "LANDING_NAVIGATION_REQUESTED",
      },
    });
    expect(worker.executedFunctions).toEqual(["discoverCatalogSubjects"]);
    expect(worker.reloadedTabs).toEqual([41]);
    expect(worker.getSessionLease()).toBeUndefined();

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();
    expect(worker.executedFunctions).toContain("prepareCatalogSubjectSearch");
    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      currentPage: 1,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: resultUrl },
    );
    await settleEvents();
    expect(worker.executedFunctions).toContain("watchCatalogResultPage");

    const firstBatchId = worker.getStoredBatch()?.batchId ?? "";
    await dispatch(
      worker.messageListener,
      {
        type: "SAPSOS_CATALOG_PAGE_SIGNAL",
        batchId: firstBatchId,
        signal: "READY",
        navigationRevision: 1,
        pageNumber: 1,
        totalPages: 1,
        visibleCourseCount: 1,
        subjectCode: "ACCT",
        firstCourseMarker: "course-ACCT-2200",
        lastCourseMarker: "course-ACCT-2200",
        resultFingerprint: "course-ACCT-2200",
        diagnostics: pageSignalDiagnostics("ACCT", 1, 1),
        providerActionsWritten: "NO",
      },
      { id: "extension-id", tab: { id: 41 } },
    );
    expect(worker.getStoredBatch()).toMatchObject({
      completedSubjects: ["ACCT"],
      status: "RUNNING",
      lastTransition: "LANDING_NAVIGATION_REQUESTED",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();
    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: resultUrl },
    );
    await settleEvents();
    await dispatch(
      worker.messageListener,
      {
        type: "SAPSOS_CATALOG_PAGE_SIGNAL",
        batchId: firstBatchId,
        signal: "READY",
        navigationRevision: 2,
        pageNumber: 1,
        totalPages: 1,
        visibleCourseCount: 1,
        subjectCode: "ANTH",
        firstCourseMarker: "course-ANTH-2200",
        lastCourseMarker: "course-ANTH-2200",
        resultFingerprint: "course-ANTH-2200",
        diagnostics: pageSignalDiagnostics("ANTH", 1, 2),
        providerActionsWritten: "NO",
      },
      { id: "extension-id", tab: { id: 41 } },
    );

    expect(worker.getStoredBatch()).toMatchObject({
      status: "COMPLETED",
      completedSubjects: ["ACCT", "ANTH"],
      boundedAcceptancePassed: true,
      processingStage: "COMPLETED",
      completedProcessingStages: [
        "CAPTURE_COMPLETED",
        "LOCAL_STAGING",
        "LOCAL_VALIDATION",
        "LOCAL_REVIEW",
        "LOCAL_DRY_RUN",
        "LOCAL_APPLY",
        "MYPROGRESS_REMAP",
        "COMPLETED",
      ],
      localStagedCount: 2,
      localReviewValidCount: 2,
      localReviewWarningCount: 0,
      localAppliedCount: 2,
      myprogressTotalCount: 118,
      myprogressMappedBeforeCount: 34,
      myprogressMappedCount: 35,
      myprogressUnmatchedCount: 83,
      myprogressRemapExecuted: true,
      leaseStatus: "RELEASED",
      providerActionsWritten: "NO",
    });
    expect(worker.fetchMock).toHaveBeenCalledTimes(4);
    expect(worker.getSessionLease()).toBeUndefined();
  });

  it("preinstalls a revisioned navigation watchdog before starting ACCT in the page main world", async () => {
    const worker = await loadWorker();
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.scriptCalls.slice(-2)).toEqual([
      {
        name: "watchCatalogSubjectNavigation",
        world: "ISOLATED",
        args: expect.objectContaining({
          batchId: expect.any(String),
          expectedSubject: "ACCT",
          navigationRevision: 1,
          checkpointToken: expect.stringMatching(/:1:ACCT$/),
          timeoutMs: 20_000,
        }),
      },
      {
        name: "prepareCatalogSubjectSearch",
        world: "MAIN",
        args: expect.objectContaining({
          subjectCode: "ACCT",
          readyTimeoutMs: 20_000,
          settleMs: 300,
          submitCheckpoint: expect.objectContaining({
            navigationRevision: 1,
            checkpointToken: expect.stringMatching(/:1:ACCT$/),
            acknowledgmentTimeoutMs: 1_500,
          }),
        }),
      },
    ]);
    expect(worker.getStoredBatch()).toMatchObject({
      expectedNavigationRevision: 1,
      contentReadyRevision: 1,
      navigationTimeoutRevision: 1,
      preparationCheckpointRevision: 1,
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
    });
  });

  it("maps a synchronous MAIN-world executeScript failure to the exact startup operation", async () => {
    const worker = await loadWorker({
      subjectSearchError: new TypeError(
        "Cannot serialize the first-subject startup function",
      ),
    });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
      lastSuccessfulCheckpoint: "LANDING_READY",
      failedOperation: "START_SUBJECT_SEARCH",
      lastFailureDiagnostic: {
        safeErrorName: "TypeError",
        safeErrorMessage: "Cannot serialize the first-subject startup function",
        operation: "START_SUBJECT_SEARCH",
        navigationRevision: 1,
      },
      providerActionsWritten: "NO",
    });
  });

  it("does not fail when navigation replaces the MAIN-world result with null", async () => {
    const worker = await loadWorker({ subjectSearchResult: "NULL" });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      failedOperation: null,
      lastFailureDiagnostic: null,
      providerActionsWritten: "NO",
    });

    worker.updatedListener(
      41,
      { status: "loading" },
      { id: 41, url: resultUrl },
    );
    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: resultUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      lastTransition: "WAITING_FOR_RESULT_PAGE",
      lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
      failedOperation: null,
      providerActionsWritten: "NO",
    });
  });

  it("keeps preparation durable when the unified MAIN-world result is null", async () => {
    const worker = await loadWorker({ subjectSearchResult: "NULL" });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.scriptCalls.slice(-2).map((call) => call.name)).toEqual([
      "watchCatalogSubjectNavigation",
      "prepareCatalogSubjectSearch",
    ]);
    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      preparationCheckpointRevision: 1,
      lastSubjectPreparationResultKind: "NULL_RESULT",
      lastSubjectSearchResultKind: "NULL_RESULT",
      lastSuccessfulCheckpoint: "CATALOG_LISTING_VERIFIED",
      failedOperation: null,
      lastFailureDiagnostic: null,
      providerActionsWritten: "NO",
    });
  });

  it("never downgrades a loading checkpoint that wins the race with a null result", async () => {
    const worker = await loadWorker({
      subjectSearchResult: "NULL",
      subjectSearchSignalsLoadingBeforeResult: true,
    });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      lastTransition: "SUBJECT_NAVIGATION_REQUESTED",
      lastTabUpdateStatus: "loading",
      currentNavigationRevision: 1,
      stateMachineCheckpoint: "SEARCH_SUBMITTED",
      lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
      lastSubjectSearchResultKind: "NULL_RESULT",
      failedOperation: null,
      providerActionsWritten: "NO",
    });
  });

  it("persists semantic diagnostics for an empty submit injection result", async () => {
    const worker = await loadWorker({
      subjectSearchResult: "EMPTY",
      subjectSearchNavigates: false,
    });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_SEARCH_SUBMIT_RESULT_INVALID",
      failedOperation: "START_SUBJECT_SEARCH",
      lastFailureDiagnostic: {
        operation: "START_SUBJECT_SEARCH",
        returnedResultKind: "EMPTY_RESULTS",
        tabUrlClassification: "CATALOG_LANDING",
        subjectCode: "ACCT",
        runRevision: "phase15b-main-world-checkpoint-v9",
        navigationRevision: 1,
        providerActionsWritten: "NO",
      },
      providerActionsWritten: "NO",
    });
  });

  it("isolates an archived v4 run from a fresh v8 116-subject startup", async () => {
    const oldV4 = {
      ...runningStoredBatch(),
      batchId: "archived-v4-run",
      runnerRevision: "phase15b-page-ready-v4",
      acceptanceRevision: "phase15b-page-ready-v4",
      status: "FAILED" as const,
      leaseStatus: "RELEASED" as const,
      expectedNavigationRevision: 7,
      currentNavigationRevision: 7,
      navigationTimeoutRevision: 7,
      lastErrorCode: "BATCH_CATALOG_PAGE_TIMEOUT",
      lastPageDiagnostics: pageSignalDiagnostics("ANTH", 4, 7),
    };
    const subjects = Array.from({ length: 116 }, (_, index) =>
      index === 0
        ? { code: "ACCT", label: "Accounting" }
        : {
            code: `S${String(index).padStart(3, "0")}`,
            label: `Subject ${index}`,
          },
    );
    const worker = await loadWorker({
      storedBatch: oldV4,
      discoveredSubjects: subjects,
    });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "RUNNING",
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      subjectLimit: 2,
      currentSubjectIndex: 0,
      expectedNavigationRevision: 1,
      currentNavigationRevision: null,
      navigationTimeoutRevision: 1,
      lastPageDiagnostics: null,
      lastErrorCode: null,
      lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
      failedOperation: null,
      lastFailureDiagnostic: null,
    });
    expect(worker.getStoredBatch()?.subjects).toHaveLength(116);
    expect(worker.getStoredBatch()?.batchId).not.toBe(oldV4.batchId);
    expect(worker.getStoredArchives()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          batchRunId: oldV4.batchId,
          runnerRevision: "phase15b-page-ready-v4",
        }),
      ]),
    );
  });

  it("ignores stale subject-navigation timeouts and pauses the current stalled revision", async () => {
    const worker = await loadWorker({
      subjectSearchNavigates: false,
      subjectSearchResult: "NULL",
    });
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: landingUrl },
    );
    await settleEvents();
    const batchId = worker.getStoredBatch()?.batchId ?? "";

    await dispatch(
      worker.messageListener,
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId,
        navigationRevision: 0,
        signal: "TIMEOUT",
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        diagnostics: subjectNavigationDiagnostics,
        providerActionsWritten: "NO",
      },
      { id: "extension-id", tab: { id: 41 } },
    );
    expect(worker.getStoredBatch()?.status).toBe("RUNNING");

    await dispatch(
      worker.messageListener,
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId,
        navigationRevision: 1,
        signal: "TIMEOUT",
        currentPath: "/Student/Student/Courses",
        subjectCode: "ACCT",
        diagnostics: subjectNavigationDiagnostics,
        providerActionsWritten: "NO",
      },
      { id: "extension-id", tab: { id: 41 } },
    );
    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      expectedNavigationRevision: 1,
      contentReadyRevision: 1,
      navigationTimeoutRevision: 1,
      lastFailureDiagnostic: {
        operation: "WATCH_SUBJECT_NAVIGATION",
        returnedResultKind: "NULL_RESULT",
        tabUrlClassification: "CATALOG_LANDING",
        subjectCode: "ACCT",
        runRevision: "phase15b-main-world-checkpoint-v9",
        navigationRevision: 1,
        providerActionsWritten: "NO",
      },
      providerActionsWritten: "NO",
    });
  });

  it("keeps a current-revision 116-subject full run explicitly locked", async () => {
    const subjects: CatalogSubject[] = [
      { code: "ACCT", label: "Accounting" },
      { code: "ANTH", label: "Anthropology" },
      ...Array.from({ length: 114 }, (_, index) => ({
        code: `S${String(index + 1).padStart(3, "0")}`,
        label: `Subject ${index + 1}`,
      })),
    ];
    const worker = await loadWorker({
      storedBatch: currentCompletedBoundedBatch(),
      discoveredSubjects: subjects,
    });

    const started = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "FULL",
    });

    expect(started).toMatchObject({
      ok: false,
      status: 409,
      payload: {
        code: "BATCH_CATALOG_FULL_CAPTURE_EXPLICIT_UNLOCK_REQUIRED",
      },
    });
    expect(worker.executedFunctions).toEqual([]);
  });

  it("keeps full capture locked when only a legacy unversioned acceptance flag exists", async () => {
    const worker = await loadWorker({ storedBatch: completedBoundedBatch() });

    const response = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "FULL",
    });

    expect(response).toMatchObject({
      ok: false,
      status: 409,
      payload: { code: "BATCH_CATALOG_BOUNDED_ACCEPTANCE_REQUIRED" },
    });
    expect(worker.executedFunctions).toEqual([]);
  });

  it("ignores another tab becoming active or completing navigation", async () => {
    const worker = await loadWorker();
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    const watchesBefore = worker.executedFunctions.filter(
      (name) => name === "watchCatalogResultPage",
    ).length;

    worker.updatedListener(
      99,
      { status: "complete" },
      { id: 99, url: "https://example.com" },
    );
    await settleEvents();

    expect(
      worker.executedFunctions.filter(
        (name) => name === "watchCatalogResultPage",
      ),
    ).toHaveLength(watchesBefore);
    expect(worker.getStoredBatch()?.status).toBe("RUNNING");
  });

  it("pauses fail-closed when the authorized tab closes", async () => {
    const worker = await loadWorker();
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    worker.removedListener(41);
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "AUTHORIZED_CATALOG_TAB_CLOSED",
      lastErrorCode: "BATCH_CATALOG_TAB_CLOSED",
      lastTransition: "PAUSED",
    });
    expect(worker.getSessionLease()).toBeUndefined();
  });

  it("restores a run without a same-session lease as paused without touching the portal", async () => {
    const storedBatch = runningStoredBatch();
    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "WORKER_RESTART_RECOVERY_REQUIRED",
      lastErrorCode: "BATCH_CATALOG_WORKER_RESTART",
    });
    expect(worker.executedFunctions).toEqual([]);
    expect(worker.fetchMock).not.toHaveBeenCalled();
  });

  it("supersedes a legacy paused run with progress while preserving its local evidence", async () => {
    const storedBatch = {
      ...runningStoredBatch(),
      status: "PAUSED" as const,
      currentSubjectIndex: 1,
      completedSubjects: ["ACCT"],
      coursesCaptured: 98,
      uniqueCourses: 98,
      localImportRunIds: ["11111111-1111-4111-8111-111111111111"],
      lastErrorCode: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      lastErrorMessage:
        "The authorized Catalog tab remained on the landing page after the subject search was requested.",
      lastTransition: "PAUSED" as const,
    } as CatalogBatchState & { runnerRevision?: string };
    Reflect.deleteProperty(storedBatch, "runnerRevision");

    const worker = await loadWorker({
      storedBatch,
      sessionLease: { batchId: storedBatch.batchId },
    });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: storedBatch.batchId,
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "PAUSED",
        runnerRevision: "LEGACY_UNVERSIONED",
        completedSubjects: ["ACCT"],
        coursesCaptured: 98,
        localImportRunIds: ["11111111-1111-4111-8111-111111111111"],
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      kind: "SUPERSEDED",
      batchRunId: storedBatch.batchId,
      previousStatus: "PAUSED",
      previousRunnerRevision: "LEGACY_UNVERSIONED",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
      providerActionsWritten: "NO",
    });
    expect(worker.getSessionLease()).toBeUndefined();
    expect(worker.fetchMock).not.toHaveBeenCalled();
  });

  it("supersedes a failed run from an older revision", async () => {
    const storedBatch = Object.assign(runningStoredBatch(), {
      status: "FAILED" as const,
      runnerRevision: "phase15b-subject-transition-v2",
      lastTransition: "FAILED" as const,
      lastErrorCode: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
    });

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: storedBatch.batchId,
        archiveStatus: "SUPERSEDED",
        originalStatus: "FAILED",
        runnerRevision: "phase15b-subject-transition-v2",
      }),
    ]);
  });

  it("preserves and supersedes the exact failed real v5 run when v8 loads", async () => {
    const storedBatch = Object.assign(runningStoredBatch(), {
      batchId: "dad8f3bb-d3f0-4a12-bf93-33813cf46e27",
      runnerRevision: "phase15b-content-ready-v5",
      acceptanceRevision: "phase15b-content-ready-v5",
      status: "FAILED" as const,
      leaseStatus: "RELEASED" as const,
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 1,
      currentNavigationRevision: null,
      contentReadyRevision: null,
      navigationTimeoutRevision: 1,
      lastErrorCode: "BATCH_CATALOG_UNEXPECTED_ERROR",
      lastErrorMessage:
        "The batch stopped because an unexpected local error occurred.",
      lastErrorContext: {
        phase: "LANDING_DOM_READY" as const,
        subject: "ACCT",
        page: 1,
        urlClassification: "CATALOG_LANDING" as const,
        revision: 1,
        timestamp: "2026-08-31T09:22:30.226Z",
        diagnostics: null,
      },
      lastTransition: "FAILED" as const,
      stateMachineCheckpoint: "FAILED" as const,
      lastTransitionAt: "2026-08-31T09:22:30.226Z",
    }) as CatalogBatchState & Record<string, unknown>;
    Reflect.deleteProperty(storedBatch, "lastSuccessfulCheckpoint");
    Reflect.deleteProperty(storedBatch, "failedOperation");
    Reflect.deleteProperty(storedBatch, "lastFailureDiagnostic");

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: "dad8f3bb-d3f0-4a12-bf93-33813cf46e27",
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "FAILED",
        runnerRevision: "phase15b-content-ready-v5",
        lastErrorCode: "BATCH_CATALOG_UNEXPECTED_ERROR",
        lastErrorContext: expect.objectContaining({
          phase: "LANDING_DOM_READY",
          subject: "ACCT",
          revision: 1,
        }),
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      batchRunId: "dad8f3bb-d3f0-4a12-bf93-33813cf46e27",
      previousRunnerRevision: "phase15b-content-ready-v5",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
    });
  });

  it("archives the exact failed real v6 null-result run before v8 starts", async () => {
    const storedBatch = Object.assign(runningStoredBatch(), {
      batchId: "14c1b82f-d5fa-4f33-b302-4fd91f4dadf4",
      runnerRevision: "phase15b-content-ready-v6",
      acceptanceRevision: "phase15b-content-ready-v6",
      status: "FAILED" as const,
      leaseStatus: "RELEASED" as const,
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 1,
      currentNavigationRevision: 1,
      contentReadyRevision: null,
      navigationTimeoutRevision: 1,
      lastErrorCode: "BATCH_CATALOG_SEARCH_TRIGGER_FAILED",
      lastErrorMessage: "Cannot read properties of null (reading 'action')",
      lastSuccessfulCheckpoint: "LANDING_READY" as const,
      failedOperation: "START_SUBJECT_SEARCH" as const,
      lastFailureDiagnostic: {
        safeErrorName: "TypeError",
        safeErrorMessage: "Cannot read properties of null (reading 'action')",
        safeStack:
          "TypeError: Cannot read properties of null (reading 'action') at beginCatalogSubject (dist/background/catalog-batch-controller.js:162:20)",
        safeCause: null,
        phase: "SUBJECT_SELECTION_STARTED" as const,
        operation: "START_SUBJECT_SEARCH" as const,
        checkpoint: "LANDING_READY" as const,
        runRevision: "phase15b-content-ready-v6",
        navigationRevision: 1,
        timestamp: "2026-08-31T16:37:20.399Z",
      },
      lastTransition: "FAILED" as const,
      stateMachineCheckpoint: "FAILED" as const,
      lastTransitionAt: "2026-08-31T16:37:20.399Z",
      providerActionsWritten: "NO" as const,
    }) as CatalogBatchState & Record<string, unknown>;
    Reflect.deleteProperty(storedBatch, "lastSubjectSearchResultKind");

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: "14c1b82f-d5fa-4f33-b302-4fd91f4dadf4",
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "FAILED",
        runnerRevision: "phase15b-content-ready-v6",
        lastErrorCode: "BATCH_CATALOG_SEARCH_TRIGGER_FAILED",
        lastSuccessfulCheckpoint: "LANDING_READY",
        failedOperation: "START_SUBJECT_SEARCH",
        lastFailureDiagnostic: expect.objectContaining({
          safeErrorName: "TypeError",
          safeErrorMessage: "Cannot read properties of null (reading 'action')",
          phase: "SUBJECT_SELECTION_STARTED",
          operation: "START_SUBJECT_SEARCH",
          checkpoint: "LANDING_READY",
          runRevision: "phase15b-content-ready-v6",
          navigationRevision: 1,
          subjectCode: "ACCT",
          providerActionsWritten: "NO",
        }),
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      batchRunId: "14c1b82f-d5fa-4f33-b302-4fd91f4dadf4",
      previousRunnerRevision: "phase15b-content-ready-v6",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
      providerActionsWritten: "NO",
    });
  });

  it("archives the exact failed real v7 preparation null-result run before v8 starts", async () => {
    const storedBatch = Object.assign(runningStoredBatch(), {
      batchId: "66fff0c2-de28-434c-aa24-ad8ea7eb84dc",
      runnerRevision: "phase15b-navigation-contract-v7",
      acceptanceRevision: "phase15b-navigation-contract-v7",
      status: "FAILED" as const,
      leaseStatus: "RELEASED" as const,
      subjectLimit: 2,
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 1,
      currentNavigationRevision: null,
      contentReadyRevision: null,
      navigationTimeoutRevision: 1,
      lastTabUpdateStatus: null,
      lastSubjectSearchResultKind: "NULL_RESULT" as const,
      lastErrorCode: "BATCH_CATALOG_CONTENT_SCRIPT_RESULT_INVALID",
      lastErrorMessage:
        "The visible page returned NULL_RESULT instead of the reviewed Catalog operation result.",
      lastSuccessfulCheckpoint: "LANDING_READY" as const,
      failedOperation: "START_SUBJECT_SEARCH" as const,
      lastFailureDiagnostic: {
        safeErrorName: "CatalogBatchError",
        safeErrorMessage:
          "The visible page returned NULL_RESULT instead of the reviewed Catalog operation result.",
        safeStack: "",
        safeCause: null,
        phase: "SUBJECT_SELECTION_STARTED" as const,
        operation: "START_SUBJECT_SEARCH" as const,
        checkpoint: "LANDING_READY" as const,
        runRevision: "phase15b-navigation-contract-v7",
        navigationRevision: 1,
        returnedResultKind: "NULL_RESULT" as const,
        tabUrlClassification: "CATALOG_LANDING" as const,
        subjectCode: "ACCT",
        providerActionsWritten: "NO" as const,
        timestamp: "2026-09-01T05:17:26.662Z",
      },
      createdAt: "2026-09-01T05:17:23.782Z",
      startedAt: "2026-09-01T05:17:23.782Z",
      updatedAt: "2026-09-01T05:17:26.662Z",
      lastTransition: "FAILED" as const,
      stateMachineCheckpoint: "FAILED" as const,
      lastTransitionAt: "2026-09-01T05:17:26.662Z",
      providerActionsWritten: "NO" as const,
    }) as CatalogBatchState & Record<string, unknown>;
    Reflect.deleteProperty(storedBatch, "lastSubjectPreparationResultKind");

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: "66fff0c2-de28-434c-aa24-ad8ea7eb84dc",
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "FAILED",
        runnerRevision: "phase15b-navigation-contract-v7",
        lastErrorCode: "BATCH_CATALOG_CONTENT_SCRIPT_RESULT_INVALID",
        lastErrorMessage:
          "The visible page returned NULL_RESULT instead of the reviewed Catalog operation result.",
        lastSuccessfulCheckpoint: "LANDING_READY",
        failedOperation: "START_SUBJECT_SEARCH",
        lastFailureDiagnostic: expect.objectContaining({
          safeErrorName: "CatalogBatchError",
          phase: "SUBJECT_SELECTION_STARTED",
          operation: "START_SUBJECT_SEARCH",
          checkpoint: "LANDING_READY",
          runRevision: "phase15b-navigation-contract-v7",
          navigationRevision: 1,
          returnedResultKind: "NULL_RESULT",
          tabUrlClassification: "CATALOG_LANDING",
          subjectCode: "ACCT",
          providerActionsWritten: "NO",
        }),
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      batchRunId: "66fff0c2-de28-434c-aa24-ad8ea7eb84dc",
      previousRunnerRevision: "phase15b-navigation-contract-v7",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
      providerActionsWritten: "NO",
    });
  });

  it("supersedes the paused v4 real run when the v8 worker loads", async () => {
    const v4Diagnostics = {
      ...pageSignalDiagnostics("ACCT", 1, 1),
      visibleSubject: null,
      visibleSubjectSource: "UNAVAILABLE" as const,
      courseCardCount: 30,
      spinnerPresent: true,
      spinnerVisible: true,
      spinnerNodeCount: 1,
      spinnerHardGateValid: false,
      knockoutReady: false,
      domStable: false,
      domStableDurationMs: 0,
      contentScriptRevision: "phase15b-page-ready-v4",
      runnerRevision: "phase15b-page-ready-v4",
      pageReadyGateFailedOn: "KNOCKOUT_READY",
      currentPageTimeoutRootCause: "KNOCKOUT_READY",
    };
    const storedBatch = Object.assign(runningStoredBatch(), {
      batchId: "3f261cc7-fa8c-42bd-b0c1-3c34f28305d0",
      status: "PAUSED" as const,
      runnerRevision: "phase15b-page-ready-v4",
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 1,
      coursesCaptured: 0,
      pauseReason: "BATCH_CATALOG_PAGE_TIMEOUT",
      lastErrorCode: "BATCH_CATALOG_PAGE_TIMEOUT",
      lastErrorMessage:
        "The Catalog result page did not become ready within the bounded timeout.",
      lastPageDiagnostics: v4Diagnostics,
      lastErrorContext: {
        phase: "SEARCHRESULT_NAVIGATING" as const,
        subject: "ACCT",
        page: 1,
        urlClassification: "CATALOG_SEARCH_RESULT" as const,
        revision: 1,
        timestamp: "2026-08-27T09:00:30.000Z",
        diagnostics: v4Diagnostics,
      },
      lastTransition: "PAUSED" as const,
    });

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: storedBatch.batchId,
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "PAUSED",
        runnerRevision: "phase15b-page-ready-v4",
        coursesCaptured: 0,
        lastErrorCode: "BATCH_CATALOG_PAGE_TIMEOUT",
        lastErrorContext: expect.objectContaining({
          diagnostics: expect.objectContaining({
            courseCardCount: 30,
            knockoutReady: false,
            pageReadyGateFailedOn: "KNOCKOUT_READY",
            currentPageTimeoutRootCause: "KNOCKOUT_READY",
          }),
        }),
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      kind: "SUPERSEDED",
      batchRunId: storedBatch.batchId,
      previousStatus: "PAUSED",
      previousRunnerRevision: "phase15b-page-ready-v4",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
      providerActionsWritten: "NO",
    });
    expect(worker.getSessionLease()).toBeUndefined();
    expect(worker.fetchMock).not.toHaveBeenCalled();
  });

  it("keeps a same-revision paused run resumable", async () => {
    const storedBatch = Object.assign(runningStoredBatch(), {
      status: "PAUSED" as const,
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      pauseReason: "AUTHORIZED_CATALOG_TAB_CLOSED",
      lastTransition: "PAUSED" as const,
    });

    const worker = await loadWorker({ storedBatch });
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      batchId: storedBatch.batchId,
      status: "PAUSED",
      runnerRevision: "phase15b-main-world-checkpoint-v9",
    });
    expect(worker.getStoredArchives()).toEqual([]);

    const startResponse = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    expect(startResponse).toMatchObject({
      ok: false,
      status: 409,
      payload: {
        code: "BATCH_CATALOG_SAME_REVISION_PAUSED_RUN_EXISTS",
      },
    });
    expect(worker.getStoredBatch()?.batchId).toBe(storedBatch.batchId);
  });

  it("preserves completed evidence before a fresh bounded run obtains a new id", async () => {
    const completed = Object.assign(currentCompletedBoundedBatch(), {
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      coursesCaptured: 120,
      uniqueCourses: 118,
      localImportRunIds: ["11111111-1111-4111-8111-333333333333"],
    });
    const worker = await loadWorker({ storedBatch: completed });

    const response = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    expect(response).toMatchObject({
      ok: true,
      status: 202,
      payload: { runnerRevision: "phase15b-main-world-checkpoint-v9" },
    });
    expect(worker.getStoredBatch()).toMatchObject({
      batchId: expect.not.stringMatching(completed.batchId),
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 0,
      coursesCaptured: 0,
      uniqueCourses: 0,
      pagesCaptured: 0,
      lastPageDiagnostics: null,
      providerActionsWritten: "NO",
    });
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: completed.batchId,
        archiveStatus: "COMPLETED",
        originalStatus: "COMPLETED",
        coursesCaptured: 120,
        localImportRunIds: ["11111111-1111-4111-8111-333333333333"],
        providerActionsWritten: "NO",
      }),
    ]);
  });

  it("never evicts immutable completed evidence when transient archive history is bounded", async () => {
    const storedArchives: StoredCatalogBatchArchive[] = Array.from(
      { length: 20 },
      (_, index) => ({
        batchRunId: `completed-${index + 1}`,
        archiveStatus: "COMPLETED",
        reason: "REPLACED_BY_NEW_RUN",
        originalStatus: "COMPLETED",
        runnerRevision: "phase15b-page-ready-v4",
        completedSubjects: ["ACCT", "AD"],
        coursesCaptured: 100 + index,
        localImportRunIds: [`import-${index + 1}`],
        providerActionsWritten: "NO",
      }),
    );
    const legacyPaused = {
      ...runningStoredBatch(),
      status: "PAUSED" as const,
      lastTransition: "PAUSED" as const,
    } as CatalogBatchState & { runnerRevision?: string };
    Reflect.deleteProperty(legacyPaused, "runnerRevision");

    const worker = await loadWorker({
      storedBatch: legacyPaused,
      storedArchives,
    });
    await settleEvents();

    expect(worker.getStoredArchives()).toEqual([
      ...storedArchives,
      expect.objectContaining({
        batchRunId: legacyPaused.batchId,
        archiveStatus: "SUPERSEDED",
      }),
    ]);
  });

  it("pauses a running checkpoint after worker restart even when a stale session lease remains", async () => {
    const storedBatch = runningStoredBatch();
    const worker = await loadWorker({
      storedBatch,
      sessionLease: { batchId: storedBatch.batchId },
    });
    await settleEvents();

    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "WORKER_RESTART_RECOVERY_REQUIRED",
      lastErrorCode: "BATCH_CATALOG_WORKER_RESTART",
    });
    expect(worker.getSessionLease()).toBeUndefined();
  });

  it("archives the exact paused real v8 split-injection run before v9 starts", async () => {
    const subjects = Array.from({ length: 116 }, (_, index) =>
      index === 0
        ? { code: "ACCT", label: "Accounting" }
        : {
            code: `S${String(index).padStart(3, "0")}`,
            label: `Subject ${index}`,
          },
    );
    const storedBatch = Object.assign(runningStoredBatch(), {
      batchId: "547fbad0-9939-406d-ad4b-3ea2b24b7b0d",
      runnerRevision: "phase15b-preparation-contract-v8",
      acceptanceRevision: "phase15b-preparation-contract-v8",
      extensionVersion: "0.1.6",
      subjects,
      status: "PAUSED" as const,
      leaseStatus: "RELEASED" as const,
      subjectLimit: 2,
      currentSubjectIndex: 0,
      currentPage: 1,
      expectedNavigationRevision: 1,
      currentNavigationRevision: null,
      contentReadyRevision: 1,
      navigationTimeoutRevision: 1,
      lastTabUpdateStatus: null,
      lastSubjectPreparationResultKind: "NULL_RESULT" as const,
      lastSubjectSearchResultKind: "NULL_RESULT" as const,
      coursesCaptured: 0,
      uniqueCourses: 0,
      duplicatesIgnored: 0,
      pagesCaptured: 0,
      completedSubjects: [],
      localImportRunIds: [],
      localReviewSessionIds: [],
      myprogressRemapExecuted: false,
      lastErrorCode: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      lastErrorMessage:
        "The authorized Catalog tab remained on the landing page after the subject search was requested.",
      lastErrorContext: {
        phase: "SEARCH_SUBMIT_STARTED" as const,
        subject: "ACCT",
        page: 1,
        urlClassification: "CATALOG_LANDING" as const,
        revision: 1,
        timestamp: "2026-09-01T08:10:40.959Z",
        diagnostics: null,
      },
      lastSuccessfulCheckpoint: "LANDING_READY" as const,
      failedOperation: "WATCH_SUBJECT_NAVIGATION" as const,
      lastFailureDiagnostic: {
        safeErrorName: "CatalogBatchError",
        safeErrorMessage:
          "The authorized Catalog tab remained on the landing page after the subject search was requested.",
        safeStack: "",
        safeCause: null,
        phase: "SEARCH_SUBMIT_STARTED" as const,
        operation: "WATCH_SUBJECT_NAVIGATION" as const,
        checkpoint: "LANDING_READY" as const,
        runRevision: "phase15b-preparation-contract-v8",
        navigationRevision: 1,
        returnedResultKind: "NULL_RESULT" as const,
        tabUrlClassification: "CATALOG_LANDING" as const,
        subjectCode: "ACCT",
        providerActionsWritten: "NO" as const,
        timestamp: "2026-09-01T08:10:40.959Z",
      },
      updatedAt: "2026-09-01T08:10:40.959Z",
      lastTransition: "PAUSED" as const,
      stateMachineCheckpoint: "PAUSED" as const,
      lastTransitionAt: "2026-09-01T08:10:40.959Z",
      pauseReason: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      providerActionsWritten: "NO" as const,
    }) as CatalogBatchState & Record<string, unknown>;
    Reflect.deleteProperty(storedBatch, "preparationCheckpointRevision");
    Reflect.deleteProperty(storedBatch, "lastSubjectNavigationDiagnostics");

    const worker = await loadWorker({
      storedBatch,
      sessionLease: { batchId: storedBatch.batchId as string },
    });
    await settleEvents();

    expect(worker.getStoredBatch()).toBeUndefined();
    expect(worker.getStoredArchives()).toEqual([
      expect.objectContaining({
        batchRunId: "547fbad0-9939-406d-ad4b-3ea2b24b7b0d",
        archiveStatus: "SUPERSEDED",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        originalStatus: "PAUSED",
        runnerRevision: "phase15b-preparation-contract-v8",
        subjectLimit: 2,
        discoveredSubjectCount: 116,
        coursesCaptured: 0,
        completedSubjects: [],
        lastErrorCode: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
        lastSuccessfulCheckpoint: "LANDING_READY",
        failedOperation: "WATCH_SUBJECT_NAVIGATION",
        lastFailureDiagnostic: expect.objectContaining({
          phase: "SEARCH_SUBMIT_STARTED",
          operation: "WATCH_SUBJECT_NAVIGATION",
          checkpoint: "LANDING_READY",
          runRevision: "phase15b-preparation-contract-v8",
          navigationRevision: 1,
          returnedResultKind: "NULL_RESULT",
          tabUrlClassification: "CATALOG_LANDING",
          subjectCode: "ACCT",
          providerActionsWritten: "NO",
        }),
        providerActionsWritten: "NO",
      }),
    ]);
    expect(worker.getLifecycleNotice()).toMatchObject({
      batchRunId: "547fbad0-9939-406d-ad4b-3ea2b24b7b0d",
      previousStatus: "PAUSED",
      previousRunnerRevision: "phase15b-preparation-contract-v8",
      currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
      reason: "SUPERSEDED_BY_NEW_REVISION",
      providerActionsWritten: "NO",
    });
    expect(worker.getSessionLease()).toBeUndefined();
    expect(worker.fetchMock).not.toHaveBeenCalled();
  });

  it("fails closed when the initial durable Catalog navigation is rejected", async () => {
    const worker = await loadWorker({ tabReloadFails: true });

    const response = await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });

    expect(response).toMatchObject({
      ok: false,
      status: 503,
      payload: { code: "BATCH_CATALOG_TAB_UNAVAILABLE" },
    });
    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "BATCH_CATALOG_TAB_UNAVAILABLE",
      lastTransition: "PAUSED",
    });
    expect(worker.getSessionLease()).toBeUndefined();
  });

  it("pauses on a page-ready timeout and never sends local imports", async () => {
    const worker = await loadWorker();
    await dispatch(worker.messageListener, {
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 41,
      landingUrl,
      mode: "BOUNDED_ACCEPTANCE",
    });
    worker.updatedListener(
      41,
      { status: "complete" },
      { id: 41, url: resultUrl },
    );
    await settleEvents();
    const batchId = worker.getStoredBatch()?.batchId ?? "";
    const navigationRevision =
      worker.getStoredBatch()?.expectedNavigationRevision ?? -1;

    await dispatch(
      worker.messageListener,
      {
        type: "SAPSOS_CATALOG_PAGE_SIGNAL",
        batchId,
        signal: "TIMEOUT",
        navigationRevision,
        pageNumber: null,
        totalPages: null,
        visibleCourseCount: null,
        subjectCode: null,
        firstCourseMarker: null,
        lastCourseMarker: null,
        resultFingerprint: null,
        diagnostics: {
          ...pageSignalDiagnostics("ACCT", 1, navigationRevision),
          pageNumber: null,
          pageNumberSource: "UNAVAILABLE",
          courseCardCount: 0,
          visibleSubject: null,
          visibleSubjectSource: "UNAVAILABLE",
          pageFingerprint: null,
          domStable: false,
          pageReadyGateFailedOn: "COURSE_CARD_COUNT",
          currentPageTimeoutRootCause: "COURSE_CARD_COUNT",
        },
        providerActionsWritten: "NO",
      },
      { id: "extension-id", tab: { id: 41 } },
    );

    expect(worker.getStoredBatch()).toMatchObject({
      status: "PAUSED",
      pauseReason: "BATCH_CATALOG_PAGE_TIMEOUT",
    });
    expect(worker.fetchMock).not.toHaveBeenCalled();
  });

  it("falls back to an extension-owned monitor tab when Side Panel open fails", async () => {
    const worker = await loadWorker({ sidePanelFails: true });

    const response = await dispatch(worker.messageListener, {
      type: "SAPSOS_OPEN_CATALOG_BATCH_MONITOR",
      apiBaseUrl: "http://localhost:8000",
      tabId: 41,
    });

    expect(response).toMatchObject({
      ok: true,
      payload: {
        surface: "MONITOR_TAB",
        sidePanelSupported: true,
        sidePanelError: "unsupported",
        fallbackError: null,
      },
    });
    expect(worker.createdTabs).toEqual([
      "chrome-extension://extension-id/src/monitor/index.html",
    ]);
  });

  it("returns the actual Side Panel and fallback errors when neither can open", async () => {
    const worker = await loadWorker({
      sidePanelFails: true,
      fallbackTabFails: true,
    });

    const response = await dispatch(worker.messageListener, {
      type: "SAPSOS_OPEN_CATALOG_BATCH_MONITOR",
      apiBaseUrl: "http://localhost:8000",
      tabId: 41,
    });

    expect(response).toMatchObject({
      ok: false,
      status: 503,
      payload: {
        surface: null,
        sidePanelSupported: true,
        sidePanelError: "unsupported",
        fallbackError: "Edge refused extension tab",
      },
    });
  });
});
