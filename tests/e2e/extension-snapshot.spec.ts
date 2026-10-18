import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { extractAcademicPageFromTables } from "../../apps/extension/src/content/extractors.js";
import { BOUNDED_EXTRACTION_LIMITS } from "../../apps/extension/src/content/snapshot-limits.js";
import {
  advanceCatalogResultPage,
  discoverCatalogSubjects,
  inspectCatalogResultPage,
  prepareCatalogSubjectSearch,
  watchCatalogResultPage,
  watchCatalogSubjectNavigation,
} from "../../apps/extension/src/content/catalog-batch-page.js";
import { snapshotVisibleAcademicPage } from "../../apps/extension/src/popup/browser-actions.js";

const fixturePath = resolve(
  process.cwd(),
  "apps",
  "extension",
  "tests",
  "fixtures",
  "kean-my-progress-table-heavy-nested.html",
);

const catalogCardFixturePath = resolve(
  process.cwd(),
  "apps",
  "extension",
  "tests",
  "fixtures",
  "kean-course-catalog-card-list.html",
);

const responsiveSectionFixturePath = resolve(
  process.cwd(),
  "apps",
  "extension",
  "tests",
  "fixtures",
  "kean-section-responsive-listing.html",
);

const catalogSearchFixturePath = resolve(
  process.cwd(),
  "apps",
  "extension",
  "tests",
  "fixtures",
  "kean-course-catalog-search.html",
);

const catalogPaginationFixturePath = resolve(
  process.cwd(),
  "apps",
  "extension",
  "tests",
  "fixtures",
  "kean-course-catalog-pagination.html",
);

type CapturedCatalogSignal = {
  signal: string;
  navigationRevision?: number;
  pageNumber: number | null;
  totalPages: number | null;
  visibleCourseCount: number | null;
  subjectCode: string | null;
  firstCourseMarker: string | null;
  lastCourseMarker: string | null;
  resultFingerprint: string | null;
  diagnostics?: Record<string, unknown>;
};

async function openCatalogPaginationFixture(page: Page): Promise<string> {
  const resultUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses/SearchResult";
  await page.route(resultUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogPaginationFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(resultUrl);
  return resultUrl;
}

async function installCatalogSignalCapture(page: Page): Promise<void> {
  await page.evaluate(() => {
    const target = globalThis as typeof globalThis & {
      phase15CatalogSignals?: unknown[];
      chrome?: {
        runtime: {
          lastError?: { message?: string };
          sendMessage: (
            message: unknown,
            callback?: (response: unknown) => void,
          ) => void;
        };
      };
    };
    target.phase15CatalogSignals = [];
    target.chrome = {
      runtime: {
        sendMessage: (message, callback) => {
          target.phase15CatalogSignals?.push(message);
          callback?.({ ok: true });
        },
      },
    };
  });
}

async function waitForCatalogSignal(
  page: Page,
): Promise<CapturedCatalogSignal> {
  await page.waitForFunction(
    () =>
      ((globalThis as typeof globalThis & { phase15CatalogSignals?: unknown[] })
        .phase15CatalogSignals?.length ?? 0) > 0,
  );
  return await page.evaluate(
    () =>
      (
        globalThis as typeof globalThis & {
          phase15CatalogSignals?: CapturedCatalogSignal[];
        }
      ).phase15CatalogSignals?.[0] ?? {
        signal: "MISSING",
        pageNumber: null,
        totalPages: null,
        visibleCourseCount: null,
        subjectCode: null,
        firstCourseMarker: null,
        lastCourseMarker: null,
        resultFingerprint: null,
      },
  );
}

test("preserves MyProgress summary evidence on a table-heavy nested DOM", async ({
  page,
}) => {
  await page.setContent(readFileSync(fixturePath, "utf8"), {
    waitUntil: "load",
  });

  const snapshot = await page.evaluate(
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );

  expect(snapshot.tables).toHaveLength(17);
  expect(
    snapshot.tables.reduce((count, table) => count + table.rows.length, 0),
  ).toBe(86);
  expect(snapshot.headings).toContain("Mock Finance, BS");
  expect(snapshot.visibleText).toContain("Program Mock Finance, BS");
  expect(snapshot.snapshotMetadata).toMatchObject({
    bounded: false,
    directSnapshotRan: true,
  });
  expect(snapshot.warnings ?? []).not.toContainEqual(
    expect.objectContaining({ code: "EXTRACTION_LIMIT_REACHED" }),
  );
});

test("captures and parses sanitized Kean catalog cards without portal actions", async ({
  page,
}) => {
  await page.setContent(readFileSync(catalogCardFixturePath, "utf8"), {
    waitUntil: "load",
  });

  const snapshot = await page.evaluate(
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );
  const extraction = extractAcademicPageFromTables({
    ...snapshot,
    title: "Course Catalog",
    url: "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/Search?keyword=MOCK",
  });

  const catalogBlocks = (snapshot.rowLikeBlocks ?? []).filter(
    (block) => block.section === "COURSE_CATALOG_CARD",
  );
  expect(catalogBlocks).toHaveLength(2);
  expect(catalogBlocks.flatMap((block) => block.cells ?? [])).not.toContain(
    "Add Course to Plan",
  );
  expect(extraction.pageType).toBe("KEAN_COURSE_CATALOG_PAGE");
  expect(extraction.records).toHaveLength(2);
  expect(extraction.records[0]).toMatchObject({
    course_code: "MOCK 1234",
    course_title: "Explainable Systems",
    credits: "3",
    description:
      "A source-tagged mock description for a sanitized catalog regression fixture.",
    prerequisites: "MOCK*1000 - Must be completed prior to taking this course.",
    corequisites: "MOCK*1200 - Must be taken at the same time as this course.",
    minimum_grade: "Minimum grade of C required.",
    standing_requirements:
      "Junior standing or 24 credits in MOCK, or Department Chair permission required.",
    raw_requisites:
      "MOCK*1000 - Must be completed prior to taking this course. | MOCK*1200 - Must be taken at the same time as this course. | Minimum grade of C required. | Junior standing or 24 credits in MOCK, or Department Chair permission required.",
    rule_review_status: "MANUAL_CONFIRMATION_REQUIRED",
  });
  expect(extraction.warnings.map((warning) => warning.code)).toContain(
    "KEAN_CATALOG_RULE_REQUIRES_REVIEW",
  );
});

test("captures and parses responsive Kean sections without schedule actions", async ({
  page,
}) => {
  await page.setContent(readFileSync(responsiveSectionFixturePath, "utf8"), {
    waitUntil: "load",
  });

  const snapshot = await page.evaluate(
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );
  const extraction = extractAcademicPageFromTables({
    ...snapshot,
    title: "Course Catalog",
    url: "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/Search?searchResultsView=SectionListing&terms=2026FA",
  });

  expect(snapshot.tables[0]?.headers).toEqual([
    "",
    "Term",
    "Status",
    "Section Name",
    "Title",
    "",
    "Dates",
    "Location",
    "Instructional Methods",
    "Meetings",
    "Faculty",
    "Availability",
    "Credits",
    "Course Types",
  ]);
  expect(snapshot.tables[0]?.rows[0]?.[0]).toBe("");
  expect(snapshot.tables[0]?.rows[0]?.[5]).toBe("");
  expect(extraction.pageType).toBe("KEAN_SECTION_SEARCH_PAGE");
  expect(extraction.importType).toBe("SECTION_SCHEDULE");
  expect(extraction.records).toHaveLength(2);
  expect(extraction.records[0]).toMatchObject({
    term_code: "2026FA",
    term_label: "Fall 2026",
    course_code: "MOCK 1234",
    section_code: "01",
    course_title: "Explainable Systems",
    component: "LECTURE_LAB",
    modality: "LECTURE",
    status: "OPEN",
    meeting_days: "MONDAY,WEDNESDAY",
    start_time: "09:00",
    end_time: "10:15",
    location: "Mock Hall 101 (Main)",
    instructor_display: "Mock Instructor",
    external_reference: "",
    crn_source_status: "NOT_PROVIDED",
    validation_state: "AUTO_VERIFIED",
  });
  expect(JSON.parse(extraction.records[0]?.meetings_json ?? "[]")).toHaveLength(
    2,
  );
  expect(extraction.records[1]).toMatchObject({
    course_code: "MOCK 2345",
    section_code: "ON01",
    modality: "ONLINE",
    location: "ONLINE",
  });
  expect(
    JSON.parse(extraction.records[1]?.meetings_json ?? "[]")[0],
  ).toMatchObject({ is_async: true, is_tba: false, is_arranged: false });
  expect(extraction.warnings.map((warning) => warning.code)).toEqual(
    expect.arrayContaining(["SECTION_DUPLICATE_VISIBLE_ROW"]),
  );
  expect(extraction.warnings.map((warning) => warning.code)).not.toContain(
    "KEAN_SECTION_CRN_MISSING",
  );
});

test("discovers public Catalog subjects and starts only the visible read-only Catalog search", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    (
      window as Window & {
        capturedCatalogAction?: object;
        catalogSearchResultsView?: string;
        ko?: { contextFor: (element: Element) => object | null };
      }
    ).capturedCatalogAction = undefined;
    (
      window as Window & {
        ko?: { contextFor: (element: Element) => object | null };
      }
    ).ko = { contextFor: () => ({}) };
    (
      window as Window & { catalogSearchResultsView?: string }
    ).catalogSearchResultsView = "SectionListing";
    document
      .querySelector("#course-catalog-result-view-type-course")
      ?.addEventListener("click", () => {
        (
          window as Window & { catalogSearchResultsView?: string }
        ).catalogSearchResultsView = "CatalogListing";
      });
    document
      .querySelector("#submit-search-form")
      ?.addEventListener("click", () => {
        const subject = document.querySelector<HTMLSelectElement>("#subject-0");
        const resultView = document.querySelector<HTMLInputElement>(
          "#course-catalog-result-view-type-course",
        );
        (
          window as Window & { capturedCatalogAction?: object }
        ).capturedCatalogAction = {
          subject: subject?.value,
          resultView: resultView?.value,
          checked: resultView?.checked,
          viewModel: (window as Window & { catalogSearchResultsView?: string })
            .catalogSearchResultsView,
        };
      });
  });

  const discovery = await page.evaluate(discoverCatalogSubjects, landingUrl);
  expect(discovery).toEqual({
    landingUrl,
    subjects: [
      { code: "ACCT", label: "Accounting" },
      { code: "FIN", label: "Finance" },
      { code: "MATH", label: "Mathematics" },
    ],
    providerActionsWritten: "NO",
  });

  expect(
    await page.evaluate(
      () =>
        (window as Window & { capturedCatalogAction?: object })
          .capturedCatalogAction,
    ),
  ).toBeUndefined();

  await page.evaluate(() => {
    const form = document.querySelector<HTMLFormElement>("#search-form");
    if (form) form.method = "post";
  });
  await expect(
    page.evaluate(prepareCatalogSubjectSearch, {
      expectedUrl: landingUrl,
      subjectCode: "FIN",
    }),
  ).rejects.toThrow("BATCH_CATALOG_PARSER_DRIFT");
  await page.evaluate(() => {
    const form = document.querySelector<HTMLFormElement>("#search-form");
    if (form) form.method = "get";
  });

  const action = await page.evaluate(prepareCatalogSubjectSearch, {
    expectedUrl: landingUrl,
    subjectCode: "FIN",
  });
  expect(action).toEqual({
    action: "CATALOG_SEARCH_PREPARED",
    subjectCode: "FIN",
    completedCheckpoints: [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
    ],
    providerActionsWritten: "NO",
  });
  expect(
    await page.evaluate(
      () =>
        (window as Window & { capturedCatalogAction?: object })
          .capturedCatalogAction,
    ),
  ).toBeUndefined();
  expect(
    await page.evaluate(
      () =>
        (window as Window & { capturedCatalogAction?: object })
          .capturedCatalogAction,
    ),
  ).toBeUndefined();
  expect(await page.evaluate(() => document.activeElement?.id)).toBe(
    "submit-search-form",
  );
});

test("waits for delayed Kean Knockout bindings before preparing the Catalog search", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    const target = window as Window & {
      capturedCatalogAction?: object;
      catalogSearchResultsView?: string;
      ko?: { contextFor: (element: Element) => object | null };
    };
    target.catalogSearchResultsView = "SectionListing";
    target.ko = { contextFor: () => null };
    window.setTimeout(() => {
      target.ko = { contextFor: () => ({}) };
      document
        .querySelector("#course-catalog-result-view-type-course")
        ?.addEventListener("click", () => {
          target.catalogSearchResultsView = "CatalogListing";
        });
      document
        .querySelector("#submit-search-form")
        ?.addEventListener("click", () => {
          const subject =
            document.querySelector<HTMLSelectElement>("#subject-0");
          target.capturedCatalogAction = {
            subject: subject?.value,
            viewModel: target.catalogSearchResultsView,
          };
        });
    }, 100);
  });

  const request = {
    expectedUrl: landingUrl,
    subjectCode: "FIN",
    readyTimeoutMs: 600,
    settleMs: 80,
  };
  await page.evaluate(prepareCatalogSubjectSearch, request);
  // The fixture deliberately binds at 100 ms; 250 ms covers that known delay
  // plus the requested 80 ms stable-ready window.
  await page.waitForTimeout(250);

  expect(
    await page.evaluate(() => ({
      subject: document.querySelector<HTMLSelectElement>("#subject-0")?.value,
      viewModel: (window as Window & { catalogSearchResultsView?: string })
        .catalogSearchResultsView,
      submitted: (window as Window & { capturedCatalogAction?: object })
        .capturedCatalogAction,
    })),
  ).toEqual({
    subject: "FIN",
    viewModel: "CatalogListing",
    submitted: undefined,
  });
});

test("reacquires Catalog controls rebuilt after selecting the next subject", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    const target = window as Window & {
      capturedCatalogAction?: object;
      catalogSearchResultsView?: string;
      catalogControlsRebuilt?: boolean;
      boundCatalogControls?: WeakSet<Element>;
      ko?: { contextFor: (element: Element) => object | null };
    };
    target.catalogSearchResultsView = "SectionListing";
    target.catalogControlsRebuilt = false;
    target.boundCatalogControls = new WeakSet<Element>();
    document
      .querySelector<HTMLSelectElement>("#subject-0")
      ?.setAttribute("data-bind", "value: selectedSubject");

    const bindCurrentControls = (): void => {
      const subject = document.querySelector<HTMLSelectElement>("#subject-0");
      const catalogView = document.querySelector<HTMLInputElement>(
        "#course-catalog-result-view-type-course",
      );
      const submit = document.querySelector<HTMLInputElement>(
        "#submit-search-form",
      );
      if (!subject || !catalogView || !submit) return;
      target.boundCatalogControls?.add(subject);
      target.boundCatalogControls?.add(catalogView);
      target.boundCatalogControls?.add(submit);
      catalogView.addEventListener("click", (event) => {
        if (!(event.currentTarget as Element).isConnected) return;
        target.catalogSearchResultsView = "CatalogListing";
      });
      submit.addEventListener("click", (event) => {
        if (!(event.currentTarget as Element).isConnected) return;
        const currentSubject =
          document.querySelector<HTMLSelectElement>("#subject-0");
        target.capturedCatalogAction = {
          subject: currentSubject?.value,
          viewModel: target.catalogSearchResultsView,
        };
      });
    };

    target.ko = {
      contextFor: (element) =>
        element.isConnected && target.boundCatalogControls?.has(element)
          ? {}
          : null,
    };
    bindCurrentControls();

    document
      .querySelector<HTMLSelectElement>("#subject-0")
      ?.addEventListener("input", () => {
        if (target.catalogControlsRebuilt) return;
        target.catalogControlsRebuilt = true;
        const subject = document.querySelector<HTMLSelectElement>("#subject-0");
        const catalogView = document.querySelector<HTMLInputElement>(
          "#course-catalog-result-view-type-course",
        );
        const submit = document.querySelector<HTMLInputElement>(
          "#submit-search-form",
        );
        if (!subject || !catalogView || !submit) return;
        const nextSubject = subject.cloneNode(true) as HTMLSelectElement;
        nextSubject.value = "";
        const nextCatalogView = catalogView.cloneNode(true) as HTMLInputElement;
        nextCatalogView.checked = false;
        const nextSubmit = submit.cloneNode(true) as HTMLInputElement;
        subject.replaceWith(nextSubject);
        catalogView.replaceWith(nextCatalogView);
        submit.replaceWith(nextSubmit);
        window.setTimeout(bindCurrentControls, 100);
      });
  });

  await page.evaluate(prepareCatalogSubjectSearch, {
    expectedUrl: landingUrl,
    subjectCode: "FIN",
    readyTimeoutMs: 1_000,
    settleMs: 80,
  });

  await expect
    .poll(() =>
      page.evaluate(() => ({
        subject: document.querySelector<HTMLSelectElement>("#subject-0")?.value,
        viewModel: (window as Window & { catalogSearchResultsView?: string })
          .catalogSearchResultsView,
        submitted: (window as Window & { capturedCatalogAction?: object })
          .capturedCatalogAction,
      })),
    )
    .toEqual({
      subject: "FIN",
      viewModel: "CatalogListing",
      submitted: undefined,
    });
});

test("persists the reviewed preparation checkpoint before one MAIN-world search click", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    const target = window as Window & {
      capturedCatalogAction?: object;
      catalogCheckpointEvents: string[];
      catalogSearchResultsView?: string;
      chrome?: {
        runtime?: {
          lastError?: { message?: string };
          sendMessage: (
            message: unknown,
            callback?: (response: unknown) => void,
          ) => void;
        };
      };
      ko?: { contextFor: (element: Element) => object | null };
    };
    target.catalogSearchResultsView = "SectionListing";
    target.catalogCheckpointEvents = [];
    target.ko = { contextFor: () => ({}) };
    target.chrome = {
      runtime: {
        sendMessage: (message, callback) => {
          if (message && typeof message === "object" && "signal" in message) {
            target.catalogCheckpointEvents.push(String(message.signal));
          }
          callback?.({ ok: true });
        },
      },
    };
    document
      .querySelector("#course-catalog-result-view-type-course")
      ?.addEventListener("click", () => {
        target.catalogSearchResultsView = "CatalogListing";
      });
    document
      .querySelector("#submit-search-form")
      ?.addEventListener("click", () => {
        target.catalogCheckpointEvents.push("SEARCH_SUBMITTED");
        target.capturedCatalogAction = {
          submittedSubject:
            document.querySelector<HTMLSelectElement>("#subject-0")?.value,
          resultView: target.catalogSearchResultsView,
        };
      });
  });

  const checkpointToken = "bounded-main-world-checkpoint:7";
  await page.evaluate(watchCatalogSubjectNavigation, {
    expectedUrl: landingUrl,
    expectedSubject: "FIN",
    batchId: "bounded-main-world-checkpoint",
    navigationRevision: 7,
    checkpointToken,
    timeoutMs: 400,
  } as Parameters<typeof watchCatalogSubjectNavigation>[0] & {
    expectedSubject: string;
    checkpointToken: string;
  });
  const action = await page.evaluate(prepareCatalogSubjectSearch, {
    expectedUrl: landingUrl,
    subjectCode: "FIN",
    readyTimeoutMs: 1_000,
    settleMs: 80,
    submitCheckpoint: {
      batchId: "bounded-main-world-checkpoint",
      navigationRevision: 7,
      checkpointToken,
      acknowledgmentTimeoutMs: 500,
    },
  } as Parameters<typeof prepareCatalogSubjectSearch>[0] & {
    submitCheckpoint: {
      batchId: string;
      navigationRevision: number;
      checkpointToken: string;
      acknowledgmentTimeoutMs: number;
    };
  });

  expect(action).toEqual({
    action: "CATALOG_SEARCH_PREPARED_AND_SUBMITTED",
    subjectCode: "FIN",
    completedCheckpoints: [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
      "SEARCH_SUBMITTED",
    ],
    providerActionsWritten: "NO",
  });
  // The fixture intentionally has no result list. A later navigation timeout
  // must not overwrite the independently observed search click.
  await expect
    .poll(() =>
      page.evaluate(() =>
        (
          window as Window & { catalogCheckpointEvents: string[] }
        ).catalogCheckpointEvents.includes("TIMEOUT"),
      ),
    )
    .toBe(true);
  expect(
    await page.evaluate(() =>
      (
        window as Window & { catalogCheckpointEvents: string[] }
      ).catalogCheckpointEvents.filter((event) => event !== "TIMEOUT"),
    ),
  ).toEqual(["PREPARATION_VERIFIED", "SEARCH_SUBMITTED"]);
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as Window & { capturedCatalogAction?: object })
            .capturedCatalogAction,
      ),
    )
    .toEqual({ submittedSubject: "FIN", resultView: "CatalogListing" });
});

test("does not click Search when the preparation checkpoint is not acknowledged", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    const target = window as Window & {
      submittedCatalogSearchCount?: number;
      ko?: { contextFor: (element: Element) => object | null };
    };
    target.submittedCatalogSearchCount = 0;
    target.ko = { contextFor: () => ({}) };
    document
      .querySelector("#submit-search-form")
      ?.addEventListener("click", () => {
        target.submittedCatalogSearchCount =
          (target.submittedCatalogSearchCount ?? 0) + 1;
      });
  });

  await expect(
    page.evaluate(prepareCatalogSubjectSearch, {
      expectedUrl: landingUrl,
      subjectCode: "FIN",
      readyTimeoutMs: 1_000,
      settleMs: 80,
      submitCheckpoint: {
        batchId: "bounded-missing-checkpoint-ack",
        navigationRevision: 3,
        checkpointToken: "bounded-missing-checkpoint-ack:3:FIN",
        acknowledgmentTimeoutMs: 80,
      },
    }),
  ).rejects.toThrow("BATCH_CATALOG_PREPARATION_SIGNAL_TIMEOUT");
  expect(
    await page.evaluate(
      () =>
        (window as Window & { submittedCatalogSearchCount?: number })
          .submittedCatalogSearchCount,
    ),
  ).toBe(0);
});

test("emits a revisioned timeout when subject navigation remains on the Catalog landing page", async ({
  page,
}) => {
  const landingUrl =
    "https://kean-ss.colleague.elluciancloud.com/Student/Courses";
  await page.route(landingUrl, async (route) => {
    await route.fulfill({
      body: readFileSync(catalogSearchFixturePath, "utf8"),
      contentType: "text/html",
    });
  });
  await page.goto(landingUrl);
  await page.evaluate(() => {
    const target = window as Window & {
      chrome?: {
        runtime?: {
          lastError?: { message?: string };
          sendMessage: (message: unknown, callback?: () => void) => void;
        };
      };
      capturedSubjectNavigationSignal?: unknown;
    };
    target.chrome ??= {};
    target.chrome.runtime = {
      sendMessage: (message, callback) => {
        target.capturedSubjectNavigationSignal = message;
        callback?.();
      },
    };
  });

  expect(
    await page.evaluate(watchCatalogSubjectNavigation, {
      expectedUrl: landingUrl,
      expectedSubject: "FIN",
      batchId: "bounded-navigation-timeout",
      navigationRevision: 7,
      checkpointToken: "bounded-navigation-timeout:7:FIN",
      timeoutMs: 80,
    }),
  ).toEqual({
    action: "CATALOG_SUBJECT_NAVIGATION_WATCH_STARTED",
    providerActionsWritten: "NO",
  });
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (
            window as Window & {
              capturedSubjectNavigationSignal?: unknown;
            }
          ).capturedSubjectNavigationSignal,
      ),
    )
    .toEqual({
      type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
      batchId: "bounded-navigation-timeout",
      navigationRevision: 7,
      signal: "TIMEOUT",
      currentPath: "/Student/Courses",
      subjectCode: "FIN",
      diagnostics: {
        documentReady: true,
        subjectControlPresent: true,
        expectedSubjectSelected: false,
        catalogListingControlPresent: true,
        catalogListingChecked: false,
        submitControlPresent: true,
        submitControlEnabled: true,
        preparationSignalObserved: false,
        resultSurfacePresent: false,
        resultListPresent: false,
        courseCardCount: 0,
        validCourseIdentityCount: 0,
        sectionResultPresent: false,
      },
      providerActionsWritten: "NO",
    });
});

test("inspects and advances only explicit Catalog result pagination", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await page.evaluate(() => {
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Link to results page 2"]',
      )
      ?.addEventListener("click", () => {
        const current = document.querySelector<HTMLInputElement>(
          "#course-results-current-page",
        );
        const list = document.querySelector("#course-resultul");
        if (current) current.value = "2";
        if (list) {
          list.innerHTML =
            '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
            '<li><span id="course-FIN-3300">FIN*3300</span></li>';
        }
      });
  });

  expect(await page.evaluate(inspectCatalogResultPage, resultUrl)).toEqual({
    ready: true,
    pageNumber: 1,
    totalPages: 2,
    visibleCourseCount: 2,
    subjectCode: "FIN",
    firstCourseMarker: "course-FIN-1300",
    lastCourseMarker: "course-FIN-1400",
    resultFingerprint: "course-FIN-1300\u001fcourse-FIN-1400",
    fatalSignal: null,
    providerActionsWritten: "NO",
  });
  expect(
    await page.evaluate(advanceCatalogResultPage, {
      expectedUrl: resultUrl,
      targetPage: 2,
    }),
  ).toEqual({
    action: "CATALOG_PAGE_REQUESTED",
    targetPage: 2,
    previousFirstCourseMarker: "course-FIN-1300",
    previousResultFingerprint: "course-FIN-1300\u001fcourse-FIN-1400",
    providerActionsWritten: "NO",
  });
  expect(
    await page.evaluate(inspectCatalogResultPage, resultUrl),
  ).toMatchObject({
    ready: true,
    pageNumber: 2,
    totalPages: 2,
    firstCourseMarker: "course-FIN-2300",
    lastCourseMarker: "course-FIN-3300",
    resultFingerprint: "course-FIN-2300\u001fcourse-FIN-3300",
  });

  await page
    .locator("#course-resultul")
    .evaluate((element) => element.remove());
  expect(
    await page.evaluate(inspectCatalogResultPage, resultUrl),
  ).toMatchObject({
    ready: false,
    errorCode: "BATCH_CATALOG_PARSER_DRIFT",
    providerActionsWritten: "NO",
  });

  await page.setContent(
    '<main><div role="grid" aria-label="Table for sections"></div></main>',
  );
  await page.evaluate(
    (url) => window.history.replaceState({}, "", url),
    resultUrl,
  );
  expect(
    await page.evaluate(inspectCatalogResultPage, resultUrl),
  ).toMatchObject({
    ready: false,
    errorCode: "BATCH_CATALOG_RESULT_VIEW_MISMATCH",
    providerActionsWritten: "NO",
  });
});

test("accepts a stable first Catalog page when Kean omits the current-page input", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.locator("#course-results-current-page").evaluate((element) => {
    element.previousElementSibling?.remove();
    element.remove();
  });

  const firstPageWatch = {
    expectedUrl: resultUrl,
    batchId: "bounded-first-page-without-input",
    expectedPage: 1,
    expectedSubject: "FIN",
    navigationRevision: 7,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 400,
    settleMs: 50,
  } as Parameters<typeof watchCatalogResultPage>[0] & {
    expectedSubject: string;
    navigationRevision: number;
    runnerRevision: string;
  };
  await page.evaluate(watchCatalogResultPage, firstPageWatch);

  await expect
    .poll(() => waitForCatalogSignal(page))
    .toMatchObject({
      signal: "READY",
      pageNumber: 1,
      totalPages: 2,
      visibleCourseCount: 2,
      subjectCode: "FIN",
      firstCourseMarker: "course-FIN-1300",
      lastCourseMarker: "course-FIN-1400",
      navigationRevision: 7,
      diagnostics: {
        expectedSubject: "FIN",
        expectedPage: 1,
        searchResultUrlMatch: true,
        courseResultContainerPresent: true,
        courseCardCount: 2,
        visibleSubject: "FIN",
        visibleSubjectSource: "COURSE_CARD_ID",
        pageNumber: 1,
        pageNumberSource: "FIRST_PAGE_STRUCTURE",
        spinnerVisible: false,
        domStable: true,
        contentScriptRevision: "phase15b-main-world-checkpoint-v9",
        runnerRevision: "phase15b-main-world-checkpoint-v9",
        expectedRevision: 7,
        pageReadyGateFailedOn: null,
        currentPageTimeoutRootCause: null,
      },
    });
});

test("uses the one visible Catalog result tree when a hidden duplicate is stale", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    const visibleSurface =
      document.querySelector<HTMLElement>("#course-results");
    if (!visibleSurface)
      throw new Error("Missing visible Catalog result surface");
    const hiddenSurface = visibleSurface.cloneNode(true) as HTMLElement;
    hiddenSurface.style.display = "none";
    for (const marker of hiddenSurface.querySelectorAll<HTMLElement>(
      'span[id^="course-"]',
    )) {
      marker.id = marker.id.replace("course-FIN-", "course-ACCT-");
    }
    visibleSurface.before(hiddenSurface);
  });

  expect(
    await page.evaluate(inspectCatalogResultPage, resultUrl),
  ).toMatchObject({
    ready: true,
    pageNumber: 1,
    subjectCode: "FIN",
    visibleCourseCount: 2,
  });
  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "visible-result-tree-only",
    expectedPage: 1,
    expectedSubject: "FIN",
    navigationRevision: 8,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 400,
    settleMs: 50,
  });

  await expect
    .poll(() => waitForCatalogSignal(page))
    .toMatchObject({
      signal: "READY",
      pageNumber: 1,
      subjectCode: "FIN",
      navigationRevision: 8,
      providerActionsWritten: "NO",
    });
});

test("rejects a stable Catalog page-number mismatch with a specific signal", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-page-number-mismatch",
    expectedPage: 2,
    expectedSubject: "FIN",
    navigationRevision: 2,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: "course-previous-page-marker",
    previousResultFingerprint: "previous-page-fingerprint",
    timeoutMs: 180,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "PAGE_NUMBER_MISMATCH",
    pageNumber: 1,
    diagnostics: {
      expectedPage: 2,
      pageNumber: 1,
      pageReadyGateFailedOn: "EXPECTED_PAGE_MATCH",
      failedPredicate: "PAGE_NUMBER_MISMATCH",
      currentPageTimeoutRootCause: "PAGE_NUMBER_MISMATCH",
    },
    providerActionsWritten: "NO",
  });
});

test("accepts 30 stable page-1 cards without a page-world Knockout context or visible subject marker", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    const list = document.querySelector<HTMLElement>("#course-resultul");
    const results = document.querySelector<HTMLElement>("#course-results");
    if (!list || !results) throw new Error("Missing Catalog result fixture");

    list.setAttribute("data-bind", "foreach: catalogResults");
    list.innerHTML = Array.from({ length: 30 }, (_, index) => {
      const courseNumber = 2200 + index;
      return `<li><span id="course-card${String(index + 1).padStart(2, "0")}">Catalog course ${index + 1}</span><h3>ACCT*${courseNumber} Catalog course ${index + 1} (3 Credits)</h3></li>`;
    }).join("");
    const spinner = document.createElement("div");
    spinner.className = "esg-spinner-container";
    spinner.textContent = "Catalog loading indicator";
    results.append(spinner);
    Reflect.deleteProperty(globalThis, "ko");
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-real-page1-30-card-regression",
    expectedPage: 1,
    expectedSubject: "ACCT",
    navigationRevision: 9,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 400,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "READY",
    pageNumber: 1,
    visibleCourseCount: 30,
    subjectCode: "ACCT",
    navigationRevision: 9,
    diagnostics: {
      visibleSubject: null,
      visibleSubjectSource: "CHECKPOINT_BOUND",
      courseCardCount: 30,
      validCourseIdentityCount: 30,
      knockoutReady: false,
      spinnerPresent: true,
      spinnerVisible: true,
      spinnerHardGateValid: false,
      spinnerClassification: "NON_BLOCKING",
      domStable: true,
      contentStable: true,
      contentScriptRevision: "phase15b-main-world-checkpoint-v9",
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      pageReadyGateFailedOn: null,
      failedPredicate: null,
    },
    providerActionsWritten: "NO",
  });
  expect(
    await page.evaluate(inspectCatalogResultPage, {
      expectedUrl: resultUrl,
      expectedSubject: "ACCT",
    }),
  ).toMatchObject({
    ready: true,
    pageNumber: 1,
    visibleCourseCount: 30,
    subjectCode: "ACCT",
    resultFingerprint: signal.resultFingerprint,
    providerActionsWritten: "NO",
  });
});

test("keeps rendered Catalog markers without a parseable course identity not ready", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    const list = document.querySelector<HTMLElement>("#course-resultul");
    if (!list) throw new Error("Missing Catalog result list");
    list.innerHTML = Array.from(
      { length: 30 },
      (_, index) =>
        `<li><span id="course-card${String(index + 1).padStart(2, "0")}">Unparseable Catalog card ${index + 1}</span></li>`,
    ).join("");
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-unparseable-identities",
    expectedPage: 1,
    expectedSubject: "ACCT",
    navigationRevision: 10,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 180,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    diagnostics: {
      courseCardCount: 30,
      validCourseIdentityCount: 0,
      contentStable: false,
      failedPredicate: "VALID_COURSE_IDENTITY_COUNT_ZERO",
      currentPageTimeoutRootCause: "VALID_COURSE_IDENTITY_COUNT_ZERO",
    },
    providerActionsWritten: "NO",
  });
});

test("keeps an empty Catalog result payload not ready even when its spinner is visible", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    const list = document.querySelector<HTMLElement>("#course-resultul");
    const results = document.querySelector<HTMLElement>("#course-results");
    if (!list || !results) throw new Error("Missing Catalog result fixture");
    list.replaceChildren();
    results.setAttribute("aria-busy", "true");
    const spinner = document.createElement("div");
    spinner.className = "esg-spinner-container";
    spinner.setAttribute("aria-busy", "true");
    spinner.textContent = "Loading Catalog results";
    results.append(spinner);
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-zero-card-regression",
    expectedPage: 1,
    expectedSubject: "ACCT",
    navigationRevision: 10,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 180,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    diagnostics: {
      courseResultContainerPresent: true,
      courseCardCount: 0,
      spinnerPresent: true,
      spinnerVisible: true,
      spinnerHardGateValid: true,
      spinnerClassification: "BLOCKING",
      domStable: false,
      pageReadyGateFailedOn: "COURSE_CARD_COUNT",
      failedPredicate: "COURSE_CARD_COUNT_ZERO",
      currentPageTimeoutRootCause: "COURSE_CARD_COUNT_ZERO",
    },
    providerActionsWritten: "NO",
  });
});

test("keeps changing Catalog identities not ready until the bounded timeout", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.clock.install();
  await page.evaluate(() => {
    const list = document.querySelector<HTMLElement>("#course-resultul");
    if (!list) throw new Error("Missing Catalog result list");
    let revision = 0;
    window.setInterval(() => {
      revision += 1;
      list.innerHTML =
        '<li><span id="course-FIN-1300">FIN*1300</span></li>' +
        `<li><span id="course-FIN-${1400 + revision}">FIN changing course</span></li>`;
    }, 25);
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-changing-fingerprint",
    expectedPage: 1,
    expectedSubject: "FIN",
    navigationRevision: 11,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 180,
    settleMs: 80,
  });
  await page.clock.runFor(180);
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    diagnostics: {
      courseCardCount: 2,
      domStable: false,
      pageReadyGateFailedOn: "DOM_STABLE",
      contentStable: false,
      failedPredicate: "CONTENT_FINGERPRINT_UNSTABLE",
      currentPageTimeoutRootCause: "CONTENT_FINGERPRINT_UNSTABLE",
    },
    providerActionsWritten: "NO",
  });
});

test("requires one connected result container for the full content stability window", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  // Drive replacement and readiness timers deterministically under CPU load.
  await page.clock.install();
  await page.evaluate(() => {
    const results = document.querySelector<HTMLElement>("#course-results");
    if (!results) throw new Error("Missing Catalog result surface");
    window.setInterval(() => {
      const list = document.querySelector<HTMLElement>("#course-resultul");
      if (!list) return;
      const replacement = list.cloneNode(true);
      list.replaceWith(replacement);
    }, 35);
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-connected-container-stability",
    expectedPage: 1,
    expectedSubject: "FIN",
    navigationRevision: 12,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 220,
    settleMs: 90,
  });
  await page.clock.runFor(220);
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    diagnostics: {
      courseCardCount: 2,
      validCourseIdentityCount: 2,
      contentStable: false,
      failedPredicate: "CONTENT_FINGERPRINT_UNSTABLE",
      currentPageTimeoutRootCause: "CONTENT_FINGERPRINT_UNSTABLE",
    },
    providerActionsWritten: "NO",
  });
});

test("emits a provider-error signal instead of capturing an error page", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    const alert = document.createElement("div");
    alert.className = "esg-alert";
    alert.setAttribute("role", "alert");
    alert.textContent = "Something went wrong while loading the Catalog.";
    document.querySelector("main")?.prepend(alert);
  });

  await page.evaluate(watchCatalogResultPage, {
    expectedUrl: resultUrl,
    batchId: "bounded-provider-error",
    expectedPage: 1,
    expectedSubject: "FIN",
    navigationRevision: 12,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    previousFirstCourseMarker: null,
    timeoutMs: 300,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "PROVIDER_ERROR",
    diagnostics: {
      pageReadyGateFailedOn: "PROVIDER_ERROR",
      failedPredicate: "PROVIDER_ERROR",
    },
    providerActionsWritten: "NO",
  });
});

for (const updateOrder of ["ACTIVE_PAGE_FIRST", "CARDS_FIRST"] as const) {
  test(`waits for a stable same-URL Catalog transition when ${updateOrder.toLowerCase()} updates`, async ({
    page,
  }) => {
    const resultUrl = await openCatalogPaginationFixture(page);
    await installCatalogSignalCapture(page);
    await page.evaluate((order) => {
      document
        .querySelector<HTMLButtonElement>(
          'button[aria-label="Link to results page 2"]',
        )
        ?.addEventListener("click", () => {
          const current = document.querySelector<HTMLInputElement>(
            "#course-results-current-page",
          );
          const list = document.querySelector("#course-resultul");
          if (!current || !list) return;
          if (order === "ACTIVE_PAGE_FIRST") {
            current.value = "2";
            window.setTimeout(() => {
              list.innerHTML =
                '<li><span id="course-FIN-2300">FIN*2300</span></li>';
            }, 10);
            window.setTimeout(() => {
              list.innerHTML =
                '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
                '<li><span id="course-FIN-3300">FIN*3300</span></li>';
            }, 40);
            return;
          }
          list.innerHTML =
            '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
            '<li><span id="course-FIN-3300">FIN*3300</span></li>';
          window.setTimeout(() => {
            current.value = "2";
          }, 40);
        });
    }, updateOrder);

    await page.evaluate(advanceCatalogResultPage, {
      expectedUrl: resultUrl,
      targetPage: 2,
      batchId: "bounded-real-regression",
      timeoutMs: 800,
      settleMs: 80,
    });
    const signal = await waitForCatalogSignal(page);

    expect(page.url()).toBe(resultUrl);
    expect(signal).toMatchObject({
      signal: "READY",
      pageNumber: 2,
      totalPages: 2,
      visibleCourseCount: 2,
      subjectCode: "FIN",
      firstCourseMarker: "course-FIN-2300",
      lastCourseMarker: "course-FIN-3300",
      resultFingerprint: "course-FIN-2300\u001fcourse-FIN-3300",
    });
  });
}

test("accepts a stable next page when the first card stays the same but the remaining set changes", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Link to results page 2"]',
      )
      ?.addEventListener("click", () => {
        const current = document.querySelector<HTMLInputElement>(
          "#course-results-current-page",
        );
        const list = document.querySelector("#course-resultul");
        if (current) current.value = "2";
        if (list) {
          list.innerHTML =
            '<li><span id="course-FIN-1300">FIN*1300</span></li>' +
            '<li><span id="course-FIN-3300">FIN*3300</span></li>';
        }
      });
  });

  await page.evaluate(advanceCatalogResultPage, {
    expectedUrl: resultUrl,
    targetPage: 2,
    batchId: "bounded-same-first-card",
    timeoutMs: 800,
    settleMs: 80,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "READY",
    pageNumber: 2,
    visibleCourseCount: 2,
    subjectCode: "FIN",
    firstCourseMarker: "course-FIN-1300",
    lastCourseMarker: "course-FIN-3300",
    resultFingerprint: "course-FIN-1300\u001fcourse-FIN-3300",
  });
});

test("does not emit a ready checkpoint while the result-level loading surface is visible", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Link to results page 2"]',
      )
      ?.addEventListener("click", () => {
        const current = document.querySelector<HTMLInputElement>(
          "#course-results-current-page",
        );
        const list = document.querySelector("#course-resultul");
        const results = document.querySelector("#course-results");
        if (!current || !list || !results) return;
        current.value = "2";
        list.innerHTML =
          '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
          '<li><span id="course-FIN-3300">FIN*3300</span></li>';
        const loading = document.createElement("div");
        loading.className = "esg-spinner-container";
        loading.setAttribute("aria-busy", "true");
        loading.textContent = "Updating Catalog results...";
        results.setAttribute("aria-busy", "true");
        results.append(loading);
        window.setTimeout(() => {
          loading.remove();
          results.setAttribute("aria-busy", "false");
        }, 150);
      });
  });

  await page.evaluate(advanceCatalogResultPage, {
    expectedUrl: resultUrl,
    targetPage: 2,
    batchId: "bounded-result-loading",
    timeoutMs: 600,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal.signal).toBe("READY");
  expect(
    await page.locator("#course-results > .esg-spinner-container").count(),
  ).toBe(0);
});

test("accepts a stable next page while a class-only Catalog spinner remains visible", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Link to results page 2"]',
      )
      ?.addEventListener("click", () => {
        const current = document.querySelector<HTMLInputElement>(
          "#course-results-current-page",
        );
        const list = document.querySelector("#course-resultul");
        const results = document.querySelector("#course-results");
        if (!current || !list || !results) return;
        current.value = "2";
        list.innerHTML =
          '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
          '<li><span id="course-FIN-3300">FIN*3300</span></li>';
        const spinner = document.createElement("div");
        spinner.className = "esg-spinner-container";
        spinner.textContent = "Persistent Catalog loading indicator";
        results.append(spinner);
      });
  });

  await page.evaluate(advanceCatalogResultPage, {
    expectedUrl: resultUrl,
    targetPage: 2,
    batchId: "bounded-class-only-spinner",
    expectedSubject: "FIN",
    navigationRevision: 10,
    runnerRevision: "phase15b-main-world-checkpoint-v9",
    timeoutMs: 300,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "READY",
    pageNumber: 2,
    subjectCode: "FIN",
    diagnostics: {
      spinnerPresent: true,
      spinnerVisible: true,
      spinnerHardGateValid: false,
      domStable: true,
      pageReadyGateFailedOn: null,
    },
    providerActionsWritten: "NO",
  });
});

for (const pageMarkerState of ["MISSING", "MISMATCHED"] as const) {
  test(`keeps page 2 not ready when its current-page marker is ${pageMarkerState.toLowerCase()}`, async ({
    page,
  }) => {
    const resultUrl = await openCatalogPaginationFixture(page);
    await installCatalogSignalCapture(page);
    await page.evaluate((markerState) => {
      document
        .querySelector<HTMLButtonElement>(
          'button[aria-label="Link to results page 2"]',
        )
        ?.addEventListener("click", () => {
          const current = document.querySelector<HTMLInputElement>(
            "#course-results-current-page",
          );
          const list = document.querySelector("#course-resultul");
          if (!current || !list) return;
          list.innerHTML =
            '<li><span id="course-FIN-2300">FIN*2300</span></li>' +
            '<li><span id="course-FIN-3300">FIN*3300</span></li>';
          if (markerState === "MISSING") current.remove();
          else current.value = "1";
        });
    }, pageMarkerState);

    await page.evaluate(advanceCatalogResultPage, {
      expectedUrl: resultUrl,
      targetPage: 2,
      batchId: `bounded-page-marker-${pageMarkerState.toLowerCase()}`,
      expectedSubject: "FIN",
      navigationRevision: 13,
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      timeoutMs: 200,
      settleMs: 50,
    });
    const signal = await waitForCatalogSignal(page);

    expect(signal).toMatchObject({
      signal: "TIMEOUT",
      diagnostics: {
        pageReadyGateFailedOn:
          pageMarkerState === "MISSING"
            ? "PAGE_NUMBER_AVAILABLE"
            : "EXPECTED_PAGE_MATCH",
        failedPredicate: "PAGE_NUMBER_MISMATCH",
        currentPageTimeoutRootCause: "PAGE_NUMBER_MISMATCH",
      },
      providerActionsWritten: "NO",
    });
  });
}

test("does not treat a reordered page-1 identity set as a new Catalog page", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);
  await page.evaluate(() => {
    document
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Link to results page 2"]',
      )
      ?.addEventListener("click", () => {
        const current = document.querySelector<HTMLInputElement>(
          "#course-results-current-page",
        );
        const list = document.querySelector("#course-resultul");
        if (current) current.value = "2";
        if (list) {
          list.innerHTML =
            '<li><span id="course-FIN-1400">FIN*1400</span></li>' +
            '<li><span id="course-FIN-1300">FIN*1300</span></li>';
        }
      });
  });

  await page.evaluate(advanceCatalogResultPage, {
    expectedUrl: resultUrl,
    targetPage: 2,
    batchId: "bounded-reordered-stale-page",
    timeoutMs: 180,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    pageNumber: null,
    resultFingerprint: null,
    diagnostics: {
      pageReadyGateFailedOn: "PAGE_FINGERPRINT_CHANGED",
      failedPredicate: "PREVIOUS_PAGE_FINGERPRINT_UNCHANGED",
      currentPageTimeoutRootCause: "PREVIOUS_PAGE_FINGERPRINT_UNCHANGED",
    },
  });
});

test("stops with a bounded timeout when the visible page remains stale page 1", async ({
  page,
}) => {
  const resultUrl = await openCatalogPaginationFixture(page);
  await installCatalogSignalCapture(page);

  await page.evaluate(advanceCatalogResultPage, {
    expectedUrl: resultUrl,
    targetPage: 2,
    batchId: "bounded-stale-page",
    timeoutMs: 150,
    settleMs: 50,
  });
  const signal = await waitForCatalogSignal(page);

  expect(signal).toMatchObject({
    signal: "TIMEOUT",
    pageNumber: null,
    resultFingerprint: null,
  });
});

test("snapshot visibility cache is per capture and never exposes blocked content", async ({
  page,
}) => {
  await page.setContent(
    '<main><p>Visible synthetic evidence</p><section id="hidden" hidden><p>Hidden synthetic evidence</p></section><button>Blocked synthetic action</button><textarea>Private synthetic field</textarea></main>',
  );
  const first = await page.evaluate(
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );
  expect(first.visibleText).toContain("Visible synthetic evidence");
  expect(first.visibleText).not.toContain("Hidden synthetic evidence");
  expect(first.visibleText).not.toContain("Blocked synthetic action");
  expect(first.visibleText).not.toContain("Private synthetic field");
  await page.locator("#hidden").evaluate((element) => {
    (element as HTMLElement).hidden = false;
  });
  const second = await page.evaluate(
    snapshotVisibleAcademicPage,
    BOUNDED_EXTRACTION_LIMITS,
  );
  expect(second.visibleText).toContain("Hidden synthetic evidence");
  expect(second.visibleText).not.toContain("Blocked synthetic action");
  expect(second.visibleText).not.toContain("Private synthetic field");
});
