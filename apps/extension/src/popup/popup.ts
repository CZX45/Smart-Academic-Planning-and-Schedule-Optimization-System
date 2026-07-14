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
  shouldAttemptExtractionForUrl,
  type PopupChromeApi,
} from "./browser-actions.js";
import {
  KEAN_OPTIONAL_HOST_PERMISSION,
  KEAN_SOURCE_LABEL,
} from "../shared/kean.js";
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
};

type ChromeApi = Omit<PopupChromeApi, "runtime"> & {
  runtime: {
    lastError?: { message?: string };
    sendMessage: (message: unknown, callback: (response: unknown) => void) => void;
  };
  storage: {
    local: {
      get: (
        keys: string[],
        callback: (settings: StoredSettings) => void,
      ) => void;
      set: (settings: StoredSettings) => void;
    };
  };
};

declare const chrome: ChromeApi;

const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const studentProfileIdInput = document.getElementById("studentProfileIdInput");
const apiBearerTokenInput = document.getElementById("apiBearerTokenInput");
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

function sendBackgroundMessage(message: unknown): Promise<ApiResponse> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response: unknown) => {
      if (!isObject(response)) {
        resolve({
          ok: false,
          status: 503,
          payload: { code: "invalid_background_response" },
        });
        return;
      }
      resolve({
        ok: response.ok === true,
        status: typeof response.status === "number" ? response.status : 503,
        payload: response.payload,
      });
    });
  });
}

function setPairingStatus(message: string): void {
  if (pairingStatusText) {
    pairingStatusText.textContent = message;
  }
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

async function responseJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
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
  return null;
}

function isLocalApiBaseUrl(apiBaseUrl: string): boolean {
  try {
    const parsed = new URL(apiBaseUrl);
    return ["localhost", "127.0.0.1"].includes(parsed.hostname);
  } catch {
    return false;
  }
}

function isSecureNonLocalApiBaseUrl(apiBaseUrl: string): boolean {
  try {
    const parsed = new URL(apiBaseUrl);
    return parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function importRequestHeaders(apiBearerToken: string): Record<string, string> {
  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (apiBearerToken.length > 0) {
    headers.authorization = `Bearer ${apiBearerToken}`;
  }
  return headers;
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
  const apiBearerToken = inputValue(apiBearerTokenInput);
  if (!apiBaseUrl || !studentProfileId) {
    setStatus("API base URL and student profile ID are required.");
    return;
  }
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    if (!isSecureNonLocalApiBaseUrl(apiBaseUrl)) {
      setStatus("Non-local API base URL must use HTTPS for staging imports.");
      return;
    }
    if (apiBearerToken.length === 0) {
      setStatus("API bearer token is required for non-local staging imports.");
      return;
    }
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
      const result: ApiResponse = await (isLocalApiBaseUrl(apiBaseUrl)
        ? sendBackgroundMessage({
            type: "SAPSOS_SUBMIT_IMPORT",
            apiBaseUrl,
            request,
          })
        : (() => {
            return fetch(`${apiBaseUrl}/api/v1/data-imports`, {
              method: "POST",
              headers: importRequestHeaders(apiBearerToken),
              body: JSON.stringify(request),
            }).then(async (response) => ({
              ok: response.ok,
              status: response.status,
              payload: await responseJson(response),
            }));
          })());
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
    setPairingStatus("Paired with the local app. The credential is held by the Extension worker.");
  } else {
    setPairingStatus(apiErrorMessage(payload) ?? "Pairing failed. Check the code and app state.");
  }
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
    setPairingStatus("A local app pairing is active.");
  } else if (result.ok === true) {
    setPairingStatus("Pairing required.");
  } else {
    setPairingStatus("Local app unavailable.");
  }
}

chrome.storage.local.get(["apiBaseUrl", "studentProfileId"], (settings) => {
  if (settings.apiBaseUrl) {
    setInputValue(apiBaseUrlInput, settings.apiBaseUrl);
  }
  if (settings.studentProfileId) {
    setInputValue(studentProfileIdInput, settings.studentProfileId);
  }
  void refreshPairingStatus();
});

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

pairExtensionButton?.addEventListener("click", () => {
  void handlePairExtension();
});

renderPreview([]);
setCaptureGuidedEnabled(false);
setApiStatus("Local app/API not contacted.");
