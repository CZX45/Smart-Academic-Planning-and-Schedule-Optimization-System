import { createDataImportRequestFromExtraction } from "../content/extractors.js";
import type { BrowserExtensionExtraction } from "../shared/types.js";

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
};

declare const chrome: ChromeApi;

const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const studentProfileIdInput = document.getElementById("studentProfileIdInput");
const extractCurrentPageButton = document.getElementById(
  "extractCurrentPageButton",
);
const confirmImportButton = document.getElementById("confirmImportButton");
const statusText = document.getElementById("statusText");
const previewText = document.getElementById("previewText");

let latestExtraction: BrowserExtensionExtraction | null = null;

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

function setPreview(extraction: BrowserExtensionExtraction | null): void {
  if (!previewText) {
    return;
  }
  previewText.textContent = extraction
    ? JSON.stringify(
        {
          page_type: extraction.pageType,
          import_type: extraction.importType,
          records: extraction.records.length,
          warnings: extraction.warnings.map((warning) => warning.code),
        },
        null,
        2,
      )
    : "";
}

function setConfirmEnabled(enabled: boolean): void {
  if (confirmImportButton instanceof HTMLButtonElement) {
    confirmImportButton.disabled = !enabled;
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
    setConfirmEnabled(false);
    const tab = await activeTab();
    latestExtraction = await executeExtraction(tab.id ?? 0);
    setPreview(latestExtraction);
    setConfirmEnabled(latestExtraction.records.length > 0);
    setStatus("Preview ready. Confirm before sending to staging import.");
  } catch (error: unknown) {
    latestExtraction = null;
    setPreview(null);
    setStatus(error instanceof Error ? error.message : "Extraction failed.");
  }
}

async function handleConfirm(): Promise<void> {
  if (!latestExtraction) {
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
  const request = createDataImportRequestFromExtraction(
    studentProfileId,
    latestExtraction,
  );
  setStatus("Sending confirmed staging import.");
  const response = await fetch(`${apiBaseUrl}/api/v1/data-imports`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    setStatus(`Staging import failed with HTTP ${response.status}.`);
    return;
  }
  setStatus("Staging import created. Review is still required in the app.");
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

confirmImportButton?.addEventListener("click", () => {
  void handleConfirm();
});
