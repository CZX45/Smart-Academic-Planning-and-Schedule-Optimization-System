import { describe, expect, it } from "vitest";

import {
  executeExtraction,
  popupDiagnosticsFromExtractions,
  readActiveTab,
  shouldAttemptExtractionForUrl,
  type PopupChromeApi,
} from "../src/popup/browser-actions.js";
import { KEAN_STUDENT_PORTAL_PREFIX } from "../src/shared/kean.js";
import type {
  AcademicPageSnapshot,
  BrowserExtensionExtraction,
} from "../src/shared/types.js";

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

function chromeWithMessageFailure(message: string): PopupChromeApi {
  const runtime: { lastError?: { message: string } } = {};
  return {
    runtime,
    tabs: {
      query: () => undefined,
      sendMessage: (_tabId, _message, callback) => {
        runtime.lastError = { message };
        callback();
        delete runtime.lastError;
      },
    },
    scripting: {
      executeScript: (_details, callback) => {
        callback();
      },
    },
    permissions: {
      contains: () => undefined,
      request: () => undefined,
    },
  };
}

function chromeWithExtractionSnapshot(
  snapshot: AcademicPageSnapshot,
  calls: string[] = [],
): PopupChromeApi {
  return {
    tabs: {
      query: () => undefined,
      sendMessage: (_tabId, message, callback) => {
        calls.push(`send:${message.type}`);
        callback({ ok: true, snapshot } as never);
      },
    },
    scripting: {
      executeScript: (details, callback) => {
        calls.push(`inject:${details.files.join(",")}`);
        callback();
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

  it("does not attempt extraction on Kean host pages outside the Student portal", () => {
    expect(
      shouldAttemptExtractionForUrl(
        "https://kean-ss.colleague.elluciancloud.com/Finance/Billing",
      ),
    ).toBe(false);
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
    ).rejects.toThrow(
      "Could not inject extractor into the active tab: Cannot access page",
    );
  });

  it("reports content-script messaging runtime errors", async () => {
    await expect(
      executeExtraction(
        chromeWithMessageFailure(
          "Could not establish connection. Receiving end does not exist.",
        ),
        42,
      ),
    ).rejects.toThrow(
      "Could not contact the page extractor: Could not establish connection. Receiving end does not exist.",
    );
  });

  it("injects the content script before sending the extraction request", async () => {
    const calls: string[] = [];
    const snapshot: AcademicPageSnapshot = {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
    };

    await executeExtraction(chromeWithExtractionSnapshot(snapshot, calls), 42);

    expect(calls).toEqual([
      "inject:dist/content/content-script.js",
      "send:SAPSOS_EXTRACT_PAGE",
    ]);
  });

  it("extracts diagnostics from content-script snapshots", async () => {
    const snapshot: AcademicPageSnapshot = {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
    };

    const extraction = await executeExtraction(
      chromeWithExtractionSnapshot(snapshot),
      42,
    );

    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
      detectedPageType: "UNKNOWN_PAGE",
      tablesFound: 0,
      rowsFound: 0,
    });
    expect(extraction.diagnostics.warningCodes).toContain(
      "KEAN_WHITELISTED_PAGE_NO_ACADEMIC_TABLE_FOUND",
    );
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
