import type { AcademicPageSnapshot, TableSnapshot } from "../shared/types.js";

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

declare const chrome:
  | {
      runtime?: RuntimeApi;
    }
  | undefined;

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

function cellTexts(cells: HTMLCollectionOf<HTMLTableCellElement>): string[] {
  return Array.from(cells).map(readableCellText);
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

function bodyRows(table: HTMLTableElement): string[][] {
  const rows = Array.from(table.rows);
  const firstBodyIndex = rows.findIndex((row) =>
    Array.from(row.cells).some((cell) => cell.tagName.toLowerCase() === "td"),
  );
  if (firstBodyIndex < 0) {
    return [];
  }
  return rows.slice(firstBodyIndex).map((row) => cellTexts(row.cells));
}

function readVisibleTables(documentRef: Document): TableSnapshot[] {
  return Array.from(documentRef.querySelectorAll("table"))
    .filter((table): table is HTMLTableElement => isVisible(table))
    .map((table, index) => ({
      index,
      caption: cleanText(table.caption?.textContent),
      headers: headerTexts(table),
      rows: bodyRows(table),
    }));
}

function readAcademicPageSnapshot(documentRef: Document): AcademicPageSnapshot {
  return {
    title: documentRef.title,
    url: documentRef.location.href,
    tables: readVisibleTables(documentRef),
  };
}

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
