export type AcademicPageType =
  | "TRANSCRIPT_TABLE"
  | "DEGREE_AUDIT_TABLE"
  | "COURSE_CATALOG_TABLE"
  | "SECTION_SEARCH_TABLE"
  | "KEAN_TRANSCRIPT_PAGE"
  | "KEAN_DEGREE_AUDIT_PAGE"
  | "KEAN_MY_PROGRESS_PAGE"
  | "KEAN_COURSE_CATALOG_PAGE"
  | "KEAN_SECTION_SEARCH_PAGE"
  | "KEAN_STUDENT_PLANNING_PAGE"
  | "KEAN_SCHEDULE_PAGE"
  | "UNKNOWN_PAGE";

export type DataImportType =
  | "UNOFFICIAL_TRANSCRIPT"
  | "DEGREE_AUDIT_EXPORT"
  | "COURSE_CATALOG"
  | "SECTION_SCHEDULE"
  | "GENERIC_CSV"
  | "GENERIC_JSON"
  | "UNKNOWN";

export type ExtensionWarningSeverity = "INFO" | "WARNING" | "ERROR";

export type ExtractedRecord = Record<string, string>;

export type ExtensionExtractionWarning = {
  code: string;
  severity: ExtensionWarningSeverity;
  message: string;
};

export type TableSnapshot = {
  index: number;
  caption: string;
  headers: string[];
  rows: string[][];
};

export type RowLikeBlockSnapshot = {
  index: number;
  text: string;
  cells?: string[];
  section?: string;
};

export type AcademicPageSnapshotMetadata = {
  directSnapshotRan?: boolean;
  visibleTextLength?: number;
  rowLikeBlocksFound?: number;
  bounded?: boolean;
};

export type AcademicPageSnapshot = {
  title: string;
  url: string;
  tables: TableSnapshot[];
  headings?: string[];
  visibleText?: string;
  rowLikeBlocks?: RowLikeBlockSnapshot[];
  snapshotMetadata?: AcademicPageSnapshotMetadata;
  warnings?: ExtensionExtractionWarning[];
};

export type ExtensionDiagnostics = {
  currentUrl: string;
  detectedPageType: AcademicPageType;
  matchedPageMarker: string;
  tablesFound: number;
  rowsFound: number;
  visibleTextLength: number;
  rowLikeBlocksFound: number;
  extractedAcademicFieldCount: number;
  ignoredSensitiveFieldCount: number;
  directSnapshotRan: boolean;
  bounded: boolean;
  warningCodes: string[];
  academicTablesDetected: number;
  academicTablesParsed: number;
  academicRowsParsed: number;
  academicRowsSkipped: number;
  academicRowsCapped: number;
  parserWarningCodes: string[];
};

export type BrowserExtensionExtraction = {
  pageType: AcademicPageType;
  importType: DataImportType;
  sourceType: "BROWSER_EXTENSION";
  sourceLabel?: "KEAN_STUDENT_PORTAL";
  isOfficial: false;
  title: string;
  url: string;
  fileName: string;
  fileMimeType: "text/csv" | "application/json";
  content: string;
  records: ExtractedRecord[];
  warnings: ExtensionExtractionWarning[];
  diagnostics: ExtensionDiagnostics;
  requiresReview: boolean;
  extractedAt: string;
};

export type BrowserExtensionDataImportRequest = {
  student_profile_id: string;
  import_type: DataImportType;
  file_name: string;
  file_mime_type: string;
  content: string;
  source_type: "BROWSER_EXTENSION";
  source_reference: string;
  page_type: AcademicPageType;
  extracted_record_count: number;
  visible_row_count: number;
  academic_field_count: number;
  warnings: ExtensionExtractionWarning[];
  diagnostics: ExtensionDiagnostics;
  bounded: boolean;
  truncated: boolean;
};
