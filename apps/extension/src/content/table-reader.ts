import { BOUNDED_EXTRACTION_LIMITS } from "./snapshot-limits.js";
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
  const texts: string[] = [];
  for (
    let index = 0;
    index < cells.length &&
    texts.length < BOUNDED_EXTRACTION_LIMITS.maxCellsPerRow;
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

function bodyRows(table: HTMLTableElement): string[][] {
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
  for (
    let index = 0;
    index < table.rows.length &&
    rows.length < BOUNDED_EXTRACTION_LIMITS.maxRowsPerTable;
    index += 1
  ) {
    const row = table.rows.item(index);
    if (!row) {
      continue;
    }
    if (!bodyStarted && !hasBodyCell(row)) {
      continue;
    }
    bodyStarted = true;
    rows.push(cellTexts(row.cells));
  }
  return rows;
}

export function readVisibleTables(documentRef: Document): TableSnapshot[] {
  const tables: TableSnapshot[] = [];
  const tableElements = documentRef.getElementsByTagName("table");
  for (
    let elementIndex = 0;
    elementIndex < tableElements.length &&
    tables.length < BOUNDED_EXTRACTION_LIMITS.maxTables;
    elementIndex += 1
  ) {
    const table = tableElements.item(elementIndex);
    if (!table || !isVisible(table)) {
      continue;
    }
    tables.push({
      index: tables.length,
      caption: cleanText(table.caption?.textContent),
      headers: headerTexts(table),
      rows: bodyRows(table),
    });
  }
  return tables;
}
