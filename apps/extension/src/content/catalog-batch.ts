import type {
  BrowserExtensionExtraction,
  ExtractedRecord,
  ExtensionExtractionWarning,
} from "../shared/types.js";
import type {
  CatalogPageReadyDiagnostics,
  CatalogSubjectNavigationDiagnostics,
} from "./catalog-batch-page.js";
export {
  CATALOG_BATCH_ACCEPTANCE_REVISION,
  CATALOG_FULL_CAPTURE_UNLOCKED,
} from "../shared/catalog-batch-version.js";
import { CATALOG_BATCH_ACCEPTANCE_REVISION } from "../shared/catalog-batch-version.js";

export const CATALOG_BATCH_LIMITS = {
  concurrency: 1,
  pageIntervalMs: 2_500,
  maxSubjects: 200,
  maxPages: 2_500,
  maxPagesPerSubject: 50,
  maxRecords: 25_000,
  timeoutMs: 45 * 60 * 1_000,
  retryLimit: 1,
} as const;

export const LEGACY_CATALOG_BATCH_RUNNER_REVISION = "LEGACY_UNVERSIONED";
export const CATALOG_BATCH_ARCHIVE_LIMIT = 20;

export type CatalogBatchStatus =
  | "RUNNING"
  | "PAUSED"
  | "CANCELLED"
  | "COMPLETED"
  | "FAILED";

export type CatalogBatchMode = "BOUNDED_ACCEPTANCE" | "FULL";

export type CatalogBatchProcessingStage =
  | "CAPTURE_RUNNING"
  | "CAPTURE_COMPLETED"
  | "LOCAL_STAGING"
  | "LOCAL_VALIDATION"
  | "LOCAL_REVIEW"
  | "LOCAL_DRY_RUN"
  | "LOCAL_APPLY"
  | "MYPROGRESS_REMAP"
  | "COMPLETED";

export const CATALOG_BATCH_LOCAL_PROCESSING_STAGES = [
  "LOCAL_STAGING",
  "LOCAL_VALIDATION",
  "LOCAL_REVIEW",
  "LOCAL_DRY_RUN",
  "LOCAL_APPLY",
  "MYPROGRESS_REMAP",
] as const satisfies readonly CatalogBatchProcessingStage[];

export type CatalogSchoolTabUrlClassification =
  | "CATALOG_LANDING"
  | "CATALOG_SEARCH_RESULT"
  | "AUTHENTICATION"
  | "OUT_OF_SCOPE"
  | "UNAVAILABLE";

export type CatalogScriptResultKind =
  | "VALUE"
  | "NULL_RESULT"
  | "MISSING_RESULT"
  | "EMPTY_RESULTS"
  | "UNEXPECTED_VALUE";

export type CatalogBatchErrorContext = {
  phase: CatalogBatchStateMachineCheckpoint;
  subject: string | null;
  page: number;
  urlClassification: CatalogSchoolTabUrlClassification;
  revision: number;
  timestamp: string;
  diagnostics: CatalogPageReadyDiagnostics | null;
};

export type CatalogBatchOperation =
  | "INITIALIZE_FIRST_SUBJECT"
  | "GET_AUTHORIZED_TAB"
  | "NAVIGATE_TO_LANDING"
  | "PERSIST_STATE"
  | "WATCH_SUBJECT_NAVIGATION"
  | "START_SUBJECT_SEARCH"
  | "WATCH_RESULT_PAGE"
  | "HANDLE_PAGE_SIGNAL"
  | "CAPTURE_PAGE"
  | "ADVANCE_PAGE"
  | "PROCESS_SUBJECT"
  | "RESUME_BATCH"
  | "UNKNOWN";

export type CatalogBatchFailureDiagnostic = {
  safeErrorName: string;
  safeErrorMessage: string;
  safeStack: string;
  safeCause: string | null;
  phase: CatalogBatchStateMachineCheckpoint;
  operation: CatalogBatchOperation;
  checkpoint: CatalogBatchStateMachineCheckpoint;
  runRevision: string;
  navigationRevision: number;
  returnedResultKind: CatalogScriptResultKind | null;
  tabUrlClassification: CatalogSchoolTabUrlClassification;
  subjectCode: string | null;
  providerActionsWritten: "NO";
  timestamp: string;
};

export type CatalogBatchTransition =
  | "SUBJECTS_DISCOVERED"
  | "SUBJECT_NAVIGATION_REQUESTED"
  | "WAITING_FOR_RESULT_PAGE"
  | "PAGE_READY"
  | "PAGE_CAPTURED"
  | "PAGE_NAVIGATION_REQUESTED"
  | "LAST_PAGE_CONFIRMED"
  | "SUBJECT_PROCESSING"
  | "SUBJECT_COMPLETED"
  | "LANDING_NAVIGATION_REQUESTED"
  | "PAUSED"
  | "RESUMED"
  | "CANCELLED"
  | "FAILED"
  | "COMPLETED"
  | "LEGACY_STATE_RESTORED";

export type CatalogBatchStateMachineCheckpoint =
  | "RUN_CREATED"
  | "SUBJECT_DISCOVERY_STARTED"
  | "SUBJECT_DISCOVERY_COMPLETED"
  | "SUBJECTS_DISCOVERED"
  | "FIRST_SUBJECT_INITIALIZED"
  | "SUBJECT_START_REQUESTED"
  | "LANDING_NAVIGATING"
  | "LANDING_READY_WAIT_STARTED"
  | "LANDING_READY"
  | "LANDING_DOM_READY"
  | "SUBJECT_SELECTION_STARTED"
  | "KNOCKOUT_READY"
  | "SUBJECT_SELECTED"
  | "SUBJECT_SELECTION_VERIFIED"
  | "CATALOG_LISTING_SELECTED"
  | "CATALOG_LISTING_VERIFIED"
  | "SEARCH_SUBMIT_STARTED"
  | "SEARCH_SUBMITTED"
  | "SEARCHRESULT_NAVIGATING"
  | "SEARCHRESULT_DOM_READY"
  | "PAGE_CAPTURED"
  | "NEXT_PAGE"
  | "LAST_PAGE_CONFIRMED"
  | "SUBJECT_COMPLETED"
  | "NEXT_SUBJECT"
  | "PAUSED"
  | "RESUMED"
  | "CANCELLED"
  | "FAILED"
  | "COMPLETED"
  | "LEGACY_STATE_RESTORED";

const CATALOG_BATCH_OPERATIONS = new Set<string>([
  "INITIALIZE_FIRST_SUBJECT",
  "GET_AUTHORIZED_TAB",
  "NAVIGATE_TO_LANDING",
  "PERSIST_STATE",
  "WATCH_SUBJECT_NAVIGATION",
  "START_SUBJECT_SEARCH",
  "WATCH_RESULT_PAGE",
  "HANDLE_PAGE_SIGNAL",
  "CAPTURE_PAGE",
  "ADVANCE_PAGE",
  "PROCESS_SUBJECT",
  "RESUME_BATCH",
  "UNKNOWN",
]);

const CATALOG_BATCH_CHECKPOINTS = new Set<string>([
  "RUN_CREATED",
  "SUBJECT_DISCOVERY_STARTED",
  "SUBJECT_DISCOVERY_COMPLETED",
  "SUBJECTS_DISCOVERED",
  "FIRST_SUBJECT_INITIALIZED",
  "SUBJECT_START_REQUESTED",
  "LANDING_NAVIGATING",
  "LANDING_READY_WAIT_STARTED",
  "LANDING_READY",
  "LANDING_DOM_READY",
  "SUBJECT_SELECTION_STARTED",
  "KNOCKOUT_READY",
  "SUBJECT_SELECTED",
  "SUBJECT_SELECTION_VERIFIED",
  "CATALOG_LISTING_SELECTED",
  "CATALOG_LISTING_VERIFIED",
  "SEARCH_SUBMIT_STARTED",
  "SEARCH_SUBMITTED",
  "SEARCHRESULT_NAVIGATING",
  "SEARCHRESULT_DOM_READY",
  "PAGE_CAPTURED",
  "NEXT_PAGE",
  "LAST_PAGE_CONFIRMED",
  "SUBJECT_COMPLETED",
  "NEXT_SUBJECT",
  "PAUSED",
  "RESUMED",
  "CANCELLED",
  "FAILED",
  "COMPLETED",
  "LEGACY_STATE_RESTORED",
]);

function isCatalogBatchOperation(
  value: unknown,
): value is CatalogBatchOperation {
  return typeof value === "string" && CATALOG_BATCH_OPERATIONS.has(value);
}

function isCatalogBatchCheckpoint(
  value: unknown,
): value is CatalogBatchStateMachineCheckpoint {
  return typeof value === "string" && CATALOG_BATCH_CHECKPOINTS.has(value);
}

export type CatalogSubject = {
  code: string;
  label: string;
};

export function catalogPreparationCheckpointToken(
  batchId: string,
  navigationRevision: number,
  subjectCode: string,
): string {
  const token = `${batchId}:${navigationRevision}:${subjectCode}`;
  if (
    !batchId ||
    !Number.isInteger(navigationRevision) ||
    navigationRevision < 1 ||
    !/^[A-Z0-9]{1,8}$/.test(subjectCode) ||
    !/^[A-Za-z0-9:._-]{1,256}$/.test(token)
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_CHECKPOINT_INVALID",
      "The Catalog preparation checkpoint identity was invalid.",
    );
  }
  return token;
}

export function sanitizedCatalogSubjectNavigationDiagnostics(
  value: unknown,
): CatalogSubjectNavigationDiagnostics | null {
  if (typeof value !== "object" || value === null) return null;
  const raw = value as Record<string, unknown>;
  const booleanFields = [
    "documentReady",
    "subjectControlPresent",
    "expectedSubjectSelected",
    "catalogListingControlPresent",
    "catalogListingChecked",
    "submitControlPresent",
    "submitControlEnabled",
    "preparationSignalObserved",
    "resultSurfacePresent",
    "resultListPresent",
    "sectionResultPresent",
  ] as const;
  if (booleanFields.some((field) => typeof raw[field] !== "boolean")) {
    return null;
  }
  const boundedCount = (field: string): number | null => {
    const count = raw[field];
    return typeof count === "number" &&
      Number.isInteger(count) &&
      count >= 0 &&
      count <= CATALOG_BATCH_LIMITS.maxRecords
      ? count
      : null;
  };
  const courseCardCount = boundedCount("courseCardCount");
  const validCourseIdentityCount = boundedCount("validCourseIdentityCount");
  if (courseCardCount === null || validCourseIdentityCount === null) {
    return null;
  }
  return {
    documentReady: raw.documentReady as boolean,
    subjectControlPresent: raw.subjectControlPresent as boolean,
    expectedSubjectSelected: raw.expectedSubjectSelected as boolean,
    catalogListingControlPresent: raw.catalogListingControlPresent as boolean,
    catalogListingChecked: raw.catalogListingChecked as boolean,
    submitControlPresent: raw.submitControlPresent as boolean,
    submitControlEnabled: raw.submitControlEnabled as boolean,
    preparationSignalObserved: raw.preparationSignalObserved as boolean,
    resultSurfacePresent: raw.resultSurfacePresent as boolean,
    resultListPresent: raw.resultListPresent as boolean,
    courseCardCount,
    validCourseIdentityCount,
    sectionResultPresent: raw.sectionResultPresent as boolean,
  };
}

export type CatalogBatchFatalSignal =
  | "RATE_LIMIT"
  | "PROVIDER_ERROR"
  | "TIMEOUT";

export type CatalogBatchPage = {
  subjectCode: string;
  pageNumber: number;
  totalPages: number;
  fatalSignal: CatalogBatchFatalSignal | null;
  extraction: BrowserExtensionExtraction;
};

export type CatalogBatchState = {
  batchId: string;
  runnerRevision: string;
  acceptanceRevision: string;
  extensionVersion: string;
  createdAt: string;
  apiBaseUrl: string;
  studentProfileId: string;
  tabId: number;
  landingUrl: string;
  subjects: CatalogSubject[];
  mode: CatalogBatchMode;
  subjectLimit: number;
  boundedAcceptancePassed: boolean;
  boundedAcceptanceRevision: string | null;
  currentSubjectIndex: number;
  currentPage: number;
  expectedNavigationRevision: number;
  currentNavigationRevision: number | null;
  contentReadyRevision: number | null;
  navigationTimeoutRevision: number | null;
  preparationCheckpointRevision: number | null;
  lastTabUpdateStatus: "loading" | "complete" | null;
  lastSubjectPreparationResultKind: CatalogScriptResultKind | null;
  lastSubjectSearchResultKind: CatalogScriptResultKind | null;
  lastSubjectNavigationDiagnostics: CatalogSubjectNavigationDiagnostics | null;
  totalPagesForCurrentSubject: number | null;
  previousFirstCourseMarker: string | null;
  lastPageDiagnostics: CatalogPageReadyDiagnostics | null;
  currentSchoolTabUrlClassification: CatalogSchoolTabUrlClassification;
  processingStage: CatalogBatchProcessingStage;
  completedProcessingStages: CatalogBatchProcessingStage[];
  completedSubjects: string[];
  pendingRecords: ExtractedRecord[];
  seenCourseFingerprints: Record<string, string>;
  acceptedPageKeys: string[];
  acceptedPageFingerprints: Record<string, string>;
  subjectWarnings: ExtensionExtractionWarning[];
  coursesCaptured: number;
  uniqueCourses: number;
  duplicatesIgnored: number;
  pagesCaptured: number;
  localImportRunIds: string[];
  localReviewSessionIds: string[];
  localImportsApplied: number;
  localCoursesCreated: number;
  localCoursesUpdated: number;
  localStagedCount: number;
  localReviewValidCount: number;
  localReviewWarningCount: number;
  localAppliedCount: number;
  myprogressRunId: string | null;
  myprogressMappedCount: number;
  myprogressUnmatchedCount: number;
  myprogressTotalCount: number;
  myprogressMappedBeforeCount: number;
  myprogressRemapExecuted: boolean;
  warnings: string[];
  status: CatalogBatchStatus;
  leaseStatus: "ACTIVE" | "RELEASED";
  startedAt: string;
  updatedAt: string;
  lastCapturedAt: string | null;
  lastSourceUrl: string | null;
  lastErrorCode: string | null;
  lastErrorMessage: string | null;
  lastErrorContext: CatalogBatchErrorContext | null;
  lastSuccessfulCheckpoint: CatalogBatchStateMachineCheckpoint;
  failedOperation: CatalogBatchOperation | null;
  lastFailureDiagnostic: CatalogBatchFailureDiagnostic | null;
  lastTransition: CatalogBatchTransition;
  stateMachineCheckpoint: CatalogBatchStateMachineCheckpoint;
  lastTransitionAt: string;
  pauseReason: string | null;
  providerActionsWritten: "NO";
};

export type CatalogBatchArchiveStatus =
  | "SUPERSEDED"
  | "COMPLETED"
  | "CANCELLED"
  | "FAILED";

export type CatalogBatchArchiveReason =
  | "SUPERSEDED_BY_NEW_REVISION"
  | "REPLACED_BY_NEW_RUN";

export type CatalogBatchArchive = {
  schemaVersion: 1;
  batchRunId: string;
  archiveStatus: CatalogBatchArchiveStatus;
  reason: CatalogBatchArchiveReason;
  originalStatus: CatalogBatchStatus;
  leaseStatus: "ACTIVE" | "RELEASED";
  runnerRevision: string;
  boundedAcceptanceRevision: string | null;
  mode: CatalogBatchMode;
  subjectLimit: number;
  discoveredSubjectCount: number;
  currentSubjectIndex: number;
  completedSubjects: string[];
  coursesCaptured: number;
  uniqueCourses: number;
  duplicatesIgnored: number;
  pagesCaptured: number;
  localImportRunIds: string[];
  localReviewSessionIds: string[];
  localImportsApplied: number;
  localCoursesCreated: number;
  localCoursesUpdated: number;
  myprogressRunId: string | null;
  myprogressMappedCount: number;
  myprogressUnmatchedCount: number;
  myprogressRemapExecuted: boolean;
  warnings: string[];
  lastErrorCode: string | null;
  lastErrorMessage: string | null;
  lastErrorContext: CatalogBatchErrorContext | null;
  lastSuccessfulCheckpoint: CatalogBatchStateMachineCheckpoint;
  failedOperation: CatalogBatchOperation | null;
  lastFailureDiagnostic: CatalogBatchFailureDiagnostic | null;
  lastTransition: CatalogBatchTransition;
  stateMachineCheckpoint: CatalogBatchStateMachineCheckpoint;
  startedAt: string;
  updatedAt: string;
  archivedAt: string;
  providerActionsWritten: "NO";
};

export type CatalogBatchLifecycleNotice = {
  kind: "SUPERSEDED";
  batchRunId: string;
  previousStatus: CatalogBatchStatus;
  previousRunnerRevision: string;
  currentRunnerRevision: string;
  reason: "SUPERSEDED_BY_NEW_REVISION";
  archivedAt: string;
  providerActionsWritten: "NO";
};

export type CatalogSubjectLocalOutcome = {
  importRunId: string;
  reviewSessionId: string | null;
  createdCount: number;
  updatedCount: number;
  processingStagesCompleted: CatalogBatchProcessingStage[];
  stagedRecordCount: number;
  reviewValidCount: number;
  reviewWarningCount: number;
  appliedRecordCount: number;
  myprogressRunId: string | null;
  myprogressTotalCount: number;
  myprogressMappedBeforeCount: number;
  myprogressMappedCount: number;
  myprogressUnmatchedCount: number;
  myprogressRemapExecuted: true;
  reasonCodes: string[];
  providerActionsWritten: "NO";
  completedAt: string;
};

type CreateCatalogBatchStateInput = {
  batchId?: string;
  apiBaseUrl: string;
  studentProfileId: string;
  tabId: number;
  landingUrl: string;
  subjects: CatalogSubject[];
  startedAt: string;
  extensionVersion?: string;
  mode?: CatalogBatchMode;
  subjectLimit?: number;
  boundedAcceptancePassed?: boolean;
  boundedAcceptanceRevision?: string | null;
};

const BATCH_FIELDS = [
  "course_code",
  "normalized_code",
  "raw_visible_course_code",
  "course_title",
  "raw_visible_title",
  "credits",
  "course_level",
  "department",
  "description",
  "prerequisites",
  "corequisites",
  "minimum_grade",
  "standing_requirements",
  "restrictions",
  "raw_requisites",
  "rule_review_status",
  "source_page",
  "source_subject",
  "source_page_number",
  "capture_timestamp",
  "source_label",
] as const;

const PARSER_DRIFT_WARNING_CODES = new Set([
  "NO_IMPORTABLE_ROWS",
  "MALFORMED_ROW",
  "UNKNOWN_COLUMNS_REDACTED",
  "MISSING_EXPECTED_FIELD",
  "KEAN_CATALOG_COURSE_CODE_MISSING",
  "KEAN_CATALOG_TITLE_MISSING",
]);

export class CatalogBatchError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly safeCause?: unknown,
    readonly diagnosticContext?: {
      returnedResultKind?: CatalogScriptResultKind;
    },
  ) {
    super(`${code}: ${message}`);
    this.name = "CatalogBatchError";
  }
}

function redactedDiagnosticText(value: string, maxLength: number): string {
  const redacted = value
    .replace(
      /\b((?:proxy-)?authorization)\s*[:=]\s*(?:(?:bearer|basic)\s+)?[^\s,;]+/gi,
      "$1: [SECRET_REDACTED]",
    )
    .replace(
      /\b(set-cookie|cookie)\s*[:=]\s*[^\r\n]*/gi,
      "$1: [SECRET_REDACTED]",
    )
    .replace(
      /(["']?)(authorization|proxy[_-]?authorization|cookie|set[_-]?cookie|access[_-]?token|refresh[_-]?token|id[_-]?token|auth[_-]?token|session[_-]?token|api[_-]?key|client[_-]?secret|password|passwd|secret|token|(?:pairing|extension)[_-]?credential|credential)(["']?)\s*[:=]\s*(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s,;)\]}]+)/gi,
      "$1$2$3=[SECRET_REDACTED]",
    )
    .replace(/\bbearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [SECRET_REDACTED]")
    .replace(
      /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]{10,})?\b/g,
      "[SECRET_REDACTED]",
    )
    .replace(
      /chrome-extension:\/\/[a-p]{32}/gi,
      "chrome-extension://[EXTENSION_ID_REDACTED]",
    )
    .replace(/https?:\/\/[^\s)]+/gi, "[URL_REDACTED]")
    .replace(/file:\/\/\/[^\s)]+/gi, "[PATH_REDACTED]")
    .replace(/[A-Z]:\\[^\s)]+/gi, "[PATH_REDACTED]")
    .replace(
      /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi,
      "[UUID_REDACTED]",
    );
  return [...redacted]
    .filter((character) => {
      const codePoint = character.charCodeAt(0);
      return (
        codePoint === 9 ||
        codePoint === 10 ||
        codePoint === 13 ||
        (codePoint >= 32 && codePoint !== 127)
      );
    })
    .join("")
    .slice(0, maxLength);
}

function operationFallbackCode(operation: CatalogBatchOperation): string {
  const codes: Partial<Record<CatalogBatchOperation, string>> = {
    GET_AUTHORIZED_TAB: "BATCH_CATALOG_AUTHORIZED_TAB_INVALID",
    NAVIGATE_TO_LANDING: "BATCH_CATALOG_LANDING_PREPARATION_FAILED",
    PERSIST_STATE: "BATCH_CATALOG_STATE_PERSIST_FAILED",
    WATCH_SUBJECT_NAVIGATION: "BATCH_CATALOG_SCRIPT_INJECTION_FAILED",
    START_SUBJECT_SEARCH: "BATCH_CATALOG_SEARCH_TRIGGER_FAILED",
    WATCH_RESULT_PAGE: "BATCH_CATALOG_CONTENT_SCRIPT_UNAVAILABLE",
    CAPTURE_PAGE: "BATCH_CATALOG_CONTENT_SCRIPT_UNAVAILABLE",
    ADVANCE_PAGE: "BATCH_CATALOG_CONTENT_SCRIPT_UNAVAILABLE",
    PROCESS_SUBJECT: "BATCH_CATALOG_LOCAL_APPLY_BLOCKED",
  };
  return codes[operation] ?? "BATCH_CATALOG_UNEXPECTED_ERROR";
}

export function catalogBatchErrorDetails(
  error: unknown,
  operation: CatalogBatchOperation,
): {
  code: string;
  message: string;
  safeErrorName: string;
  safeErrorMessage: string;
  safeStack: string;
  safeCause: string | null;
  returnedResultKind: CatalogScriptResultKind | null;
} {
  const outer = error instanceof Error ? error : null;
  const diagnosticSource =
    error instanceof CatalogBatchError && error.safeCause instanceof Error
      ? error.safeCause
      : outer;
  const sourceMessage =
    diagnosticSource?.message ??
    (typeof error === "string" ? error : "Unknown non-Error value");
  const explicitCode =
    error instanceof CatalogBatchError
      ? error.code
      : (sourceMessage.match(/^([A-Z][A-Z0-9_]+)(?::|$)/)?.[1] ?? null);
  const code =
    explicitCode === "BATCH_CATALOG_STORAGE_UNAVAILABLE"
      ? "BATCH_CATALOG_STATE_PERSIST_FAILED"
      : (explicitCode ?? operationFallbackCode(operation));
  const safeErrorMessage = redactedDiagnosticText(sourceMessage, 1_000);
  const safeStack = redactedDiagnosticText(
    diagnosticSource?.stack ?? outer?.stack ?? "",
    4_000,
  );
  const cause =
    error instanceof CatalogBatchError ? error.safeCause : outer?.cause;
  const safeCause =
    cause instanceof Error
      ? redactedDiagnosticText(`${cause.name}: ${cause.message}`, 1_000)
      : typeof cause === "string"
        ? redactedDiagnosticText(cause, 1_000)
        : null;
  return {
    code,
    message: safeErrorMessage,
    safeErrorName: redactedDiagnosticText(
      diagnosticSource?.name ?? outer?.name ?? "UnknownError",
      128,
    ),
    safeErrorMessage,
    safeStack,
    safeCause,
    returnedResultKind:
      error instanceof CatalogBatchError
        ? (error.diagnosticContext?.returnedResultKind ?? null)
        : null,
  };
}

function nowFromExtraction(extraction: BrowserExtensionExtraction): string {
  const parsed = Date.parse(extraction.extractedAt);
  if (!Number.isFinite(parsed)) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PROVENANCE_INVALID",
      "Capture timestamp is missing or invalid.",
    );
  }
  return new Date(parsed).toISOString();
}

function normalizedCourseCode(value: string | undefined): string | null {
  const match = (value ?? "")
    .trim()
    .match(/^([A-Z]{2,8})[*\s-]?(\d{3,5}[A-Z]?)$/i);
  return match ? `${match[1]?.toUpperCase()} ${match[2]?.toUpperCase()}` : null;
}

function required(value: string | undefined): string {
  return (value ?? "").trim();
}

function optional(value: string | undefined): string {
  return required(value) || "NOT_PROVIDED";
}

function canonicalRecordFingerprint(record: ExtractedRecord): string {
  return JSON.stringify(
    [
      "course_title",
      "credits",
      "description",
      "prerequisites",
      "corequisites",
      "minimum_grade",
      "standing_requirements",
      "restrictions",
      "raw_requisites",
      "rule_review_status",
    ].map((field) => record[field] ?? ""),
  );
}

function canonicalPageFingerprint(records: readonly ExtractedRecord[]): string {
  return JSON.stringify(
    records
      .map((record): [string, string] => [
        record.normalized_code ?? "",
        canonicalRecordFingerprint(record),
      ])
      .sort((left, right) => left[0].localeCompare(right[0])),
  );
}

function enrichRecord(
  record: ExtractedRecord,
  page: CatalogBatchPage,
): ExtractedRecord {
  const rawCode = required(record.course_code);
  const normalizedCode = normalizedCourseCode(rawCode);
  const title = required(record.course_title ?? record.title);
  const credits = required(record.credits);
  const numericCredits = Number(credits);
  if (
    !normalizedCode ||
    !title ||
    !credits ||
    !Number.isFinite(numericCredits) ||
    numericCredits <= 0
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_MALFORMED_COURSE",
      "Every captured course requires a normalized code, visible title, and positive credits.",
    );
  }

  const sourceUrl = new URL(page.extraction.url);
  if (
    sourceUrl.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    ![
      "/Student/Courses/SearchResult",
      "/Student/Student/Courses/SearchResult",
    ].includes(sourceUrl.pathname)
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PROVENANCE_INVALID",
      "Catalog result provenance did not match the authorized Kean result page.",
    );
  }

  const capturedAt = nowFromExtraction(page.extraction);
  return {
    ...record,
    course_code: normalizedCode,
    normalized_code: normalizedCode,
    raw_visible_course_code: rawCode,
    course_title: title,
    raw_visible_title: title,
    credits,
    course_level: optional(record.course_level),
    department: optional(record.department),
    description: optional(record.description),
    prerequisites: optional(record.prerequisites),
    corequisites: optional(record.corequisites),
    minimum_grade: optional(record.minimum_grade),
    standing_requirements: optional(record.standing_requirements),
    restrictions: optional(record.restrictions),
    raw_requisites: optional(record.raw_requisites),
    rule_review_status:
      required(record.rule_review_status) || "REVIEW_REQUIRED",
    source_page: `${sourceUrl.origin}${sourceUrl.pathname}`,
    source_subject: page.subjectCode,
    source_page_number: String(page.pageNumber),
    capture_timestamp: capturedAt,
    source_label:
      required(record.source_label) || "Visible course catalog cards",
  };
}

function pageFailure(page: CatalogBatchPage): CatalogBatchError | null {
  if (page.fatalSignal === "RATE_LIMIT") {
    return new CatalogBatchError(
      "BATCH_CATALOG_RATE_LIMIT",
      "The school page reported a rate limit; the batch stopped without retrying.",
    );
  }
  if (page.fatalSignal === "PROVIDER_ERROR") {
    return new CatalogBatchError(
      "BATCH_CATALOG_PROVIDER_ERROR",
      "The school page reported an error; the batch stopped.",
    );
  }
  if (page.fatalSignal === "TIMEOUT") {
    return new CatalogBatchError(
      "BATCH_CATALOG_PAGE_TIMEOUT",
      "The Catalog page did not become ready within the bounded timeout.",
    );
  }
  const warningCodes = new Set([
    ...page.extraction.warnings.map((warning) => warning.code),
    ...page.extraction.diagnostics.warningCodes,
    ...page.extraction.diagnostics.parserWarningCodes,
  ]);
  if (
    page.extraction.diagnostics.bounded ||
    warningCodes.has("EXTRACTION_LIMIT_REACHED")
  ) {
    return new CatalogBatchError(
      "BATCH_CATALOG_TRUNCATED_PAGE",
      "A bounded or truncated Catalog page cannot be included in a full-catalog batch.",
    );
  }
  if ([...warningCodes].some((code) => PARSER_DRIFT_WARNING_CODES.has(code))) {
    return new CatalogBatchError(
      "BATCH_CATALOG_PARSER_DRIFT",
      "Catalog page parsing was incomplete or did not produce the expected course rows.",
    );
  }
  if (
    page.extraction.warnings.some((warning) => warning.severity === "ERROR")
  ) {
    return new CatalogBatchError(
      "BATCH_CATALOG_EXTRACTION_ERROR",
      "Catalog extraction reported an error.",
    );
  }
  return null;
}

function normalizedSubjects(
  subjects: readonly CatalogSubject[],
): CatalogSubject[] {
  const seen = new Set<string>();
  const normalized: CatalogSubject[] = [];
  for (const subject of subjects) {
    const code = subject.code.trim().toUpperCase();
    const label = subject.label.trim();
    if (!/^[A-Z0-9]{1,8}$/.test(code) || !label || seen.has(code)) {
      continue;
    }
    seen.add(code);
    normalized.push({ code, label });
  }
  return normalized;
}

export function createCatalogBatchState(
  input: CreateCatalogBatchStateInput,
): CatalogBatchState {
  const subjects = normalizedSubjects(input.subjects);
  if (
    subjects.length === 0 ||
    subjects.length > CATALOG_BATCH_LIMITS.maxSubjects
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_SUBJECT_DISCOVERY_INVALID",
      "Subject discovery returned an empty or over-limit set.",
    );
  }
  const landing = new URL(input.landingUrl);
  if (
    landing.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    !["/Student/Courses", "/Student/Student/Courses"].includes(landing.pathname)
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PROVENANCE_INVALID",
      "The batch must begin on the authorized Kean Course Catalog page.",
    );
  }
  const mode = input.mode ?? "FULL";
  const subjectLimit = input.subjectLimit ?? subjects.length;
  const boundedAcceptanceRevision =
    input.boundedAcceptancePassed === true &&
    input.boundedAcceptanceRevision === CATALOG_BATCH_ACCEPTANCE_REVISION
      ? CATALOG_BATCH_ACCEPTANCE_REVISION
      : null;
  if (
    !Number.isInteger(subjectLimit) ||
    subjectLimit < 1 ||
    subjectLimit > subjects.length ||
    (mode === "BOUNDED_ACCEPTANCE" && subjectLimit > 2)
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_SUBJECT_LIMIT_INVALID",
      "The Catalog batch subject limit was outside the reviewed safety boundary.",
    );
  }
  return {
    batchId:
      input.batchId?.trim().slice(0, 128) ||
      `${input.startedAt}:${input.tabId}`,
    runnerRevision: CATALOG_BATCH_ACCEPTANCE_REVISION,
    acceptanceRevision: CATALOG_BATCH_ACCEPTANCE_REVISION,
    extensionVersion:
      input.extensionVersion?.trim().slice(0, 64) ||
      "UNKNOWN_EXTENSION_VERSION",
    createdAt: input.startedAt,
    apiBaseUrl: input.apiBaseUrl,
    studentProfileId: input.studentProfileId,
    tabId: input.tabId,
    landingUrl: `${landing.origin}${landing.pathname}`,
    subjects,
    mode,
    subjectLimit,
    boundedAcceptancePassed: boundedAcceptanceRevision !== null,
    boundedAcceptanceRevision,
    currentSubjectIndex: 0,
    currentPage: 1,
    expectedNavigationRevision: 0,
    currentNavigationRevision: null,
    contentReadyRevision: null,
    navigationTimeoutRevision: null,
    preparationCheckpointRevision: null,
    lastTabUpdateStatus: null,
    lastSubjectPreparationResultKind: null,
    lastSubjectSearchResultKind: null,
    lastSubjectNavigationDiagnostics: null,
    totalPagesForCurrentSubject: null,
    previousFirstCourseMarker: null,
    lastPageDiagnostics: null,
    currentSchoolTabUrlClassification: "CATALOG_LANDING",
    processingStage: "CAPTURE_RUNNING",
    completedProcessingStages: [],
    completedSubjects: [],
    pendingRecords: [],
    seenCourseFingerprints: {},
    acceptedPageKeys: [],
    acceptedPageFingerprints: {},
    subjectWarnings: [],
    coursesCaptured: 0,
    uniqueCourses: 0,
    duplicatesIgnored: 0,
    pagesCaptured: 0,
    localImportRunIds: [],
    localReviewSessionIds: [],
    localImportsApplied: 0,
    localCoursesCreated: 0,
    localCoursesUpdated: 0,
    localStagedCount: 0,
    localReviewValidCount: 0,
    localReviewWarningCount: 0,
    localAppliedCount: 0,
    myprogressRunId: null,
    myprogressMappedCount: 0,
    myprogressUnmatchedCount: 0,
    myprogressTotalCount: 0,
    myprogressMappedBeforeCount: 0,
    myprogressRemapExecuted: false,
    warnings: [],
    status: "RUNNING",
    leaseStatus: "ACTIVE",
    startedAt: input.startedAt,
    updatedAt: input.startedAt,
    lastCapturedAt: null,
    lastSourceUrl: null,
    lastErrorCode: null,
    lastErrorMessage: null,
    lastErrorContext: null,
    lastSuccessfulCheckpoint: "SUBJECT_DISCOVERY_COMPLETED",
    failedOperation: null,
    lastFailureDiagnostic: null,
    lastTransition: "SUBJECTS_DISCOVERED",
    stateMachineCheckpoint: "SUBJECTS_DISCOVERED",
    lastTransitionAt: input.startedAt,
    pauseReason: null,
    providerActionsWritten: "NO",
  };
}

export function acceptCatalogPage(
  state: CatalogBatchState,
  page: CatalogBatchPage,
): CatalogBatchState {
  if (state.status !== "RUNNING") {
    throw new CatalogBatchError(
      "BATCH_CATALOG_NOT_RUNNING",
      "Only a running user-initiated batch can accept a Catalog page.",
    );
  }
  const currentSubject = state.subjects[state.currentSubjectIndex];
  if (!currentSubject || currentSubject.code !== page.subjectCode) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_SUBJECT_MISMATCH",
      "The captured page does not match the current discovered subject.",
    );
  }
  if (
    !Number.isInteger(page.pageNumber) ||
    !Number.isInteger(page.totalPages) ||
    page.pageNumber < 1 ||
    page.totalPages < page.pageNumber ||
    page.totalPages > CATALOG_BATCH_LIMITS.maxPagesPerSubject
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PAGINATION_INVALID",
      "Catalog pagination was malformed or exceeded the configured subject limit.",
    );
  }
  const failure = pageFailure(page);
  if (failure) {
    throw failure;
  }
  if (
    page.extraction.pageType !== "KEAN_COURSE_CATALOG_PAGE" ||
    page.extraction.importType !== "COURSE_CATALOG" ||
    page.extraction.sourceType !== "BROWSER_EXTENSION" ||
    page.extraction.sourceLabel !== "KEAN_STUDENT_PORTAL" ||
    page.extraction.isOfficial !== false ||
    page.extraction.records.length === 0
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_PARSER_DRIFT",
      "The page was not recognized as a non-official Kean Course Catalog result.",
    );
  }

  const pageKey = `${page.subjectCode}:${page.pageNumber}`;
  const enrichedRecords = page.extraction.records.map((record) =>
    enrichRecord(record, page),
  );
  const pageFingerprint = canonicalPageFingerprint(enrichedRecords);
  if (state.acceptedPageKeys.includes(pageKey)) {
    if (state.acceptedPageFingerprints[pageKey] !== pageFingerprint) {
      throw new CatalogBatchError(
        "CONFLICTING_ACCEPTED_CATALOG_PAGE",
        "A previously accepted Catalog page changed before the batch resumed.",
      );
    }
    return state;
  }
  if (state.pagesCaptured + 1 > CATALOG_BATCH_LIMITS.maxPages) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_MAX_PAGES",
      "The batch reached its global page limit.",
    );
  }

  const next = structuredClone(state);
  for (const record of enrichedRecords) {
    next.coursesCaptured += 1;
    const identity = record.normalized_code ?? "";
    const fingerprint = canonicalRecordFingerprint(record);
    const previousFingerprint = next.seenCourseFingerprints[identity];
    if (previousFingerprint !== undefined) {
      if (previousFingerprint !== fingerprint) {
        throw new CatalogBatchError(
          "CONFLICTING_DUPLICATE_COURSE",
          `Duplicate Catalog identity ${identity} contained conflicting visible fields.`,
        );
      }
      next.duplicatesIgnored += 1;
      continue;
    }
    if (next.uniqueCourses + 1 > CATALOG_BATCH_LIMITS.maxRecords) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_MAX_RECORDS",
        "The batch reached its global record limit.",
      );
    }
    next.seenCourseFingerprints[identity] = fingerprint;
    next.pendingRecords.push(record);
    next.uniqueCourses += 1;
  }
  next.acceptedPageKeys.push(pageKey);
  next.acceptedPageFingerprints[pageKey] = pageFingerprint;
  next.pagesCaptured += 1;
  next.subjectWarnings = [
    ...next.subjectWarnings,
    ...page.extraction.warnings.filter(
      (warning) =>
        !next.subjectWarnings.some((current) => current.code === warning.code),
    ),
  ];
  next.updatedAt = nowFromExtraction(page.extraction);
  next.lastCapturedAt = next.updatedAt;
  next.lastSourceUrl = page.extraction.url;
  return next;
}

function csvCell(value: string): string {
  return /[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function csvContent(records: readonly ExtractedRecord[]): string {
  return `${[
    BATCH_FIELDS.join(","),
    ...records.map((record) =>
      BATCH_FIELDS.map((field) => csvCell(record[field] ?? "")).join(","),
    ),
  ].join("\n")}\n`;
}

export function buildCatalogSubjectExtraction(
  state: CatalogBatchState,
): BrowserExtensionExtraction {
  const subject = state.subjects[state.currentSubjectIndex];
  if (!subject || state.pendingRecords.length === 0 || !state.lastCapturedAt) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_EMPTY_SUBJECT",
      "No captured Catalog rows are ready for the current subject.",
    );
  }
  const warnings = [...state.subjectWarnings];
  if (
    state.pendingRecords.some(
      (record) =>
        record.rule_review_status === "MANUAL_CONFIRMATION_REQUIRED" ||
        record.rule_review_status === "REVIEW_REQUIRED",
    ) &&
    !warnings.some(
      (warning) => warning.code === "KEAN_CATALOG_RULE_REQUIRES_REVIEW",
    )
  ) {
    warnings.push({
      code: "KEAN_CATALOG_RULE_REQUIRES_REVIEW",
      severity: "WARNING",
      message:
        "Visible requisite text was preserved as raw review-required evidence and was not activated as verified policy.",
    });
  }
  return {
    pageType: "KEAN_COURSE_CATALOG_PAGE",
    importType: "COURSE_CATALOG",
    sourceType: "BROWSER_EXTENSION",
    sourceLabel: "KEAN_STUDENT_PORTAL",
    isOfficial: false,
    title: `Course Catalog ${subject.code}`,
    url:
      state.lastSourceUrl ??
      "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
    fileName: `kean-student-portal-course-catalog-${subject.code.toLowerCase()}.csv`,
    fileMimeType: "text/csv",
    content: csvContent(state.pendingRecords),
    records: structuredClone(state.pendingRecords),
    warnings,
    diagnostics: {
      currentUrl:
        state.lastSourceUrl ??
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
      detectedPageType: "KEAN_COURSE_CATALOG_PAGE",
      matchedPageMarker: "/Student/Student/Courses/SearchResult",
      tablesFound: 0,
      rowsFound: state.pendingRecords.length,
      visibleTextLength: 0,
      rowLikeBlocksFound: state.pendingRecords.length,
      extractedAcademicFieldCount:
        state.pendingRecords.length * BATCH_FIELDS.length,
      ignoredSensitiveFieldCount: 0,
      directSnapshotRan: true,
      bounded: false,
      warningCodes: warnings.map((warning) => warning.code),
      academicTablesDetected: 1,
      academicTablesParsed: 1,
      academicRowsParsed: state.pendingRecords.length,
      academicRowsSkipped: 0,
      academicRowsCapped: 0,
      parserWarningCodes: [],
    },
    requiresReview: true,
    extractedAt: state.lastCapturedAt,
  };
}

export function pauseCatalogBatch(state: CatalogBatchState): CatalogBatchState {
  return state.status === "RUNNING"
    ? {
        ...state,
        status: "PAUSED",
        leaseStatus: "RELEASED",
        lastTransition: "PAUSED",
        stateMachineCheckpoint: "PAUSED",
      }
    : state;
}

export function resumeCatalogBatch(
  state: CatalogBatchState,
): CatalogBatchState {
  if (state.status !== "PAUSED") {
    return state;
  }
  return {
    ...state,
    status: "RUNNING",
    leaseStatus: "ACTIVE",
    pauseReason: null,
    lastErrorCode: null,
    lastErrorMessage: null,
    lastErrorContext: null,
    lastTransition: "RESUMED",
    stateMachineCheckpoint: "RESUMED",
  };
}

export function cancelCatalogBatch(
  state: CatalogBatchState,
): CatalogBatchState {
  if (["COMPLETED", "CANCELLED"].includes(state.status)) {
    return state;
  }
  return {
    ...state,
    status: "CANCELLED",
    leaseStatus: "RELEASED",
    pendingRecords: [],
    subjectWarnings: [],
    lastTransition: "CANCELLED",
    stateMachineCheckpoint: "CANCELLED",
    providerActionsWritten: "NO",
  };
}

export function completeCatalogSubject(
  state: CatalogBatchState,
  outcome: CatalogSubjectLocalOutcome,
): CatalogBatchState {
  const subject = state.subjects[state.currentSubjectIndex];
  if (
    state.status !== "RUNNING" ||
    !subject ||
    state.pendingRecords.length === 0 ||
    !outcome.importRunId ||
    outcome.providerActionsWritten !== "NO" ||
    outcome.reasonCodes.length > 0 ||
    !Number.isInteger(outcome.createdCount) ||
    !Number.isInteger(outcome.updatedCount) ||
    outcome.createdCount < 0 ||
    outcome.updatedCount < 0 ||
    outcome.createdCount + outcome.updatedCount !==
      state.pendingRecords.length ||
    outcome.processingStagesCompleted.length !==
      CATALOG_BATCH_LOCAL_PROCESSING_STAGES.length ||
    outcome.processingStagesCompleted.some(
      (stage, index) => stage !== CATALOG_BATCH_LOCAL_PROCESSING_STAGES[index],
    ) ||
    ![
      outcome.stagedRecordCount,
      outcome.reviewValidCount,
      outcome.reviewWarningCount,
      outcome.appliedRecordCount,
      outcome.myprogressTotalCount,
      outcome.myprogressMappedBeforeCount,
      outcome.myprogressMappedCount,
      outcome.myprogressUnmatchedCount,
    ].every((count) => Number.isInteger(count) && count >= 0) ||
    outcome.stagedRecordCount !== state.pendingRecords.length ||
    outcome.reviewValidCount !== outcome.stagedRecordCount ||
    outcome.reviewWarningCount > outcome.reviewValidCount ||
    outcome.appliedRecordCount !== state.pendingRecords.length ||
    outcome.appliedRecordCount !==
      outcome.createdCount + outcome.updatedCount ||
    outcome.myprogressTotalCount !==
      outcome.myprogressMappedCount + outcome.myprogressUnmatchedCount ||
    outcome.myprogressMappedBeforeCount > outcome.myprogressTotalCount ||
    outcome.myprogressRemapExecuted !== true
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_LOCAL_APPLY_INVALID",
      "The local dry-run and Apply result did not safely account for every unique captured course.",
    );
  }
  const currentSubjectIndex = state.currentSubjectIndex + 1;
  const completed = currentSubjectIndex >= state.subjectLimit;
  const boundedAcceptanceCompleted =
    completed && state.mode === "BOUNDED_ACCEPTANCE";
  const boundedAcceptanceRevision = boundedAcceptanceCompleted
    ? CATALOG_BATCH_ACCEPTANCE_REVISION
    : state.boundedAcceptancePassed &&
        state.boundedAcceptanceRevision === CATALOG_BATCH_ACCEPTANCE_REVISION
      ? CATALOG_BATCH_ACCEPTANCE_REVISION
      : null;
  return {
    ...state,
    currentSubjectIndex,
    completedSubjects: [...state.completedSubjects, subject.code],
    pendingRecords: [],
    subjectWarnings: [],
    localImportRunIds: [...state.localImportRunIds, outcome.importRunId],
    localReviewSessionIds: outcome.reviewSessionId
      ? [...state.localReviewSessionIds, outcome.reviewSessionId]
      : state.localReviewSessionIds,
    localImportsApplied: state.localImportsApplied + 1,
    localCoursesCreated: state.localCoursesCreated + outcome.createdCount,
    localCoursesUpdated: state.localCoursesUpdated + outcome.updatedCount,
    localStagedCount: state.localStagedCount + outcome.stagedRecordCount,
    localReviewValidCount:
      state.localReviewValidCount + outcome.reviewValidCount,
    localReviewWarningCount:
      state.localReviewWarningCount + outcome.reviewWarningCount,
    localAppliedCount: state.localAppliedCount + outcome.appliedRecordCount,
    myprogressRunId: outcome.myprogressRunId,
    myprogressTotalCount: outcome.myprogressTotalCount,
    myprogressMappedBeforeCount:
      state.localImportRunIds.length === 0
        ? outcome.myprogressMappedBeforeCount
        : state.myprogressMappedBeforeCount,
    myprogressMappedCount: outcome.myprogressMappedCount,
    myprogressUnmatchedCount: outcome.myprogressUnmatchedCount,
    myprogressRemapExecuted: outcome.myprogressRemapExecuted,
    warnings: [...new Set([...state.warnings, ...outcome.reasonCodes])],
    status: completed ? "COMPLETED" : "RUNNING",
    leaseStatus: completed ? "RELEASED" : "ACTIVE",
    processingStage: completed ? "COMPLETED" : "CAPTURE_RUNNING",
    completedProcessingStages: [
      ...new Set([
        ...state.completedProcessingStages,
        "CAPTURE_COMPLETED" as const,
        ...outcome.processingStagesCompleted,
        ...(completed ? (["COMPLETED"] as const) : []),
      ]),
    ],
    boundedAcceptancePassed: boundedAcceptanceRevision !== null,
    boundedAcceptanceRevision,
    currentPage: completed ? state.currentPage : 0,
    totalPagesForCurrentSubject: completed
      ? state.totalPagesForCurrentSubject
      : null,
    previousFirstCourseMarker: null,
    updatedAt: outcome.completedAt,
    lastErrorCode: null,
    lastErrorMessage: null,
    lastErrorContext: null,
    failedOperation: null,
    lastFailureDiagnostic: null,
    lastTransition: completed ? "COMPLETED" : "SUBJECT_COMPLETED",
    stateMachineCheckpoint: completed ? "COMPLETED" : "SUBJECT_COMPLETED",
    lastTransitionAt: outcome.completedAt,
    pauseReason: null,
    providerActionsWritten: "NO",
  };
}

export function catalogBatchErrorContext(
  state: CatalogBatchState,
  timestamp: string,
): CatalogBatchErrorContext {
  return {
    phase: state.stateMachineCheckpoint,
    subject: state.subjects[state.currentSubjectIndex]?.code ?? null,
    page: state.currentPage,
    urlClassification: state.currentSchoolTabUrlClassification,
    revision: state.expectedNavigationRevision,
    timestamp,
    diagnostics: state.lastPageDiagnostics
      ? { ...state.lastPageDiagnostics }
      : null,
  };
}

export function failCatalogBatch(
  state: CatalogBatchState,
  errorCode: string,
  errorMessage: string,
  failedAt: string,
  diagnostic: CatalogBatchFailureDiagnostic | null = null,
): CatalogBatchState {
  return {
    ...state,
    status: "FAILED",
    leaseStatus: "RELEASED",
    warnings: [...new Set([...state.warnings, errorCode])],
    updatedAt: failedAt,
    lastErrorCode: errorCode,
    lastErrorMessage: errorMessage,
    lastErrorContext: catalogBatchErrorContext(state, failedAt),
    failedOperation: diagnostic?.operation ?? state.failedOperation,
    lastFailureDiagnostic: diagnostic ?? state.lastFailureDiagnostic,
    lastTransition: "FAILED",
    stateMachineCheckpoint: "FAILED",
    lastTransitionAt: failedAt,
    pauseReason: null,
    providerActionsWritten: "NO",
  };
}

export function restoreCatalogBatchState(
  raw: unknown,
  restoredAt: string,
): CatalogBatchState {
  if (
    typeof raw !== "object" ||
    raw === null ||
    !("batchId" in raw) ||
    typeof raw.batchId !== "string" ||
    !("status" in raw) ||
    !["RUNNING", "PAUSED", "CANCELLED", "COMPLETED", "FAILED"].includes(
      String(raw.status),
    ) ||
    !("subjects" in raw) ||
    !Array.isArray(raw.subjects) ||
    !("providerActionsWritten" in raw) ||
    raw.providerActionsWritten !== "NO"
  ) {
    throw new CatalogBatchError(
      "BATCH_CATALOG_STATE_SCHEMA_INVALID",
      "Stored Catalog batch progress was missing required safety fields.",
    );
  }
  const state = structuredClone(raw) as CatalogBatchState;
  state.runnerRevision =
    "runnerRevision" in raw &&
    typeof raw.runnerRevision === "string" &&
    raw.runnerRevision.trim().length > 0 &&
    raw.runnerRevision.length <= 128
      ? raw.runnerRevision
      : LEGACY_CATALOG_BATCH_RUNNER_REVISION;
  state.acceptanceRevision =
    typeof state.acceptanceRevision === "string" && state.acceptanceRevision
      ? state.acceptanceRevision
      : state.runnerRevision;
  state.extensionVersion =
    typeof state.extensionVersion === "string" && state.extensionVersion
      ? state.extensionVersion
      : "LEGACY_UNKNOWN";
  state.createdAt =
    typeof state.createdAt === "string" && state.createdAt
      ? state.createdAt
      : state.startedAt;
  state.mode = state.mode === "BOUNDED_ACCEPTANCE" ? state.mode : "FULL";
  state.subjectLimit =
    Number.isInteger(state.subjectLimit) &&
    state.subjectLimit > 0 &&
    state.subjectLimit <= state.subjects.length
      ? state.subjectLimit
      : state.subjects.length;
  state.boundedAcceptanceRevision =
    state.boundedAcceptancePassed === true &&
    state.boundedAcceptanceRevision === CATALOG_BATCH_ACCEPTANCE_REVISION
      ? CATALOG_BATCH_ACCEPTANCE_REVISION
      : null;
  state.boundedAcceptancePassed = state.boundedAcceptanceRevision !== null;
  state.currentPage =
    Number.isInteger(state.currentPage) && state.currentPage >= 0
      ? state.currentPage
      : 0;
  state.expectedNavigationRevision =
    Number.isInteger(state.expectedNavigationRevision) &&
    state.expectedNavigationRevision >= 0
      ? state.expectedNavigationRevision
      : 0;
  const restoredRevision = (value: unknown): number | null =>
    Number.isInteger(value) &&
    Number(value) >= 0 &&
    Number(value) <= state.expectedNavigationRevision
      ? Number(value)
      : null;
  state.currentNavigationRevision = restoredRevision(
    state.currentNavigationRevision,
  );
  state.contentReadyRevision = restoredRevision(state.contentReadyRevision);
  state.navigationTimeoutRevision = restoredRevision(
    state.navigationTimeoutRevision,
  );
  state.preparationCheckpointRevision = restoredRevision(
    state.preparationCheckpointRevision,
  );
  state.lastTabUpdateStatus = ["loading", "complete"].includes(
    String(state.lastTabUpdateStatus),
  )
    ? (state.lastTabUpdateStatus as "loading" | "complete")
    : null;
  state.lastSubjectPreparationResultKind = [
    "VALUE",
    "NULL_RESULT",
    "MISSING_RESULT",
    "EMPTY_RESULTS",
    "UNEXPECTED_VALUE",
  ].includes(String(state.lastSubjectPreparationResultKind))
    ? state.lastSubjectPreparationResultKind
    : null;
  state.lastSubjectSearchResultKind = [
    "VALUE",
    "NULL_RESULT",
    "MISSING_RESULT",
    "EMPTY_RESULTS",
    "UNEXPECTED_VALUE",
  ].includes(String(state.lastSubjectSearchResultKind))
    ? state.lastSubjectSearchResultKind
    : null;
  state.lastSubjectNavigationDiagnostics =
    sanitizedCatalogSubjectNavigationDiagnostics(
      state.lastSubjectNavigationDiagnostics,
    );
  state.totalPagesForCurrentSubject =
    Number.isInteger(state.totalPagesForCurrentSubject) &&
    Number(state.totalPagesForCurrentSubject) > 0
      ? Number(state.totalPagesForCurrentSubject)
      : null;
  state.previousFirstCourseMarker =
    typeof state.previousFirstCourseMarker === "string"
      ? state.previousFirstCourseMarker
      : null;
  state.lastPageDiagnostics =
    state.lastPageDiagnostics && typeof state.lastPageDiagnostics === "object"
      ? state.lastPageDiagnostics
      : null;
  state.currentSchoolTabUrlClassification = [
    "CATALOG_LANDING",
    "CATALOG_SEARCH_RESULT",
    "AUTHENTICATION",
    "OUT_OF_SCOPE",
    "UNAVAILABLE",
  ].includes(String(state.currentSchoolTabUrlClassification))
    ? state.currentSchoolTabUrlClassification
    : "UNAVAILABLE";
  state.processingStage = [
    "CAPTURE_RUNNING",
    "CAPTURE_COMPLETED",
    "LOCAL_STAGING",
    "LOCAL_VALIDATION",
    "LOCAL_REVIEW",
    "LOCAL_DRY_RUN",
    "LOCAL_APPLY",
    "MYPROGRESS_REMAP",
    "COMPLETED",
  ].includes(String(state.processingStage))
    ? state.processingStage
    : "CAPTURE_RUNNING";
  state.completedProcessingStages = Array.isArray(
    state.completedProcessingStages,
  )
    ? state.completedProcessingStages
    : [];
  for (const field of [
    "localStagedCount",
    "localReviewValidCount",
    "localReviewWarningCount",
    "localAppliedCount",
    "myprogressTotalCount",
    "myprogressMappedBeforeCount",
  ] as const) {
    state[field] =
      Number.isInteger(state[field]) && state[field] >= 0 ? state[field] : 0;
  }
  state.myprogressRemapExecuted = state.myprogressRemapExecuted === true;
  state.lastErrorMessage =
    typeof state.lastErrorMessage === "string"
      ? redactedDiagnosticText(state.lastErrorMessage, 1_000)
      : null;
  state.lastTransition =
    typeof state.lastTransition === "string"
      ? state.lastTransition
      : "LEGACY_STATE_RESTORED";
  state.lastErrorContext =
    state.lastErrorContext && typeof state.lastErrorContext === "object"
      ? state.lastErrorContext
      : null;
  state.lastSuccessfulCheckpoint = isCatalogBatchCheckpoint(
    state.lastSuccessfulCheckpoint,
  )
    ? state.lastSuccessfulCheckpoint
    : "SUBJECT_DISCOVERY_COMPLETED";
  state.failedOperation = isCatalogBatchOperation(state.failedOperation)
    ? state.failedOperation
    : null;
  state.lastFailureDiagnostic =
    state.lastFailureDiagnostic &&
    typeof state.lastFailureDiagnostic === "object" &&
    typeof state.lastFailureDiagnostic.safeErrorName === "string" &&
    typeof state.lastFailureDiagnostic.safeErrorMessage === "string" &&
    typeof state.lastFailureDiagnostic.safeStack === "string" &&
    isCatalogBatchCheckpoint(state.lastFailureDiagnostic.phase) &&
    isCatalogBatchOperation(state.lastFailureDiagnostic.operation) &&
    isCatalogBatchCheckpoint(state.lastFailureDiagnostic.checkpoint) &&
    typeof state.lastFailureDiagnostic.runRevision === "string" &&
    Number.isInteger(state.lastFailureDiagnostic.navigationRevision) &&
    state.lastFailureDiagnostic.navigationRevision >= 0 &&
    state.lastFailureDiagnostic.navigationRevision <=
      state.expectedNavigationRevision &&
    typeof state.lastFailureDiagnostic.timestamp === "string"
      ? {
          ...state.lastFailureDiagnostic,
          safeErrorName: redactedDiagnosticText(
            state.lastFailureDiagnostic.safeErrorName,
            128,
          ),
          safeErrorMessage: redactedDiagnosticText(
            state.lastFailureDiagnostic.safeErrorMessage,
            1_000,
          ),
          safeStack: redactedDiagnosticText(
            state.lastFailureDiagnostic.safeStack,
            4_000,
          ),
          safeCause:
            typeof state.lastFailureDiagnostic.safeCause === "string"
              ? redactedDiagnosticText(
                  state.lastFailureDiagnostic.safeCause,
                  1_000,
                )
              : null,
          returnedResultKind: [
            "VALUE",
            "NULL_RESULT",
            "MISSING_RESULT",
            "EMPTY_RESULTS",
            "UNEXPECTED_VALUE",
          ].includes(String(state.lastFailureDiagnostic.returnedResultKind))
            ? state.lastFailureDiagnostic.returnedResultKind
            : null,
          tabUrlClassification: [
            "CATALOG_LANDING",
            "CATALOG_SEARCH_RESULT",
            "AUTHENTICATION",
            "OUT_OF_SCOPE",
            "UNAVAILABLE",
          ].includes(String(state.lastFailureDiagnostic.tabUrlClassification))
            ? state.lastFailureDiagnostic.tabUrlClassification
            : state.currentSchoolTabUrlClassification,
          subjectCode:
            typeof state.lastFailureDiagnostic.subjectCode === "string" &&
            /^[A-Z0-9]{1,8}$/.test(state.lastFailureDiagnostic.subjectCode)
              ? state.lastFailureDiagnostic.subjectCode
              : (state.subjects[state.currentSubjectIndex]?.code ?? null),
          providerActionsWritten: "NO",
        }
      : null;
  state.stateMachineCheckpoint = isCatalogBatchCheckpoint(
    state.stateMachineCheckpoint,
  )
    ? state.stateMachineCheckpoint
    : "LEGACY_STATE_RESTORED";
  state.lastTransitionAt =
    typeof state.lastTransitionAt === "string"
      ? state.lastTransitionAt
      : state.updatedAt;
  state.pauseReason =
    typeof state.pauseReason === "string" ? state.pauseReason : null;
  state.leaseStatus =
    state.leaseStatus === "ACTIVE" || state.leaseStatus === "RELEASED"
      ? state.leaseStatus
      : state.status === "RUNNING"
        ? "ACTIVE"
        : "RELEASED";
  if (
    !state.acceptedPageFingerprints ||
    typeof state.acceptedPageFingerprints !== "object" ||
    Object.values(state.acceptedPageFingerprints).some(
      (fingerprint) => typeof fingerprint !== "string",
    )
  ) {
    if (state.acceptedPageKeys.length > 0) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_STATE_SCHEMA_INVALID",
        "Stored accepted pages were missing deterministic page fingerprints.",
      );
    }
    state.acceptedPageFingerprints = {};
  }
  if (state.status !== "RUNNING") {
    return state;
  }
  return {
    ...state,
    status: "PAUSED",
    leaseStatus: "RELEASED",
    warnings: [...new Set([...state.warnings, "BATCH_CATALOG_WORKER_RESTART"])],
    updatedAt: restoredAt,
    lastErrorCode: "BATCH_CATALOG_WORKER_RESTART",
    lastErrorMessage:
      "The extension worker restarted. Resume explicitly to continue the saved batch.",
    lastErrorContext: catalogBatchErrorContext(state, restoredAt),
    lastTransition: "PAUSED",
    stateMachineCheckpoint: "PAUSED",
    lastTransitionAt: restoredAt,
    pauseReason: "WORKER_RESTART_RECOVERY_REQUIRED",
    providerActionsWritten: "NO",
  };
}

export function archiveCatalogBatchEvidence(
  state: CatalogBatchState,
  archiveStatus: CatalogBatchArchiveStatus,
  reason: CatalogBatchArchiveReason,
  archivedAt: string,
): CatalogBatchArchive {
  return {
    schemaVersion: 1,
    batchRunId: state.batchId,
    archiveStatus,
    reason,
    originalStatus: state.status,
    leaseStatus: state.leaseStatus,
    runnerRevision: state.runnerRevision,
    boundedAcceptanceRevision: state.boundedAcceptanceRevision,
    mode: state.mode,
    subjectLimit: state.subjectLimit,
    discoveredSubjectCount: state.subjects.length,
    currentSubjectIndex: state.currentSubjectIndex,
    completedSubjects: [...state.completedSubjects],
    coursesCaptured: state.coursesCaptured,
    uniqueCourses: state.uniqueCourses,
    duplicatesIgnored: state.duplicatesIgnored,
    pagesCaptured: state.pagesCaptured,
    localImportRunIds: [...state.localImportRunIds],
    localReviewSessionIds: [...state.localReviewSessionIds],
    localImportsApplied: state.localImportsApplied,
    localCoursesCreated: state.localCoursesCreated,
    localCoursesUpdated: state.localCoursesUpdated,
    myprogressRunId: state.myprogressRunId,
    myprogressMappedCount: state.myprogressMappedCount,
    myprogressUnmatchedCount: state.myprogressUnmatchedCount,
    myprogressRemapExecuted: state.myprogressRemapExecuted,
    warnings: [...state.warnings],
    lastErrorCode: state.lastErrorCode,
    lastErrorMessage: state.lastErrorMessage,
    lastErrorContext: state.lastErrorContext
      ? { ...state.lastErrorContext }
      : null,
    lastSuccessfulCheckpoint: state.lastSuccessfulCheckpoint,
    failedOperation: state.failedOperation,
    lastFailureDiagnostic: state.lastFailureDiagnostic
      ? { ...state.lastFailureDiagnostic }
      : null,
    lastTransition: state.lastTransition,
    stateMachineCheckpoint: state.stateMachineCheckpoint,
    startedAt: state.startedAt,
    updatedAt: state.updatedAt,
    archivedAt,
    providerActionsWritten: "NO",
  };
}
