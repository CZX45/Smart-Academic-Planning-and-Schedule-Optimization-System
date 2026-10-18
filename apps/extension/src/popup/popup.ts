import {
  createDataImportRequestsFromExtractions,
  createDataImportRequestFromExtraction,
  hasStagedImportContent,
} from "../content/extractors.js";
import {
  ensureHostPermission,
  executeExtraction,
  popupDiagnosticsFromExtractions,
  readActiveTab,
  safeDiagnosticUrl,
  shouldAttemptExtractionForUrl,
  type PopupChromeApi,
} from "./browser-actions.js";
import { isLocalApiBaseUrl } from "../shared/local-api.js";
import {
  KEAN_OPTIONAL_HOST_PERMISSION,
  KEAN_SOURCE_LABEL,
} from "../shared/kean.js";
import {
  openCatalogBatchMonitor,
  safeExtensionError,
  type CatalogMonitorChromeApi,
} from "../shared/catalog-monitor.js";
import {
  CATALOG_BATCH_ACCEPTANCE_REVISION,
  CATALOG_FULL_CAPTURE_UNLOCKED,
  type CatalogBatchLifecycleNotice,
} from "../content/catalog-batch.js";
import type { CatalogBatchPublicState } from "../content/catalog-batch-lifecycle.js";
import type {
  BrowserExtensionDataImportRequest,
  BrowserExtensionExtraction,
} from "../shared/types.js";

type StoredSettings = {
  apiBaseUrl?: string;
  studentProfileId?: string;
};

type CreatedImportSummary = {
  id: string;
  recordCount: number | null;
};

type ApiResponse = {
  ok: boolean;
  status: number;
  payload: unknown;
  received: boolean;
};

type CatalogBatchUiDiagnostics = {
  boundedStartMessageReceived: "UNKNOWN" | "NO" | "YES";
  authorizedCatalogTabId: number | null;
  authorizedTabUrl: string | null;
  batchState: string;
  discoveryStarted: boolean;
  discoveredSubjectCount: number;
  lastTransition: string;
  lastError: { code: string; message: string } | null;
  monitorOpenMethod: "SIDE_PANEL" | "MONITOR_TAB" | null;
  monitorOpenError: string | null;
  updatedAt: string;
};

type StoredLocalData = StoredSettings & {
  catalogBatchUiDiagnostics?: CatalogBatchUiDiagnostics;
  catalogBatchLifecycleNotice?: CatalogBatchLifecycleNotice;
};

type ChromeApi = Omit<PopupChromeApi, "runtime" | "tabs"> &
  CatalogMonitorChromeApi & {
    runtime: {
      lastError?: { message?: string };
      getURL: (path: string) => string;
      sendMessage: (
        message: unknown,
        callback: (response: unknown) => void,
      ) => void;
    };
    tabs: PopupChromeApi["tabs"] & CatalogMonitorChromeApi["tabs"];
    storage: {
      local: {
        get: (
          keys: string[],
          callback: (settings: StoredLocalData) => void,
        ) => void;
        set: (settings: Partial<StoredLocalData>) => void;
      };
    };
  };

declare const chrome: ChromeApi;

const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const studentProfileIdInput = document.getElementById("studentProfileIdInput");
const pairingCodeInput = document.getElementById("pairingCodeInput");
const pairExtensionButton = document.getElementById("pairExtensionButton");
const pairingStatusText = document.getElementById("pairingStatusText");
const extractCurrentPageButton = document.getElementById(
  "extractCurrentPageButton",
);
const startKeanImportButton = document.getElementById("startKeanImportButton");
const captureGuidedPageButton = document.getElementById(
  "captureGuidedPageButton",
);
const confirmImportButton = document.getElementById("confirmImportButton");
const startCatalogBatchButton = document.getElementById(
  "startCatalogBatchButton",
);
const pauseCatalogBatchButton = document.getElementById(
  "pauseCatalogBatchButton",
);
const resumeCatalogBatchButton = document.getElementById(
  "resumeCatalogBatchButton",
);
const cancelCatalogBatchButton = document.getElementById(
  "cancelCatalogBatchButton",
);
const openCatalogBatchMonitorButton = document.getElementById(
  "openCatalogBatchMonitorButton",
);
const catalogBatchStatusText = document.getElementById(
  "catalogBatchStatusText",
);
const catalogBatchMonitorStatusText = document.getElementById(
  "catalogBatchMonitorStatusText",
);
const catalogBatchStartReasonText = document.getElementById(
  "catalogBatchStartReasonText",
);
const catalogBatchResumeReasonText = document.getElementById(
  "catalogBatchResumeReasonText",
);
const catalogBatchCancelReasonText = document.getElementById(
  "catalogBatchCancelReasonText",
);
const catalogBatchProgressText = document.getElementById(
  "catalogBatchProgressText",
);
const statusText = document.getElementById("statusText");
const apiStatusText = document.getElementById("apiStatusText");
const detectedPageText = document.getElementById("detectedPageText");
const countsText = document.getElementById("countsText");
const warningsList = document.getElementById("warningsList");
const previewTable = document.getElementById("previewTable");
const diagnosticUrlText = document.getElementById("diagnosticUrlText");
const diagnosticMarkerText = document.getElementById("diagnosticMarkerText");
const diagnosticTablesText = document.getElementById("diagnosticTablesText");
const diagnosticRowsText = document.getElementById("diagnosticRowsText");
const diagnosticVisibleTextLengthText = document.getElementById(
  "diagnosticVisibleTextLengthText",
);
const diagnosticRowLikeBlocksText = document.getElementById(
  "diagnosticRowLikeBlocksText",
);
const diagnosticAcademicFieldsText = document.getElementById(
  "diagnosticAcademicFieldsText",
);
const diagnosticSensitiveFieldsText = document.getElementById(
  "diagnosticSensitiveFieldsText",
);
const diagnosticDirectSnapshotText = document.getElementById(
  "diagnosticDirectSnapshotText",
);
const diagnosticBoundedText = document.getElementById("diagnosticBoundedText");

let latestExtraction: BrowserExtensionExtraction | null = null;
let latestCapturedUrl: string | null = null;
let guidedMode = false;
let guidedExtractions: BrowserExtensionExtraction[] = [];
let confirmSubmissionInFlight = false;
let latestCatalogBatchState: CatalogBatchPublicState | null = null;
let latestCatalogBatchLifecycleNotice: CatalogBatchLifecycleNotice | null =
  null;
let latestCatalogBatchUiDiagnostics: CatalogBatchUiDiagnostics = {
  boundedStartMessageReceived: "UNKNOWN",
  authorizedCatalogTabId: null,
  authorizedTabUrl: null,
  batchState: "NOT_CREATED",
  discoveryStarted: false,
  discoveredSubjectCount: 0,
  lastTransition: "NOT_STARTED",
  lastError: null,
  monitorOpenMethod: null,
  monitorOpenError: null,
  updatedAt: new Date(0).toISOString(),
};

function persistCatalogBatchUiDiagnostics(
  updates: Partial<CatalogBatchUiDiagnostics>,
): void {
  latestCatalogBatchUiDiagnostics = {
    ...latestCatalogBatchUiDiagnostics,
    ...updates,
    updatedAt: new Date().toISOString(),
  };
  chrome.storage.local.set({
    catalogBatchUiDiagnostics: latestCatalogBatchUiDiagnostics,
  });
}

function sendBackgroundMessage(message: unknown): Promise<ApiResponse> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response: unknown) => {
      const messageError = chrome.runtime.lastError?.message;
      if (messageError) {
        resolve({
          ok: false,
          status: 503,
          payload: {
            code: "BATCH_BACKGROUND_MESSAGE_FAILED",
            message: safeExtensionError(messageError),
          },
          received: false,
        });
        return;
      }
      if (!isObject(response)) {
        resolve({
          ok: false,
          status: 503,
          payload: { code: "invalid_background_response" },
          received: false,
        });
        return;
      }
      resolve({
        ok: response.ok === true,
        status: typeof response.status === "number" ? response.status : 503,
        payload: response.payload,
        received: true,
      });
    });
  });
}

function setPairingStatus(message: string): void {
  if (pairingStatusText) {
    pairingStatusText.textContent = message;
  }
}

function catalogBatchState(payload: unknown): CatalogBatchPublicState | null {
  if (
    !isObject(payload) ||
    typeof payload.batchRunId !== "string" ||
    typeof payload.batchStatus !== "string" ||
    typeof payload.discoveredSubjectCount !== "number" ||
    typeof payload.completedSubjectCount !== "number" ||
    payload.providerActionsWritten !== "NO"
  ) {
    return null;
  }
  return payload as CatalogBatchPublicState;
}

function setBatchButtonEnabled(
  element: Element | null,
  enabled: boolean,
): void {
  if (element instanceof HTMLButtonElement) {
    element.disabled = !enabled;
  }
}

function renderCatalogBatch(state: CatalogBatchPublicState | null): void {
  latestCatalogBatchState = state;
  const status = state?.batchStatus ?? "NOT_STARTED";
  const running = status === "RUNNING";
  const paused = status === "PAUSED";
  const fullCaptureLocked =
    state?.boundedAcceptancePassed === true && !CATALOG_FULL_CAPTURE_UNLOCKED;
  const resumeDisabledReason = !paused
    ? "NO_PAUSED_RUN"
    : state?.runnerRevision !== CATALOG_BATCH_ACCEPTANCE_REVISION
      ? "REVISION_MISMATCH"
      : state.leaseStatus !== "RELEASED" ||
          state.lastError?.code === "BATCH_CATALOG_CHECKPOINT_INVALID"
        ? "CHECKPOINT_INVALID"
        : state.lastError?.code === "BATCH_CATALOG_TAB_CLOSED" ||
            state.currentSchoolTabUrlClassification === "UNAVAILABLE"
          ? "AUTHORIZED_TAB_MISSING"
          : state.currentSchoolTabUrlClassification === "AUTHENTICATION"
            ? "MANUAL_REAUTH_REQUIRED"
            : state.currentSchoolTabUrlClassification === "OUT_OF_SCOPE"
              ? "AUTHORIZED_TAB_OUT_OF_SCOPE"
              : null;
  setBatchButtonEnabled(
    startCatalogBatchButton,
    !running && !paused && !fullCaptureLocked,
  );
  setBatchButtonEnabled(pauseCatalogBatchButton, running);
  setBatchButtonEnabled(
    resumeCatalogBatchButton,
    paused && resumeDisabledReason === null,
  );
  setBatchButtonEnabled(cancelCatalogBatchButton, running || paused);
  setText(
    catalogBatchStartReasonText,
    running
      ? "ACTIVE_RUN_ALREADY_RUNNING — Run is disabled while this batch owns the checkpoint."
      : paused
        ? "SAME_REVISION_PAUSED_RUN_EXISTS — Use Resume or Cancel."
        : fullCaptureLocked
          ? "FULL_CAPTURE_EXPLICIT_UNLOCK_REQUIRED — The 116-subject run remains locked in this build."
          : "READY — A fresh run may be started from the Catalog landing page.",
  );
  setText(
    catalogBatchResumeReasonText,
    resumeDisabledReason
      ? `${resumeDisabledReason} — Resume is unavailable at this checkpoint.`
      : "READY — The persisted checkpoint can resume.",
  );
  setText(
    catalogBatchCancelReasonText,
    running || paused
      ? "READY — Cancel preserves captured local evidence."
      : "NO_ACTIVE_RUN — Cancel requires a running or paused batch.",
  );
  if (startCatalogBatchButton instanceof HTMLButtonElement) {
    startCatalogBatchButton.textContent = state?.boundedAcceptancePassed
      ? "Full Course Catalog locked"
      : "Run bounded Catalog acceptance (2 subjects)";
  }
  if (!state) {
    setText(
      catalogBatchStatusText,
      latestCatalogBatchLifecycleNotice?.kind === "SUPERSEDED"
        ? "The previous acceptance from an older build was archived. Fresh bounded acceptance is ready."
        : "Not started.",
    );
    setText(
      catalogBatchProgressText,
      "Subjects discovered: 0 | Subjects completed: 0 / 0 | Courses captured: 0 | Unique courses: 0 | Duplicates ignored: 0 | Warnings: 0",
    );
    return;
  }
  const statusMessage =
    state.batchStatus === "COMPLETED"
      ? "Catalog capture complete. Open local review."
      : state.batchStatus === "FAILED"
        ? `Catalog capture stopped safely: ${state.lastError?.code ?? "UNKNOWN"}.`
        : state.batchStatus === "CANCELLED"
          ? "Catalog capture cancelled. Saved local results remain available."
          : state.batchStatus === "PAUSED"
            ? resumeDisabledReason
              ? `BATCH_CATALOG_SAME_REVISION_PAUSED_RUN_EXISTS: Previous bounded acceptance is paused. Start is disabled; Resume is disabled (${resumeDisabledReason}); use Cancel.`
              : "BATCH_CATALOG_SAME_REVISION_PAUSED_RUN_EXISTS: Previous bounded acceptance is paused. Start is disabled; use Resume or Cancel."
            : "BATCH_CATALOG_ACTIVE_RUN_ALREADY_RUNNING: Catalog capture is running read-only.";
  setText(catalogBatchStatusText, statusMessage);
  setText(
    catalogBatchProgressText,
    `Subjects discovered: ${state.discoveredSubjectCount} | Subjects completed: ${state.completedSubjectCount} / ${state.subjectLimit} | Courses captured: ${state.capturedRecordCount} | Unique courses: ${state.uniqueRecordCount} | Duplicates ignored: ${state.duplicateRecordCount} | Warnings: ${state.warningCount} | Current: ${state.currentSubject ?? "-"} page ${state.currentPage}`,
  );
}

async function refreshCatalogBatchState(): Promise<void> {
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    renderCatalogBatch(null);
    return;
  }
  const result = await sendBackgroundMessage({
    type: "SAPSOS_GET_CATALOG_BATCH_STATE",
    apiBaseUrl,
  });
  const state = result.ok ? catalogBatchState(result.payload) : null;
  if (!state) {
    latestCatalogBatchLifecycleNotice = await new Promise((resolve) => {
      chrome.storage.local.get(["catalogBatchLifecycleNotice"], (settings) => {
        resolve(settings.catalogBatchLifecycleNotice ?? null);
      });
    });
  }
  renderCatalogBatch(state);
}

function isCatalogLandingUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return (
      parsed.origin === "https://kean-ss.colleague.elluciancloud.com" &&
      ["/Student/Courses", "/Student/Student/Courses"].includes(parsed.pathname)
    );
  } catch {
    return false;
  }
}

async function handleStartCatalogBatch(
  monitorOpenRequest: Promise<
    Awaited<ReturnType<typeof openCatalogBatchMonitor>>
  >,
): Promise<void> {
  const monitor = await monitorOpenRequest;
  persistCatalogBatchUiDiagnostics({
    monitorOpenMethod: monitor.method,
    monitorOpenError:
      monitor.ok === true
        ? monitor.sidePanelError
        : [monitor.sidePanelError, monitor.fallbackError]
            .filter((value): value is string => Boolean(value))
            .join(" | ") || "BATCH_CATALOG_MONITOR_OPEN_FAILED",
  });
  setText(
    catalogBatchMonitorStatusText,
    monitor.ok
      ? `${monitor.method}: persistent batch monitor opened.${monitor.sidePanelError ? ` Side Panel error: ${monitor.sidePanelError}` : ""}`
      : "BATCH_CATALOG_MONITOR_OPEN_FAILED",
  );
  if (!monitor.ok) {
    setText(
      catalogBatchStatusText,
      "BATCH_CATALOG_MONITOR_OPEN_FAILED: The persistent monitor must open before a fresh batch can start.",
    );
    return;
  }
  if (
    latestCatalogBatchState?.boundedAcceptancePassed === true &&
    !CATALOG_FULL_CAPTURE_UNLOCKED
  ) {
    setText(
      catalogBatchStatusText,
      "BATCH_CATALOG_FULL_CAPTURE_EXPLICIT_UNLOCK_REQUIRED: The 116-subject run remains locked pending separate authorization.",
    );
    return;
  }
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  const studentProfileId = inputValue(studentProfileIdInput);
  if (!isLocalApiBaseUrl(apiBaseUrl) || !studentProfileId) {
    setText(
      catalogBatchStatusText,
      "Pair with the local app and resolve one local student profile first.",
    );
    return;
  }
  let tab: Awaited<ReturnType<typeof readActiveTab>>;
  try {
    const granted = await ensureKeanPermission();
    if (!granted) {
      const message = "Kean Catalog permission was not granted.";
      persistCatalogBatchUiDiagnostics({
        boundedStartMessageReceived: "NO",
        lastTransition: "START_PRECHECK_REJECTED",
        lastError: { code: "BATCH_CATALOG_PERMISSION_REQUIRED", message },
      });
      setText(catalogBatchStatusText, message);
      return;
    }
    tab = await readActiveTab(chrome);
  } catch (error: unknown) {
    const message = safeExtensionError(error);
    persistCatalogBatchUiDiagnostics({
      boundedStartMessageReceived: "NO",
      lastTransition: "START_PRECHECK_REJECTED",
      lastError: { code: "BATCH_CATALOG_ACTIVE_TAB_UNAVAILABLE", message },
    });
    setText(
      catalogBatchStatusText,
      `BATCH_CATALOG_ACTIVE_TAB_UNAVAILABLE: ${message}`,
    );
    return;
  }
  const safeTabUrl = safeDiagnosticUrl(tab.url);
  if (!isCatalogLandingUrl(tab.url)) {
    const path = (() => {
      try {
        return new URL(tab.url).pathname;
      } catch {
        return "UNKNOWN_PATH";
      }
    })();
    const message = `Current path ${path} is not the Kean Course Catalog landing page.`;
    persistCatalogBatchUiDiagnostics({
      boundedStartMessageReceived: "NO",
      authorizedCatalogTabId: null,
      authorizedTabUrl: safeTabUrl,
      batchState: "NOT_CREATED",
      discoveryStarted: false,
      discoveredSubjectCount: 0,
      lastTransition: "START_PRECHECK_REJECTED",
      lastError: { code: "BATCH_CATALOG_LANDING_REQUIRED", message },
    });
    setText(
      catalogBatchStatusText,
      `BATCH_CATALOG_LANDING_REQUIRED: ${message}`,
    );
    return;
  }
  chrome.storage.local.set({ apiBaseUrl, studentProfileId });
  setBatchButtonEnabled(startCatalogBatchButton, false);
  setText(
    catalogBatchStatusText,
    "Discovering visible Catalog subjects. No registration actions will run.",
  );
  persistCatalogBatchUiDiagnostics({
    boundedStartMessageReceived: "UNKNOWN",
    authorizedCatalogTabId: tab.id,
    authorizedTabUrl: safeTabUrl,
    batchState: "STARTING",
    discoveryStarted: false,
    discoveredSubjectCount: 0,
    lastTransition: "START_MESSAGE_DISPATCHED",
    lastError: null,
  });
  const result = await sendBackgroundMessage({
    type: "SAPSOS_START_CATALOG_BATCH",
    apiBaseUrl,
    studentProfileId,
    tabId: tab.id,
    landingUrl: tab.url,
    mode: "BOUNDED_ACCEPTANCE",
  });
  const state = result.ok ? catalogBatchState(result.payload) : null;
  if (!state) {
    const message =
      apiErrorMessage(result.payload) ??
      "Catalog batch could not start safely.";
    const responseCode =
      isObject(result.payload) && typeof result.payload.code === "string"
        ? result.payload.code
        : null;
    persistCatalogBatchUiDiagnostics({
      boundedStartMessageReceived: result.received ? "YES" : "UNKNOWN",
      batchState: "NOT_CREATED",
      discoveryStarted: false,
      discoveredSubjectCount: 0,
      lastTransition: result.received
        ? "START_RESPONSE_REJECTED"
        : "START_RESPONSE_MISSING",
      lastError: {
        code: result.received
          ? (responseCode ?? "BATCH_CATALOG_START_REJECTED")
          : "BATCH_BACKGROUND_MESSAGE_FAILED",
        message,
      },
    });
    setText(catalogBatchStatusText, message);
    setBatchButtonEnabled(startCatalogBatchButton, true);
    return;
  }
  persistCatalogBatchUiDiagnostics({
    boundedStartMessageReceived: "YES",
    authorizedCatalogTabId: state.authorizedTabId,
    authorizedTabUrl: safeTabUrl,
    batchState: state.batchStatus,
    discoveryStarted: state.discoveredSubjectCount > 0,
    discoveredSubjectCount: state.discoveredSubjectCount,
    lastTransition: state.lastTransition,
    lastError: state.lastError
      ? {
          code: state.lastError.code,
          message: state.lastError.message ?? "",
        }
      : null,
  });
  renderCatalogBatch(state);
}

async function handleCatalogBatchCommand(
  type:
    | "SAPSOS_PAUSE_CATALOG_BATCH"
    | "SAPSOS_RESUME_CATALOG_BATCH"
    | "SAPSOS_CANCEL_CATALOG_BATCH",
): Promise<void> {
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  if (!isLocalApiBaseUrl(apiBaseUrl)) return;
  const result = await sendBackgroundMessage({ type, apiBaseUrl });
  const state = result.ok ? catalogBatchState(result.payload) : null;
  if (state) renderCatalogBatch(state);
}

async function handleOpenCatalogBatchMonitor(): Promise<void> {
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  if (!isLocalApiBaseUrl(apiBaseUrl)) return;
  let activeTab: Awaited<ReturnType<typeof readActiveTab>>;
  try {
    activeTab = await readActiveTab(chrome);
  } catch (error: unknown) {
    const message = safeExtensionError(error);
    persistCatalogBatchUiDiagnostics({
      monitorOpenMethod: null,
      monitorOpenError: message,
    });
    setText(
      catalogBatchMonitorStatusText,
      `BATCH_CATALOG_MONITOR_TAB_UNAVAILABLE: ${message}`,
    );
    return;
  }
  const tabId = latestCatalogBatchState?.authorizedTabId ?? activeTab.id;
  const result = await openCatalogBatchMonitor(chrome, tabId);
  const monitorError = result.ok
    ? result.sidePanelError
    : [result.sidePanelError, result.fallbackError]
        .filter((value): value is string => Boolean(value))
        .join(" | ");
  persistCatalogBatchUiDiagnostics({
    monitorOpenMethod: result.method,
    monitorOpenError: monitorError || null,
  });
  setText(
    catalogBatchMonitorStatusText,
    result.ok
      ? `${result.method}: persistent batch monitor opened.${result.sidePanelError ? ` Side Panel error: ${result.sidePanelError}` : ""}`
      : `BATCH_CATALOG_MONITOR_OPEN_FAILED: ${monitorError || "Unknown extension error"}`,
  );
}

function inputValue(element: Element | null): string {
  return element instanceof HTMLInputElement ? element.value.trim() : "";
}

function setInputValue(element: Element | null, value: string): void {
  if (element instanceof HTMLInputElement) {
    element.value = value;
  }
}

function setStatus(message: string): void {
  if (statusText) {
    statusText.textContent = message;
  }
}

function setApiStatus(message: string): void {
  if (apiStatusText) {
    apiStatusText.textContent = message;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function apiErrorMessage(payload: unknown): string | null {
  if (!isObject(payload)) {
    return null;
  }
  const detail = payload.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (isObject(detail) && typeof detail.message === "string") {
    return detail.message;
  }
  if (typeof payload.message === "string") {
    return payload.message;
  }
  if (typeof payload.code === "string") {
    return payload.code;
  }
  return null;
}

function createdImportSummary(payload: unknown): CreatedImportSummary {
  if (!isObject(payload)) {
    return { id: "unknown import id", recordCount: null };
  }
  return {
    id: typeof payload.id === "string" ? payload.id : "unknown import id",
    recordCount:
      typeof payload.record_count === "number" ? payload.record_count : null,
  };
}

function pluralize(count: number, singular: string): string {
  return `${count} ${count === 1 ? singular : `${singular}s`}`;
}

function createdImportSummaryText(
  summaries: readonly CreatedImportSummary[],
): string {
  const ids = summaries.map((summary) => summary.id).join(", ");
  const knownRowCounts = summaries.filter(
    (summary) => summary.recordCount !== null,
  );
  if (knownRowCounts.length === 0) {
    return `${ids}; row count unavailable`;
  }
  const totalRows = knownRowCounts.reduce(
    (current, summary) => current + (summary.recordCount ?? 0),
    0,
  );
  return `${ids}; ${pluralize(totalRows, "row")}`;
}

function submittedCountsText(
  requests: readonly BrowserExtensionDataImportRequest[],
): string {
  const countsByType = requests.reduce<Record<string, number>>(
    (current, request) => {
      current[request.import_type] =
        (current[request.import_type] ?? 0) + request.extracted_record_count;
      return current;
    },
    {},
  );
  const rowCounts = Object.entries(countsByType)
    .map(([importType, count]) => `submitted ${importType} rows: ${count}`)
    .join("; ");
  const visibleRows = requests.reduce(
    (count, request) => count + request.visible_row_count,
    0,
  );
  const academicFields = requests.reduce(
    (count, request) => count + request.academic_field_count,
    0,
  );
  return `${rowCounts}; submitted visible rows: ${visibleRows}; submitted academic fields: ${academicFields}`;
}

function setDetectedPage(
  extractions: readonly BrowserExtensionExtraction[],
): void {
  if (!detectedPageText) {
    return;
  }
  detectedPageText.textContent =
    extractions.length === 0
      ? "No supported academic page captured."
      : extractions.map((extraction) => extraction.pageType).join(", ");
}

function setCounts(extractions: readonly BrowserExtensionExtraction[]): void {
  if (!countsText) {
    return;
  }
  const counts = extractions.reduce<Record<string, number>>(
    (current, extraction) => {
      current[extraction.importType] =
        (current[extraction.importType] ?? 0) + extraction.records.length;
      return current;
    },
    {},
  );
  countsText.textContent =
    Object.keys(counts).length === 0
      ? "No rows ready."
      : Object.entries(counts)
          .map(([importType, count]) => `${importType}: ${count}`)
          .join(" | ");
}

function setWarnings(extractions: readonly BrowserExtensionExtraction[]): void {
  if (!warningsList) {
    return;
  }
  warningsList.replaceChildren();
  const warnings = extractions.flatMap((extraction) => extraction.warnings);
  for (const warning of warnings) {
    const item = document.createElement("li");
    item.textContent = `${warning.severity}: ${warning.code} - ${warning.message}`;
    warningsList.append(item);
  }
}

function setText(element: Element | null, value: string): void {
  if (element) {
    element.textContent = value;
  }
}

function setDiagnostics(
  extractions: readonly BrowserExtensionExtraction[],
  capturedUrl?: string | null,
): void {
  const diagnostics = capturedUrl
    ? popupDiagnosticsFromExtractions(extractions, { capturedUrl })
    : popupDiagnosticsFromExtractions(extractions);
  setText(diagnosticUrlText, diagnostics.currentUrl);
  setText(diagnosticMarkerText, diagnostics.matchedPageMarker);
  setText(diagnosticTablesText, String(diagnostics.tablesFound));
  setText(diagnosticRowsText, String(diagnostics.rowsFound));
  setText(
    diagnosticVisibleTextLengthText,
    String(diagnostics.visibleTextLength),
  );
  setText(diagnosticRowLikeBlocksText, String(diagnostics.rowLikeBlocksFound));
  setText(
    diagnosticAcademicFieldsText,
    String(diagnostics.extractedAcademicFieldCount),
  );
  setText(
    diagnosticSensitiveFieldsText,
    String(diagnostics.ignoredSensitiveFieldCount),
  );
  setText(
    diagnosticDirectSnapshotText,
    diagnostics.directSnapshotRan ? "yes" : "no",
  );
  setText(diagnosticBoundedText, diagnostics.bounded ? "yes" : "no");
}

function appendCell(
  row: HTMLTableRowElement,
  value: string,
  cellName: "td" | "th" = "td",
): void {
  const cell = document.createElement(cellName);
  cell.textContent = value;
  row.append(cell);
}

function setPreview(extractions: readonly BrowserExtensionExtraction[]): void {
  if (!previewTable) {
    return;
  }
  previewTable.replaceChildren();
  const header = document.createElement("tr");
  for (const label of ["Page", "Type", "Course", "Title", "Term", "Status"]) {
    appendCell(header, label, "th");
  }
  previewTable.append(header);
  for (const extraction of extractions) {
    for (const record of extraction.records.slice(0, 6)) {
      const row = document.createElement("tr");
      appendCell(row, extraction.pageType);
      appendCell(row, extraction.importType);
      appendCell(row, record.course_code ?? "");
      appendCell(
        row,
        record.course_title ?? record.title ?? record.requirements ?? "",
      );
      appendCell(row, record.term_code ?? record.term ?? "");
      appendCell(row, record.status ?? record.attempt_status ?? "");
      previewTable.append(row);
    }
  }
}

function renderPreview(
  extractions: readonly BrowserExtensionExtraction[],
  options: { capturedUrl?: string | null } = {},
): void {
  setDetectedPage(extractions);
  setCounts(extractions);
  setWarnings(extractions);
  setDiagnostics(extractions, options.capturedUrl);
  setPreview(extractions);
}

function setConfirmEnabled(enabled: boolean): void {
  if (confirmImportButton instanceof HTMLButtonElement) {
    confirmImportButton.disabled = !enabled;
  }
}

function setCaptureGuidedEnabled(enabled: boolean): void {
  if (captureGuidedPageButton instanceof HTMLButtonElement) {
    captureGuidedPageButton.disabled = !enabled;
  }
}

async function handleExtract(): Promise<void> {
  try {
    setStatus("Extracting visible page data.");
    guidedMode = false;
    guidedExtractions = [];
    latestCapturedUrl = null;
    setConfirmEnabled(false);
    const tab = await readActiveTab(chrome);
    latestCapturedUrl = tab.url;
    if (!shouldAttemptExtractionForUrl(tab.url)) {
      latestExtraction = null;
      renderPreview([], { capturedUrl: tab.url });
      setStatus("This browser page cannot be inspected by the extension.");
      return;
    }
    latestExtraction = await executeExtraction(chrome, tab);
    renderPreview([latestExtraction]);
    setConfirmEnabled(hasStagedImportContent(latestExtraction));
    setStatus("Preview ready. Confirm before sending to staging import.");
  } catch (error: unknown) {
    latestExtraction = null;
    renderPreview([], { capturedUrl: latestCapturedUrl });
    setStatus(error instanceof Error ? error.message : "Extraction failed.");
  }
}

function ensureKeanPermission(): Promise<boolean> {
  return ensureHostPermission(chrome, [KEAN_OPTIONAL_HOST_PERMISSION]);
}

async function handleStartKeanImport(): Promise<void> {
  setStatus("Requesting Kean Student Portal permission.");
  let granted = false;
  try {
    granted = await ensureKeanPermission();
  } catch (error: unknown) {
    setStatus(
      error instanceof Error
        ? error.message
        : "Kean import permission check failed.",
    );
    return;
  }
  if (!granted) {
    guidedMode = false;
    guidedExtractions = [];
    renderPreview([]);
    setCaptureGuidedEnabled(false);
    setConfirmEnabled(false);
    setStatus("Kean import permission was not granted.");
    return;
  }
  guidedMode = true;
  latestExtraction = null;
  guidedExtractions = [];
  renderPreview([]);
  setCaptureGuidedEnabled(true);
  setConfirmEnabled(false);
  setStatus(
    "Guided Kean import started. Open a supported page and capture it.",
  );
}

async function handleCaptureGuidedPage(): Promise<void> {
  if (!guidedMode) {
    setStatus("Start Kean import before capturing guided pages.");
    return;
  }
  try {
    setStatus("Capturing current Kean academic page.");
    latestCapturedUrl = null;
    const tab = await readActiveTab(chrome);
    latestCapturedUrl = tab.url;
    if (!shouldAttemptExtractionForUrl(tab.url)) {
      renderPreview([], { capturedUrl: tab.url });
      setConfirmEnabled(guidedExtractions.some(hasStagedImportContent));
      setStatus("This browser page cannot be inspected by the extension.");
      return;
    }
    const extraction = await executeExtraction(chrome, tab);
    if (
      extraction.sourceLabel !== KEAN_SOURCE_LABEL ||
      extraction.pageType === "UNKNOWN_PAGE" ||
      !hasStagedImportContent(extraction)
    ) {
      renderPreview([extraction]);
      setConfirmEnabled(guidedExtractions.some(hasStagedImportContent));
      setStatus("This page did not add supported Kean academic rows.");
      return;
    }
    guidedExtractions = [
      ...guidedExtractions.filter(
        (current) => current.pageType !== extraction.pageType,
      ),
      extraction,
    ];
    renderPreview(guidedExtractions);
    setConfirmEnabled(true);
    setStatus(
      "Kean page captured. Continue with another page or confirm import.",
    );
  } catch (error: unknown) {
    renderPreview(guidedExtractions, { capturedUrl: latestCapturedUrl });
    setStatus(
      error instanceof Error ? error.message : "Guided capture failed.",
    );
  }
}

async function handleConfirm(): Promise<void> {
  if (confirmSubmissionInFlight) {
    return;
  }
  const extractions = guidedMode
    ? guidedExtractions
    : latestExtraction
      ? [latestExtraction]
      : [];
  if (extractions.length === 0) {
    setStatus("Extract the current page before confirming.");
    return;
  }
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  const studentProfileId = inputValue(studentProfileIdInput);
  if (!apiBaseUrl || !studentProfileId) {
    setStatus("API base URL and student profile ID are required.");
    return;
  }
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    setStatus(
      "Staging imports are available only through the paired local app.",
    );
    return;
  }
  chrome.storage.local.set({ apiBaseUrl, studentProfileId });
  let requests: BrowserExtensionDataImportRequest[];
  try {
    if (guidedMode) {
      requests = createDataImportRequestsFromExtractions(
        studentProfileId,
        extractions,
      );
    } else {
      const firstExtraction = extractions[0];
      if (!firstExtraction) {
        setStatus("Extract the current page before confirming.");
        return;
      }
      requests = [
        createDataImportRequestFromExtraction(
          studentProfileId,
          firstExtraction,
        ),
      ];
    }
  } catch (error: unknown) {
    setStatus(
      error instanceof Error
        ? error.message
        : "Preview data was lost before submission. Please re-extract the page.",
    );
    return;
  }
  if (requests.length === 0) {
    setStatus("No extracted rows are available to import.");
    return;
  }
  confirmSubmissionInFlight = true;
  setConfirmEnabled(false);
  setStatus("Sending...");
  try {
    const summaries: CreatedImportSummary[] = [];
    for (const request of requests) {
      const result: ApiResponse = await sendBackgroundMessage({
        type: "SAPSOS_SUBMIT_IMPORT",
        apiBaseUrl,
        request,
      });
      const resultPayload = result.payload;
      if (result.ok !== true) {
        const message = apiErrorMessage(resultPayload);
        setApiStatus(
          `Local app/API failed with HTTP ${String(result.status ?? "unknown")}${
            message ? `: ${message}` : "."
          }`,
        );
        setStatus(
          "Staging import failed. Retry only after reviewing the issue.",
        );
        return;
      }
      const summary = createdImportSummary(resultPayload);
      if (
        summary.recordCount !== null &&
        request.extracted_record_count > 0 &&
        summary.recordCount < request.extracted_record_count
      ) {
        setApiStatus(
          `Local app/API accepted ${summary.recordCount} record${
            summary.recordCount === 1 ? "" : "s"
          } but ${request.extracted_record_count} extracted row(s) were submitted.`,
        );
        setStatus(
          "Staging import failed. Retry only after reviewing the issue.",
        );
        return;
      }
      summaries.push(summary);
    }
    const summaryText = createdImportSummaryText(summaries);
    const submittedText = submittedCountsText(requests);
    setApiStatus(
      `Local app/API accepted ${pluralize(
        summaries.length,
        "staging import",
      )}: ${summaryText}. ${submittedText}.`,
    );
    setStatus(
      `Success: staging import created. ${summaryText}. ${submittedText}. Review is still required in the app.`,
    );
  } catch (error: unknown) {
    setApiStatus(
      "Local app/API connection failed. Check the API base URL, extension local API host permission, and CORS.",
    );
    setStatus(
      error instanceof Error
        ? `Staging import failed: ${error.message}`
        : "Staging import failed.",
    );
  } finally {
    confirmSubmissionInFlight = false;
    setConfirmEnabled(true);
  }
}

async function handlePairExtension(): Promise<void> {
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  const code = inputValue(pairingCodeInput).trim();
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    setPairingStatus("Pairing is available only with the local app.");
    return;
  }
  if (!code) {
    setPairingStatus("Enter the short-lived code shown in the local app.");
    return;
  }
  setPairingStatus("Pairing with the local app...");
  const result = await sendBackgroundMessage({
    type: "SAPSOS_PAIR_EXTENSION",
    apiBaseUrl,
    code,
  });
  const payload = result.payload;
  if (result.ok === true) {
    await refreshLocalStudentProfile(apiBaseUrl);
  } else {
    setPairingStatus(
      apiErrorMessage(payload) ??
        "Pairing failed. Check the code and app state.",
    );
  }
}

function localStudentProfiles(
  payload: unknown,
): Array<{ id: string; displayName: string }> {
  if (!Array.isArray(payload)) {
    return [];
  }
  const profiles: Array<{ id: string; displayName: string }> = [];
  for (const item of payload) {
    if (!isObject(item) || !isObject(item.student)) {
      continue;
    }
    const id = item.student.id;
    const displayName = item.student.display_name;
    if (
      typeof id === "string" &&
      id.length > 0 &&
      typeof displayName === "string" &&
      displayName.length > 0
    ) {
      profiles.push({ id, displayName });
    }
  }
  return profiles;
}

async function refreshLocalStudentProfile(apiBaseUrl: string): Promise<void> {
  const result = await sendBackgroundMessage({
    type: "SAPSOS_GET_LOCAL_STUDENT_PROFILES",
    apiBaseUrl,
  });
  if (result.ok !== true) {
    setPairingStatus(
      apiErrorMessage(result.payload) ??
        "Paired, but local student profiles could not be read.",
    );
    return;
  }
  const profiles = localStudentProfiles(result.payload);
  if (profiles.length === 0) {
    setInputValue(studentProfileIdInput, "");
    chrome.storage.local.set({ apiBaseUrl, studentProfileId: "" });
    setPairingStatus(
      "A local app pairing is active. Create a local student profile in SAPSOS first.",
    );
    return;
  }
  if (profiles.length > 1) {
    setInputValue(studentProfileIdInput, "");
    chrome.storage.local.set({ apiBaseUrl, studentProfileId: "" });
    setPairingStatus(
      "A local app pairing is active. Multiple local profiles exist; import is disabled until the intended profile is unambiguous in SAPSOS.",
    );
    return;
  }
  const profile = profiles[0];
  if (!profile) {
    return;
  }
  setInputValue(studentProfileIdInput, profile.id);
  chrome.storage.local.set({ apiBaseUrl, studentProfileId: profile.id });
  setPairingStatus(
    `A local app pairing is active. Using ${profile.displayName}. The credential remains in the Extension worker.`,
  );
}

async function refreshPairingStatus(): Promise<void> {
  const apiBaseUrl = inputValue(apiBaseUrlInput).replace(/\/+$/, "");
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    setPairingStatus("Pairing is available only with the local app.");
    return;
  }
  const result = await sendBackgroundMessage({
    type: "SAPSOS_GET_PAIRING_STATUS",
    apiBaseUrl,
  });
  const payload = result.payload;
  if (result.ok === true && isObject(payload) && payload.paired === true) {
    await refreshLocalStudentProfile(apiBaseUrl);
  } else if (result.ok === true) {
    setPairingStatus("Pairing required.");
  } else {
    setPairingStatus("Local app unavailable.");
  }
}

chrome.storage.local.get(
  ["apiBaseUrl", "studentProfileId", "catalogBatchUiDiagnostics"],
  (settings) => {
    if (settings.catalogBatchUiDiagnostics) {
      latestCatalogBatchUiDiagnostics = settings.catalogBatchUiDiagnostics;
    }
    latestCatalogBatchLifecycleNotice =
      settings.catalogBatchLifecycleNotice ?? null;
    if (settings.apiBaseUrl) {
      setInputValue(apiBaseUrlInput, settings.apiBaseUrl);
    }
    if (settings.studentProfileId) {
      setInputValue(studentProfileIdInput, settings.studentProfileId);
    }
    void refreshPairingStatus();
    void refreshCatalogBatchState();
  },
);

extractCurrentPageButton?.addEventListener("click", () => {
  void handleExtract();
});

startKeanImportButton?.addEventListener("click", () => {
  void handleStartKeanImport();
});

captureGuidedPageButton?.addEventListener("click", () => {
  void handleCaptureGuidedPage();
});

confirmImportButton?.addEventListener("click", () => {
  void handleConfirm();
});

startCatalogBatchButton?.addEventListener("click", () => {
  // `sidePanel.open()` must be invoked before this direct user-gesture stack
  // yields. The remaining permission, tab, and worker checks continue only
  // after the persistent surface confirms that its open request was accepted.
  const monitorOpenRequest = openCatalogBatchMonitor(chrome, { windowId: -2 });
  void handleStartCatalogBatch(monitorOpenRequest);
});

pauseCatalogBatchButton?.addEventListener("click", () => {
  void handleCatalogBatchCommand("SAPSOS_PAUSE_CATALOG_BATCH");
});

resumeCatalogBatchButton?.addEventListener("click", () => {
  void handleCatalogBatchCommand("SAPSOS_RESUME_CATALOG_BATCH");
});

cancelCatalogBatchButton?.addEventListener("click", () => {
  void handleCatalogBatchCommand("SAPSOS_CANCEL_CATALOG_BATCH");
});

openCatalogBatchMonitorButton?.addEventListener("click", () => {
  void handleOpenCatalogBatchMonitor();
});

pairExtensionButton?.addEventListener("click", () => {
  void handlePairExtension();
});

renderPreview([]);
renderCatalogBatch(null);
setCaptureGuidedEnabled(false);
setApiStatus("Local app/API not contacted.");
