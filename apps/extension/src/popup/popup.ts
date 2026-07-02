import {
  createDataImportRequestsFromExtractions,
  createDataImportRequestFromExtraction,
} from "../content/extractors.js";
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

type Tab = {
  id?: number;
};

type ChromeApi = {
  storage: {
    local: {
      get: (
        keys: string[],
        callback: (settings: StoredSettings) => void,
      ) => void;
      set: (settings: StoredSettings) => void;
    };
  };
  tabs: {
    query: (
      query: { active: true; currentWindow: true },
      callback: (tabs: Tab[]) => void,
    ) => void;
    sendMessage: (
      tabId: number,
      message: { type: string },
      callback: (response?: {
        ok: true;
        extraction: BrowserExtensionExtraction;
      }) => void,
    ) => void;
  };
  scripting: {
    executeScript: (
      details: { target: { tabId: number }; files: string[] },
      callback: () => void,
    ) => void;
  };
  permissions: {
    contains: (
      permissions: { origins: string[] },
      callback: (granted: boolean) => void,
    ) => void;
    request: (
      permissions: { origins: string[] },
      callback: (granted: boolean) => void,
    ) => void;
  };
};

declare const chrome: ChromeApi;

const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const studentProfileIdInput = document.getElementById("studentProfileIdInput");
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
const diagnosticAcademicFieldsText = document.getElementById(
  "diagnosticAcademicFieldsText",
);
const diagnosticSensitiveFieldsText = document.getElementById(
  "diagnosticSensitiveFieldsText",
);

let latestExtraction: BrowserExtensionExtraction | null = null;
let guidedMode = false;
let guidedExtractions: BrowserExtensionExtraction[] = [];

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
): void {
  const latest = extractions.at(-1);
  if (!latest) {
    setText(diagnosticUrlText, "No page captured.");
    setText(diagnosticMarkerText, "No marker.");
    setText(diagnosticTablesText, "0");
    setText(diagnosticRowsText, "0");
    setText(diagnosticAcademicFieldsText, "0");
    setText(diagnosticSensitiveFieldsText, "0");
    return;
  }
  setText(diagnosticUrlText, latest.diagnostics.currentUrl);
  setText(diagnosticMarkerText, latest.diagnostics.matchedPageMarker);
  setText(diagnosticTablesText, String(latest.diagnostics.tablesFound));
  setText(diagnosticRowsText, String(latest.diagnostics.rowsFound));
  setText(
    diagnosticAcademicFieldsText,
    String(latest.diagnostics.extractedAcademicFieldCount),
  );
  setText(
    diagnosticSensitiveFieldsText,
    String(latest.diagnostics.ignoredSensitiveFieldCount),
  );
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
): void {
  setDetectedPage(extractions);
  setCounts(extractions);
  setWarnings(extractions);
  setDiagnostics(extractions);
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

function activeTab(): Promise<Tab> {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab?.id) {
        reject(new Error("No active tab is available."));
        return;
      }
      resolve(tab);
    });
  });
}

function executeExtraction(tabId: number): Promise<BrowserExtensionExtraction> {
  return new Promise((resolve, reject) => {
    chrome.scripting.executeScript(
      {
        target: { tabId },
        files: ["dist/content/content-script.js"],
      },
      () => {
        chrome.tabs.sendMessage(
          tabId,
          { type: "SAPSOS_EXTRACT_PAGE" },
          (response) => {
            if (!response?.ok) {
              reject(
                new Error("The page did not return an extraction result."),
              );
              return;
            }
            resolve(response.extraction);
          },
        );
      },
    );
  });
}

async function handleExtract(): Promise<void> {
  try {
    setStatus("Extracting visible page data.");
    guidedMode = false;
    guidedExtractions = [];
    setConfirmEnabled(false);
    const tab = await activeTab();
    latestExtraction = await executeExtraction(tab.id ?? 0);
    renderPreview([latestExtraction]);
    setConfirmEnabled(latestExtraction.records.length > 0);
    setStatus("Preview ready. Confirm before sending to staging import.");
  } catch (error: unknown) {
    latestExtraction = null;
    renderPreview([]);
    setStatus(error instanceof Error ? error.message : "Extraction failed.");
  }
}

function ensureKeanPermission(): Promise<boolean> {
  const origins = [KEAN_OPTIONAL_HOST_PERMISSION];
  return new Promise((resolve) => {
    chrome.permissions.contains({ origins }, (alreadyGranted) => {
      if (alreadyGranted) {
        resolve(true);
        return;
      }
      chrome.permissions.request({ origins }, (granted) => resolve(granted));
    });
  });
}

async function handleStartKeanImport(): Promise<void> {
  setStatus("Requesting Kean Student Portal permission.");
  const granted = await ensureKeanPermission();
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
    const tab = await activeTab();
    const extraction = await executeExtraction(tab.id ?? 0);
    if (
      extraction.sourceLabel !== KEAN_SOURCE_LABEL ||
      extraction.pageType === "UNKNOWN_PAGE" ||
      extraction.records.length === 0
    ) {
      renderPreview([extraction]);
      setConfirmEnabled(guidedExtractions.length > 0);
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
    setStatus(
      error instanceof Error ? error.message : "Guided capture failed.",
    );
  }
}

async function handleConfirm(): Promise<void> {
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
  chrome.storage.local.set({ apiBaseUrl, studentProfileId });
  let requests: BrowserExtensionDataImportRequest[];
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
      createDataImportRequestFromExtraction(studentProfileId, firstExtraction),
    ];
  }
  setStatus("Sending confirmed staging import.");
  try {
    let createdCount = 0;
    for (const request of requests) {
      const response = await fetch(`${apiBaseUrl}/api/v1/data-imports`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(request),
      });
      if (!response.ok) {
        setApiStatus(`Local app/API failed with HTTP ${response.status}.`);
        setStatus(
          "Staging import failed. Retry only after reviewing the issue.",
        );
        return;
      }
      createdCount += 1;
    }
    setApiStatus(`Local app/API accepted ${createdCount} staging import(s).`);
    setStatus("Staging import created. Review is still required in the app.");
  } catch (error: unknown) {
    setApiStatus("Local app/API connection failed.");
    setStatus(
      error instanceof Error ? error.message : "Staging import failed.",
    );
  }
}

chrome.storage.local.get(["apiBaseUrl", "studentProfileId"], (settings) => {
  if (settings.apiBaseUrl) {
    setInputValue(apiBaseUrlInput, settings.apiBaseUrl);
  }
  if (settings.studentProfileId) {
    setInputValue(studentProfileIdInput, settings.studentProfileId);
  }
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

renderPreview([]);
setCaptureGuidedEnabled(false);
setApiStatus("Local app/API not contacted.");
