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

function myProgressSnapshot(): AcademicPageSnapshot {
  return {
    title: "My Progress",
    url: `${KEAN_STUDENT_PORTAL_PREFIX}/Planning/Programs/MyProgress#BS.FINANCE.24`,
    visibleText: "My Progress Requirements Status Course Term Credits",
    tables: [
      {
        index: 0,
        caption: "My Progress",
        headers: ["Status", "Course", "Title", "Grade", "Term", "Credits"],
        rows: [
          [
            "Completed",
            "SYN 101",
            "Synthetic Planning Course",
            "B",
            "2024FA",
            "3.0",
          ],
        ],
      },
    ],
    snapshotMetadata: {
      directSnapshotRan: true,
      visibleTextLength: 52,
      rowLikeBlocksFound: 0,
    },
  };
}

async function importPopupWithFetch(fetchImpl: typeof fetch): Promise<{
  elements: PopupElements;
  fetchMock: ReturnType<typeof vi.fn>;
}> {
  vi.resetModules();
  const elements = createPopupElements();
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
            apiBaseUrl: "http://localhost:8000",
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
        callback([{ result: myProgressSnapshot() }]);
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
});
