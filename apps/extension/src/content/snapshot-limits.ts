import type {
  AcademicPageSnapshot,
  ExtensionExtractionWarning,
  RowLikeBlockSnapshot,
  TableSnapshot,
} from "../shared/types.js";

export const BOUNDED_EXTRACTION_LIMITS = {
  maxTables: 20,
  maxRowsPerTable: 200,
  maxCellsPerRow: 20,
  maxTotalRows: 1000,
  maxTotalTextLength: 100000,
  maxNodeCount: 5000,
  maxDurationMs: 1000,
  maxCellTextLength: 500,
} as const;

export type BoundedExtractionLimits = typeof BOUNDED_EXTRACTION_LIMITS;

export const EXTRACTION_LIMIT_REACHED_WARNING: ExtensionExtractionWarning = {
  code: "EXTRACTION_LIMIT_REACHED",
  severity: "WARNING",
  message:
    "Extraction stopped early because the page is large. Try expanding only the relevant section or use a more specific supported page.",
};

export function limitAcademicPageSnapshot(
  snapshot: AcademicPageSnapshot,
  limits = BOUNDED_EXTRACTION_LIMITS,
): AcademicPageSnapshot {
  const startedAt = Date.now();
  let limited = false;
  let totalRows = 0;
  let totalTextLength = 0;
  let visitedNodeCount = 0;

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

  function boundedText(value: string): string {
    if (value.length > limits.maxCellTextLength) {
      markLimited();
    }
    const cellBounded = value.slice(0, limits.maxCellTextLength);
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
    const remainingTextBudget = Math.max(
      limits.maxTotalTextLength - totalTextLength,
      0,
    );
    if (value.length > remainingTextBudget) {
      markLimited();
    }
    const bounded = value.slice(0, remainingTextBudget);
    totalTextLength += bounded.length;
    return bounded;
  }

  function boundedCells(cells: readonly string[]): string[] {
    if (cells.length > limits.maxCellsPerRow) {
      markLimited();
    }
    return cells.slice(0, limits.maxCellsPerRow).map((cell) => {
      visitedNodeCount += 1;
      return boundedText(cell);
    });
  }

  function boundedRowLikeBlock(
    block: RowLikeBlockSnapshot,
  ): RowLikeBlockSnapshot {
    const cells = block.cells ? boundedCells(block.cells) : undefined;
    const boundedBlock: RowLikeBlockSnapshot = {
      index: block.index,
      text: boundedText(block.text),
    };
    if (cells) {
      boundedBlock.cells = cells;
    }
    if (block.section) {
      boundedBlock.section = boundedText(block.section);
    }
    return boundedBlock;
  }

  const tables: TableSnapshot[] = [];
  if (snapshot.tables.length > limits.maxTables) {
    markLimited();
  }
  for (const table of snapshot.tables.slice(0, limits.maxTables)) {
    visitedNodeCount += 1;
    if (overBudget()) {
      break;
    }
    const rows: string[][] = [];
    for (const row of table.rows) {
      if (
        rows.length >= limits.maxRowsPerTable ||
        totalRows >= limits.maxTotalRows ||
        overBudget()
      ) {
        markLimited();
        break;
      }
      visitedNodeCount += 1;
      rows.push(boundedCells(row));
      totalRows += 1;
    }
    if (table.rows.length > rows.length) {
      markLimited();
    }
    tables.push({
      index: table.index,
      caption: boundedText(table.caption),
      headers: boundedCells(table.headers),
      rows,
    });
  }

  const rowLikeBlocks: RowLikeBlockSnapshot[] = [];
  const sourceRowLikeBlocks = snapshot.rowLikeBlocks ?? [];
  for (const block of sourceRowLikeBlocks) {
    if (totalRows >= limits.maxTotalRows || overBudget()) {
      markLimited();
      break;
    }
    visitedNodeCount += 1;
    rowLikeBlocks.push(boundedRowLikeBlock(block));
    totalRows += 1;
  }
  if (sourceRowLikeBlocks.length > rowLikeBlocks.length) {
    markLimited();
  }

  const headings = snapshot.headings?.map((heading) => boundedText(heading));
  const visibleText =
    snapshot.visibleText === undefined
      ? undefined
      : boundedVisibleText(snapshot.visibleText);

  const warnings = [...(snapshot.warnings ?? [])];
  if (
    limited &&
    !warnings.some(
      (warning) => warning.code === EXTRACTION_LIMIT_REACHED_WARNING.code,
    )
  ) {
    warnings.push(EXTRACTION_LIMIT_REACHED_WARNING);
  }

  const snapshotMetadata = {
    ...(snapshot.snapshotMetadata ?? {}),
    visibleTextLength: visibleText?.length ?? 0,
    rowLikeBlocksFound: rowLikeBlocks.length,
    bounded:
      (snapshot.snapshotMetadata?.bounded ?? false) ||
      limited ||
      warnings.some(
        (warning) => warning.code === EXTRACTION_LIMIT_REACHED_WARNING.code,
      ),
  };

  return {
    ...snapshot,
    tables,
    ...(headings ? { headings } : {}),
    ...(visibleText !== undefined ? { visibleText } : {}),
    ...(rowLikeBlocks.length > 0 ? { rowLikeBlocks } : {}),
    snapshotMetadata,
    ...(warnings.length > 0 ? { warnings } : {}),
  };
}
