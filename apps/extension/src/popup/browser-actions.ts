import { extractAcademicPageFromTables } from "../content/extractors.js";
import { isKeanStudentPortalUrl } from "../shared/kean.js";
import type {
  AcademicPageSnapshot,
  BrowserExtensionExtraction,
  ExtensionDiagnostics,
} from "../shared/types.js";

type PopupTab = {
  id?: number;
  url?: string;
};

type ExtractionResponse = {
  ok?: true;
  extraction?: BrowserExtensionExtraction;
  snapshot?: AcademicPageSnapshot;
};

export type PopupChromeApi = {
  runtime?: {
    lastError?: {
      message?: string;
    };
  };
  tabs: {
    query: (
      query: { active: true; currentWindow: true },
      callback: (tabs: PopupTab[]) => void,
    ) => void;
    sendMessage: (
      tabId: number,
      message: { type: string },
      callback: (response?: ExtractionResponse) => void,
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

export type ActiveBrowserTab = {
  id: number;
  url: string;
};

function lastErrorMessage(chromeApi: PopupChromeApi): string {
  return chromeApi.runtime?.lastError?.message?.trim() ?? "";
}

export function safeDiagnosticUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "";
  }
}

export function popupDiagnosticsFromExtractions(
  extractions: readonly BrowserExtensionExtraction[],
  options: { capturedUrl?: string } = {},
): ExtensionDiagnostics {
  const latest = extractions.at(-1);
  if (latest) {
    return latest.diagnostics;
  }
  return {
    currentUrl: options.capturedUrl
      ? safeDiagnosticUrl(options.capturedUrl)
      : "No page captured.",
    detectedPageType: "UNKNOWN_PAGE",
    matchedPageMarker: "No marker.",
    tablesFound: 0,
    rowsFound: 0,
    extractedAcademicFieldCount: 0,
    ignoredSensitiveFieldCount: 0,
    warningCodes: [],
  };
}

export function readActiveTab(
  chromeApi: PopupChromeApi,
): Promise<ActiveBrowserTab> {
  return new Promise((resolve, reject) => {
    chromeApi.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const queryError = lastErrorMessage(chromeApi);
      if (queryError) {
        reject(new Error(queryError));
        return;
      }
      const tab = tabs[0];
      if (typeof tab?.id !== "number") {
        reject(new Error("No active browser tab found"));
        return;
      }
      if (!tab.url) {
        reject(
          new Error(
            "Could not read the active tab URL. Please grant site access and try again",
          ),
        );
        return;
      }
      resolve({ id: tab.id, url: tab.url });
    });
  });
}

export function shouldAttemptExtractionForUrl(url: string): boolean {
  return isKeanStudentPortalUrl(url);
}

export function executeExtraction(
  chromeApi: PopupChromeApi,
  tabId: number,
): Promise<BrowserExtensionExtraction> {
  return new Promise((resolve, reject) => {
    chromeApi.scripting.executeScript(
      {
        target: { tabId },
        files: ["dist/content/content-script.js"],
      },
      () => {
        const injectionError = lastErrorMessage(chromeApi);
        if (injectionError) {
          reject(
            new Error(
              `Could not inject extractor into the active tab: ${injectionError}`,
            ),
          );
          return;
        }
        chromeApi.tabs.sendMessage(
          tabId,
          { type: "SAPSOS_EXTRACT_PAGE" },
          (response) => {
            const messageError = lastErrorMessage(chromeApi);
            if (messageError) {
              reject(
                new Error(
                  `Could not contact the page extractor: ${messageError}`,
                ),
              );
              return;
            }
            if (!response?.ok) {
              reject(
                new Error(
                  "Could not contact the page extractor: The page did not return an extraction result.",
                ),
              );
              return;
            }
            if (response.extraction) {
              resolve(response.extraction);
              return;
            }
            if (response.snapshot) {
              resolve(extractAcademicPageFromTables(response.snapshot));
              return;
            }
            reject(
              new Error(
                "Could not contact the page extractor: The page did not return an extraction result.",
              ),
            );
          },
        );
      },
    );
  });
}

export function ensureHostPermission(
  chromeApi: PopupChromeApi,
  origins: string[],
): Promise<boolean> {
  return new Promise((resolve, reject) => {
    chromeApi.permissions.contains({ origins }, (alreadyGranted) => {
      const containsError = lastErrorMessage(chromeApi);
      if (containsError) {
        reject(new Error(containsError));
        return;
      }
      if (alreadyGranted) {
        resolve(true);
        return;
      }
      chromeApi.permissions.request({ origins }, (granted) => {
        const requestError = lastErrorMessage(chromeApi);
        if (requestError) {
          reject(new Error(requestError));
          return;
        }
        resolve(granted);
      });
    });
  });
}
