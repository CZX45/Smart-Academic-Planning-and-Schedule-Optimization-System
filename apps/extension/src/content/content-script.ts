import type {
  AcademicPageSnapshot,
  ExtensionExtractionWarning,
  TableSnapshot,
} from "../shared/types.js";

type ExtensionMessage = {
  type?: string;
};

type ExtractionResponse = {
  ok: true;
  snapshot: AcademicPageSnapshot;
};

type RuntimeMessageSender = unknown;

type RuntimeApi = {
  onMessage: {
    addListener: (
      listener: (
        message: ExtensionMessage,
        sender: RuntimeMessageSender,
        sendResponse: (response: ExtractionResponse) => void,
      ) => boolean | undefined,
    ) => void;
  };
};

type GlobalWithSapsosState = typeof globalThis & {
  SAPSOS_CONTENT_SCRIPT_READY?: true;
};

declare const chrome:
  | {
      runtime?: RuntimeApi;
    }
  | undefined;

const BOUNDED_EXTRACTION_LIMITS = {
  maxTables: 20,
  maxRowsPerTable: 200,
  maxCellsPerRow: 20,
  maxTotalRows: 1000,
  maxTotalTextLength: 100000,
  maxNodeCount: 5000,
  maxDurationMs: 1000,
  maxCellTextLength: 500,
} as const;

const EXTRACTION_LIMIT_REACHED_WARNING: ExtensionExtractionWarning = {
  code: "EXTRACTION_LIMIT_REACHED",
  severity: "WARNING",
  message:
    "Extraction stopped early because the page is large. Try expanding only the relevant section or use a more specific supported page.",
};

function cleanText(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function isVisible(element: HTMLElement): boolean {
  const style = element.ownerDocument.defaultView?.getComputedStyle(element);
  if (!style) {
    return true;
  }
  return (
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    style.opacity !== "0" &&
    element.hidden !== true
  );
}

function readableCellText(cell: HTMLTableCellElement): string {
  const clone = cell.cloneNode(true);
  if (clone instanceof HTMLElement) {
    clone
      .querySelectorAll(
        "button, input, select, textarea, option, [role='button']",
      )
      .forEach((control) => control.remove());
    return cleanText(clone.textContent);
  }
  return cleanText(cell.textContent);
}

function cellTexts(
  cells: HTMLCollectionOf<HTMLTableCellElement>,
): string[] {
  const texts: string[] = [];
  const maxCells = BOUNDED_EXTRACTION_LIMITS.maxCellsPerRow;
  for (
    let index = 0;
    index < cells.length && texts.length < maxCells;
    index += 1
  ) {
    const cell = cells.item(index);
    if (cell) {
      texts.push(readableCellText(cell));
    }
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

function bodyRows(table: HTMLTableElement): {
  limited: boolean;
  rows: string[][];
} {
  function hasBodyCell(row: HTMLTableRowElement): boolean {
    for (let index = 0; index < row.cells.length; index += 1) {
      const cell = row.cells.item(index);
      if (cell?.tagName.toLowerCase() === "td") {
        return true;
      }
      if (index >= BOUNDED_EXTRACTION_LIMITS.maxCellsPerRow) {
        return false;
      }
    }
    return false;
  }

  const rows: string[][] = [];
  let bodyStarted = false;
  let scannedRows = 0;
  for (let index = 0; index < table.rows.length; index += 1) {
    if (scannedRows >= BOUNDED_EXTRACTION_LIMITS.maxRowsPerTable) {
      return { rows, limited: true };
    }
    const row = table.rows.item(index);
    if (!row) {
      continue;
    }
    scannedRows += 1;
    if (!bodyStarted && !hasBodyCell(row)) {
      continue;
    }
    bodyStarted = true;
    rows.push(cellTexts(row.cells));
    if (rows.length >= BOUNDED_EXTRACTION_LIMITS.maxRowsPerTable) {
      return {
        rows,
        limited: index < table.rows.length - 1,
      };
    }
  }
  return { rows, limited: false };
}

function limitedTableCandidates(documentRef: Document): HTMLTableElement[] {
  const tables: HTMLTableElement[] = [];
  const tableElements = documentRef.getElementsByTagName("table");
  for (let index = 0; index < tableElements.length; index += 1) {
    const table = tableElements.item(index);
    if (table && isVisible(table)) {
      tables.push(table);
    }
    if (tables.length >= BOUNDED_EXTRACTION_LIMITS.maxTables) {
      break;
    }
  }
  return tables;
}

function readVisibleTables(documentRef: Document): {
  tables: TableSnapshot[];
  warnings: ExtensionExtractionWarning[];
} {
  const startedAt = Date.now();
  const warnings: ExtensionExtractionWarning[] = [];
  let limited = false;
  let totalRows = 0;
  let totalTextLength = 0;
  let visitedNodeCount = 0;

  function markLimited(): void {
    limited = true;
  }

  function overBudget(): boolean {
    if (visitedNodeCount >= BOUNDED_EXTRACTION_LIMITS.maxNodeCount) {
      markLimited();
      return true;
    }
    if (
      Date.now() - startedAt >=
      BOUNDED_EXTRACTION_LIMITS.maxDurationMs
    ) {
      markLimited();
      return true;
    }
    return false;
  }

  function boundedText(value: string): string {
    if (value.length > BOUNDED_EXTRACTION_LIMITS.maxCellTextLength) {
      markLimited();
    }
    const cellBounded = value.slice(
      0,
      BOUNDED_EXTRACTION_LIMITS.maxCellTextLength,
    );
    const remainingTextBudget = Math.max(
      BOUNDED_EXTRACTION_LIMITS.maxTotalTextLength - totalTextLength,
      0,
    );
    if (cellBounded.length > remainingTextBudget) {
      markLimited();
    }
    const totalBounded = cellBounded.slice(0, remainingTextBudget);
    totalTextLength += totalBounded.length;
    return totalBounded;
  }

  function boundedCells(cells: readonly string[]): string[] {
    if (cells.length > BOUNDED_EXTRACTION_LIMITS.maxCellsPerRow) {
      markLimited();
    }
    return cells
      .slice(0, BOUNDED_EXTRACTION_LIMITS.maxCellsPerRow)
      .map((cell) => {
        visitedNodeCount += 1;
        return boundedText(cell);
      });
  }

  const candidates = limitedTableCandidates(documentRef);
  if (candidates.length >= BOUNDED_EXTRACTION_LIMITS.maxTables) {
    markLimited();
  }
  const tables = candidates.map((table, index) => {
    visitedNodeCount += 1;
    if (overBudget()) {
      markLimited();
      return {
        index,
        caption: "",
        headers: [],
        rows: [],
      };
    }
    const body = bodyRows(table);
    const rows: string[][] = [];
    for (const row of body.rows) {
      if (
        rows.length >= BOUNDED_EXTRACTION_LIMITS.maxRowsPerTable ||
        totalRows >= BOUNDED_EXTRACTION_LIMITS.maxTotalRows ||
        overBudget()
      ) {
        markLimited();
        break;
      }
      visitedNodeCount += 1;
      rows.push(boundedCells(row));
      totalRows += 1;
    }
    if (body.limited || body.rows.length > rows.length) {
      markLimited();
    }
    return {
      index,
      caption: boundedText(cleanText(table.caption?.textContent)),
      headers: boundedCells(headerTexts(table)),
      rows,
    };
  });

  if (limited) {
    warnings.push(EXTRACTION_LIMIT_REACHED_WARNING);
  }
  return { tables, warnings };
}

function readAcademicPageSnapshot(documentRef: Document): AcademicPageSnapshot {
  const { tables, warnings } = readVisibleTables(documentRef);
  return {
    title: documentRef.title,
    url: documentRef.location.href,
    tables,
    ...(warnings.length > 0 ? { warnings } : {}),
  };
}

const globalSapsosState = globalThis as GlobalWithSapsosState;

if (!globalSapsosState.SAPSOS_CONTENT_SCRIPT_READY) {
  globalSapsosState.SAPSOS_CONTENT_SCRIPT_READY = true;
  chrome?.runtime?.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type !== "SAPSOS_EXTRACT_PAGE") {
      return false;
    }
    sendResponse({
      ok: true,
      snapshot: readAcademicPageSnapshot(document),
    });
    return false;
  });
}
