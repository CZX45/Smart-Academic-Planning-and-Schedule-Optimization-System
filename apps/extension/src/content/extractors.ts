import { readVisibleTables } from "./table-reader.js";
import {
  BOUNDED_EXTRACTION_LIMITS,
  limitAcademicPageSnapshot,
} from "./snapshot-limits.js";
import type {
  AcademicPageSnapshot,
  AcademicPageType,
  BrowserExtensionDataImportRequest,
  BrowserExtensionExtraction,
  DataImportType,
  ExtensionDiagnostics,
  ExtensionExtractionWarning,
  ExtractedRecord,
  TableSnapshot,
} from "../shared/types.js";
import {
  detectKeanPageDefinition,
  isKeanHostUrl,
  isKeanStudentPortalUrl,
  KEAN_SOURCE_LABEL,
  type KeanExtractionStrategy,
  type KeanPageDefinition,
} from "../shared/kean.js";

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
  expectedFields?: readonly string[];
  missingFieldWarningCodes?: Readonly<Record<string, string>>;
  redactUnknownColumns?: boolean;
  sourceLabel?: "KEAN_STUDENT_PORTAL";
  manualReviewWarning?: ExtensionExtractionWarning;
};

type TableCandidate = {
  spec: ExtractionSpec;
  table: TableSnapshot;
  score: number;
};

type ParserDiagnostics = Pick<
  ExtensionDiagnostics,
  | "academicTablesDetected"
  | "academicTablesParsed"
  | "academicRowsParsed"
  | "academicRowsSkipped"
  | "academicRowsCapped"
  | "parserWarningCodes"
>;

type MyProgressParseResult = {
  records: ExtractedRecord[];
  diagnostics: ParserDiagnostics;
};

function cleanText(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

const DEGREE_AUDIT_MANUAL_REVIEW_WARNING: ExtensionExtractionWarning = {
  code: "DEGREE_AUDIT_REQUIRES_MANUAL_REVIEW",
  severity: "WARNING",
  message:
    "Degree-audit rows are staged for manual review and are not official policy.",
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
  manualReviewWarning: DEGREE_AUDIT_MANUAL_REVIEW_WARNING,
};

const MY_PROGRESS_COURSE_SPEC: ExtractionSpec = {
  pageType: "KEAN_MY_PROGRESS_PAGE",
  importType: "DEGREE_AUDIT_EXPORT",
  fileBaseName: "kean-student-portal-my-progress",
  mimeType: "application/json",
  fields: [
    "requirements",
    "requirement_section",
    "status",
    "raw_course_code",
    "course_code",
    "course_title",
    "grade",
    "term_code",
    "credits",
    "source_page_type",
    "type",
    "source_label",
  ],
  aliases: {
    requirements: ["requirement", "requirements", "section"],
    requirement_section: [
      "requirement_section",
      "requirement",
      "requirements",
      "section",
    ],
    status: ["status", "course_status", "attempt_status"],
    course_code: ["course", "course_code", "code"],
    raw_course_code: ["course", "course_code", "code"],
    course_title: ["title", "course_title", "name"],
    grade: ["grade", "final_grade"],
    term_code: ["term", "term_code", "semester"],
    credits: ["credits", "credit_hours", "credit"],
  },
  requiredFields: ["status", "course_code"],
  manualReviewWarning: DEGREE_AUDIT_MANUAL_REVIEW_WARNING,
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
    "prerequisites",
    "restrictions",
    "source_label",
  ],
  aliases: {
    course_code: ["course_code", "course", "code"],
    course_title: ["course_title", "title", "name"],
    credits: ["credits", "credit_hours"],
    course_level: ["level", "course_level"],
    department: ["department", "subject"],
    description: ["description"],
    prerequisites: ["prerequisite", "prerequisites", "prereqs"],
    restrictions: ["restriction", "restrictions", "notes"],
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

const SPEC_BY_KEAN_STRATEGY: Record<KeanExtractionStrategy, ExtractionSpec> = {
  TRANSCRIPT: TRANSCRIPT_SPEC,
  DEGREE_AUDIT: DEGREE_AUDIT_SPEC,
  MY_PROGRESS: MY_PROGRESS_COURSE_SPEC,
  COURSE_CATALOG: CATALOG_SPEC,
  SECTION_SCHEDULE: SECTION_SPEC,
};

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
  snapshot = limitAcademicPageSnapshot(snapshot);
  const extractedAt = "1970-01-01T00:00:00.000Z";
  if (isKeanHostUrl(snapshot.url) && !isKeanStudentPortalUrl(snapshot.url)) {
    return noDataExtraction(
      snapshot,
      "OUTSIDE_KEAN_STUDENT_PORTAL",
      extractedAt,
      "The page is on the Kean host but outside the supported Student portal prefix.",
      KEAN_SOURCE_LABEL,
    );
  }

  const keanDefinition = detectKeanPageDefinition(
    snapshot.url,
    snapshot.title,
    visibleTextForDetection(snapshot),
  );
  if (isKeanStudentPortalUrl(snapshot.url) && !keanDefinition) {
    return noDataExtraction(
      snapshot,
      "KEAN_PAGE_NOT_WHITELISTED",
      extractedAt,
      "This Kean Student Portal page is not one of the configured academic-planning pages.",
      KEAN_SOURCE_LABEL,
    );
  }

  const candidateTables = tablesForExtraction(snapshot);
  const candidate = keanDefinition
    ? bestCandidate(candidateTables, specsForKeanDefinition(keanDefinition))
    : bestCandidate(candidateTables);
  if (!candidate) {
    return noDataExtraction(
      snapshot,
      keanDefinition
        ? "KEAN_WHITELISTED_PAGE_NO_ACADEMIC_TABLE_FOUND"
        : "NO_ACADEMIC_TABLE_FOUND",
      extractedAt,
      "No recognizable academic table was found on the visible page.",
      keanDefinition ? KEAN_SOURCE_LABEL : undefined,
    );
  }

  const warnings: ExtensionExtractionWarning[] = [...(snapshot.warnings ?? [])];
  const parseResult = isMyProgressCourseSpec(candidate.spec)
    ? recordsFromMyProgressTables(candidate.spec, candidateTables, warnings)
    : {
        records: recordsFromTable(candidate.spec, candidate.table, warnings),
        diagnostics: emptyParserDiagnostics(),
      };
  const { records } = parseResult;
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
  if (candidate.spec.sourceLabel === KEAN_SOURCE_LABEL) {
    warnings.push({
      code: "KEAN_IMPORT_NON_OFFICIAL_REVIEW_REQUIRED",
      severity: "WARNING",
      message:
        "Kean Student Portal browser-extension data is non-official and requires Phase 7B review.",
    });
  }

  return {
    pageType: candidate.spec.pageType,
    importType: candidate.spec.importType,
    sourceType: SOURCE_TYPE,
    ...(candidate.spec.sourceLabel
      ? { sourceLabel: candidate.spec.sourceLabel }
      : {}),
    isOfficial: false,
    title: snapshot.title,
    url: safeUrl(snapshot.url),
    fileName: fileName(candidate.spec),
    fileMimeType: candidate.spec.mimeType,
    content: contentFor(candidate.spec, records),
    records,
    warnings,
    diagnostics: diagnosticsForExtraction(
      snapshot,
      candidate.spec.pageType,
      matchedPageMarker(snapshot, keanDefinition),
      records,
      candidate.spec.fields,
      warnings,
      parseResult.diagnostics,
    ),
    requiresReview: true,
    extractedAt,
  };
}

export function createDataImportRequestFromExtraction(
  studentProfileId: string,
  extraction: BrowserExtensionExtraction,
): BrowserExtensionDataImportRequest {
  const sourceReferencePrefix =
    extraction.sourceLabel === KEAN_SOURCE_LABEL
      ? `${KEAN_SOURCE_LABEL} browser extension import`
      : "Browser extension visible-page import";
  return {
    student_profile_id: studentProfileId,
    import_type: extraction.importType,
    file_name: extraction.fileName,
    file_mime_type: extraction.fileMimeType,
    content: extraction.content,
    source_type: SOURCE_TYPE,
    source_reference: `${sourceReferencePrefix}: ${extraction.url}`,
  };
}

export function createDataImportRequestsFromExtractions(
  studentProfileId: string,
  extractions: readonly BrowserExtensionExtraction[],
): BrowserExtensionDataImportRequest[] {
  return extractions
    .filter((extraction) => extraction.records.length > 0)
    .map((extraction) =>
      createDataImportRequestFromExtraction(studentProfileId, extraction),
    );
}

function bestCandidate(
  tables: TableSnapshot[],
  specs: readonly ExtractionSpec[] = SPECS,
): TableCandidate | null {
  const candidates = tables.flatMap((table) =>
    specs.map((spec) => ({
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

function tablesForExtraction(snapshot: AcademicPageSnapshot): TableSnapshot[] {
  return [
    ...snapshot.tables,
    ...myProgressCourseTablesFromSnapshot(snapshot, snapshot.tables.length),
  ];
}

function emptyParserDiagnostics(): ParserDiagnostics {
  return {
    academicTablesDetected: 0,
    academicTablesParsed: 0,
    academicRowsParsed: 0,
    academicRowsSkipped: 0,
    academicRowsCapped: 0,
    parserWarningCodes: [],
  };
}

function isMyProgressCourseSpec(spec: ExtractionSpec): boolean {
  return (
    spec.pageType === "KEAN_MY_PROGRESS_PAGE" &&
    spec.importType === "DEGREE_AUDIT_EXPORT" &&
    spec.requiredFields.includes("status") &&
    spec.requiredFields.includes("course_code")
  );
}

function recordsFromMyProgressTables(
  spec: ExtractionSpec,
  tables: readonly TableSnapshot[],
  warnings: ExtensionExtractionWarning[],
): MyProgressParseResult {
  const parserWarningsStart = warnings.length;
  const diagnostics = emptyParserDiagnostics();
  const relevantTables = tables.filter((table) => scoreTable(spec, table) > 0);
  diagnostics.academicTablesDetected = relevantTables.length;
  const records: ExtractedRecord[] = [];

  for (const table of relevantTables) {
    const parsedBeforeTable = records.length;
    const columnByField = buildMyProgressColumnMap(spec, table.headers);
    let currentRequirement = requirementLabelFromTable(table);
    warnForUnknownColumns(spec, table.headers, warnings);

    for (const row of table.rows) {
      const rowText = cleanText(row.join(" "));
      if (!rowText || isMyProgressHeader(rowText)) {
        continue;
      }
      const rowRequirement = requirementLabelFromCells(row);
      if (rowRequirement) {
        currentRequirement = rowRequirement;
        continue;
      }
      const record = myProgressRecordFromRow(
        spec,
        table,
        row,
        columnByField,
        currentRequirement,
      );
      if (!hasRequiredFields(spec, record)) {
        diagnostics.academicRowsSkipped += 1;
        continue;
      }
      if (records.length >= BOUNDED_EXTRACTION_LIMITS.maxTotalRows) {
        diagnostics.academicRowsCapped += 1;
        continue;
      }
      records.push(record);
    }

    if (records.length > parsedBeforeTable) {
      diagnostics.academicTablesParsed += 1;
    }
  }

  diagnostics.academicRowsParsed = records.length;
  if (diagnostics.academicRowsSkipped > 0) {
    pushUniqueWarning(warnings, {
      code: "MY_PROGRESS_ROWS_SKIPPED",
      severity: "INFO",
      message: `Skipped ${diagnostics.academicRowsSkipped} visible MyProgress row(s) that were missing required academic fields.`,
    });
  }
  if (diagnostics.academicRowsCapped > 0) {
    pushUniqueWarning(warnings, {
      code: "MY_PROGRESS_ROWS_CAPPED",
      severity: "WARNING",
      message: `Stopped after ${records.length} MyProgress row(s) to keep extraction bounded.`,
    });
  }
  if (isPartialMyProgressParse(diagnostics, warnings)) {
    pushUniqueWarning(warnings, {
      code: "MY_PROGRESS_PARTIAL_TABLE_PARSE",
      severity: "WARNING",
      message:
        "Only a subset of visible MyProgress rows was parsed. Some requirement tables may need parser support.",
    });
  }
  diagnostics.parserWarningCodes = warnings
    .slice(parserWarningsStart)
    .map((warning) => warning.code);
  return { records, diagnostics };
}

function myProgressRecordFromRow(
  spec: ExtractionSpec,
  table: TableSnapshot,
  row: readonly string[],
  columnByField: ReadonlyMap<string, number>,
  currentRequirement: string,
): ExtractedRecord {
  const record = spec.fields.reduce<ExtractedRecord>((current, field) => {
    const columnIndex = columnByField.get(field);
    current[field] =
      columnIndex === undefined
        ? ""
        : normalizeValue(field, row[columnIndex] ?? "");
    return current;
  }, {});
  const rawCourseIndex =
    columnByField.get("raw_course_code") ?? columnByField.get("course_code");
  const rawCourseCode =
    rawCourseIndex === undefined
      ? (record.course_code ?? "")
      : (row[rawCourseIndex] ?? "");
  const parsedCourse = splitCourseCodeAndTitle(rawCourseCode);
  record.raw_course_code = cleanText(rawCourseCode);
  if (parsedCourse) {
    record.course_code = parsedCourse.courseCode;
    record.course_title ||= parsedCourse.courseTitle;
  }

  const requirement =
    record.requirement_section || record.requirements || currentRequirement;
  record.requirements = requirement;
  record.requirement_section = requirement;
  record.source_page_type = spec.pageType;
  record.type = spec.importType;
  record.source_label = table.caption || `visible table ${table.index + 1}`;
  return record;
}

function splitCourseCodeAndTitle(
  value: string,
): { courseCode: string; courseTitle: string } | null {
  const match = cleanText(value).match(
    /^([A-Z]{2,6})[*\s-]*(\d{3,4}[A-Z]?)(?:\s*[-:]\s*|\s+)?(.*)$/i,
  );
  if (!match?.[1] || !match[2]) {
    return null;
  }
  return {
    courseCode: `${match[1].toUpperCase()} ${match[2].toUpperCase()}`,
    courseTitle: cleanText(match[3] ?? ""),
  };
}

function requirementLabelFromTable(table: TableSnapshot): string {
  const caption = cleanText(table.caption);
  return caption.length <= 160 ? caption : "";
}

function requirementLabelFromCells(cells: readonly string[]): string {
  const nonEmptyCells = cells.map(cleanText).filter(Boolean);
  if (nonEmptyCells.length !== 1) {
    return "";
  }
  const [value] = nonEmptyCells;
  if (!value || value.length > 160 || looksLikeMyProgressCourseRow(value)) {
    return "";
  }
  if (
    isMyProgressHeader(value) ||
    /\b[A-Z]{2,6}[*\s-]?\d{3,4}[A-Z]?\b/.test(value)
  ) {
    return "";
  }
  return value;
}

function isPartialMyProgressParse(
  diagnostics: ParserDiagnostics,
  warnings: readonly ExtensionExtractionWarning[],
): boolean {
  if (diagnostics.academicTablesDetected === 0) {
    return false;
  }
  return (
    diagnostics.academicRowsSkipped > 0 ||
    diagnostics.academicRowsCapped > 0 ||
    warnings.some((warning) => warning.code === "EXTRACTION_LIMIT_REACHED")
  );
}

function pushUniqueWarning(
  warnings: ExtensionExtractionWarning[],
  warning: ExtensionExtractionWarning,
): void {
  if (!warnings.some((current) => current.code === warning.code)) {
    warnings.push(warning);
  }
}

function myProgressCourseTablesFromSnapshot(
  snapshot: AcademicPageSnapshot,
  startingIndex: number,
): TableSnapshot[] {
  const blocks = snapshot.rowLikeBlocks ?? [];
  if (blocks.length === 0) {
    return [];
  }
  const rows: string[][] = [];
  let currentRequirement = "";
  for (const block of blocks) {
    const blockText = cleanText(
      block.cells && block.cells.length > 0
        ? block.cells.join(" ")
        : block.text,
    );
    if (!blockText) {
      continue;
    }
    if (isMyProgressHeader(blockText)) {
      continue;
    }
    const requirement = requirementLabelFromBlock(blockText);
    if (requirement) {
      currentRequirement = requirement;
      continue;
    }
    const parsed = myProgressCourseRow(blockText, currentRequirement);
    if (parsed) {
      rows.push(parsed);
    }
  }
  if (rows.length === 0) {
    return [];
  }
  return [
    {
      index: startingIndex,
      caption: "Kean MyProgress row-like blocks",
      headers: [
        "Requirement",
        "Status",
        "Course",
        "Title",
        "Grade",
        "Term",
        "Credits",
      ],
      rows,
    },
  ];
}

function isMyProgressHeader(value: string): boolean {
  const header = normalizeHeader(value);
  return (
    header.includes("status") &&
    header.includes("course") &&
    header.includes("term") &&
    header.includes("credit")
  );
}

function requirementLabelFromBlock(value: string): string {
  if (looksLikeMyProgressCourseRow(value) || isMyProgressHeader(value)) {
    return "";
  }
  return /\brequirements?\b/i.test(value) && value.length <= 160 ? value : "";
}

function looksLikeMyProgressCourseRow(value: string): boolean {
  return myProgressCourseRow(value, "") !== null;
}

function myProgressCourseRow(
  value: string,
  requirement: string,
): string[] | null {
  const statusMatch = value.match(
    /^(Completed|Reg(?:istered)?|Planned|Fully Planned|Not Started|In[- ]Progress|Attempted|Failed|Withdrawn)\s+/i,
  );
  if (!statusMatch?.[1]) {
    return null;
  }
  const status = statusMatch[1];
  const remainder = value.slice(statusMatch[0].length).trim();
  const courseMatch = remainder.match(/^([A-Z]{2,5})[*\s-]?(\d{3,4}[A-Z]?)\b/i);
  if (!courseMatch?.[1] || !courseMatch[2]) {
    return null;
  }
  const course = `${courseMatch[1].toUpperCase()} ${courseMatch[2].toUpperCase()}`;
  let details = remainder.slice(courseMatch[0].length).trim();
  let credits = "";
  let term = "";
  let grade = "";
  const tokens = details.split(/\s+/).filter(Boolean);
  const lastToken = (): string => tokens[tokens.length - 1] ?? "";
  if (/^\d+(?:\.\d+)?$/.test(lastToken())) {
    credits = tokens.pop() ?? "";
  }
  if (/^(?:\d{4}[A-Z]{2,4}[A-Z]?|[A-Z]{2,4}\d{2,4})$/i.test(lastToken())) {
    term = tokens.pop() ?? "";
  }
  if (/^(?:A|A-|B\+|B|B-|C\+|C|C-|D\+|D|D-|F|P|PR|IP|W)$/i.test(lastToken())) {
    grade = tokens.pop() ?? "";
  }
  details = tokens.join(" ");
  return [requirement, status, course, details, grade, term, credits];
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
  warnForMissingExpectedFields(spec, table.headers, warnings);
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
    if (spec.importType === "SECTION_SCHEDULE") {
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

function buildMyProgressColumnMap(
  spec: ExtractionSpec,
  headers: readonly string[],
): Map<string, number> {
  const columnByField = buildColumnMap(spec, headers);
  if (columnByField.has("course_title")) {
    return columnByField;
  }

  const normalizedHeaders = headers.map(normalizeHeader);
  const statusIndex = normalizedHeaders.findIndex((header) =>
    spec.aliases.status?.includes(header),
  );
  if (statusIndex < 0) {
    return columnByField;
  }
  const courseIndex = statusIndex + 1;
  const titleIndex = courseIndex + 1;
  const gradeIndex = titleIndex + 1;
  const termIndex = gradeIndex + 1;
  const creditsIndex = termIndex + 1;
  const matchesBlankTitleShape =
    spec.aliases.course_code?.includes(normalizedHeaders[courseIndex] ?? "") ===
      true &&
    normalizedHeaders[titleIndex] === "" &&
    spec.aliases.grade?.includes(normalizedHeaders[gradeIndex] ?? "") === true &&
    spec.aliases.term_code?.includes(normalizedHeaders[termIndex] ?? "") ===
      true &&
    spec.aliases.credits?.includes(normalizedHeaders[creditsIndex] ?? "") ===
      true;

  if (matchesBlankTitleShape) {
    columnByField.set("course_title", titleIndex);
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
      message: spec.redactUnknownColumns
        ? "Ignored unsupported visible columns."
        : `Ignored unsupported visible columns: ${unknownHeaders.join(", ")}.`,
    });
  }
}

function warnForMissingExpectedFields(
  spec: ExtractionSpec,
  headers: readonly string[],
  warnings: ExtensionExtractionWarning[],
): void {
  if (!spec.expectedFields || !spec.missingFieldWarningCodes) {
    return;
  }
  const normalizedHeaders = new Set(headers.map(normalizeHeader));
  const missingFields = spec.expectedFields.filter(
    (field) =>
      !spec.aliases[field]?.some((alias) => normalizedHeaders.has(alias)),
  );
  for (const field of missingFields) {
    warnings.push({
      code:
        spec.missingFieldWarningCodes[field] ?? "KEAN_EXPECTED_FIELD_MISSING",
      severity: "INFO",
      message: `Expected academic-planning field ${field} was not visible on this page.`,
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
    return cleaned.toUpperCase().replace(/^([A-Z]+)[*\-\s]*(\d)/, "$1 $2");
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
  warningMessage = "No recognizable academic table was found on the visible page.",
  sourceLabel?: "KEAN_STUDENT_PORTAL",
): BrowserExtensionExtraction {
  const warnings: ExtensionExtractionWarning[] = [
    ...(snapshot.warnings ?? []),
    {
      code: warningCode,
      severity: "WARNING",
      message: warningMessage,
    },
  ];
  return {
    pageType: "UNKNOWN_PAGE",
    importType: "UNKNOWN",
    sourceType: SOURCE_TYPE,
    ...(sourceLabel ? { sourceLabel } : {}),
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
    diagnostics: diagnosticsForExtraction(
      snapshot,
      "UNKNOWN_PAGE",
      warningCode,
      [],
      [],
      warnings,
    ),
    requiresReview: true,
    extractedAt,
  };
}

function fileName(spec: ExtractionSpec): string {
  return `${spec.fileBaseName}${spec.mimeType === "application/json" ? ".json" : ".csv"}`;
}

function specsForKeanDefinition(
  definition: KeanPageDefinition,
): ExtractionSpec[] {
  const bases =
    definition.extractionStrategy === "MY_PROGRESS"
      ? [MY_PROGRESS_COURSE_SPEC, DEGREE_AUDIT_SPEC]
      : [SPEC_BY_KEAN_STRATEGY[definition.extractionStrategy]];
  return bases.map((base) => specForKeanDefinition(definition, base));
}

function specForKeanDefinition(
  definition: KeanPageDefinition,
  base: ExtractionSpec,
): ExtractionSpec {
  return {
    ...base,
    pageType: definition.key,
    importType: definition.importType,
    fileBaseName: fileBaseNameForKeanDefinition(definition),
    expectedFields: definition.expectedFields,
    missingFieldWarningCodes: definition.warningCodesForMissingFields,
    redactUnknownColumns: true,
    sourceLabel: KEAN_SOURCE_LABEL,
  };
}

function fileBaseNameForKeanDefinition(definition: KeanPageDefinition): string {
  const suffix = definition.key
    .toLowerCase()
    .replace(/^kean_/, "")
    .replace(/_page$/, "")
    .replace(/_/g, "-");
  return `kean-student-portal-${suffix}`;
}

function visibleTextForDetection(snapshot: AcademicPageSnapshot): string {
  return [
    ...(snapshot.headings ?? []),
    snapshot.visibleText ?? "",
    ...(snapshot.rowLikeBlocks ?? []).map((block) => block.text),
    ...snapshot.tables.flatMap((table) => [table.caption, ...table.headers]),
  ]
    .filter(Boolean)
    .join(" ");
}

function matchedPageMarker(
  snapshot: AcademicPageSnapshot,
  definition: KeanPageDefinition | null,
): string {
  if (!definition) {
    return "generic-academic-table";
  }
  const normalizedPath = safeUrl(snapshot.url).toLowerCase();
  const haystack =
    `${snapshot.title} ${visibleTextForDetection(snapshot)}`.toLowerCase();
  return (
    definition.routeMarkers.find((marker) =>
      normalizedPath.includes(marker.toLowerCase()),
    ) ??
    definition.visibleTextMarkers.find((marker) =>
      haystack.includes(marker.toLowerCase()),
    ) ??
    definition.key
  );
}

function diagnosticsForExtraction(
  snapshot: AcademicPageSnapshot,
  detectedPageType: BrowserExtensionExtraction["pageType"],
  matchedPageMarker: string,
  records: readonly ExtractedRecord[],
  academicFields: readonly string[],
  warnings: readonly ExtensionExtractionWarning[],
  parserDiagnostics: ParserDiagnostics = emptyParserDiagnostics(),
): ExtensionDiagnostics {
  const visibleAcademicFields = academicFields.filter(
    (field) => field !== "source_label",
  );
  const extractedAcademicFieldCount = records.reduce(
    (count, record) =>
      count +
      visibleAcademicFields.filter(
        (field) => (record[field] ?? "").trim().length > 0,
      ).length,
    0,
  );
  const tableRowsFound = snapshot.tables.reduce(
    (count, table) => count + table.rows.length,
    0,
  );
  const rowLikeBlocksFound =
    snapshot.snapshotMetadata?.rowLikeBlocksFound ??
    snapshot.rowLikeBlocks?.length ??
    0;
  const visibleTextLength =
    snapshot.snapshotMetadata?.visibleTextLength ??
    snapshot.visibleText?.length ??
    0;
  const bounded =
    snapshot.snapshotMetadata?.bounded === true ||
    warnings.some((warning) => warning.code === "EXTRACTION_LIMIT_REACHED");
  return {
    currentUrl: safeUrl(snapshot.url),
    detectedPageType,
    matchedPageMarker,
    tablesFound: snapshot.tables.length,
    rowsFound: tableRowsFound + rowLikeBlocksFound,
    visibleTextLength,
    rowLikeBlocksFound,
    extractedAcademicFieldCount,
    ignoredSensitiveFieldCount: 0,
    directSnapshotRan: snapshot.snapshotMetadata?.directSnapshotRan === true,
    bounded,
    warningCodes: warnings.map((warning) => warning.code),
    ...parserDiagnostics,
  };
}

function safeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "";
  }
}
