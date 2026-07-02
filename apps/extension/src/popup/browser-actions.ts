import { extractAcademicPageFromTables } from "../content/extractors.js";
import {
  BOUNDED_EXTRACTION_LIMITS,
  type BoundedExtractionLimits,
} from "../content/snapshot-limits.js";
import { isKeanStudentPortalUrl } from "../shared/kean.js";
import type {
  AcademicPageSnapshot,
  BrowserExtensionExtraction,
  ExtensionDiagnostics,
  RowLikeBlockSnapshot,
} from "../shared/types.js";

type PopupTab = {
  id?: number;
  url?: string;
};

type ScriptInjectionResult<Result> = {
  result?: Result;
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
  };
  scripting: {
    executeScript: (
      details: {
        target: { tabId: number };
        func: (limits: BoundedExtractionLimits) => AcademicPageSnapshot;
        args: [BoundedExtractionLimits];
      },
      callback: (
        results: Array<ScriptInjectionResult<AcademicPageSnapshot>>,
      ) => void,
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
    visibleTextLength: 0,
    rowLikeBlocksFound: 0,
    extractedAcademicFieldCount: 0,
    ignoredSensitiveFieldCount: 0,
    directSnapshotRan: false,
    bounded: false,
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

export function snapshotVisibleAcademicPage(
  rawLimits: BoundedExtractionLimits,
): AcademicPageSnapshot {
  const limits = {
    maxTables: rawLimits.maxTables,
    maxRowsPerTable: rawLimits.maxRowsPerTable,
    maxCellsPerRow: rawLimits.maxCellsPerRow,
    maxTotalRows: rawLimits.maxTotalRows,
    maxTotalTextLength: rawLimits.maxTotalTextLength,
    maxNodeCount: rawLimits.maxNodeCount,
    maxDurationMs: rawLimits.maxDurationMs,
    maxCellTextLength: rawLimits.maxCellTextLength,
  };
  const startedAt = Date.now();
  let limited = false;
  let visitedNodeCount = 0;
  let totalRows = 0;
  let totalTextLength = 0;

  function markLimited(): void {
    limited = true;
  }

  function overBudget(): boolean {
    if (visitedNodeCount >= limits.maxNodeCount) {
      markLimited();
      return true;
    }
    if (Date.now() - startedAt >= limits.maxDurationMs) {
      markLimited();
      return true;
    }
    return false;
  }

  function cleanText(value: string | null | undefined): string {
    return (value ?? "").replace(/\s+/g, " ").trim();
  }

  function boundedText(value: string): string {
    const cleaned = cleanText(value);
    if (cleaned.length > limits.maxCellTextLength) {
      markLimited();
    }
    const cellBounded = cleaned.slice(0, limits.maxCellTextLength);
    const remainingTextBudget = Math.max(
      limits.maxTotalTextLength - totalTextLength,
      0,
    );
    if (cellBounded.length > remainingTextBudget) {
      markLimited();
    }
    const totalBounded = cellBounded.slice(0, remainingTextBudget);
    totalTextLength += totalBounded.length;
    return totalBounded;
  }

  function boundedVisibleText(value: string): string {
    const cleaned = cleanText(value);
    const remainingTextBudget = Math.max(
      limits.maxTotalTextLength - totalTextLength,
      0,
    );
    if (cleaned.length > remainingTextBudget) {
      markLimited();
    }
    const bounded = cleaned.slice(0, remainingTextBudget);
    totalTextLength += bounded.length;
    return bounded;
  }

  function isBlockedElement(element: Element): boolean {
    const tag = element.tagName.toLowerCase();
    return [
      "button",
      "input",
      "select",
      "textarea",
      "option",
      "script",
      "style",
      "noscript",
      "template",
      "svg",
    ].includes(tag);
  }

  function isVisibleElement(element: Element): boolean {
    if (!(element instanceof HTMLElement)) {
      return true;
    }
    const style = element.ownerDocument.defaultView?.getComputedStyle(element);
    if (!style) {
      return true;
    }
    return (
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0" &&
      element.hidden !== true &&
      element.getAttribute("aria-hidden") !== "true"
    );
  }

  function hasBlockedOrHiddenAncestor(element: Element | null): boolean {
    let current = element;
    while (current) {
      if (isBlockedElement(current) || !isVisibleElement(current)) {
        return true;
      }
      current = current.parentElement;
    }
    return false;
  }

  function visibleTextUnder(root: Element, maxLength: number): string {
    const pieces: string[] = [];
    let localLength = 0;
    const walker = root.ownerDocument.createTreeWalker(root, 4);
    let node = walker.nextNode();
    while (node && localLength < maxLength && !overBudget()) {
      visitedNodeCount += 1;
      if (
        node.parentElement &&
        !hasBlockedOrHiddenAncestor(node.parentElement)
      ) {
        const text = cleanText(node.textContent);
        if (text) {
          const remaining = Math.max(maxLength - localLength, 0);
          const bounded = text.slice(0, remaining);
          pieces.push(bounded);
          localLength += bounded.length;
          if (text.length > bounded.length) {
            markLimited();
          }
        }
      }
      node = walker.nextNode();
    }
    return cleanText(pieces.join(" "));
  }

  function visibleCellsUnder(element: Element): string[] {
    const cells: string[] = [];
    for (
      let index = 0;
      index < element.children.length && cells.length < limits.maxCellsPerRow;
      index += 1
    ) {
      const child = element.children.item(index);
      if (!child || hasBlockedOrHiddenAncestor(child)) {
        continue;
      }
      const text = visibleTextUnder(child, limits.maxCellTextLength);
      if (text) {
        cells.push(boundedText(text));
      }
    }
    if (element.children.length > limits.maxCellsPerRow) {
      markLimited();
    }
    return cells;
  }

  function cellTexts(cells: HTMLCollectionOf<HTMLTableCellElement>): string[] {
    const texts: string[] = [];
    for (
      let index = 0;
      index < cells.length && texts.length < limits.maxCellsPerRow;
      index += 1
    ) {
      const cell = cells.item(index);
      if (cell && !hasBlockedOrHiddenAncestor(cell)) {
        texts.push(
          boundedText(visibleTextUnder(cell, limits.maxCellTextLength)),
        );
      }
    }
    if (cells.length > limits.maxCellsPerRow) {
      markLimited();
    }
    return texts;
  }

  function headerTexts(table: HTMLTableElement): string[] {
    const explicitHeader = table.querySelector("thead tr");
    if (explicitHeader instanceof HTMLTableRowElement) {
      const headers = cellTexts(explicitHeader.cells);
      if (headers.length > 0) {
        return headers;
      }
    }
    const firstRow = table.rows.item(0);
    return firstRow ? cellTexts(firstRow.cells) : [];
  }

  function hasBodyCell(row: HTMLTableRowElement): boolean {
    for (let index = 0; index < row.cells.length; index += 1) {
      const cell = row.cells.item(index);
      if (cell?.tagName.toLowerCase() === "td") {
        return true;
      }
      if (index >= limits.maxCellsPerRow) {
        markLimited();
        return false;
      }
    }
    return false;
  }

  function tableRows(table: HTMLTableElement): string[][] {
    const rows: string[][] = [];
    let bodyStarted = false;
    let scannedRows = 0;
    for (let index = 0; index < table.rows.length; index += 1) {
      if (
        scannedRows >= limits.maxRowsPerTable ||
        totalRows >= limits.maxTotalRows ||
        overBudget()
      ) {
        markLimited();
        break;
      }
      const row = table.rows.item(index);
      if (!row || hasBlockedOrHiddenAncestor(row)) {
        continue;
      }
      scannedRows += 1;
      visitedNodeCount += 1;
      if (!bodyStarted && !hasBodyCell(row)) {
        continue;
      }
      bodyStarted = true;
      rows.push(cellTexts(row.cells));
      totalRows += 1;
    }
    return rows;
  }

  function visibleTables(
    documentRef: Document,
  ): AcademicPageSnapshot["tables"] {
    const tables: AcademicPageSnapshot["tables"] = [];
    const tableElements = documentRef.getElementsByTagName("table");
    for (let index = 0; index < tableElements.length; index += 1) {
      if (tables.length >= limits.maxTables || overBudget()) {
        markLimited();
        break;
      }
      const table = tableElements.item(index);
      if (!table || hasBlockedOrHiddenAncestor(table)) {
        continue;
      }
      visitedNodeCount += 1;
      tables.push({
        index: tables.length,
        caption: boundedText(
          table.caption
            ? visibleTextUnder(table.caption, limits.maxCellTextLength)
            : "",
        ),
        headers: headerTexts(table),
        rows: tableRows(table),
      });
    }
    return tables;
  }

  function headingTexts(documentRef: Document): string[] {
    const headings: string[] = [];
    for (const tag of ["h1", "h2", "h3", "h4"]) {
      const elements = documentRef.getElementsByTagName(tag);
      for (
        let index = 0;
        index < elements.length && headings.length < 40 && !overBudget();
        index += 1
      ) {
        const element = elements.item(index);
        if (!element || hasBlockedOrHiddenAncestor(element)) {
          continue;
        }
        const text = boundedText(visibleTextUnder(element, 240));
        if (text) {
          headings.push(text);
        }
      }
    }
    return headings;
  }

  function looksLikeAcademicRow(text: string): boolean {
    return (
      /\b(?:Completed|Reg(?:istered)?|Planned|Not Started|In Progress)\b/i.test(
        text,
      ) && /\b[A-Z]{2,5}[*\s-]?\d{3,4}[A-Z]?\b/.test(text)
    );
  }

  function looksLikeAcademicHeader(text: string): boolean {
    const normalized = text.toLowerCase();
    return (
      normalized.includes("status") &&
      normalized.includes("course") &&
      normalized.includes("term") &&
      normalized.includes("credit")
    );
  }

  function looksLikeRequirementBlock(text: string): boolean {
    return /\brequirements?\b/i.test(text) && text.length <= 240;
  }

  function rowLikeBlocks(documentRef: Document): RowLikeBlockSnapshot[] {
    const blocks: RowLikeBlockSnapshot[] = [];
    const body = documentRef.body;
    if (!body) {
      return blocks;
    }
    const skippedContainerTags = new Set([
      "body",
      "html",
      "main",
      "section",
      "table",
      "thead",
      "tbody",
      "tfoot",
    ]);
    const elements = body.getElementsByTagName("*");
    for (
      let index = 0;
      index < elements.length &&
      blocks.length < limits.maxTotalRows &&
      !overBudget();
      index += 1
    ) {
      const element = elements.item(index);
      if (
        !element ||
        skippedContainerTags.has(element.tagName.toLowerCase()) ||
        hasBlockedOrHiddenAncestor(element) ||
        element.closest("table")
      ) {
        continue;
      }
      visitedNodeCount += 1;
      const text = visibleTextUnder(element, limits.maxCellTextLength * 4);
      if (
        !text ||
        (!looksLikeAcademicRow(text) &&
          !looksLikeAcademicHeader(text) &&
          !looksLikeRequirementBlock(text))
      ) {
        continue;
      }
      const cells = visibleCellsUnder(element);
      const block = {
        index: blocks.length,
        text: boundedText(text),
      };
      blocks.push(cells.length > 1 ? { ...block, cells } : block);
    }
    if (
      (blocks.length >= limits.maxTotalRows &&
        elements.length > blocks.length) ||
      overBudget()
    ) {
      markLimited();
    }
    return blocks;
  }

  const documentRef = document;
  const tables = visibleTables(documentRef);
  const headings = headingTexts(documentRef);
  const blocks = rowLikeBlocks(documentRef);
  const visibleText = documentRef.body
    ? boundedVisibleText(
        visibleTextUnder(
          documentRef.body,
          Math.max(limits.maxTotalTextLength - totalTextLength, 0),
        ),
      )
    : "";
  const warnings = limited
    ? [
        {
          code: "EXTRACTION_LIMIT_REACHED",
          severity: "WARNING" as const,
          message:
            "Extraction stopped early because the page is large. Try expanding only the relevant section or use a more specific supported page.",
        },
      ]
    : [];
  return {
    title: documentRef.title,
    url: documentRef.location.href,
    tables,
    headings,
    visibleText,
    rowLikeBlocks: blocks,
    snapshotMetadata: {
      directSnapshotRan: true,
      visibleTextLength: visibleText.length,
      rowLikeBlocksFound: blocks.length,
      bounded: limited,
    },
    ...(warnings.length > 0 ? { warnings } : {}),
  };
}

export function executeExtraction(
  chromeApi: PopupChromeApi,
  tab: ActiveBrowserTab,
): Promise<BrowserExtensionExtraction> {
  if (!shouldAttemptExtractionForUrl(tab.url)) {
    return Promise.reject(
      new Error("This browser page cannot be inspected by the extension."),
    );
  }
  return new Promise((resolve, reject) => {
    chromeApi.scripting.executeScript(
      {
        target: { tabId: tab.id },
        func: snapshotVisibleAcademicPage,
        args: [BOUNDED_EXTRACTION_LIMITS],
      },
      (results) => {
        const injectionError = lastErrorMessage(chromeApi);
        if (injectionError) {
          reject(
            new Error(`Could not snapshot the active tab: ${injectionError}`),
          );
          return;
        }
        const snapshot = results[0]?.result;
        if (!snapshot) {
          reject(
            new Error(
              "Could not snapshot the active tab: The page did not return visible content.",
            ),
          );
          return;
        }
        if (!shouldAttemptExtractionForUrl(snapshot.url)) {
          reject(
            new Error(
              "This browser page cannot be inspected by the extension.",
            ),
          );
          return;
        }
        resolve(
          extractAcademicPageFromTables({
            ...snapshot,
            snapshotMetadata: {
              ...(snapshot.snapshotMetadata ?? {}),
              directSnapshotRan: true,
            },
          }),
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
