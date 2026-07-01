import type { TableSnapshot } from "../shared/types.js";

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

export function readVisibleTables(documentRef: Document): TableSnapshot[] {
  return Array.from(documentRef.querySelectorAll("table"))
    .filter((table): table is HTMLTableElement => isVisible(table))
    .map((table, index) => ({
      index,
      caption: cleanText(table.caption?.textContent),
      headers: headerTexts(table),
      rows: bodyRows(table),
    }));
}
