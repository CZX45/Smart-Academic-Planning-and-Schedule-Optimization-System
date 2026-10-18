import {
  handleAuthorizedCatalogTabClosed,
  handleCatalogPageSignal,
  handleCatalogSubjectNavigationSignal,
  handleCatalogTabLoaded,
  recordCatalogTabUpdate,
  resumeCatalogBatchEventDriven,
  type CatalogBatchEventDriver,
} from "./catalog-batch-controller.js";
import {
  CatalogBatchError,
  CATALOG_BATCH_ARCHIVE_LIMIT,
  CATALOG_BATCH_ACCEPTANCE_REVISION,
  CATALOG_FULL_CAPTURE_UNLOCKED,
  CATALOG_BATCH_LOCAL_PROCESSING_STAGES,
  archiveCatalogBatchEvidence,
  cancelCatalogBatch,
  catalogPreparationCheckpointToken,
  createCatalogBatchState,
  restoreCatalogBatchState,
  type CatalogBatchArchive,
  type CatalogBatchArchiveStatus,
  type CatalogBatchLifecycleNotice,
  type CatalogBatchPage,
  type CatalogBatchState,
  type CatalogSubjectLocalOutcome,
} from "../content/catalog-batch.js";
import {
  catalogBatchPublicState,
  pauseCatalogBatchForReason,
  recordCatalogBatchTransition,
} from "../content/catalog-batch-lifecycle.js";
import {
  advanceCatalogResultPage,
  discoverCatalogSubjects,
  inspectCatalogResultPage,
  prepareCatalogSubjectSearch,
  watchCatalogSubjectNavigation,
  watchCatalogResultPage,
  type CatalogPageSignal,
  type CatalogSubjectNavigationSignal,
} from "../content/catalog-batch-page.js";
import {
  extractAcademicPageFromTables,
  createDataImportRequestFromExtraction,
} from "../content/extractors.js";
import { BOUNDED_EXTRACTION_LIMITS } from "../content/snapshot-limits.js";
import { snapshotVisibleAcademicPage } from "../popup/browser-actions.js";
import { isLocalApiBaseUrl } from "../shared/local-api.js";
import {
  openCatalogBatchMonitor,
  safeExtensionError,
} from "../shared/catalog-monitor.js";
import type {
  AcademicPageSnapshot,
  BrowserExtensionDataImportRequest,
} from "../shared/types.js";

type PairingRecord = {
  apiBaseUrl: string;
  credential: string;
  protocolVersion: number;
};

type Message =
  | { type: "SAPSOS_PAIR_EXTENSION"; apiBaseUrl: string; code: string }
  | { type: "SAPSOS_GET_PAIRING_STATUS"; apiBaseUrl: string }
  | { type: "SAPSOS_GET_LOCAL_STUDENT_PROFILES"; apiBaseUrl: string }
  | {
      type: "SAPSOS_SUBMIT_IMPORT";
      apiBaseUrl: string;
      request: Record<string, unknown>;
    }
  | {
      type: "SAPSOS_START_CATALOG_BATCH";
      apiBaseUrl: string;
      studentProfileId: string;
      tabId: number;
      landingUrl: string;
      mode: "BOUNDED_ACCEPTANCE" | "FULL";
    }
  | { type: "SAPSOS_GET_CATALOG_BATCH_STATE"; apiBaseUrl: string }
  | { type: "SAPSOS_PAUSE_CATALOG_BATCH"; apiBaseUrl: string }
  | { type: "SAPSOS_RESUME_CATALOG_BATCH"; apiBaseUrl: string }
  | { type: "SAPSOS_CANCEL_CATALOG_BATCH"; apiBaseUrl: string }
  | CatalogPageSignal
  | CatalogSubjectNavigationSignal
  | {
      type: "SAPSOS_OPEN_CATALOG_BATCH_MONITOR";
      apiBaseUrl: string;
      tabId: number;
    };

type WorkerTab = {
  id?: number;
  url?: string;
  title?: string;
  windowId?: number;
};

type WorkerMessageSender = { id?: string; tab?: WorkerTab };

type ChromeRuntime = {
  id?: string;
  lastError?: { message?: string };
  getURL: (path: string) => string;
  getManifest?: () => { version: string };
  onInstalled: { addListener: (listener: () => void) => void };
  onMessage: {
    addListener: (
      listener: (
        message: Message,
        sender: WorkerMessageSender,
        sendResponse: (response: unknown) => void,
      ) => boolean,
    ) => void;
  };
};

type ChromeStorage = {
  local: {
    get: (
      keys: string[],
      callback: (value: {
        sapsosPairing?: PairingRecord;
        catalogBatch?: CatalogBatchState;
        catalogBatchArchives?: CatalogBatchArchive[];
        catalogBatchLifecycleNotice?: CatalogBatchLifecycleNotice;
      }) => void,
    ) => void;
    set: (
      value: {
        sapsosPairing?: PairingRecord;
        catalogBatch?: CatalogBatchState;
        catalogBatchArchives?: CatalogBatchArchive[];
        catalogBatchLifecycleNotice?: CatalogBatchLifecycleNotice;
      },
      callback?: () => void,
    ) => void;
    remove: (keys: string[], callback?: () => void) => void;
  };
  session: {
    remove: (keys: string[], callback?: () => void) => void;
  };
};

type ChromeTabs = {
  get: (tabId: number, callback: (tab: WorkerTab) => void) => void;
  update: (
    tabId: number,
    updateProperties: { url: string },
    callback: (tab?: WorkerTab) => void,
  ) => void;
  reload: (
    tabId: number,
    reloadProperties: Record<string, never>,
    callback: () => void,
  ) => void;
  create: (
    createProperties: { url: string },
    callback?: (tab?: WorkerTab) => void,
  ) => void;
  onUpdated: {
    addListener: (
      listener: (
        tabId: number,
        changeInfo: { status?: string; url?: string },
        tab: WorkerTab,
      ) => void,
    ) => void;
  };
  onRemoved: {
    addListener: (listener: (tabId: number) => void) => void;
  };
};

type ChromeScripting = {
  executeScript: <Argument, Result>(
    details: {
      target: { tabId: number };
      func: (argument: Argument) => Result | Promise<Result>;
      args: [Argument];
      world?: "ISOLATED" | "MAIN";
    },
    callback: (results: Array<{ result?: Result | null }>) => void,
  ) => void;
};

declare const chrome: {
  runtime: ChromeRuntime;
  storage: ChromeStorage;
  tabs: ChromeTabs;
  scripting: ChromeScripting;
  sidePanel?: {
    open: (options: { tabId?: number; windowId?: number }) => Promise<void>;
  };
};

const CATALOG_PAGE_READY_TIMEOUT_MS = 20_000;
const CATALOG_PAGE_SETTLE_MS = 300;

function persistPairing(pairing: PairingRecord): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.set({ sapsosPairing: pairing }, () => {
      const storageError = chrome.runtime.lastError?.message;
      if (storageError) {
        reject(new Error("Extension storage is unavailable."));
        return;
      }
      resolve();
    });
  });
}

function readStoredWorkerData(): Promise<{
  sapsosPairing?: PairingRecord;
  catalogBatch?: CatalogBatchState;
  catalogBatchArchives?: CatalogBatchArchive[];
  catalogBatchLifecycleNotice?: CatalogBatchLifecycleNotice;
}> {
  return new Promise((resolve) => {
    chrome.storage.local.get(
      [
        "sapsosPairing",
        "catalogBatch",
        "catalogBatchArchives",
        "catalogBatchLifecycleNotice",
      ],
      resolve,
    );
  });
}

function persistCatalogBatch(state: CatalogBatchState): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.set({ catalogBatch: state }, () => {
      const storageError = chrome.runtime.lastError?.message;
      if (storageError) {
        reject(
          new CatalogBatchError(
            "BATCH_CATALOG_STATE_PERSIST_FAILED",
            "The durable Catalog batch checkpoint could not be saved.",
            new Error(storageError),
          ),
        );
        return;
      }
      resolve();
    });
  });
}

function clearCatalogBatchLease(): Promise<void> {
  return new Promise((resolve) => {
    chrome.storage.session.remove(["catalogBatchLease"], resolve);
  });
}

function clearStoredCatalogBatch(): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.remove(["catalogBatch"], () => {
      const storageError = chrome.runtime.lastError?.message;
      if (storageError) {
        reject(new Error("BATCH_CATALOG_STORAGE_UNAVAILABLE"));
        return;
      }
      resolve();
    });
  });
}

function clearCatalogBatchLifecycleNotice(): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.remove(["catalogBatchLifecycleNotice"], () => {
      const storageError = chrome.runtime.lastError?.message;
      if (storageError) {
        reject(new Error("BATCH_CATALOG_STORAGE_UNAVAILABLE"));
        return;
      }
      resolve();
    });
  });
}

async function persistCatalogBatchArchive(
  state: CatalogBatchState,
  archiveStatus: CatalogBatchArchiveStatus,
  reason: "SUPERSEDED_BY_NEW_REVISION" | "REPLACED_BY_NEW_RUN",
  archivedAt: string,
  notice?: CatalogBatchLifecycleNotice,
): Promise<void> {
  const stored = await readStoredWorkerData();
  const archive = archiveCatalogBatchEvidence(
    state,
    archiveStatus,
    reason,
    archivedAt,
  );
  const existing = Array.isArray(stored.catalogBatchArchives)
    ? stored.catalogBatchArchives
    : [];
  const alreadyArchived = existing.some(
    (candidate) =>
      candidate.batchRunId === archive.batchRunId &&
      candidate.archiveStatus === archive.archiveStatus &&
      candidate.reason === archive.reason,
  );
  const nextArchives = alreadyArchived ? [...existing] : [...existing, archive];
  const transientArchivesToKeep = new Set(
    nextArchives
      .filter((candidate) => candidate.archiveStatus !== "COMPLETED")
      .slice(-CATALOG_BATCH_ARCHIVE_LIMIT),
  );
  const catalogBatchArchives = nextArchives.filter(
    (candidate) =>
      candidate.archiveStatus === "COMPLETED" ||
      transientArchivesToKeep.has(candidate),
  );
  await new Promise<void>((resolve, reject) => {
    chrome.storage.local.set(
      {
        catalogBatchArchives,
        ...(notice ? { catalogBatchLifecycleNotice: notice } : {}),
      },
      () => {
        const storageError = chrome.runtime.lastError?.message;
        if (storageError) {
          reject(new Error("BATCH_CATALOG_STORAGE_UNAVAILABLE"));
          return;
        }
        resolve();
      },
    );
  });
}

function archiveStatusForReplacement(
  status: CatalogBatchState["status"],
): CatalogBatchArchiveStatus {
  if (status === "COMPLETED" || status === "CANCELLED" || status === "FAILED") {
    return status;
  }
  return "SUPERSEDED";
}

function getTab(tabId: number): Promise<WorkerTab> {
  return new Promise((resolve, reject) => {
    chrome.tabs.get(tabId, (tab) => {
      const tabError = chrome.runtime.lastError?.message;
      if (tabError) {
        reject(
          new CatalogBatchError("BATCH_CATALOG_TAB_UNAVAILABLE", tabError),
        );
        return;
      }
      resolve(tab);
    });
  });
}

function navigateTab(tabId: number, url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.tabs.update(tabId, { url }, () => {
      const tabError = chrome.runtime.lastError?.message;
      if (tabError) {
        reject(
          new CatalogBatchError("BATCH_CATALOG_TAB_UNAVAILABLE", tabError),
        );
        return;
      }
      resolve();
    });
  });
}

function reloadTab(tabId: number): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.tabs.reload(tabId, {}, () => {
      const tabError = chrome.runtime.lastError?.message;
      if (tabError) {
        reject(
          new CatalogBatchError("BATCH_CATALOG_TAB_UNAVAILABLE", tabError),
        );
        return;
      }
      resolve();
    });
  });
}

type TabExecutionResult<Result> =
  | { kind: "VALUE"; value: Result }
  | { kind: "NULL_RESULT"; value: null }
  | { kind: "MISSING_RESULT"; value: undefined }
  | { kind: "EMPTY_RESULTS"; value: undefined };

function executeTabFunctionResult<Argument, Result>(
  tabId: number,
  func: (argument: Argument) => Result | Promise<Result>,
  argument: Argument,
  world?: "ISOLATED" | "MAIN",
  failureCode = "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
): Promise<TabExecutionResult<Result>> {
  return new Promise((resolve, reject) => {
    try {
      chrome.scripting.executeScript(
        {
          target: { tabId },
          func,
          args: [argument],
          ...(world ? { world } : {}),
        },
        (results) => {
          const executionError = chrome.runtime.lastError?.message;
          if (executionError) {
            const explicitCode = executionError.match(
              /^([A-Z][A-Z0-9_]+)(?::|$)/,
            )?.[1];
            reject(
              new CatalogBatchError(
                explicitCode ?? failureCode,
                "The browser rejected the reviewed Catalog page operation.",
                new Error(executionError),
              ),
            );
            return;
          }
          if (results.length === 0) {
            resolve({ kind: "EMPTY_RESULTS", value: undefined });
            return;
          }
          const result = results[0]?.result;
          if (result === undefined) {
            resolve({ kind: "MISSING_RESULT", value: undefined });
            return;
          }
          if (result === null) {
            resolve({ kind: "NULL_RESULT", value: null });
            return;
          }
          resolve({ kind: "VALUE", value: result });
        },
      );
    } catch (error: unknown) {
      reject(
        new CatalogBatchError(
          failureCode,
          "The browser could not start the reviewed Catalog page operation.",
          error,
        ),
      );
    }
  });
}

async function executeTabFunction<Argument, Result>(
  tabId: number,
  func: (argument: Argument) => Result | Promise<Result>,
  argument: Argument,
  world?: "ISOLATED" | "MAIN",
  failureCode = "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
): Promise<Result> {
  const execution = await executeTabFunctionResult(
    tabId,
    func,
    argument,
    world,
    failureCode,
  );
  if (execution.kind !== "VALUE") {
    throw new CatalogBatchError(
      "BATCH_CATALOG_CONTENT_SCRIPT_RESULT_INVALID",
      `The visible page returned ${execution.kind} instead of the reviewed Catalog operation result.`,
      undefined,
      { returnedResultKind: execution.kind },
    );
  }
  return execution.value;
}

async function executeTabNavigationFunction<Argument, Result>(
  tabId: number,
  func: (argument: Argument) => Result | Promise<Result>,
  argument: Argument,
  world?: "ISOLATED" | "MAIN",
  failureCode = "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
): Promise<
  Extract<TabExecutionResult<Result>, { kind: "VALUE" | "NULL_RESULT" }>
> {
  const execution = await executeTabFunctionResult(
    tabId,
    func,
    argument,
    world,
    failureCode,
  );
  if (
    execution.kind === "EMPTY_RESULTS" ||
    execution.kind === "MISSING_RESULT"
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_SEARCH_SUBMIT_RESULT_INVALID",
      `The Catalog submit operation returned ${execution.kind} without navigation-result evidence.`,
      undefined,
      { returnedResultKind: execution.kind },
    );
  }
  return execution;
}

function safePageUrl(url: string): string {
  const parsed = new URL(url);
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
}

async function responsePayload(
  response: Response,
): Promise<Record<string, unknown>> {
  const payload: unknown = await response.json().catch(() => ({}));
  return typeof payload === "object" && payload !== null
    ? (payload as Record<string, unknown>)
    : {};
}

function extensionRequestHeaders(credential: string): Record<string, string> {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const nonce = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return {
    "content-type": "application/json",
    "X-SAPSOS-Extension-Id": chrome.runtime.id ?? "",
    "X-SAPSOS-Extension-Credential": credential,
    "X-SAPSOS-Extension-Nonce": nonce,
    "X-SAPSOS-Extension-Timestamp": String(Date.now()),
  };
}

function sendJson(
  sendResponse: (response: unknown) => void,
  response: Response,
): Promise<void> {
  return responsePayload(response).then((payload) => {
    sendResponse({ ok: response.ok, status: response.status, payload });
  });
}

function objectValue(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function integerValue(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0
    ? value
    : null;
}

async function pairedLocalRequest(
  apiBaseUrl: string,
  path: string,
  method: "GET" | "POST",
  body?: BrowserExtensionDataImportRequest,
): Promise<Record<string, unknown>> {
  const stored = await readStoredWorkerData();
  const pairing = stored.sapsosPairing;
  if (!pairing || pairing.apiBaseUrl !== apiBaseUrl) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PAIRING_REQUIRED",
      "Pair with the isolated local app before starting or resuming the batch.",
    );
  }
  const response = await fetch(`${apiBaseUrl.replace(/\/+$/, "")}${path}`, {
    method,
    headers: extensionRequestHeaders(pairing.credential),
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const payload = await responsePayload(response);
  if (!response.ok) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_LOCAL_API_FAILED",
      `The isolated local API rejected batch processing with HTTP ${response.status}.`,
    );
  }
  return payload;
}

async function captureCatalogPage(
  state: CatalogBatchState,
  subjectCode: string,
  expectedPage: number,
  expectedResultFingerprint: string,
): Promise<CatalogBatchPage> {
  const tab = await getTab(state.tabId);
  const currentUrl = tab.url ? safePageUrl(tab.url) : "";
  if (!currentUrl) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_TAB_UNAVAILABLE",
      "The authorized Catalog result tab URL was unavailable.",
    );
  }
  const inspection = await executeTabFunction(
    state.tabId,
    inspectCatalogResultPage,
    { expectedUrl: currentUrl, expectedSubject: subjectCode },
  );
  if (!inspection.ready) {
    throw new CatalogBatchError(
      inspection.errorCode,
      "The visible Catalog result page no longer matched the page-ready checkpoint.",
    );
  }
  if (
    inspection.pageNumber !== expectedPage ||
    inspection.subjectCode !== subjectCode ||
    inspection.resultFingerprint !== expectedResultFingerprint
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PAGINATION_INVALID",
      "The visible Catalog page did not match the requested page checkpoint.",
    );
  }
  const snapshot = await executeTabFunction(
    state.tabId,
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );
  const extraction = extractAcademicPageFromTables({
    ...(snapshot as AcademicPageSnapshot),
    title: tab.title ?? "Course Catalog",
    url: currentUrl,
  });
  if (
    extraction.records.length === 0 ||
    extraction.records.length !== inspection.visibleCourseCount
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PARSER_DRIFT",
      "The visible Catalog result card count did not exactly match the extracted course count.",
    );
  }
  return {
    subjectCode,
    pageNumber: inspection.pageNumber,
    totalPages: inspection.totalPages,
    fatalSignal: inspection.fatalSignal,
    extraction,
  };
}

function catalogProcessOutcome(
  payload: Record<string, unknown>,
  importRunId: string,
): CatalogSubjectLocalOutcome {
  const reasonCodes = Array.isArray(payload.reason_codes)
    ? payload.reason_codes.filter(
        (reason): reason is string => typeof reason === "string",
      )
    : ["BATCH_CATALOG_LOCAL_RESPONSE_INVALID"];
  const applicationResult = objectValue(payload.application_result);
  const appliedRecords = Array.isArray(applicationResult?.applied_records)
    ? applicationResult.applied_records
    : [];
  const createdCount = appliedRecords.filter(
    (record) => objectValue(record)?.action === "CREATED",
  ).length;
  const updatedCount = appliedRecords.filter(
    (record) => objectValue(record)?.action === "UPDATED",
  ).length;
  const reviewSession = objectValue(payload.review_session);
  const reviewSessionId =
    typeof reviewSession?.id === "string" ? reviewSession.id : null;
  const processingStagesCompleted = Array.isArray(
    payload.processing_stages_completed,
  )
    ? payload.processing_stages_completed.filter(
        (
          stage,
        ): stage is (typeof CATALOG_BATCH_LOCAL_PROCESSING_STAGES)[number] =>
          typeof stage === "string" &&
          CATALOG_BATCH_LOCAL_PROCESSING_STAGES.includes(
            stage as (typeof CATALOG_BATCH_LOCAL_PROCESSING_STAGES)[number],
          ),
      )
    : [];
  const stagedRecordCount = integerValue(payload.staged_record_count);
  const reviewValidCount = integerValue(payload.review_valid_count);
  const reviewWarningCount = integerValue(payload.review_warning_count);
  const appliedRecordCount = integerValue(payload.applied_record_count);
  const myprogressTotalCount = integerValue(payload.myprogress_total_count);
  const myprogressMappedBeforeCount = integerValue(
    payload.myprogress_mapped_before_count,
  );
  const myprogressMappedCount = integerValue(payload.myprogress_mapped_count);
  const myprogressUnmatchedCount = integerValue(
    payload.myprogress_unmatched_count,
  );
  const myprogressRemapExecuted = payload.myprogress_remap_executed === true;
  if (
    payload.status !== "APPLIED" ||
    payload.provider_actions_written !== "NO" ||
    reasonCodes.length > 0 ||
    !applicationResult ||
    processingStagesCompleted.length !==
      CATALOG_BATCH_LOCAL_PROCESSING_STAGES.length ||
    processingStagesCompleted.some(
      (stage, index) => stage !== CATALOG_BATCH_LOCAL_PROCESSING_STAGES[index],
    ) ||
    stagedRecordCount === null ||
    reviewValidCount === null ||
    reviewWarningCount === null ||
    appliedRecordCount === null ||
    myprogressTotalCount === null ||
    myprogressMappedBeforeCount === null ||
    myprogressMappedCount === null ||
    myprogressUnmatchedCount === null ||
    !myprogressRemapExecuted
  ) {
    throw new CatalogBatchError(
      reasonCodes[0] ?? "BATCH_CATALOG_LOCAL_APPLY_BLOCKED",
      "The isolated local dry-run or Apply gate blocked this Catalog subject.",
    );
  }
  return {
    importRunId,
    reviewSessionId,
    createdCount,
    updatedCount,
    processingStagesCompleted,
    stagedRecordCount,
    reviewValidCount,
    reviewWarningCount,
    appliedRecordCount,
    myprogressRunId:
      typeof payload.myprogress_run_id === "string"
        ? payload.myprogress_run_id
        : null,
    myprogressTotalCount,
    myprogressMappedBeforeCount,
    myprogressMappedCount,
    myprogressUnmatchedCount,
    myprogressRemapExecuted: true,
    reasonCodes,
    providerActionsWritten: "NO",
    completedAt: new Date().toISOString(),
  };
}

function createCatalogBatchDriver(): CatalogBatchEventDriver {
  return {
    now: () => new Date().toISOString(),
    loadState: async (batchId) => {
      const state = (await readStoredWorkerData()).catalogBatch;
      return state && (!batchId || state.batchId === batchId) ? state : null;
    },
    persistState: persistCatalogBatch,
    getAuthorizedTabUrl: async (tabId) => {
      try {
        return (await getTab(tabId)).url ?? null;
      } catch {
        return null;
      }
    },
    navigateToLanding: (state) => navigateTab(state.tabId, state.landingUrl),
    watchSubjectNavigation: async (state, navigationRevision) => {
      const subjectCode =
        state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN";
      await executeTabFunction(
        state.tabId,
        watchCatalogSubjectNavigation,
        {
          expectedUrl: state.landingUrl,
          expectedSubject: subjectCode,
          batchId: state.batchId,
          navigationRevision,
          checkpointToken: catalogPreparationCheckpointToken(
            state.batchId,
            navigationRevision,
            subjectCode,
          ),
          timeoutMs: CATALOG_PAGE_READY_TIMEOUT_MS,
        },
        "ISOLATED",
        "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
      );
    },
    startSubjectSearch: async (state, subject) => {
      const execution = await executeTabNavigationFunction(
        state.tabId,
        prepareCatalogSubjectSearch,
        {
          expectedUrl: state.landingUrl,
          subjectCode: subject.code,
          readyTimeoutMs: CATALOG_PAGE_READY_TIMEOUT_MS,
          settleMs: CATALOG_PAGE_SETTLE_MS,
          submitCheckpoint: {
            batchId: state.batchId,
            navigationRevision: state.expectedNavigationRevision,
            checkpointToken: catalogPreparationCheckpointToken(
              state.batchId,
              state.expectedNavigationRevision,
              subject.code,
            ),
            acknowledgmentTimeoutMs: 1_500,
          },
        },
        "MAIN",
        "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
      );
      if (
        execution.kind === "VALUE" &&
        (execution.value.action !== "CATALOG_SEARCH_PREPARED_AND_SUBMITTED" ||
          execution.value.subjectCode !== subject.code ||
          execution.value.completedCheckpoints.join("|") !==
            "LANDING_DOM_READY|KNOCKOUT_READY|SUBJECT_SELECTED|SUBJECT_SELECTION_VERIFIED|CATALOG_LISTING_SELECTED|CATALOG_LISTING_VERIFIED|SEARCH_SUBMITTED" ||
          execution.value.providerActionsWritten !== "NO")
      ) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_SEARCH_SUBMIT_RESULT_INVALID",
          "The Catalog submit operation returned an unexpected navigation result.",
          undefined,
          { returnedResultKind: "UNEXPECTED_VALUE" },
        );
      }
      return execution.kind === "VALUE"
        ? {
            preparation: {
              action: "CATALOG_SEARCH_PREPARED" as const,
              subjectCode: subject.code,
              completedCheckpoints: [
                "LANDING_DOM_READY",
                "KNOCKOUT_READY",
                "SUBJECT_SELECTED",
                "SUBJECT_SELECTION_VERIFIED",
                "CATALOG_LISTING_SELECTED",
                "CATALOG_LISTING_VERIFIED",
              ] as const,
              providerActionsWritten: "NO" as const,
            },
            preparationResultKind: "VALUE",
            submissionResultKind: "VALUE",
          }
        : {
            preparation: null,
            preparationResultKind: "NULL_RESULT",
            submissionResultKind: "NULL_RESULT",
          };
    },
    watchResultPage: async (state, expectedPage, previousFirstCourseMarker) => {
      const tab = await getTab(state.tabId);
      if (!tab.url) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_TAB_UNAVAILABLE",
          "The authorized Catalog result tab URL was unavailable.",
        );
      }
      await executeTabFunction(
        state.tabId,
        watchCatalogResultPage,
        {
          expectedUrl: safePageUrl(tab.url),
          batchId: state.batchId,
          expectedPage,
          expectedSubject:
            state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN",
          navigationRevision: state.expectedNavigationRevision,
          runnerRevision: state.runnerRevision,
          previousFirstCourseMarker,
          previousResultFingerprint:
            expectedPage > 1
              ? (state.acceptedPageFingerprints[
                  `${state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN"}:${expectedPage - 1}`
                ] ?? null)
              : null,
          timeoutMs: CATALOG_PAGE_READY_TIMEOUT_MS,
          settleMs: CATALOG_PAGE_SETTLE_MS,
        },
        undefined,
        "BATCH_CATALOG_CONTENT_SCRIPT_UNAVAILABLE",
      );
    },
    capturePage: (state, subject, expectedPage, expectedResultFingerprint) =>
      captureCatalogPage(
        state,
        subject.code,
        expectedPage,
        expectedResultFingerprint,
      ),
    advancePage: async (state, targetPage) => {
      const tab = await getTab(state.tabId);
      if (!tab.url) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_TAB_UNAVAILABLE",
          "The visible Catalog result tab URL was unavailable.",
        );
      }
      await executeTabFunction(state.tabId, advanceCatalogResultPage, {
        expectedUrl: safePageUrl(tab.url),
        targetPage,
        batchId: state.batchId,
        expectedSubject:
          state.subjects[state.currentSubjectIndex]?.code ?? "UNKNOWN",
        navigationRevision: state.expectedNavigationRevision,
        runnerRevision: state.runnerRevision,
        timeoutMs: CATALOG_PAGE_READY_TIMEOUT_MS,
        settleMs: CATALOG_PAGE_SETTLE_MS,
      });
    },
    processSubject: async (state, extraction) => {
      const request = createDataImportRequestFromExtraction(
        state.studentProfileId,
        extraction,
      );
      const created = await pairedLocalRequest(
        state.apiBaseUrl,
        "/api/v1/data-imports",
        "POST",
        request,
      );
      if (typeof created.id !== "string") {
        throw new CatalogBatchError(
          "BATCH_CATALOG_LOCAL_RESPONSE_INVALID",
          "The isolated local import did not return an import identity.",
        );
      }
      const stored = (await readStoredWorkerData()).catalogBatch;
      if (
        !stored ||
        stored.batchId !== state.batchId ||
        stored.status !== "RUNNING"
      ) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_CONTROL_STATE_CHANGED",
          "The Catalog batch was paused or replaced before local validation began.",
        );
      }
      await persistCatalogBatch({
        ...stored,
        processingStage: "LOCAL_VALIDATION",
        completedProcessingStages: [
          ...new Set([
            ...stored.completedProcessingStages,
            "LOCAL_STAGING" as const,
          ]),
        ],
        updatedAt: new Date().toISOString(),
        providerActionsWritten: "NO",
      });
      const processed = await pairedLocalRequest(
        state.apiBaseUrl,
        `/api/v1/data-imports/${created.id}/catalog-batch-process`,
        "POST",
      );
      return catalogProcessOutcome(processed, created.id);
    },
  };
}

async function handleMessage(
  message: Message,
  sender: WorkerMessageSender,
  sendResponse: (response: unknown) => void,
): Promise<void> {
  await workerInitialization;
  if (message.type === "SAPSOS_CATALOG_PAGE_SIGNAL") {
    const senderTabId = sender.tab?.id;
    if (!Number.isInteger(senderTabId)) {
      sendResponse({
        ok: false,
        status: 403,
        payload: { code: "BATCH_CATALOG_SIGNAL_SENDER_INVALID" },
      });
      return;
    }
    const state = await handleCatalogPageSignal(
      message,
      senderTabId as number,
      createCatalogBatchDriver(),
    );
    if (state && state.status !== "RUNNING") await clearCatalogBatchLease();
    sendResponse({
      ok: true,
      status: 200,
      payload: state
        ? catalogBatchPublicState(state, new Date().toISOString())
        : null,
    });
    return;
  }
  if (message.type === "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL") {
    const senderTabId = sender.tab?.id;
    if (!Number.isInteger(senderTabId)) {
      sendResponse({
        ok: false,
        status: 403,
        payload: { code: "BATCH_CATALOG_SIGNAL_SENDER_INVALID" },
      });
      return;
    }
    const state = await handleCatalogSubjectNavigationSignal(
      message,
      senderTabId as number,
      createCatalogBatchDriver(),
    );
    if (state && state.status !== "RUNNING") await clearCatalogBatchLease();
    const checkpointAccepted =
      message.signal !== "PREPARATION_VERIFIED" ||
      (state?.batchId === message.batchId &&
        state.preparationCheckpointRevision === message.navigationRevision &&
        state.lastSuccessfulCheckpoint === "CATALOG_LISTING_VERIFIED");
    sendResponse({
      ok: checkpointAccepted,
      status: checkpointAccepted ? 200 : 409,
      payload: state
        ? catalogBatchPublicState(state, new Date().toISOString())
        : null,
    });
    return;
  }
  if (!isLocalApiBaseUrl(message.apiBaseUrl)) {
    sendResponse({
      ok: false,
      status: 400,
      payload: { code: "local_api_required" },
    });
    return;
  }
  if (message.type === "SAPSOS_PAIR_EXTENSION") {
    const response = await fetch(
      `${message.apiBaseUrl.replace(/\/+$/, "")}/local/pairing/complete`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code: message.code, protocol_version: 1 }),
      },
    );
    const payload = await responsePayload(response);
    if (response.ok && typeof payload.credential === "string") {
      await persistPairing({
        apiBaseUrl: message.apiBaseUrl,
        credential: payload.credential,
        protocolVersion: Number(payload.protocol_version),
      });
    }
    sendResponse({ ok: response.ok, status: response.status, payload });
    return;
  }
  if (message.type === "SAPSOS_GET_PAIRING_STATUS") {
    const response = await fetch(
      `${message.apiBaseUrl.replace(/\/+$/, "")}/local/pairing/status`,
      {
        headers: {
          "content-type": "application/json",
          "X-SAPSOS-Extension-Id": chrome.runtime.id ?? "",
        },
      },
    );
    await sendJson(sendResponse, response);
    return;
  }
  if (message.type === "SAPSOS_GET_CATALOG_BATCH_STATE") {
    const state = (await readStoredWorkerData()).catalogBatch ?? null;
    sendResponse({
      ok: true,
      status: 200,
      payload: state
        ? catalogBatchPublicState(state, new Date().toISOString())
        : null,
    });
    return;
  }
  if (message.type === "SAPSOS_OPEN_CATALOG_BATCH_MONITOR") {
    if (!Number.isInteger(message.tabId) || message.tabId < 0) {
      sendResponse({
        ok: false,
        status: 400,
        payload: { code: "BATCH_CATALOG_MONITOR_TAB_INVALID" },
      });
      return;
    }
    const result = await openCatalogBatchMonitor(chrome, message.tabId);
    sendResponse({
      ok: result.ok,
      status: result.ok ? 200 : 503,
      payload: {
        surface: result.method,
        sidePanelSupported: result.sidePanelAvailable,
        sidePanelError: result.sidePanelError,
        fallbackError: result.fallbackError,
      },
    });
    return;
  }
  if (message.type === "SAPSOS_START_CATALOG_BATCH") {
    const stored = await readStoredWorkerData();
    if (
      !stored.sapsosPairing ||
      stored.sapsosPairing.apiBaseUrl !== message.apiBaseUrl
    ) {
      sendResponse({
        ok: false,
        status: 401,
        payload: { code: "BATCH_CATALOG_PAIRING_REQUIRED" },
      });
      return;
    }
    if (stored.catalogBatch?.status === "RUNNING") {
      sendResponse({
        ok: false,
        status: 409,
        payload: { code: "BATCH_CATALOG_ACTIVE_RUN_ALREADY_RUNNING" },
      });
      return;
    }
    if (stored.catalogBatch?.status === "PAUSED") {
      sendResponse({
        ok: false,
        status: 409,
        payload: {
          code:
            stored.catalogBatch.runnerRevision ===
            CATALOG_BATCH_ACCEPTANCE_REVISION
              ? "BATCH_CATALOG_SAME_REVISION_PAUSED_RUN_EXISTS"
              : "BATCH_CATALOG_EXTENSION_REVISION_MISMATCH",
        },
      });
      return;
    }
    if (!["BOUNDED_ACCEPTANCE", "FULL"].includes(message.mode)) {
      sendResponse({
        ok: false,
        status: 400,
        payload: { code: "BATCH_CATALOG_MODE_INVALID" },
      });
      return;
    }
    if (
      message.mode === "FULL" &&
      !(
        stored.catalogBatch?.boundedAcceptancePassed === true &&
        stored.catalogBatch.boundedAcceptanceRevision ===
          CATALOG_BATCH_ACCEPTANCE_REVISION
      )
    ) {
      sendResponse({
        ok: false,
        status: 409,
        payload: { code: "BATCH_CATALOG_BOUNDED_ACCEPTANCE_REQUIRED" },
      });
      return;
    }
    if (message.mode === "FULL" && !CATALOG_FULL_CAPTURE_UNLOCKED) {
      sendResponse({
        ok: false,
        status: 409,
        payload: {
          code: "BATCH_CATALOG_FULL_CAPTURE_EXPLICIT_UNLOCK_REQUIRED",
        },
      });
      return;
    }
    if (
      !Number.isInteger(message.tabId) ||
      message.tabId < 0 ||
      !message.studentProfileId.trim()
    ) {
      sendResponse({
        ok: false,
        status: 400,
        payload: { code: "BATCH_CATALOG_START_INVALID" },
      });
      return;
    }
    const tab = await getTab(message.tabId);
    if (!tab.url || safePageUrl(tab.url) !== safePageUrl(message.landingUrl)) {
      sendResponse({
        ok: false,
        status: 400,
        payload: { code: "BATCH_CATALOG_PROVENANCE_INVALID" },
      });
      return;
    }
    const discovery = await executeTabFunction(
      message.tabId,
      discoverCatalogSubjects,
      safePageUrl(tab.url),
    );
    let state = createCatalogBatchState({
      batchId: globalThis.crypto.randomUUID(),
      apiBaseUrl: message.apiBaseUrl,
      studentProfileId: message.studentProfileId,
      tabId: message.tabId,
      landingUrl: discovery.landingUrl,
      subjects: discovery.subjects,
      startedAt: new Date().toISOString(),
      extensionVersion:
        chrome.runtime.getManifest?.().version ?? "UNKNOWN_EXTENSION_VERSION",
      mode: message.mode,
      subjectLimit:
        message.mode === "BOUNDED_ACCEPTANCE"
          ? Math.min(2, discovery.subjects.length)
          : discovery.subjects.length,
      boundedAcceptancePassed:
        stored.catalogBatch?.boundedAcceptancePassed === true &&
        stored.catalogBatch.boundedAcceptanceRevision ===
          CATALOG_BATCH_ACCEPTANCE_REVISION,
      boundedAcceptanceRevision:
        stored.catalogBatch?.boundedAcceptanceRevision ?? null,
    });
    if (stored.catalogBatch) {
      await persistCatalogBatchArchive(
        stored.catalogBatch,
        archiveStatusForReplacement(stored.catalogBatch.status),
        "REPLACED_BY_NEW_RUN",
        new Date().toISOString(),
      );
    }
    await clearCatalogBatchLifecycleNotice();
    await persistCatalogBatch(state);
    state = recordCatalogBatchTransition(
      state,
      "LANDING_NAVIGATION_REQUESTED",
      new Date().toISOString(),
      {
        currentPage: 1,
        totalPagesForCurrentSubject: null,
        previousFirstCourseMarker: null,
      },
    );
    await persistCatalogBatch(state);
    try {
      await reloadTab(state.tabId);
    } catch (error: unknown) {
      const code =
        error instanceof CatalogBatchError
          ? error.code
          : "BATCH_CATALOG_TAB_UNAVAILABLE";
      const message = safeExtensionError(error);
      state = pauseCatalogBatchForReason(
        state,
        code,
        new Date().toISOString(),
        message,
      );
      await persistCatalogBatch(state);
      await clearCatalogBatchLease();
      sendResponse({
        ok: false,
        status: 503,
        payload: { code, message },
      });
      return;
    }
    if (state.status !== "RUNNING") await clearCatalogBatchLease();
    sendResponse({
      ok: true,
      status: 202,
      payload: catalogBatchPublicState(state, new Date().toISOString()),
    });
    return;
  }
  if (
    message.type === "SAPSOS_PAUSE_CATALOG_BATCH" ||
    message.type === "SAPSOS_RESUME_CATALOG_BATCH" ||
    message.type === "SAPSOS_CANCEL_CATALOG_BATCH"
  ) {
    const stored = await readStoredWorkerData();
    if (!stored.catalogBatch) {
      sendResponse({
        ok: false,
        status: 404,
        payload: { code: "BATCH_CATALOG_NOT_FOUND" },
      });
      return;
    }
    let state = stored.catalogBatch;
    if (message.type === "SAPSOS_PAUSE_CATALOG_BATCH") {
      state = pauseCatalogBatchForReason(
        state,
        "USER_PAUSED",
        new Date().toISOString(),
        "The user paused the read-only Catalog batch.",
      );
      await persistCatalogBatch(state);
      await clearCatalogBatchLease();
    } else if (message.type === "SAPSOS_RESUME_CATALOG_BATCH") {
      if (
        !stored.sapsosPairing ||
        stored.sapsosPairing.apiBaseUrl !== message.apiBaseUrl
      ) {
        sendResponse({
          ok: false,
          status: 401,
          payload: { code: "BATCH_CATALOG_PAIRING_REQUIRED" },
        });
        return;
      }
      state = await resumeCatalogBatchEventDriven(
        state,
        createCatalogBatchDriver(),
      );
      if (state.status !== "RUNNING") await clearCatalogBatchLease();
    } else {
      state = cancelCatalogBatch(state);
      state = recordCatalogBatchTransition(
        state,
        "CANCELLED",
        new Date().toISOString(),
      );
      await persistCatalogBatch(state);
      await clearCatalogBatchLease();
    }
    sendResponse({
      ok: true,
      status: 200,
      payload: catalogBatchPublicState(state, new Date().toISOString()),
    });
    return;
  }
  chrome.storage.local.get(["sapsosPairing"], async (stored) => {
    try {
      const pairing = stored.sapsosPairing;
      if (!pairing || pairing.apiBaseUrl !== message.apiBaseUrl) {
        sendResponse({
          ok: false,
          status: 401,
          payload: { code: "pairing_required" },
        });
        return;
      }
      const baseUrl = message.apiBaseUrl.replace(/\/+$/, "");
      const response =
        message.type === "SAPSOS_GET_LOCAL_STUDENT_PROFILES"
          ? await fetch(`${baseUrl}/api/v1/local-onboarding/student-profiles`, {
              method: "GET",
              headers: extensionRequestHeaders(pairing.credential),
            })
          : await fetch(`${baseUrl}/api/v1/data-imports`, {
              method: "POST",
              headers: extensionRequestHeaders(pairing.credential),
              body: JSON.stringify(message.request),
            });
      await sendJson(sendResponse, response);
    } catch {
      sendResponse({
        ok: false,
        status: 503,
        payload: { code: "local_api_unavailable" },
      });
    }
  });
}

chrome.runtime.onInstalled.addListener(() => undefined);
async function initializeCatalogBatchWorker(): Promise<void> {
  const stored = await readStoredWorkerData();
  if (!stored.catalogBatch) return;
  const state = stored.catalogBatch;
  const restored = restoreCatalogBatchState(state, new Date().toISOString());
  if (
    (restored.status === "PAUSED" || restored.status === "FAILED") &&
    restored.runnerRevision !== CATALOG_BATCH_ACCEPTANCE_REVISION
  ) {
    const archivedAt = new Date().toISOString();
    const notice: CatalogBatchLifecycleNotice = {
      kind: "SUPERSEDED",
      batchRunId: restored.batchId,
      previousStatus: restored.status,
      previousRunnerRevision: restored.runnerRevision,
      currentRunnerRevision: CATALOG_BATCH_ACCEPTANCE_REVISION,
      reason: "SUPERSEDED_BY_NEW_REVISION",
      archivedAt,
      providerActionsWritten: "NO",
    };
    await persistCatalogBatchArchive(
      restored,
      "SUPERSEDED",
      "SUPERSEDED_BY_NEW_REVISION",
      archivedAt,
      notice,
    );
    await clearStoredCatalogBatch();
    await clearCatalogBatchLease();
    return;
  }
  await persistCatalogBatch(restored);
  if (restored.status !== "RUNNING") await clearCatalogBatchLease();
}

const workerInitialization = initializeCatalogBatchWorker();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "loading" && changeInfo.status !== "complete") {
    return;
  }
  void workerInitialization.then(async () => {
    await recordCatalogTabUpdate(
      tabId,
      changeInfo.status as "loading" | "complete",
      createCatalogBatchDriver(),
    );
    if (changeInfo.status !== "complete" || !tab.url) return;
    const state = await handleCatalogTabLoaded(
      tabId,
      tab.url ?? "",
      createCatalogBatchDriver(),
    );
    if (state && state.status !== "RUNNING") await clearCatalogBatchLease();
  });
});

chrome.tabs.onRemoved.addListener((tabId) => {
  void workerInitialization.then(async () => {
    const state = await handleAuthorizedCatalogTabClosed(
      tabId,
      createCatalogBatchDriver(),
    );
    if (state?.status === "PAUSED") await clearCatalogBatchLease();
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== undefined && sender.id !== chrome.runtime.id) {
    sendResponse({
      ok: false,
      status: 403,
      payload: { code: "invalid_sender" },
    });
    return false;
  }
  void handleMessage(message, sender, sendResponse).catch((error: unknown) => {
    sendResponse({
      ok: false,
      status: 503,
      payload: {
        code: "BATCH_BACKGROUND_HANDLER_FAILED",
        message: safeExtensionError(error),
      },
    });
  });
  return true;
});
