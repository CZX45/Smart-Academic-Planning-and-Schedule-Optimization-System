import { readVisibleTables } from "./table-reader.js";
import type {
  AcademicPageSnapshot,
  AcademicPageType,
  BrowserExtensionDataImportRequest,
  BrowserExtensionExtraction,
  DataImportType,
  ExtensionExtractionWarning,
  ExtractedRecord,
  TableSnapshot,
} from "../shared/types.js";

const SOURCE_TYPE = "BROWSER_EXTENSION" as const;

type ColumnAliases = Record<string, readonly string[]>;

type ExtractionSpec = {
  pageType: AcademicPageType;
  importType: DataImportType;
  fileBaseName: string;
  mimeType: "text/csv" | "application/json";
  fields: readonly string[];
  aliases: ColumnAliases;
  requiredFields: readonly string[];
  manualReviewWarning?: ExtensionExtractionWarning;
};

type TableCandidate = {
  spec: ExtractionSpec;
  table: TableSnapshot;
  score: number;
};

const TRANSCRIPT_SPEC: ExtractionSpec = {
  pageType: "TRANSCRIPT_TABLE",
  importType: "UNOFFICIAL_TRANSCRIPT",
  fileBaseName: "browser-extension-unofficial-transcript",
  mimeType: "text/csv",
  fields: [
    "term_code",
    "course_code",
    "course_title",
    "credits",
    "grade",
    "attempt_status",
    "source_label",
  ],
  aliases: {
    term_code: ["term", "term_code", "semester"],
    course_code: ["course", "course_code", "code", "subject_course"],
    course_title: ["title", "course_title", "name"],
    credits: ["credits", "credit_hours"],
    grade: ["grade", "final_grade"],
    attempt_status: ["status", "course_status", "attempt_status"],
  },
  requiredFields: ["term_code", "course_code"],
};

const DEGREE_AUDIT_SPEC: ExtractionSpec = {
  pageType: "DEGREE_AUDIT_TABLE",
  importType: "DEGREE_AUDIT_EXPORT",
  fileBaseName: "browser-extension-degree-audit-export",
  mimeType: "application/json",
  fields: [
    "program_code",
    "catalog_year",
    "requirements",
    "completed_courses",
    "remaining_requirements",
    "source_label",
  ],
  aliases: {
    program_code: ["program", "program_code"],
    catalog_year: ["catalog_year", "catalog"],
    requirements: ["requirement", "requirements"],
    completed_courses: ["completed_courses", "completed"],
    remaining_requirements: ["remaining", "remaining_requirements"],
  },
  requiredFields: ["program_code", "requirements"],
  manualReviewWarning: {
    code: "DEGREE_AUDIT_REQUIRES_MANUAL_REVIEW",
    severity: "WARNING",
    message:
      "Degree-audit rows are staged for manual review and are not official policy.",
  },
};

const CATALOG_SPEC: ExtractionSpec = {
  pageType: "COURSE_CATALOG_TABLE",
  importType: "COURSE_CATALOG",
  fileBaseName: "browser-extension-course-catalog",
  mimeType: "text/csv",
  fields: [
    "course_code",
    "course_title",
    "credits",
    "course_level",
    "department",
    "description",
    "source_label",
  ],
  aliases: {
    course_code: ["course_code", "course", "code"],
    course_title: ["course_title", "title", "name"],
    credits: ["credits", "credit_hours"],
    course_level: ["level", "course_level"],
    department: ["department", "subject"],
    description: ["description"],
  },
  requiredFields: ["course_code", "course_title"],
};

const SECTION_SPEC: ExtractionSpec = {
  pageType: "SECTION_SEARCH_TABLE",
  importType: "SECTION_SCHEDULE",
  fileBaseName: "browser-extension-section-schedule",
  mimeType: "text/csv",
  fields: [
    "term_code",
    "course_code",
    "section_code",
    "modality",
    "status",
    "seats_available",
    "seats_capacity",
    "waitlist_available",
    "waitlist_capacity",
    "credits",
    "day_of_week",
    "start_time",
    "end_time",
    "meeting_days",
    "meeting_time",
    "location",
    "instructor_display",
    "source_label",
  ],
  aliases: {
    term_code: ["term", "term_code"],
    course_code: ["course", "course_code", "code"],
    section_code: ["section", "section_code"],
    modality: ["modality", "instruction_mode"],
    status: ["status", "section_status"],
    seats_available: [
      "seats_available",
      "available_seats",
      "available",
      "open_seats",
    ],
    seats_capacity: ["seats_capacity", "capacity", "total_seats"],
    waitlist_available: [
      "waitlist_available",
      "waitlist",
      "waitlist_open",
      "waitlist_seats",
    ],
    waitlist_capacity: ["waitlist_capacity", "waitlist_total", "waitlist_cap"],
    credits: ["credits", "credit_hours"],
    day_of_week: ["day", "days", "day_of_week"],
    start_time: ["start", "start_time"],
    end_time: ["end", "end_time"],
    meeting_days: ["meeting_days"],
    meeting_time: ["meeting_time", "time"],
    location: ["location", "building_room", "room", "building"],
    instructor_display: ["instructor", "instructor_display"],
  },
  requiredFields: ["term_code", "course_code", "section_code"],
};

const SPECS = [
  SECTION_SPEC,
  TRANSCRIPT_SPEC,
  DEGREE_AUDIT_SPEC,
  CATALOG_SPEC,
] as const;

export const EXTENSION_STAGING_DISCLAIMERS = [
  "Browser extension data is extracted only from the currently visible page after user action.",
  "Extracted rows enter staging import first and remain non-official.",
  "Phase 7B review is required before any internal planning application.",
] as const;

export function extractAcademicPage(
  documentRef: Document,
  url = documentRef.location?.href ?? "",
  title = documentRef.title,
): BrowserExtensionExtraction {
  return extractAcademicPageFromTables({
    title,
    url,
    tables: readVisibleTables(documentRef),
  });
}

export function extractAcademicPageFromTables(
  snapshot: AcademicPageSnapshot,
): BrowserExtensionExtraction {
  const extractedAt = "1970-01-01T00:00:00.000Z";
  const candidate = bestCandidate(snapshot.tables);
  if (!candidate) {
    return noDataExtraction(snapshot, "NO_ACADEMIC_TABLE_FOUND", extractedAt);
  }

  const warnings: ExtensionExtractionWarning[] = [];
  const records = recordsFromTable(candidate.spec, candidate.table, warnings);
  if (records.length === 0) {
    warnings.push({
      code: "NO_IMPORTABLE_ROWS",
      severity: "WARNING",
      message: "The visible table did not contain importable academic rows.",
    });
  }
  if (candidate.spec.manualReviewWarning) {
    warnings.push(candidate.spec.manualReviewWarning);
  }

  return {
    pageType: candidate.spec.pageType,
    importType: candidate.spec.importType,
    sourceType: SOURCE_TYPE,
    isOfficial: false,
    title: snapshot.title,
    url: safeUrl(snapshot.url),
    fileName: fileName(candidate.spec),
    fileMimeType: candidate.spec.mimeType,
    content: contentFor(candidate.spec, records),
    records,
    warnings,
    requiresReview: true,
    extractedAt,
  };
}

export function createDataImportRequestFromExtraction(
  studentProfileId: string,
  extraction: BrowserExtensionExtraction,
): BrowserExtensionDataImportRequest {
  return {
    student_profile_id: studentProfileId,
    import_type: extraction.importType,
    file_name: extraction.fileName,
    file_mime_type: extraction.fileMimeType,
    content: extraction.content,
    source_type: SOURCE_TYPE,
    source_reference: `Browser extension visible-page import: ${extraction.url}`,
  };
}

function bestCandidate(tables: TableSnapshot[]): TableCandidate | null {
  const candidates = tables.flatMap((table) =>
    SPECS.map((spec) => ({
      spec,
      table,
      score: scoreTable(spec, table),
    })),
  );
  const scored = candidates
    .filter((candidate) => candidate.score > 0)
    .sort(
      (left, right) =>
        right.score - left.score ||
        left.table.index - right.table.index ||
        left.spec.pageType.localeCompare(right.spec.pageType),
    );
  return scored[0] ?? null;
}

function scoreTable(spec: ExtractionSpec, table: TableSnapshot): number {
  const headerKeys = new Set(table.headers.map(normalizeHeader));
  const aliasEntries = Object.entries(spec.aliases);
  const matchedFields = aliasEntries.filter(([, aliases]) =>
    aliases.some((alias) => headerKeys.has(alias)),
  );
  const requiredMatches = spec.requiredFields.filter((field) =>
    spec.aliases[field]?.some((alias) => headerKeys.has(alias)),
  );
  if (requiredMatches.length < spec.requiredFields.length) {
    return 0;
  }
  return matchedFields.length * 10 + requiredMatches.length;
}

function recordsFromTable(
  spec: ExtractionSpec,
  table: TableSnapshot,
  warnings: ExtensionExtractionWarning[],
): ExtractedRecord[] {
  const columnByField = buildColumnMap(spec, table.headers);
  warnForUnknownColumns(spec, table.headers, warnings);
  const records: ExtractedRecord[] = [];
  for (const [rowIndex, row] of table.rows.entries()) {
    const record = spec.fields.reduce<ExtractedRecord>((current, field) => {
      const columnIndex = columnByField.get(field);
      current[field] =
        columnIndex === undefined
          ? ""
          : normalizeValue(field, row[columnIndex] ?? "");
      return current;
    }, {});
    if (spec.pageType === "SECTION_SEARCH_TABLE") {
      record.meeting_days ||= record.day_of_week ?? "";
      if (!record.meeting_time && record.start_time && record.end_time) {
        record.meeting_time = `${record.start_time}-${record.end_time}`;
      }
    }
    record.source_label = table.caption || `visible table ${table.index + 1}`;
    if (!hasRequiredFields(spec, record)) {
      warnings.push({
        code: "MALFORMED_ROW",
        severity: "WARNING",
        message: `Skipped row ${rowIndex + 1} because a required academic column was empty.`,
      });
      continue;
    }
    records.push(record);
  }
  return records;
}

function buildColumnMap(
  spec: ExtractionSpec,
  headers: readonly string[],
): Map<string, number> {
  const normalizedHeaders = headers.map(normalizeHeader);
  const columnByField = new Map<string, number>();
  for (const [field, aliases] of Object.entries(spec.aliases)) {
    const index = normalizedHeaders.findIndex((header) =>
      aliases.includes(header),
    );
    if (index >= 0) {
      columnByField.set(field, index);
    }
  }
  return columnByField;
}

function warnForUnknownColumns(
  spec: ExtractionSpec,
  headers: readonly string[],
  warnings: ExtensionExtractionWarning[],
): void {
  const knownAliases = new Set(Object.values(spec.aliases).flat());
  const unknownHeaders = headers
    .map(normalizeHeader)
    .filter((header) => header && !knownAliases.has(header));
  if (unknownHeaders.length > 0) {
    warnings.push({
      code: "UNKNOWN_COLUMNS",
      severity: "INFO",
      message: `Ignored unsupported visible columns: ${unknownHeaders.join(", ")}.`,
    });
  }
}

function hasRequiredFields(
  spec: ExtractionSpec,
  record: ExtractedRecord,
): boolean {
  return spec.requiredFields.every(
    (field) => (record[field] ?? "").trim().length > 0,
  );
}

function normalizeHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function normalizeValue(field: string, value: string): string {
  const cleaned = value.replace(/\s+/g, " ").trim();
  if (field === "course_code") {
    return cleaned.toUpperCase().replace(/^([A-Z]+)[-\s]*(\d)/, "$1 $2");
  }
  if (field === "modality") {
    return enumLike(cleaned);
  }
  if (
    field === "status" ||
    field === "attempt_status" ||
    field === "day_of_week"
  ) {
    return enumLike(cleaned);
  }
  return cleaned;
}

function enumLike(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function contentFor(spec: ExtractionSpec, records: ExtractedRecord[]): string {
  if (spec.mimeType === "application/json") {
    return `${JSON.stringify(
      {
        source_type: SOURCE_TYPE,
        staging_only: true,
        page_type: spec.pageType,
        requirements: records,
        disclaimers: EXTENSION_STAGING_DISCLAIMERS,
      },
      null,
      2,
    )}\n`;
  }
  return csvFor(spec.fields, records);
}

function csvFor(
  fields: readonly string[],
  records: readonly ExtractedRecord[],
): string {
  const lines = [
    fields.join(","),
    ...records.map((record) =>
      fields.map((field) => csvCell(record[field] ?? "")).join(","),
    ),
  ];
  return `${lines.join("\n")}\n`;
}

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function noDataExtraction(
  snapshot: AcademicPageSnapshot,
  warningCode: string,
  extractedAt: string,
): BrowserExtensionExtraction {
  const warnings: ExtensionExtractionWarning[] = [
    {
      code: warningCode,
      severity: "WARNING",
      message: "No recognizable academic table was found on the visible page.",
    },
  ];
  return {
    pageType: "UNKNOWN_PAGE",
    importType: "UNKNOWN",
    sourceType: SOURCE_TYPE,
    isOfficial: false,
    title: snapshot.title,
    url: safeUrl(snapshot.url),
    fileName: "browser-extension-unknown-page.json",
    fileMimeType: "application/json",
    content: `${JSON.stringify(
      {
        source_type: SOURCE_TYPE,
        staging_only: true,
        page_type: "UNKNOWN_PAGE",
        records: [],
        disclaimers: EXTENSION_STAGING_DISCLAIMERS,
      },
      null,
      2,
    )}\n`,
    records: [],
    warnings,
    requiresReview: true,
    extractedAt,
  };
}

function fileName(spec: ExtractionSpec): string {
  return `${spec.fileBaseName}${spec.mimeType === "application/json" ? ".json" : ".csv"}`;
}

function safeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "";
  }
}
