import {
  formatAcademicTimestamp,
  type DataImportRun,
  type ImportPreviewSummary,
} from "@sapsos/shared";

export type SavedImportOption = {
  id: string;
  label: string;
  timestamp: string;
  sourceType: string;
  validationStatus: string;
  recordCount: number;
  validRecordCount: number;
  warningCount: number;
  errorCount: number;
  confidence: string;
};

export type LoadedDataImportPreview = {
  run: DataImportRun;
  preview: ImportPreviewSummary;
};

function numberFromUnknown(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function recordFromUnknown(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : {};
}

function pluralize(count: number, singular: string): string {
  return `${count} ${count === 1 ? singular : `${singular}s`}`;
}

export function savedImportOptionFromRun(run: DataImportRun): SavedImportOption {
  const timestamp = formatAcademicTimestamp(run.created_at);
  const sourceType = run.source.source_type;
  const confidence = run.source.source_confidence ?? "not recorded";
  const label = [
    timestamp,
    sourceType,
    run.status,
    pluralize(run.record_count, "record"),
    `${run.valid_record_count} valid`,
    pluralize(run.warning_count, "warning"),
    pluralize(run.error_count, "error"),
    `confidence ${confidence}`,
  ].join(" · ");
  return {
    id: run.id,
    label,
    timestamp,
    sourceType,
    validationStatus: run.status,
    recordCount: run.record_count,
    validRecordCount: run.valid_record_count,
    warningCount: run.warning_count,
    errorCount: run.error_count,
    confidence,
  };
}

export function isUsableMyProgressPreviewSummary(
  preview: ImportPreviewSummary,
): boolean {
  const payload = preview.summary_payload;
  const realImportStatus = String(payload.real_import_status ?? "");
  if (!realImportStatus.startsWith("REAL_IMPORTED_DATA")) {
    return false;
  }
  const programSummary = recordFromUnknown(payload.program_summary);
  const extractedRows =
    numberFromUnknown(payload.extracted_degree_audit_row_count) ?? 0;
  const parsedCourseRows =
    numberFromUnknown(payload.parsed_course_like_row_count) ?? 0;
  const parsedRequirementRows =
    numberFromUnknown(payload.parsed_requirement_row_count) ?? 0;
  const confidence = numberFromUnknown(payload.overall_confidence_score) ?? 0;
  const hasProgram = Object.values(programSummary).some(
    (value) => value !== null && value !== undefined && String(value).trim(),
  );
  return (
    confidence > 0 &&
    (extractedRows > 0 || parsedCourseRows > 0 || parsedRequirementRows > 0) &&
    (hasProgram || parsedCourseRows > 0 || parsedRequirementRows > 0)
  );
}

export function selectPreferredLoadedDataImport<
  T extends LoadedDataImportPreview,
>(states: readonly T[]): T | null {
  const usableMyProgress = states.find((state) =>
    isUsableMyProgressPreviewSummary(state.preview),
  );
  if (usableMyProgress) {
    return usableMyProgress;
  }
  return states[0] ?? null;
}
