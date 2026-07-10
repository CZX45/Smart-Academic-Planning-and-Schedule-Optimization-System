import { afterEach, describe, expect, it, vi } from "vitest";

import { KEAN_STUDENT_PORTAL_PREFIX } from "../src/shared/kean.js";
import type { AcademicPageSnapshot } from "../src/shared/types.js";

const FAKE_STUDENT_PROFILE_ID = "00000000-0000-4000-8000-000000000001";
const CREATED_IMPORT_ID = "11111111-1111-4111-8111-111111111111";

type Listener = () => void;

class FakeElement {
  readonly listeners = new Map<string, Listener[]>();
  readonly children: FakeElement[] = [];
  textContent = "";

  addEventListener(eventName: string, listener: EventListener): void {
    const listeners = this.listeners.get(eventName) ?? [];
    listeners.push(() => listener(new Event(eventName)));
    this.listeners.set(eventName, listeners);
  }

  append(...children: FakeElement[]): void {
    this.children.push(...children);
  }

  replaceChildren(...children: FakeElement[]): void {
    this.children.length = 0;
    this.children.push(...children);
  }

  click(): void {
    for (const listener of this.listeners.get("click") ?? []) {
      listener();
    }
  }
}

class FakeInputElement extends FakeElement {
  value = "";
}

class FakeButtonElement extends FakeElement {
  disabled = false;
}

type PopupElements = {
  apiBaseUrlInput: FakeInputElement;
  studentProfileIdInput: FakeInputElement;
  extractCurrentPageButton: FakeButtonElement;
  startKeanImportButton: FakeButtonElement;
  captureGuidedPageButton: FakeButtonElement;
  confirmImportButton: FakeButtonElement;
  statusText: FakeElement;
  apiStatusText: FakeElement;
};

function createElementForId(id: string): FakeElement {
  if (id.endsWith("Input")) {
    return new FakeInputElement();
  }
  if (id.endsWith("Button")) {
    return new FakeButtonElement();
  }
  return new FakeElement();
}

function createPopupElements(): PopupElements & Record<string, FakeElement> {
  const ids = [
    "apiBaseUrlInput",
    "studentProfileIdInput",
    "extractCurrentPageButton",
    "startKeanImportButton",
    "captureGuidedPageButton",
    "confirmImportButton",
    "statusText",
    "apiStatusText",
    "detectedPageText",
    "countsText",
    "warningsList",
    "previewTable",
    "diagnosticUrlText",
    "diagnosticMarkerText",
    "diagnosticTablesText",
    "diagnosticRowsText",
    "diagnosticVisibleTextLengthText",
    "diagnosticRowLikeBlocksText",
    "diagnosticAcademicFieldsText",
    "diagnosticSensitiveFieldsText",
    "diagnosticDirectSnapshotText",
    "diagnosticBoundedText",
  ] as const;
  const elements = Object.fromEntries(
    ids.map((id) => [id, createElementForId(id)]),
  ) as PopupElements & Record<string, FakeElement>;
  elements.apiBaseUrlInput.value = "http://localhost:8000";
  elements.studentProfileIdInput.value = FAKE_STUDENT_PROFILE_ID;
  return elements;
}

function myProgressRows(count: number): string[][] {
  const examples = [
    [
      "Not Started",
      "MATH*1044",
      "Precalculus for Business",
      "",
      "",
      "3",
    ],
    ["Not Started", "MATH*1054", "Pre-Calculus", "", "", "3"],
    ["Planned", "ENG*2403", "World Literature", "", "2026SUW", "3"],
    ["Not Started", "GE*1855", "First Year Seminar", "", "", "1"],
    ["Not Started", "AH*1700", "Art-Prehist to Middle Ages", "", "", "3"],
    [
      "Not Started",
      "AH*1701",
      "Hist Art-Renssce to Mod. Wrld",
      "",
      "",
      "3",
    ],
  ];
  return Array.from({ length: count }, (_, index) => {
    const example = examples[index];
    if (example) {
      return example;
    }
    return [
      index % 3 === 0 ? "Completed" : "In Progress",
      `FIN*${3000 + index}`,
      `Finance Requirement ${index}`,
      index % 3 === 0 ? "B" : "",
      index % 3 === 0 ? "2025FAW" : "2026SPW",
      "3",
    ];
  });
}

function myProgressSnapshot(rowCount = 1): AcademicPageSnapshot {
  return {
    title: "My Progress",
    url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    visibleText:
      "My Progress Finance, BS Degree Bachelor of Science Major Finance Department Accounting & Finance Catalog 2024 Cumulative GPA 3.916 Institution GPA 3.916 Anticipated Completion Date 12/20/2028 Total Credits 104 of 120 67 24 13 Mathematics Requirements Open Electives Requirements",
    tables: [
      {
        index: 0,
        caption: "Mathematics Requirements",
        headers: ["Status", "Course", "Title", "Grade", "Term", "Credits"],
        rows: myProgressRows(rowCount),
      },
    ],
    headings: ["My Progress", "Finance, BS", "Mathematics Requirements"],
    warnings: [
      {
        code: "EXTRACTION_LIMIT_REACHED",
        severity: "WARNING",
        message: "Extraction stopped early because the page is large.",
      },
    ],
    snapshotMetadata: {
      directSnapshotRan: true,
      visibleTextLength: 280,
      rowLikeBlocksFound: 0,
      bounded: true,
    },
  };
}

async function importPopupWithFetch(
  fetchImpl: typeof fetch,
  options: {
    apiBaseUrl?: string;
    snapshot?: AcademicPageSnapshot;
  } = {},
): Promise<{
  elements: PopupElements;
  fetchMock: ReturnType<typeof vi.fn>;
}> {
  vi.resetModules();
  const elements = createPopupElements();
  const apiBaseUrl = options.apiBaseUrl ?? "http://localhost:8000";
  const snapshot = options.snapshot ?? myProgressSnapshot();
  elements.apiBaseUrlInput.value = apiBaseUrl;
  const fetchMock = vi.fn(fetchImpl);
  const chromeApi = {
    runtime: {},
    storage: {
      local: {
        get: (
          _keys: string[],
          callback: (settings: {
            apiBaseUrl?: string;
            studentProfileId?: string;
          }) => void,
        ) => {
          callback({
            apiBaseUrl,
            studentProfileId: FAKE_STUDENT_PROFILE_ID,
          });
        },
        set: vi.fn(),
      },
    },
    tabs: {
      query: (
        _query: unknown,
        callback: (tabs: Array<{ id: number; url: string }>) => void,
      ) => {
        callback([
          {
            id: 42,
            url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
          },
        ]);
      },
    },
    scripting: {
      executeScript: (
        _details: unknown,
        callback: (results: Array<{ result: AcademicPageSnapshot }>) => void,
      ) => {
        callback([{ result: snapshot }]);
      },
    },
    permissions: {
      contains: () => undefined,
      request: () => undefined,
    },
  };
  const documentStub = {
    getElementById: (id: string) => elements[id] ?? null,
    createElement: () => new FakeElement(),
  };

  vi.stubGlobal("Element", FakeElement);
  vi.stubGlobal("HTMLInputElement", FakeInputElement);
  vi.stubGlobal("HTMLButtonElement", FakeButtonElement);
  vi.stubGlobal("document", documentStub);
  vi.stubGlobal("chrome", chromeApi);
  vi.stubGlobal("fetch", fetchMock);

  await import("../src/popup/popup.js");
  return { elements, fetchMock };
}

async function flushPopupWork(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("popup staging import confirmation", () => {
  it("posts confirmed extracted rows and shows import id with row count", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 1,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/data-imports",
      expect.objectContaining({ method: "POST" }),
    );
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(JSON.parse(String(request?.body))).toMatchObject({
      student_profile_id: FAKE_STUDENT_PROFILE_ID,
      import_type: "DEGREE_AUDIT_EXPORT",
      source_type: "BROWSER_EXTENSION",
      page_type: "KEAN_MY_PROGRESS_PAGE",
      extracted_record_count: 1,
      visible_row_count: 1,
      academic_field_count: 9,
    });
    expect(elements.statusText.textContent).toContain(CREATED_IMPORT_ID);
    expect(elements.statusText.textContent).toContain("1 row");
    expect(elements.apiStatusText.textContent).toContain("1 staging import");
  });

  it("shows API error details when the local API rejects confirmation", async () => {
    const { elements } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: "not_found",
              message: "StudentProfile fake-student was not found.",
            },
          }),
          {
            status: 404,
            headers: { "content-type": "application/json" },
          },
        ),
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(elements.apiStatusText.textContent).toContain("HTTP 404");
    expect(elements.apiStatusText.textContent).toContain(
      "StudentProfile fake-student was not found.",
    );
    expect(elements.statusText.textContent).toContain("Staging import failed");
  });

  it("submits the same 85 MyProgress rows that were shown in preview", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 87,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        snapshot: myProgressSnapshot(85),
      },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    expect(elements.statusText.textContent).toBe("Sending...");
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/data-imports",
      expect.objectContaining({ method: "POST" }),
    );
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse(String(request?.body));
    const content = JSON.parse(String(body.content));
    expect(body).toMatchObject({
      import_type: "DEGREE_AUDIT_EXPORT",
      source_type: "BROWSER_EXTENSION",
      page_type: "KEAN_MY_PROGRESS_PAGE",
      extracted_record_count: 85,
      visible_row_count: 85,
      bounded: true,
      truncated: true,
    });
    expect(body.warnings).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: "EXTRACTION_LIMIT_REACHED" }),
      ]),
    );
    expect(body.diagnostics).toMatchObject({
      detectedPageType: "KEAN_MY_PROGRESS_PAGE",
      academicRowsParsed: 85,
      bounded: true,
    });
    expect(content.courseRows).toHaveLength(85);
    expect(content.courseRows[0]).toMatchObject({
      course_code: "MATH 1044",
      course_title: "Precalculus for Business",
      status: "NOT_STARTED",
      source_table_index: "1",
      source_row_index: "1",
      raw_row_text: expect.stringContaining("MATH*1044"),
      field_provenance: expect.objectContaining({
        course_code: expect.objectContaining({
          value: "MATH*1044",
          rawText: expect.stringContaining("MATH*1044"),
        }),
      }),
    });
    expect(content.courseRows[2]).toMatchObject({
      course_code: "ENG 2403",
      term_code: "2026SUW",
      status: "PLANNED",
    });
    expect(content.warnings).toEqual(body.warnings);
    expect(content.diagnostics).toEqual(body.diagnostics);
    expect(elements.statusText.textContent).toContain(
      "Success: staging import created",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted DEGREE_AUDIT_EXPORT rows: 85",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted visible rows: 85",
    );
    expect(elements.statusText.textContent).toContain(
      "submitted academic fields:",
    );
  });

  it("does not show success when the API accepts fewer rows than were submitted", async () => {
    const { elements, fetchMock } = await importPopupWithFetch(
      async () =>
        new Response(
          JSON.stringify({
            id: CREATED_IMPORT_ID,
            record_count: 1,
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      { snapshot: myProgressSnapshot(85) },
    );

    elements.extractCurrentPageButton.click();
    await flushPopupWork();
    elements.confirmImportButton.click();
    await flushPopupWork();

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(elements.statusText.textContent).toContain("Staging import failed");
    expect(elements.apiStatusText.textContent).toContain(
      "accepted 1 record but 85 extracted row(s) were submitted",
    );
    expect(elements.statusText.textContent).not.toContain(
      "Success: staging import created",
    );
  });
});
