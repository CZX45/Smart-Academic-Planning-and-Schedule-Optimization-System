import { afterEach, describe, expect, it, vi } from "vitest";

import { KEAN_STUDENT_PORTAL_PREFIX } from "../src/shared/kean.js";
import type { CatalogBatchPublicState } from "../src/content/catalog-batch-lifecycle.js";
import type { AcademicPageSnapshot } from "../src/shared/types.js";

const FAKE_STUDENT_PROFILE_ID = "00000000-0000-4000-8000-000000000001";
const CREATED_IMPORT_ID = "11111111-1111-4111-8111-111111111111";

type Listener = () => void;

class FakeElement {
  readonly listeners = new Map<string, Listener[]>();
  readonly children: FakeElement[] = [];
  textContent = "";

  addEventListener(eventName: string, listener: EventListener): void {
    const listeners = this.listeners.get(eventName) ?? [];
    listeners.push(() => listener(new Event(eventName)));
    this.listeners.set(eventName, listeners);
  }

  append(...children: FakeElement[]): void {
    this.children.push(...children);
  }

  replaceChildren(...children: FakeElement[]): void {
    this.children.length = 0;
    this.children.push(...children);
  }

  click(): void {
    for (const listener of this.listeners.get("click") ?? []) {
      listener();
    }
  }
}

class FakeInputElement extends FakeElement {
  value = "";
}

class FakeButtonElement extends FakeElement {
  disabled = false;
}

type PopupElements = {
  apiBaseUrlInput: FakeInputElement;
  studentProfileIdInput: FakeInputElement;
  extractCurrentPageButton: FakeButtonElement;
  startKeanImportButton: FakeButtonElement;
  captureGuidedPageButton: FakeButtonElement;
  confirmImportButton: FakeButtonElement;
  startCatalogBatchButton: FakeButtonElement;
  pauseCatalogBatchButton: FakeButtonElement;
  resumeCatalogBatchButton: FakeButtonElement;
  cancelCatalogBatchButton: FakeButtonElement;
  openCatalogBatchMonitorButton: FakeButtonElement;
  catalogBatchStartReasonText: FakeElement;
  catalogBatchStatusText: FakeElement;
  catalogBatchMonitorStatusText: FakeElement;
  catalogBatchProgressText: FakeElement;
  statusText: FakeElement;
  apiStatusText: FakeElement;
  pairingStatusText: FakeElement;
};

function createElementForId(id: string): FakeElement {
  if (id.endsWith("Input")) {
    return new FakeInputElement();
  }
  if (id.endsWith("Button")) {
    return new FakeButtonElement();
  }
  return new FakeElement();
}

function createPopupElements(): PopupElements & Record<string, FakeElement> {
  const ids = [
    "apiBaseUrlInput",
    "studentProfileIdInput",
    "extractCurrentPageButton",
    "startKeanImportButton",
    "captureGuidedPageButton",
    "confirmImportButton",
    "startCatalogBatchButton",
    "pauseCatalogBatchButton",
    "resumeCatalogBatchButton",
    "cancelCatalogBatchButton",
    "openCatalogBatchMonitorButton",
    "catalogBatchStartReasonText",
    "catalogBatchStatusText",
    "catalogBatchMonitorStatusText",
    "catalogBatchProgressText",
    "statusText",
    "apiStatusText",
    "pairingCodeInput",
    "pairExtensionButton",
    "pairingStatusText",
    "detectedPageText",
    "countsText",
    "warningsList",
    "previewTable",
    "diagnosticUrlText",
    "diagnosticMarkerText",
    "diagnosticTablesText",
    "diagnosticRowsText",
    "diagnosticVisibleTextLengthText",
    "diagnosticRowLikeBlocksText",
    "diagnosticAcademicFieldsText",
    "diagnosticSensitiveFieldsText",
    "diagnosticDirectSnapshotText",
    "diagnosticBoundedText",
  ] as const;
  const elements = Object.fromEntries(
    ids.map((id) => [id, createElementForId(id)]),
  ) as PopupElements & Record<string, FakeElement>;
  elements.apiBaseUrlInput.value = "http://localhost:8000";
  elements.studentProfileIdInput.value = FAKE_STUDENT_PROFILE_ID;
  return elements;
}

function myProgressRows(count: number): string[][] {
  const examples = [
    ["Not Started", "MATH*1044", "Precalculus for Business", "", "", "3"],
    ["Not Started", "MATH*1054", "Pre-Calculus", "", "", "3"],
    ["Planned", "ENG*2403", "World Literature", "", "2026SUW", "3"],
    ["Not Started", "GE*1855", "First Year Seminar", "", "", "1"],
    ["Not Started", "AH*1700", "Art-Prehist to Middle Ages", "", "", "3"],
    ["Not Started", "AH*1701", "Hist Art-Renssce to Mod. Wrld", "", "", "3"],
  ];
  return Array.from({ length: count }, (_, index) => {
    const example = examples[index];
    if (example) {
      return example;
    }
    return [
      index % 3 === 0 ? "Completed" : "In Progress",
      `FIN*${3000 + index}`,
      `Finance Requirement ${index}`,
      index % 3 === 0 ? "B" : "",
      index % 3 === 0 ? "2025FAW" : "2026SPW",
      "3",
    ];
  });
}

function myProgressSnapshot(rowCount = 1): AcademicPageSnapshot {
  return {
    title: "My Progress",
    url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    visibleText:
      "My Progress Finance, BS Degree Bachelor of Science Major Finance Department Accounting & Finance Catalog 2024 Cumulative GPA 3.916 Institution GPA 3.916 Anticipated Completion Date 12/20/2028 Total Credits 104 of 120 67 24 13 Mathematics Requirements Open Electives Requirements",
    tables: [
      {
        index: 0,
        caption: "Mathematics Requirements",
        headers: ["Status", "Course", "Title", "Grade", "Term", "Credits"],
        rows: myProgressRows(rowCount),
      },
    ],
    headings: ["My Progress", "Finance, BS", "Mathematics Requirements"],
    warnings: [
      {
        code: "EXTRACTION_LIMIT_REACHED",
        severity: "WARNING",
        message: "Extraction stopped early because the page is large.",
      },
    ],
    snapshotMetadata: {
      directSnapshotRan: true,
      visibleTextLength: 280,
      rowLikeBlocksFound: 0,
      bounded: true,
    },
  };
}

function catalogBatchFixture(
  status: CatalogBatchPublicState["batchStatus"] = "COMPLETED",
): CatalogBatchPublicState {
  return {
    batchStatus: status,
    batchRunId: "catalog-batch-1",
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    acceptanceRevision: "phase15b-main-world-checkpoint-v9",
    extensionVersion: "0.1.7",
    createdAt: "2026-08-26T02:00:00.000Z",
    mode: "BOUNDED_ACCEPTANCE",
    subjectLimit: 2,
    boundedAcceptancePassed: status === "COMPLETED",
    boundedAcceptanceRevision:
      status === "COMPLETED" ? "phase15b-main-world-checkpoint-v9" : null,
    currentSubjectIndex: status === "COMPLETED" ? 2 : 0,
    currentSubject: status === "COMPLETED" ? null : "ACCT",
    currentPage: 2,
    expectedNavigationRevision: 1,
    currentNavigationRevision: 1,
    contentReadyRevision: 1,
    navigationTimeoutRevision: 1,
    preparationCheckpointRevision: 1,
    lastTabUpdateStatus: "complete",
    lastSubjectPreparationResultKind: "VALUE",
    lastSubjectSearchResultKind: "VALUE",
    lastSubjectNavigationDiagnostics: null,
    discoveredSubjectCount: 2,
    completedSubjectCount: status === "COMPLETED" ? 2 : 0,
    capturedRecordCount: 4,
    uniqueRecordCount: 3,
    duplicateRecordCount: 1,
    warningCount: 1,
    lastWarning: "KEAN_CATALOG_RULE_REQUIRES_REVIEW",
    lastError: null,
    lastTransition: status === "COMPLETED" ? "COMPLETED" : "PAGE_CAPTURED",
    stateMachineCheckpoint:
      status === "COMPLETED" ? "COMPLETED" : "PAGE_CAPTURED",
    lastSuccessfulCheckpoint:
      status === "COMPLETED" ? "COMPLETED" : "PAGE_CAPTURED",
    failedOperation: null,
    lastFailureDiagnostic: null,
    lastTransitionAt: "2026-08-26T02:05:00.000Z",
    pauseReason: null,
    leaseStatus: status === "RUNNING" ? "ACTIVE" : "RELEASED",
    elapsedSeconds: 300,
    estimatedRemainingSeconds: null,
    authorizedTabId: 42,
    currentSchoolTabUrlClassification: "CATALOG_SEARCH_RESULT",
    processingStage: status === "COMPLETED" ? "COMPLETED" : "CAPTURE_RUNNING",
    completedProcessingStages:
      status === "COMPLETED"
        ? [
            "LOCAL_STAGING",
            "LOCAL_VALIDATION",
            "LOCAL_REVIEW",
            "LOCAL_DRY_RUN",
            "LOCAL_APPLY",
            "MYPROGRESS_REMAP",
            "COMPLETED",
          ]
        : [],
    localStagedCount: status === "COMPLETED" ? 3 : 0,
    localReviewValidCount: status === "COMPLETED" ? 3 : 0,
    localReviewWarningCount: 0,
    localAppliedCount: status === "COMPLETED" ? 3 : 0,
    myprogressTotalCount: 86,
    myprogressMappedBeforeCount: 2,
    myprogressMappedAfterCount: status === "COMPLETED" ? 5 : 2,
    myprogressUnmatchedAfterCount: status === "COMPLETED" ? 81 : 84,
    myprogressRemapExecuted: status === "COMPLETED",
    lastPageDiagnostics: null,
    providerActionsWritten: "NO",
  };
}

async function importPopupWithFetch(
  fetchImpl: typeof fetch,
  options: {
    apiBaseUrl?: string;
    discoveredProfile?: { id: string; displayName: string };
    localProfiles?: Array<{ id: string; displayName: string }>;
    snapshot?: AcademicPageSnapshot;
    storedStudentProfileId?: string | null;
    catalogBatchState?: CatalogBatchPublicState | null;
    startBatchState?: CatalogBatchPublicState;
    startBatchResponse?: { ok: boolean; status: number; payload: unknown };
    activeTabUrl?: string;
    sidePanelError?: string;
    fallbackCreateError?: string;
    catalogBatchLifecycleNotice?: {
      kind: "SUPERSEDED";
      batchRunId: string;
      previousStatus: "PAUSED" | "FAILED";
      previousRunnerRevision: string;
      currentRunnerRevision: string;
      reason: "SUPERSEDED_BY_NEW_REVISION";
      archivedAt: string;
      providerActionsWritten: "NO";
    };
  } = {},
): Promise<{
  elements: PopupElements;
  fetchMock: ReturnType<typeof vi.fn>;
  storageSet: ReturnType<typeof vi.fn>;
  sentMessages: unknown[];
  createdTabs: string[];
  eventOrder: string[];
}> {
  vi.resetModules();
  const elements = createPopupElements();
  const apiBaseUrl = options.apiBaseUrl ?? "http://localhost:8000";
  const snapshot = options.snapshot ?? myProgressSnapshot();
  const localProfiles =
    options.localProfiles ??
    (options.discoveredProfile ? [options.discoveredProfile] : null);
  elements.apiBaseUrlInput.value = apiBaseUrl;
  elements.studentProfileIdInput.value =
    options.storedStudentProfileId === null
      ? ""
      : (options.storedStudentProfileId ?? FAKE_STUDENT_PROFILE_ID);
  const fetchMock = vi.fn(fetchImpl);
  const storageSet = vi.fn();
  const sentMessages: unknown[] = [];
  const createdTabs: string[] = [];
  const eventOrder: string[] = [];
  const runtime: {
    lastError?: { message?: string };
    getURL: (path: string) => string;
    sendMessage: (
      message: unknown,
      callback: (response: unknown) => void,
    ) => void;
  } = {
    getURL: (path: string) => `chrome-extension://extension-id/${path}`,
    sendMessage: (message: unknown, callback: (response: unknown) => void) => {
      sentMessages.push(message);
      eventOrder.push(
        typeof message === "object" &&
          message !== null &&
          "type" in message &&
          typeof message.type === "string"
          ? `message:${message.type}`
          : "message:UNKNOWN",
      );
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === "SAPSOS_GET_PAIRING_STATUS"
      ) {
        callback({
          ok: true,
          status: 200,
          payload: { paired: localProfiles !== null },
        });
        return;
      }
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === "SAPSOS_GET_CATALOG_BATCH_STATE"
      ) {
        callback({
          ok: true,
          status: 200,
          payload: options.catalogBatchState ?? null,
        });
        return;
      }
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === "SAPSOS_START_CATALOG_BATCH"
      ) {
        if (options.startBatchResponse) {
          callback(options.startBatchResponse);
          return;
        }
        callback({
          ok: true,
          status: 202,
          payload:
            options.startBatchState ??
            options.catalogBatchState ??
            catalogBatchFixture(),
        });
        return;
      }
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === "SAPSOS_GET_LOCAL_STUDENT_PROFILES"
      ) {
        callback({
          ok: true,
          status: 200,
          payload: (localProfiles ?? []).map((profile) => ({
            student: {
              id: profile.id,
              display_name: profile.displayName,
            },
          })),
        });
        return;
      }
      if (
        typeof message !== "object" ||
        message === null ||
        !("type" in message) ||
        message.type !== "SAPSOS_SUBMIT_IMPORT" ||
        !("apiBaseUrl" in message) ||
        typeof message.apiBaseUrl !== "string" ||
        !("request" in message)
      ) {
        callback({
          ok: false,
          status: 400,
          payload: { detail: "Unsupported popup test message." },
        });
        return;
      }
      void fetchMock(`${message.apiBaseUrl}/api/v1/data-imports`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(message.request),
      }).then(async (response) => {
        callback({
          ok: response.ok,
          status: response.status,
          payload: await response.json().catch(() => null),
        });
      });
    },
  };
  const chromeApi = {
    runtime,
    storage: {
      local: {
        get: (
          _keys: string[],
          callback: (settings: {
            apiBaseUrl?: string;
            studentProfileId?: string;
            catalogBatchLifecycleNotice?: typeof options.catalogBatchLifecycleNotice;
          }) => void,
        ) => {
          callback(
            options.storedStudentProfileId === null
              ? { apiBaseUrl }
              : {
                  apiBaseUrl,
                  studentProfileId:
                    options.storedStudentProfileId ?? FAKE_STUDENT_PROFILE_ID,
                  ...(options.catalogBatchLifecycleNotice
                    ? {
                        catalogBatchLifecycleNotice:
                          options.catalogBatchLifecycleNotice,
                      }
                    : {}),
                },
          );
        },
        set: storageSet,
      },
    },
    tabs: {
      query: (
        _query: unknown,
        callback: (tabs: Array<{ id: number; url: string }>) => void,
      ) => {
        eventOrder.push("active-tab-query");
        callback([
          {
            id: 42,
            url:
              options.activeTabUrl ??
              `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
          },
        ]);
      },
      create: (
        input: { url: string },
        callback: (tab?: { id?: number }) => void,
      ) => {
        createdTabs.push(input.url);
        if (options.fallbackCreateError) {
          runtime.lastError = { message: options.fallbackCreateError };
          callback();
          delete runtime.lastError;
          return;
        }
        callback({ id: 91 });
      },
    },
    scripting: {
      executeScript: (
        _details: unknown,
        callback: (results: Array<{ result: AcademicPageSnapshot }>) => void,
      ) => {
        callback([{ result: snapshot }]);
      },
    },
    permissions: {
      contains: (
        _permissions: unknown,
        callback: (granted: boolean) => void,
      ) => {
        eventOrder.push("permission-check");
        callback(true);
      },
      request: (_permissions: unknown, callback: (granted: boolean) => void) =>
        callback(true),
    },
    sidePanel: {
      open: async () => {
        eventOrder.push("side-panel-open");
        if (options.sidePanelError) throw new Error(options.sidePanelError);
      },
    },
  };
  const documentStub = {
    getElementById: (id: string) => elements[id] ?? null,
    createElement: () => new FakeElement(),
  };

  vi.stubGlobal("Element", FakeElement);
  vi.stubGlobal("HTMLInputElement", FakeInputElement);
  vi.stubGlobal("HTMLButtonElement", FakeButtonElement);
  vi.stubGlobal("document", documentStub);
  vi.stubGlobal("chrome", chromeApi);
  vi.stubGlobal("fetch", fetchMock);

  await import("../src/popup/popup.js");
  return {
    elements,
    fetchMock,
    storageSet,
    sentMessages,
    createdTabs,
    eventOrder,
  };
}

async function flushPopupWork(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("popup staging import confirmation", () => {
  it("renders persisted full-Catalog progress without exposing portal session data", async () => {
    const state = catalogBatchFixture();
    const { elements } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      { catalogBatchState: state },
    );
    await flushPopupWork();

    expect(elements.catalogBatchStatusText.textContent).toContain(
      "Catalog capture complete",
    );
    expect(elements.catalogBatchProgressText.textContent).toContain(
      "Subjects completed: 2 / 2",
    );
    expect(elements.catalogBatchProgressText.textContent).toContain(
      "Unique courses: 3",
    );
    expect(elements.catalogBatchProgressText.textContent).not.toContain(
      "credential",
    );
  });

  it("reopens on a running SearchResult checkpoint without mutating the batch", async () => {
    const state = catalogBatchFixture("RUNNING");
    const { elements, sentMessages } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: state,
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
      },
    );
    await flushPopupWork();

    expect(elements.catalogBatchStatusText.textContent).toContain(
      "Catalog capture is running read-only",
    );
    expect(sentMessages).not.toContainEqual(
      expect.objectContaining({
        type: expect.stringMatching(
          /SAPSOS_(START|PAUSE|RESUME|CANCEL)_CATALOG_BATCH/,
        ),
      }),
    );
  });

  it("keeps bounded start disabled for a same-revision zero-progress pause", async () => {
    const paused = {
      ...catalogBatchFixture("PAUSED"),
      boundedAcceptancePassed: false,
      boundedAcceptanceRevision: null,
      completedSubjectCount: 0,
      capturedRecordCount: 0,
      uniqueRecordCount: 0,
      duplicateRecordCount: 0,
      lastError: {
        code: "BATCH_CATALOG_WORKER_RESTART",
        message: "The extension worker restarted.",
        context: null,
      },
      pauseReason: "WORKER_RESTART_RECOVERY_REQUIRED",
      lastTransition: "PAUSED" as const,
      stateMachineCheckpoint: "PAUSED" as const,
    };
    const { elements } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      { catalogBatchState: paused },
    );
    await flushPopupWork();

    expect(elements.startCatalogBatchButton.disabled).toBe(true);
    expect(elements.resumeCatalogBatchButton.disabled).toBe(false);
    expect(elements.startCatalogBatchButton.textContent).toBe(
      "Run bounded Catalog acceptance (2 subjects)",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "BATCH_CATALOG_SAME_REVISION_PAUSED_RUN_EXISTS",
    );
  });

  it("explains why a progress-bearing paused acceptance disables a fresh start", async () => {
    const paused = {
      ...catalogBatchFixture("PAUSED"),
      completedSubjectCount: 1,
      capturedRecordCount: 98,
      uniqueRecordCount: 98,
      currentSubjectIndex: 1,
      currentSubject: "AD",
      pauseReason: "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      lastTransition: "PAUSED" as const,
    };
    const { elements } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      { catalogBatchState: paused },
    );
    await flushPopupWork();

    expect(elements.startCatalogBatchButton.disabled).toBe(true);
    expect(elements.resumeCatalogBatchButton.disabled).toBe(false);
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "Previous bounded acceptance is paused",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "Start is disabled",
    );
  });

  it("enables a fresh bounded start after an older acceptance was archived", async () => {
    const { elements } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: null,
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
        catalogBatchLifecycleNotice: {
          kind: "SUPERSEDED",
          batchRunId: "catalog-batch-old",
          previousStatus: "PAUSED",
          previousRunnerRevision: "LEGACY_UNVERSIONED",
          currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
          reason: "SUPERSEDED_BY_NEW_REVISION",
          archivedAt: "2026-08-29T01:00:00.000Z",
          providerActionsWritten: "NO",
        },
      },
    );
    await flushPopupWork();

    expect(elements.startCatalogBatchButton.disabled).toBe(false);
    expect(elements.startCatalogBatchButton.textContent).toBe(
      "Run bounded Catalog acceptance (2 subjects)",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "older build was archived",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "Fresh bounded acceptance is ready",
    );
  });

  it("keeps full Catalog capture locked after bounded acceptance completes", async () => {
    const { elements, sentMessages } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: catalogBatchFixture(),
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Courses",
      },
    );
    await flushPopupWork();

    expect(elements.startCatalogBatchButton.disabled).toBe(true);
    expect(elements.startCatalogBatchButton.textContent).toBe(
      "Full Course Catalog locked",
    );
    expect(elements.catalogBatchStartReasonText.textContent).toContain(
      "FULL_CAPTURE_EXPLICIT_UNLOCK_REQUIRED",
    );
    expect(sentMessages).not.toContainEqual(
      expect.objectContaining({ type: "SAPSOS_START_CATALOG_BATCH" }),
    );
  });

  it("records that a bounded start reached discovery and received a worker response", async () => {
    const running = catalogBatchFixture("RUNNING");
    const { elements, sentMessages, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: null,
        startBatchState: running,
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      },
    );
    await flushPopupWork();
    storageSet.mockClear();

    elements.startCatalogBatchButton.click();
    await flushPopupWork();

    expect(sentMessages).toContainEqual({
      type: "SAPSOS_START_CATALOG_BATCH",
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: FAKE_STUDENT_PROFILE_ID,
      tabId: 42,
      landingUrl:
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      mode: "BOUNDED_ACCEPTANCE",
    });
    expect(storageSet).toHaveBeenCalledWith({
      catalogBatchUiDiagnostics: expect.objectContaining({
        boundedStartMessageReceived: "YES",
        authorizedCatalogTabId: 42,
        authorizedTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
        batchState: "RUNNING",
        discoveryStarted: true,
        discoveredSubjectCount: 2,
        lastTransition: "PAGE_CAPTURED",
        lastError: null,
      }),
    });
  });

  it("fails before dispatch on a Catalog result tab and preserves the exact path diagnosis", async () => {
    const resultUrl =
      "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult";
    const { elements, sentMessages, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      { catalogBatchState: null, activeTabUrl: resultUrl },
    );
    await flushPopupWork();
    storageSet.mockClear();

    elements.startCatalogBatchButton.click();
    await flushPopupWork();

    expect(sentMessages).not.toContainEqual(
      expect.objectContaining({ type: "SAPSOS_START_CATALOG_BATCH" }),
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "BATCH_CATALOG_LANDING_REQUIRED",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "/Student/Student/Courses/SearchResult",
    );
    expect(storageSet).toHaveBeenCalledWith({
      catalogBatchUiDiagnostics: expect.objectContaining({
        boundedStartMessageReceived: "NO",
        authorizedCatalogTabId: null,
        authorizedTabUrl: resultUrl,
        batchState: "NOT_CREATED",
        discoveryStarted: false,
        discoveredSubjectCount: 0,
        lastTransition: "START_PRECHECK_REJECTED",
        lastError: expect.objectContaining({
          code: "BATCH_CATALOG_LANDING_REQUIRED",
        }),
      }),
    });
  });

  it("opens the persistent monitor before any asynchronous bounded-run preflight", async () => {
    const { elements, eventOrder } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: null,
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
      },
    );
    await flushPopupWork();
    eventOrder.length = 0;

    elements.startCatalogBatchButton.click();
    await flushPopupWork();

    expect(eventOrder[0]).toBe("side-panel-open");
    expect(eventOrder).toContain("message:SAPSOS_START_CATALOG_BATCH");
  });

  it("persists the worker's exact bounded-start rejection code", async () => {
    const { elements, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: null,
        activeTabUrl:
          "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
        startBatchResponse: {
          ok: false,
          status: 401,
          payload: { code: "BATCH_CATALOG_PAIRING_REQUIRED" },
        },
      },
    );
    await flushPopupWork();
    storageSet.mockClear();

    elements.startCatalogBatchButton.click();
    await flushPopupWork();

    expect(storageSet).toHaveBeenCalledWith({
      catalogBatchUiDiagnostics: expect.objectContaining({
        boundedStartMessageReceived: "YES",
        lastTransition: "START_RESPONSE_REJECTED",
        lastError: {
          code: "BATCH_CATALOG_PAIRING_REQUIRED",
          message: "BATCH_CATALOG_PAIRING_REQUIRED",
        },
      }),
    });
  });

  it("opens the monitor from the popup gesture and falls back without erasing the batch diagnosis", async () => {
    const resultUrl =
      "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult";
    const { elements, sentMessages, createdTabs } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        catalogBatchState: null,
        activeTabUrl: resultUrl,
        sidePanelError:
          "sidePanel.open() may only be called in response to a user gesture",
      },
    );
    await flushPopupWork();

    elements.startCatalogBatchButton.click();
    await flushPopupWork();

    expect(createdTabs).toEqual([
      "chrome-extension://extension-id/src/monitor/index.html",
    ]);
    expect(sentMessages).not.toContainEqual(
      expect.objectContaining({ type: "SAPSOS_OPEN_CATALOG_BATCH_MONITOR" }),
    );
    expect(elements.catalogBatchMonitorStatusText.textContent).toContain(
      "MONITOR_TAB",
    );
    expect(elements.catalogBatchStatusText.textContent).toContain(
      "BATCH_CATALOG_LANDING_REQUIRED",
    );
  });

  it("auto-selects the only local student profile after pairing", async () => {
    const discoveredId = "44444444-4444-4444-8444-444444444444";
    const { elements, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        discoveredProfile: {
          id: discoveredId,
          displayName: "Local learner",
        },
        storedStudentProfileId: null,
      },
    );
    await flushPopupWork();

    expect(elements.studentProfileIdInput.value).toBe(discoveredId);
    expect(elements.pairingStatusText.textContent).toContain("Local learner");
    expect(storageSet).toHaveBeenCalledWith({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: discoveredId,
    });
  });

  it("clears a stale profile id when pairing has no real local profiles", async () => {
    const { elements, fetchMock, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      { localProfiles: [] },
    );
    await flushPopupWork();

    expect(elements.studentProfileIdInput.value).toBe("");
    expect(elements.pairingStatusText.textContent).toContain(
      "Create a local student profile",
    );
    expect(storageSet).toHaveBeenCalledWith({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "",
    });

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(elements.statusText.textContent).toContain(
      "student profile ID are required",
    );
  });

  it("clears a stale profile id when multiple local profiles are ambiguous", async () => {
    const { elements, storageSet } = await importPopupWithFetch(
      async () => new Response("{}", { status: 200 }),
      {
        localProfiles: [
          {
            id: "44444444-4444-4444-8444-444444444444",
            displayName: "First learner",
          },
          {
            id: "55555555-5555-4555-8555-555555555555",
            displayName: "Second learner",
          },
        ],
      },
    );
    await flushPopupWork();

    expect(elements.studentProfileIdInput.value).toBe("");
    expect(elements.pairingStatusText.textContent).toContain(
      "Multiple local profiles exist",
    );
    expect(storageSet).toHaveBeenCalledWith({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "",
    });
  });

  it("posts confirmed extracted rows and shows import id with row count", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 1,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/data-imports",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledOnce();
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(request?.headers).toMatchObject({
      "content-type": "application/json",
    });
    expect(request?.headers).not.toHaveProperty("authorization");
    expect(JSON.parse(String(request?.body))).toMatchObject({
      student_profile_id: FAKE_STUDENT_PROFILE_ID,
      import_type: "DEGREE_AUDIT_EXPORT",
      source_type: "BROWSER_EXTENSION",
      page_type: "KEAN_MY_PROGRESS_PAGE",
      extracted_record_count: 1,
      visible_row_count: 1,
      academic_field_count: 9,
    });
    expect(elements.statusText.textContent).toContain(CREATED_IMPORT_ID);
    expect(elements.statusText.textContent).toContain("1 row");
    expect(elements.apiStatusText.textContent).toContain("1 staging import");
  });

  it("refuses to send academic imports to a non-local API", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () => new Response("{}", { status: 201 }),
      {
        apiBaseUrl: "https://kean-ss.colleague.elluciancloud.com",
      },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(elements.statusText.textContent).toContain(
      "Staging imports are available only through the paired local app",
    );
  });

  it("shows API error details when the local API rejects confirmation", async () => {
    const { elements } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: "not_found",
              message: "StudentProfile fake-student was not found.",
            },
          }),
          {
            status: 404,
            headers: { "content-type": "application/json" },
          },
        ),
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(elements.apiStatusText.textContent).toContain("HTTP 404");
    expect(elements.apiStatusText.textContent).toContain(
      "StudentProfile fake-student was not found.",
    );
    expect(elements.statusText.textContent).toContain("Staging import failed");
  });

  it("submits the same 85 MyProgress rows that were shown in preview", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 87,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        snapshot: myProgressSnapshot(85),
      },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    expect(elements.statusText.textContent).toBe("Sending...");
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/data-imports",
      expect.objectContaining({ method: "POST" }),
    );
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse(String(request?.body));
    const content = JSON.parse(String(body.content));
    expect(body).toMatchObject({
      import_type: "DEGREE_AUDIT_EXPORT",
      source_type: "BROWSER_EXTENSION",
      page_type: "KEAN_MY_PROGRESS_PAGE",
      extracted_record_count: 85,
      visible_row_count: 85,
      bounded: true,
      truncated: true,
    });
    expect(body.warnings).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: "EXTRACTION_LIMIT_REACHED" }),
      ]),
    );
    expect(body.diagnostics).toMatchObject({
      detectedPageType: "KEAN_MY_PROGRESS_PAGE",
      academicRowsParsed: 85,
      bounded: true,
    });
    expect(content.courseRows).toHaveLength(85);
    expect(content.courseRows[0]).toMatchObject({
      course_code: "MATH 1044",
      course_title: "Precalculus for Business",
      status: "NOT_STARTED",
      source_table_index: "1",
      source_row_index: "1",
      raw_row_text: expect.stringContaining("MATH*1044"),
      field_provenance: expect.objectContaining({
        course_code: expect.objectContaining({
          value: "MATH*1044",
          rawText: expect.stringContaining("MATH*1044"),
        }),
      }),
    });
    expect(content.courseRows[2]).toMatchObject({
      course_code: "ENG 2403",
      term_code: "2026SUW",
      status: "PLANNED",
    });
    expect(content.warnings).toEqual(body.warnings);
    expect(content.diagnostics).toEqual(body.diagnostics);
    expect(elements.statusText.textContent).toContain(
      "Success: staging import created",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted DEGREE_AUDIT_EXPORT rows: 85",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted visible rows: 85",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted academic fields:",
    );
  });

  it("disables confirmation and ignores rapid repeat clicks while submitting", async () => {
    let resolveRequest: ((response: Response) => void) | undefined;
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveRequest = resolve;
    });
    const { elements, fetchMock } = await importPopupWithFetch(
      async () => pendingResponse,
      { snapshot: myProgressSnapshot(85) },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    elements.confirmImportButton.click();

    expect(elements.confirmImportButton.disabled).toBe(true);
    expect(elements.statusText.textContent).toBe("Sending...");
    expect(fetchMock).toHaveBeenCalledOnce();

    resolveRequest?.(
      new Response(
        JSON.stringify({
          id: CREATED_IMPORT_ID,
          record_count: 87,
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    await flushPopupWork();

    expect(elements.confirmImportButton.disabled).toBe(false);
    expect(elements.statusText.textContent).toContain(
      "Success: staging import created",
    );
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("does not show success when the API accepts fewer rows than were submitted", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 1,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      { snapshot: myProgressSnapshot(85) },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(elements.statusText.textContent).toContain("Staging import failed");
    expect(elements.apiStatusText.textContent).toContain(
      "accepted 1 record but 85 extracted row(s) were submitted",
    );
    expect(elements.statusText.textContent).not.toContain(
      "Success: staging import created",
    );
  });
});
