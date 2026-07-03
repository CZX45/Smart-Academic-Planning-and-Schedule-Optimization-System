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
    },
    scripting: {
      executeScript: (_details, callback) => {
        runtime.lastError = { message };
        callback([]);
        delete runtime.lastError;
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
    },
    scripting: {
      executeScript: (details, callback) => {
        calls.push(
          `execute:${typeof details.func}:${details.target.tabId}:${details.args.length}`,
        );
        callback([{ result: snapshot }]);
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
      visibleTextLength: 0,
      rowLikeBlocksFound: 0,
      extractedAcademicFieldCount: 0,
      ignoredSensitiveFieldCount: 0,
      directSnapshotRan: false,
      bounded: false,
      warningCodes: [],
      academicTablesDetected: 0,
      academicTablesParsed: 0,
      academicRowsParsed: 0,
      academicRowsSkipped: 0,
      academicRowsCapped: 0,
      parserWarningCodes: [],
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
      executeExtraction(chromeWithExtractionFailure("Cannot access page"), {
        id: 42,
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
      }),
    ).rejects.toThrow("Could not snapshot the active tab: Cannot access page");
  });

  it("rejects extraction before injection outside the Kean Student portal", async () => {
    await expect(
      executeExtraction(
        chromeWithExtractionSnapshot({
          title: "Billing",
          url: "https://kean-ss.colleague.elluciancloud.com/Finance/Billing",
          tables: [],
        }),
        {
          id: 42,
          url: "https://kean-ss.colleague.elluciancloud.com/Finance/Billing",
        },
      ),
    ).rejects.toThrow(
      "This browser page cannot be inspected by the extension.",
    );
  });

  it("runs a direct page snapshot function without content-script messaging", async () => {
    const calls: string[] = [];
    const snapshot: AcademicPageSnapshot = {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
    };

    await executeExtraction(chromeWithExtractionSnapshot(snapshot, calls), {
      id: 42,
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    });

    expect(calls).toEqual(["execute:function:42:1"]);
  });

  it("extracts diagnostics from content-script snapshots", async () => {
    const snapshot: AcademicPageSnapshot = {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
    };

    const extraction = await executeExtraction(
      chromeWithExtractionSnapshot(snapshot),
      {
        id: 42,
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      },
    );

    expect(extraction.diagnostics).toMatchObject({
      currentUrl: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress`,
      detectedPageType: "KEAN_MY_PROGRESS_PAGE",
      tablesFound: 0,
      rowsFound: 0,
      visibleTextLength: 0,
      rowLikeBlocksFound: 0,
      directSnapshotRan: true,
      bounded: false,
    });
    expect(extraction.diagnostics.warningCodes).toContain(
      "MY_PROGRESS_PROGRAM_MISSING",
    );
  });

  it("caps oversized content-script snapshots before parsing", async () => {
    const rows = Array.from({ length: 250 }, (_value, index) => [
      "BSFIN",
      `Requirement ${index}`,
      "Completed",
      "Remaining",
    ]);
    const snapshot: AcademicPageSnapshot = {
      title: "MyProgress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [
        {
          index: 0,
          caption: "My Progress",
          headers: [
            "Program",
            "Requirements",
            "Completed Courses",
            "Remaining Requirements",
          ],
          rows,
        },
      ],
    };

    const extraction = await executeExtraction(
      chromeWithExtractionSnapshot(snapshot),
      {
        id: 42,
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      },
    );

    expect(extraction.records).toHaveLength(200);
    expect(extraction.diagnostics.rowsFound).toBe(200);
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "EXTRACTION_LIMIT_REACHED",
    );
    expect(extraction.diagnostics.warningCodes).toContain(
      "EXTRACTION_LIMIT_REACHED",
    );
  });

  it("truncates very long cell text before parsing", async () => {
    const longTitle = "A".repeat(1200);
    const snapshot: AcademicPageSnapshot = {
      title: "AcademicHistory",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
      tables: [
        {
          index: 0,
          caption: "Transcript",
          headers: ["Term", "Course", "Title"],
          rows: [["2024FA", "CPS 2231", longTitle]],
        },
      ],
    };

    const extraction = await executeExtraction(
      chromeWithExtractionSnapshot(snapshot),
      {
        id: 42,
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/AcademicHistory`,
      },
    );

    expect(extraction.records[0]?.course_title).toHaveLength(500);
    expect(extraction.warnings.map((warning) => warning.code)).toContain(
      "EXTRACTION_LIMIT_REACHED",
    );
  });

  it("keeps visible page text diagnostics beyond the per-cell limit", async () => {
    const visibleText = "My Progress ".repeat(120);
    const snapshot: AcademicPageSnapshot = {
      title: "My Progress",
      url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      tables: [],
      visibleText,
      snapshotMetadata: {
        directSnapshotRan: true,
        visibleTextLength: visibleText.length,
        rowLikeBlocksFound: 0,
      },
    };

    const extraction = await executeExtraction(
      chromeWithExtractionSnapshot(snapshot),
      {
        id: 42,
        url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
      },
    );

    expect(extraction.diagnostics.visibleTextLength).toBe(visibleText.length);
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
