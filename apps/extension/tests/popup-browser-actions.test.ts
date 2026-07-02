import { describe, expect, it } from "vitest";

import {
  executeExtraction,
  popupDiagnosticsFromExtractions,
  readActiveTab,
  shouldAttemptExtractionForUrl,
  type PopupChromeApi,
} from "../src/popup/browser-actions.js";
import { KEAN_STUDENT_PORTAL_PREFIX } from "../src/shared/kean.js";
import type { BrowserExtensionExtraction } from "../src/shared/types.js";

function chromeWithActiveTabs(
  tabs: Array<{ id?: number; url?: string }>,
  lastErrorMessage?: string,
): PopupChromeApi {
  const runtime: { lastError?: { message: string } } = {};
  return {
    runtime,
    tabs: {
      query: (_query, callback) => {
        if (lastErrorMessage) {
          runtime.lastError = { message: lastErrorMessage };
        }
        callback(tabs);
        delete runtime.lastError;
      },
      sendMessage: () => undefined,
    },
    scripting: {
      executeScript: () => undefined,
    },
    permissions: {
      contains: () => undefined,
      request: () => undefined,
    },
  };
}

function chromeWithExtractionFailure(message: string): PopupChromeApi {
  const runtime: { lastError?: { message: string } } = {};
  return {
    runtime,
    tabs: {
      query: () => undefined,
      sendMessage: () => undefined,
    },
    scripting: {
      executeScript: (_details, callback) => {
        runtime.lastError = { message };
        callback();
        delete runtime.lastError;
      },
    },
    permissions: {
      contains: () => undefined,
      request: () => undefined,
    },
  };
}

function extractionWithNoRows(url: string): BrowserExtensionExtraction {
  return {
    pageType: "UNKNOWN_PAGE",
    importType: "UNKNOWN",
    sourceType: "BROWSER_EXTENSION",
    isOfficial: false,
    title: "Unsupported page",
    url,
    fileName: "browser-extension-unknown-page.json",
    fileMimeType: "application/json",
    content: "[]",
    records: [],
    warnings: [],
    diagnostics: {
      currentUrl: url,
      detectedPageType: "UNKNOWN_PAGE",
      matchedPageMarker: "No marker.",
      tablesFound: 0,
      rowsFound: 0,
      extractedAcademicFieldCount: 0,
      ignoredSensitiveFieldCount: 0,
      warningCodes: [],
    },
    requiresReview: true,
    extractedAt: "2026-07-02T00:00:00.000Z",
  };
}

describe("popup browser actions", () => {
  it("captures the active tab id and URL", async () => {
    const tab = await readActiveTab(
      chromeWithActiveTabs([
        {
          id: 42,
          url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
        },
      ]),
    );

    expect(tab).toEqual({
      id: 42,
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    });
  });

  it("allows extraction attempts for Kean Student portal hash routes", () => {
    expect(
      shouldAttemptExtractionForUrl(
        `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      ),
    ).toBe(true);
  });

  it("reports missing active tab URL as a permission problem", async () => {
    await expect(
      readActiveTab(chromeWithActiveTabs([{ id: 42 }])),
    ).rejects.toThrow(
      "Could not read the active tab URL. Please grant site access and try again",
    );
  });

  it("reports script injection runtime errors", async () => {
    await expect(
      executeExtraction(chromeWithExtractionFailure("Cannot access page"), 42),
    ).rejects.toThrow("Cannot access page");
  });

  it("keeps a captured URL in diagnostics when no extraction result exists", () => {
    const diagnostics = popupDiagnosticsFromExtractions([], {
      capturedUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    });

    expect(diagnostics.currentUrl).toBe(
      `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
    );
    expect(diagnostics.tablesFound).toBe(0);
    expect(diagnostics.rowsFound).toBe(0);
  });

  it("keeps diagnostics URL visible when extraction returns zero rows", () => {
    const url = `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`;

    expect(
      popupDiagnosticsFromExtractions([extractionWithNoRows(url)]).currentUrl,
    ).toBe(url);
  });
});
