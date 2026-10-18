import { describe, expect, it } from "vitest";

import {
  acceptCatalogPage,
  createCatalogBatchState,
  pauseCatalogBatch,
  resumeCatalogBatch,
  type CatalogBatchPage,
  type CatalogBatchState,
} from "../src/content/catalog-batch.js";
import {
  runCatalogBatch,
  type CatalogBatchDriver,
} from "../src/background/catalog-batch-runner.js";
import type { BrowserExtensionExtraction } from "../src/shared/types.js";

const resultUrl =
  "https://kean-ss.colleague.elluciancloud.com/Student/Courses/SearchResult";

function page(
  subjectCode: string,
  pageNumber: number,
  totalPages: number,
  courseCodes: string[],
  fatalSignal: CatalogBatchPage["fatalSignal"] = null,
): CatalogBatchPage {
  const extraction: BrowserExtensionExtraction = {
    pageType: "KEAN_COURSE_CATALOG_PAGE",
    importType: "COURSE_CATALOG",
    sourceType: "BROWSER_EXTENSION",
    sourceLabel: "KEAN_STUDENT_PORTAL",
    isOfficial: false,
    title: "Course Catalog",
    url: resultUrl,
    fileName: "catalog.csv",
    fileMimeType: "text/csv",
    content: "",
    records: courseCodes.map((code) => ({
      course_code: code,
      course_title: `Visible ${code}`,
      credits: "3",
      raw_requisites: "None",
      rule_review_status: "REVIEW_REQUIRED",
    })),
    warnings: [],
    diagnostics: {
      currentUrl: resultUrl,
      detectedPageType: "KEAN_COURSE_CATALOG_PAGE",
      matchedPageMarker: "/Student/Courses/SearchResult",
      tablesFound: 0,
      rowsFound: courseCodes.length,
      visibleTextLength: 0,
      rowLikeBlocksFound: courseCodes.length,
      extractedAcademicFieldCount: courseCodes.length * 4,
      ignoredSensitiveFieldCount: 0,
      directSnapshotRan: true,
      bounded: false,
      warningCodes: [],
      academicTablesDetected: 1,
      academicTablesParsed: 1,
      academicRowsParsed: courseCodes.length,
      academicRowsSkipped: 0,
      academicRowsCapped: 0,
      parserWarningCodes: [],
    },
    requiresReview: true,
    extractedAt: `2026-08-26T02:00:0${pageNumber}.000Z`,
  };
  return { subjectCode, pageNumber, totalPages, fatalSignal, extraction };
}

function initialState(): CatalogBatchState {
  return createCatalogBatchState({
    apiBaseUrl: "http://localhost:8000",
    studentProfileId: "00000000-0000-4000-8000-000000000702",
    tabId: 41,
    landingUrl: "https://kean-ss.colleague.elluciancloud.com/Student/Courses",
    subjects: [
      { code: "ACCT", label: "Accounting" },
      { code: "FIN", label: "Finance" },
    ],
    startedAt: "2026-08-26T02:00:00.000Z",
  });
}

function fakeDriver(
  options: {
    pauseAfterFirstPage?: boolean;
    pauseDuringLocalProcess?: boolean;
    changeAcceptedPageOnResume?: boolean;
    fatalSignal?: CatalogBatchPage["fatalSignal"];
  } = {},
): CatalogBatchDriver & {
  persisted: CatalogBatchState;
  events: string[];
} {
  let currentPage = 1;
  const events: string[] = [];
  const driver: CatalogBatchDriver & {
    persisted: CatalogBatchState;
    events: string[];
  } = {
    persisted: initialState(),
    events,
    now: () => "2026-08-26T02:05:00.000Z",
    delay: async (milliseconds) => {
      events.push(`delay:${milliseconds}`);
    },
    loadState: async () => driver.persisted,
    persistState: async (state) => {
      driver.persisted = state;
      events.push(`persist:${state.status}:${state.pagesCaptured}`);
      if (options.pauseAfterFirstPage && state.pagesCaptured === 1) {
        driver.persisted = pauseCatalogBatch(state);
      }
    },
    ensureLandingPage: async () => {
      currentPage = 1;
      events.push("landing");
    },
    startSubjectSearch: async (_state, subject) => {
      currentPage = 1;
      events.push(`search:${subject.code}`);
    },
    capturePage: async (_state, subject, expectedPage) => {
      expect(expectedPage).toBe(currentPage);
      if (subject.code === "ACCT") {
        const captured = page(
          "ACCT",
          currentPage,
          2,
          currentPage === 1 ? ["ACCT 2200"] : ["ACCT 2200", "ACCT 3300"],
          options.fatalSignal,
        );
        if (
          options.changeAcceptedPageOnResume &&
          currentPage === 1 &&
          captured.extraction.records[0]
        ) {
          captured.extraction.records[0].course_title =
            "Changed visible course title";
        }
        return captured;
      }
      return page("FIN", 1, 1, ["FIN 3310"], options.fatalSignal);
    },
    advancePage: async (_state, targetPage) => {
      currentPage = targetPage;
      events.push(`page:${targetPage}`);
      return targetPage === 2 ? "course-ACCT-2200" : "course-page-marker";
    },
    processSubject: async (_state, extraction) => {
      events.push(`process:${extraction.records[0]?.course_code}`);
      if (options.pauseDuringLocalProcess) {
        driver.persisted = pauseCatalogBatch(driver.persisted);
      }
      return {
        importRunId: `import-${extraction.records[0]?.course_code}`,
        reviewSessionId: `review-${extraction.records[0]?.course_code}`,
        createdCount: extraction.records.length,
        updatedCount: 0,
        processingStagesCompleted: [
          "LOCAL_STAGING",
          "LOCAL_VALIDATION",
          "LOCAL_REVIEW",
          "LOCAL_DRY_RUN",
          "LOCAL_APPLY",
          "MYPROGRESS_REMAP",
        ],
        stagedRecordCount: extraction.records.length,
        reviewValidCount: extraction.records.length,
        reviewWarningCount: 0,
        appliedRecordCount: extraction.records.length,
        myprogressRunId: "myprogress-1",
        myprogressTotalCount: 118,
        myprogressMappedBeforeCount: 34,
        myprogressMappedCount: extraction.records.length + 34,
        myprogressUnmatchedCount: 84 - extraction.records.length,
        myprogressRemapExecuted: true,
        reasonCodes: [],
        providerActionsWritten: "NO",
        completedAt: "2026-08-26T02:05:00.000Z",
      };
    },
  };
  return driver;
}

describe("Course Catalog batch runner", () => {
  it("serially iterates subjects and pages, deduplicates overlap, and applies locally", async () => {
    const driver = fakeDriver();

    const result = await runCatalogBatch(initialState(), driver);

    expect(result).toMatchObject({
      status: "COMPLETED",
      completedSubjects: ["ACCT", "FIN"],
      coursesCaptured: 4,
      uniqueCourses: 3,
      duplicatesIgnored: 1,
      localImportsApplied: 2,
      localCoursesCreated: 3,
      providerActionsWritten: "NO",
    });
    expect(
      driver.events.filter((event) => event.startsWith("search:")),
    ).toEqual(["search:ACCT", "search:FIN"]);
    expect(
      driver.events.filter((event) => event.startsWith("process:")),
    ).toEqual(["process:ACCT 2200", "process:FIN 3310"]);
  });

  it("stops before the next page when the user pauses", async () => {
    const driver = fakeDriver({ pauseAfterFirstPage: true });

    const result = await runCatalogBatch(initialState(), driver);

    expect(result.status).toBe("PAUSED");
    expect(result.pagesCaptured).toBe(1);
    expect(driver.events).not.toContain("page:2");
    expect(driver.events.some((event) => event.startsWith("process:"))).toBe(
      false,
    );
  });

  it("records a completed local subject but stays paused when pause arrives during local processing", async () => {
    const driver = fakeDriver({ pauseDuringLocalProcess: true });

    const result = await runCatalogBatch(initialState(), driver);

    expect(result).toMatchObject({
      status: "PAUSED",
      completedSubjects: ["ACCT"],
      localImportsApplied: 1,
      localCoursesCreated: 2,
      providerActionsWritten: "NO",
    });
    expect(
      driver.events.filter((event) => event.startsWith("search:")),
    ).toEqual(["search:ACCT"]);
  });

  it("restarts a partial subject safely and ignores the already accepted page", async () => {
    let partial = acceptCatalogPage(
      initialState(),
      page("ACCT", 1, 2, ["ACCT 2200"]),
    );
    partial = pauseCatalogBatch(partial);
    const driver = fakeDriver();
    driver.persisted = resumeCatalogBatch(partial);

    const result = await runCatalogBatch(driver.persisted, driver);

    expect(result.status).toBe("COMPLETED");
    expect(result.uniqueCourses).toBe(3);
    expect(result.duplicatesIgnored).toBe(1);
    expect(result.pagesCaptured).toBe(3);
  });

  it("fails closed if a previously accepted page changes before resume", async () => {
    let partial = acceptCatalogPage(
      initialState(),
      page("ACCT", 1, 2, ["ACCT 2200"]),
    );
    partial = pauseCatalogBatch(partial);
    const driver = fakeDriver({ changeAcceptedPageOnResume: true });
    driver.persisted = resumeCatalogBatch(partial);

    const result = await runCatalogBatch(driver.persisted, driver);

    expect(result).toMatchObject({
      status: "FAILED",
      lastErrorCode: "CONFLICTING_ACCEPTED_CATALOG_PAGE",
      providerActionsWritten: "NO",
    });
    expect(driver.events.some((event) => event.startsWith("process:"))).toBe(
      false,
    );
  });

  it("fails closed immediately on a provider rate-limit signal", async () => {
    const driver = fakeDriver({ fatalSignal: "RATE_LIMIT" });

    const result = await runCatalogBatch(initialState(), driver);

    expect(result).toMatchObject({
      status: "FAILED",
      lastErrorCode: "BATCH_CATALOG_RATE_LIMIT",
      providerActionsWritten: "NO",
    });
    expect(driver.events.some((event) => event.startsWith("process:"))).toBe(
      false,
    );
  });
});
