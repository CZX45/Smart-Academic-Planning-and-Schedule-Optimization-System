import {
  CATALOG_BATCH_ACCEPTANCE_REVISION,
  CatalogBatchError,
  acceptCatalogPage,
  buildCatalogSubjectExtraction,
  catalogPreparationCheckpointToken,
  catalogBatchErrorDetails,
  catalogBatchErrorContext,
  completeCatalogSubject,
  failCatalogBatch,
  resumeCatalogBatch,
  sanitizedCatalogSubjectNavigationDiagnostics,
  type CatalogBatchPage,
  type CatalogBatchFailureDiagnostic,
  type CatalogBatchOperation,
  type CatalogBatchState,
  type CatalogSubject,
  type CatalogSubjectLocalOutcome,
} from "../content/catalog-batch.js";
import {
  pauseCatalogBatchForReason,
  recordCatalogBatchCheckpoint,
  recordCatalogBatchTransition,
} from "../content/catalog-batch-lifecycle.js";
import type {
  CatalogPageSignal,
  CatalogSearchAction,
  CatalogSubjectNavigationSignal,
} from "../content/catalog-batch-page.js";
import type { BrowserExtensionExtraction } from "../shared/types.js";

export type CatalogSubjectSearchDispatch =
  | {
      preparation: CatalogSearchAction;
      preparationResultKind: "VALUE";
      submissionResultKind: "VALUE" | "NULL_RESULT";
    }
  | {
      preparation: null;
      preparationResultKind: "NULL_RESULT";
      submissionResultKind: "VALUE" | "NULL_RESULT";
    };

export type CatalogBatchEventDriver = {
  now: () => string;
  loadState: (batchId: string) => Promise<CatalogBatchState | null>;
  persistState: (state: CatalogBatchState) => Promise<void>;
  getAuthorizedTabUrl: (tabId: number) => Promise<string | null>;
  navigateToLanding: (state: CatalogBatchState) => Promise<void>;
  watchSubjectNavigation: (
    state: CatalogBatchState,
    navigationRevision: number,
  ) => Promise<void>;
  startSubjectSearch: (
    state: CatalogBatchState,
    subject: CatalogSubject,
  ) => Promise<CatalogSubjectSearchDispatch>;
  watchResultPage: (
    state: CatalogBatchState,
    expectedPage: number,
    previousFirstCourseMarker: string | null,
  ) => Promise<void>;
  capturePage: (
    state: CatalogBatchState,
    subject: CatalogSubject,
    expectedPage: number,
    expectedResultFingerprint: string,
  ) => Promise<CatalogBatchPage>;
  advancePage: (
    state: CatalogBatchState,
    targetPage: number,
    previousFirstCourseMarker: string,
  ) => Promise<void>;
  processSubject: (
    state: CatalogBatchState,
    extraction: BrowserExtensionExtraction,
  ) => Promise<CatalogSubjectLocalOutcome>;
};

function safePageUrl(value: string): string {
  const parsed = new URL(value);
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
}

type CatalogTabUrlClassification =
  | "CATALOG_LANDING"
  | "CATALOG_SEARCH_RESULT"
  | "AUTHENTICATION"
  | "OUT_OF_SCOPE";

function classifyCatalogTabUrl(value: string): CatalogTabUrlClassification {
  const parsed = new URL(value);
  const authenticationMarker =
    `${parsed.hostname}${parsed.pathname}`.toLowerCase();
  if (
    /(?:saml|login|sign-?in|authentication|sessionexpired|session-expired)/.test(
      authenticationMarker,
    )
  ) {
    return "AUTHENTICATION";
  }
  if (parsed.origin !== "https://kean-ss.colleague.elluciancloud.com") {
    return "OUT_OF_SCOPE";
  }
  if (
    ["/Student/Courses", "/Student/Student/Courses"].includes(parsed.pathname)
  ) {
    return "CATALOG_LANDING";
  }
  if (
    [
      "/Student/Courses/SearchResult",
      "/Student/Student/Courses/SearchResult",
    ].includes(parsed.pathname)
  ) {
    return "CATALOG_SEARCH_RESULT";
  }
  return "OUT_OF_SCOPE";
}

function checkpointValidationError(state: CatalogBatchState): string | null {
  if (
    state.currentSubjectIndex !== state.completedSubjects.length ||
    state.currentSubjectIndex < 0 ||
    state.currentSubjectIndex >= state.subjectLimit ||
    state.subjectLimit > state.subjects.length ||
    !state.completedSubjects.every(
      (subject, index) => state.subjects[index]?.code === subject,
    ) ||
    !Number.isInteger(state.currentPage) ||
    state.currentPage < 0 ||
    !Number.isInteger(state.expectedNavigationRevision) ||
    state.expectedNavigationRevision < 0 ||
    state.leaseStatus !== "RELEASED"
  ) {
    return "The subject, page, or navigation checkpoint was inconsistent.";
  }
  const acceptedKeys = new Set(state.acceptedPageKeys);
  const fingerprintKeys = Object.keys(state.acceptedPageFingerprints);
  if (
    acceptedKeys.size !== state.acceptedPageKeys.length ||
    state.acceptedPageKeys.some(
      (key) =>
        !/^[A-Z0-9]{1,8}:[1-9][0-9]*$/.test(key) ||
        !state.acceptedPageFingerprints[key],
    ) ||
    fingerprintKeys.some((key) => !acceptedKeys.has(key))
  ) {
    return "Accepted Catalog pages were missing deterministic fingerprints.";
  }
  return null;
}

async function latestState(
  state: CatalogBatchState,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState> {
  return (await driver.loadState(state.batchId)) ?? state;
}

async function stopForError(
  state: CatalogBatchState,
  error: unknown,
  driver: CatalogBatchEventDriver,
  operation: CatalogBatchOperation = "UNKNOWN",
): Promise<CatalogBatchState> {
  const failedAt = driver.now();
  const details = catalogBatchErrorDetails(error, operation);
  const diagnostic: CatalogBatchFailureDiagnostic = {
    safeErrorName: details.safeErrorName,
    safeErrorMessage: details.safeErrorMessage,
    safeStack: details.safeStack,
    safeCause: details.safeCause,
    phase: state.stateMachineCheckpoint,
    operation,
    checkpoint: state.lastSuccessfulCheckpoint,
    runRevision: state.runnerRevision,
    navigationRevision: state.expectedNavigationRevision,
    returnedResultKind:
      details.returnedResultKind ??
      state.lastSubjectSearchResultKind ??
      state.lastSubjectPreparationResultKind,
    tabUrlClassification: state.currentSchoolTabUrlClassification,
    subjectCode: state.subjects[state.currentSubjectIndex]?.code ?? null,
    providerActionsWritten: "NO",
    timestamp: failedAt,
  };
  const stopped =
    details.code === "BATCH_CATALOG_PAGE_TIMEOUT" ||
    details.code === "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT" ||
    details.code === "BATCH_CATALOG_KNOCKOUT_TIMEOUT" ||
    details.code === "BATCH_CATALOG_SUBJECT_SELECTION_FAILED" ||
    details.code === "BATCH_CATALOG_TAB_UNAVAILABLE"
      ? pauseCatalogBatchForReason(
          state,
          details.code,
          failedAt,
          details.message,
        )
      : failCatalogBatch(
          state,
          details.code,
          details.message,
          failedAt,
          diagnostic,
        );
  const diagnosed = {
    ...stopped,
    failedOperation: operation,
    lastFailureDiagnostic: diagnostic,
  };
  await driver.persistState(diagnosed);
  return diagnosed;
}

export async function beginCatalogSubject(
  initialState: CatalogBatchState,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState> {
  let state = await latestState(initialState, driver);
  if (state.status !== "RUNNING") return state;
  let operation: CatalogBatchOperation = "INITIALIZE_FIRST_SUBJECT";
  try {
    operation = "GET_AUTHORIZED_TAB";
    const tabUrl = await driver.getAuthorizedTabUrl(state.tabId);
    if (!tabUrl) {
      state = pauseCatalogBatchForReason(
        state,
        "AUTHORIZED_CATALOG_TAB_CLOSED",
        driver.now(),
        "The authorized Kean Catalog tab was closed. Open the Catalog manually and start a new bounded run.",
        "BATCH_CATALOG_TAB_CLOSED",
      );
      await driver.persistState(state);
      return state;
    }
    if (safePageUrl(tabUrl) !== state.landingUrl) {
      state = recordCatalogBatchTransition(
        state,
        "LANDING_NAVIGATION_REQUESTED",
        driver.now(),
        {
          currentPage: 0,
          totalPagesForCurrentSubject: null,
          previousFirstCourseMarker: null,
          stateMachineCheckpoint: "LANDING_NAVIGATING",
        },
      );
      operation = "PERSIST_STATE";
      await driver.persistState(state);
      operation = "NAVIGATE_TO_LANDING";
      await driver.navigateToLanding(state);
      return state;
    }
    const subject = state.subjects[state.currentSubjectIndex];
    if (!subject || state.currentSubjectIndex >= state.subjectLimit) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_SUBJECT_DISCOVERY_INVALID",
        "The next bounded Catalog subject was unavailable.",
      );
    }
    state = {
      ...recordCatalogBatchCheckpoint(
        state,
        "FIRST_SUBJECT_INITIALIZED",
        driver.now(),
      ),
      lastSuccessfulCheckpoint: "FIRST_SUBJECT_INITIALIZED",
      failedOperation: null,
      lastFailureDiagnostic: null,
    };
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    const navigationRevision = state.expectedNavigationRevision + 1;
    state = recordCatalogBatchTransition(
      state,
      "SUBJECT_NAVIGATION_REQUESTED",
      driver.now(),
      {
        currentPage: 1,
        expectedNavigationRevision: navigationRevision,
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
        pauseReason: null,
        stateMachineCheckpoint: "LANDING_READY_WAIT_STARTED",
      },
    );
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    operation = "WATCH_SUBJECT_NAVIGATION";
    await driver.watchSubjectNavigation(state, navigationRevision);
    state = await latestState(state, driver);
    if (state.status !== "RUNNING") return state;
    state = {
      ...state,
      navigationTimeoutRevision: navigationRevision,
      stateMachineCheckpoint: "SUBJECT_SELECTION_STARTED",
      lastSuccessfulCheckpoint: "LANDING_READY",
    };
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    operation = "START_SUBJECT_SEARCH";
    const dispatch = await driver.startSubjectSearch(state, subject);
    const action = dispatch.preparation;
    const expectedCheckpoints: CatalogSearchAction["completedCheckpoints"] = [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
    ];
    const preparationValid =
      dispatch.preparationResultKind === "NULL_RESULT"
        ? action === null
        : action !== null &&
          action.action === "CATALOG_SEARCH_PREPARED" &&
          action.subjectCode === subject.code &&
          action.providerActionsWritten === "NO" &&
          action.completedCheckpoints.length === expectedCheckpoints.length &&
          !action.completedCheckpoints.some(
            (checkpoint, index) => checkpoint !== expectedCheckpoints[index],
          );
    state = await latestState(state, driver);
    const preparationCheckpointPersisted =
      state.preparationCheckpointRevision === navigationRevision &&
      ["CATALOG_LISTING_VERIFIED", "SEARCH_SUBMITTED"].includes(
        state.lastSuccessfulCheckpoint,
      );
    if (
      !preparationValid ||
      !preparationCheckpointPersisted ||
      !["VALUE", "NULL_RESULT"].includes(dispatch.submissionResultKind)
    ) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_CHECKPOINT_INVALID",
        "The Catalog subject search did not return the reviewed checkpoint sequence.",
      );
    }
    if (state.status !== "RUNNING") return state;
    const navigationObserved =
      state.lastTransition !== "SUBJECT_NAVIGATION_REQUESTED" ||
      state.lastTabUpdateStatus === "loading" ||
      state.lastSuccessfulCheckpoint === "SEARCH_SUBMITTED";
    if (
      state.lastTransition === "SUBJECT_NAVIGATION_REQUESTED" &&
      (dispatch.submissionResultKind === "VALUE" || navigationObserved)
    ) {
      state = {
        ...recordCatalogBatchCheckpoint(
          state,
          "SEARCH_SUBMITTED",
          driver.now(),
        ),
        lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
      };
    }
    const submissionEvidencePending =
      state.lastTransition === "SUBJECT_NAVIGATION_REQUESTED" &&
      dispatch.submissionResultKind === "NULL_RESULT" &&
      !navigationObserved;
    state = {
      ...state,
      contentReadyRevision: navigationRevision,
      lastSubjectPreparationResultKind: dispatch.preparationResultKind,
      lastSubjectSearchResultKind: dispatch.submissionResultKind,
      ...(submissionEvidencePending
        ? {
            stateMachineCheckpoint: "SEARCH_SUBMIT_STARTED" as const,
            lastSuccessfulCheckpoint:
              dispatch.preparationResultKind === "VALUE"
                ? ("CATALOG_LISTING_VERIFIED" as const)
                : state.lastSuccessfulCheckpoint,
          }
        : {}),
      failedOperation: null,
      lastFailureDiagnostic: null,
    };
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    return state;
  } catch (error: unknown) {
    return stopForError(state, error, driver, operation);
  }
}

export async function handleCatalogSubjectNavigationSignal(
  signal: CatalogSubjectNavigationSignal,
  senderTabId: number,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState | null> {
  let state = await driver.loadState(signal.batchId);
  if (
    !state ||
    state.batchId !== signal.batchId ||
    state.status !== "RUNNING" ||
    state.tabId !== senderTabId ||
    signal.providerActionsWritten !== "NO" ||
    signal.navigationRevision !== state.expectedNavigationRevision ||
    state.lastTransition !== "SUBJECT_NAVIGATION_REQUESTED"
  ) {
    return state;
  }
  const subjectCode = state.subjects[state.currentSubjectIndex]?.code ?? null;
  const landingPath = new URL(state.landingUrl).pathname;
  if (signal.signal === "PREPARATION_VERIFIED") {
    const expectedCheckpoints: CatalogSearchAction["completedCheckpoints"] = [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
    ];
    if (
      !subjectCode ||
      signal.subjectCode !== subjectCode ||
      signal.currentPath !== landingPath ||
      signal.checkpointToken !==
        catalogPreparationCheckpointToken(
          state.batchId,
          signal.navigationRevision,
          subjectCode,
        ) ||
      signal.completedCheckpoints.length !== expectedCheckpoints.length ||
      signal.completedCheckpoints.some(
        (checkpoint, index) => checkpoint !== expectedCheckpoints[index],
      )
    ) {
      return state;
    }
    const tabUrl = await driver.getAuthorizedTabUrl(state.tabId);
    if (!tabUrl || safePageUrl(tabUrl) !== state.landingUrl) return state;
    state = {
      ...recordCatalogBatchCheckpoint(
        state,
        "SEARCH_SUBMIT_STARTED",
        driver.now(),
      ),
      preparationCheckpointRevision: signal.navigationRevision,
      lastSuccessfulCheckpoint: "CATALOG_LISTING_VERIFIED",
      lastSubjectNavigationDiagnostics: null,
      failedOperation: null,
      lastFailureDiagnostic: null,
    };
    await driver.persistState(state);
    return state;
  }
  if (
    !subjectCode ||
    signal.subjectCode !== subjectCode ||
    signal.currentPath !== landingPath
  ) {
    return state;
  }
  const tabUrl = await driver.getAuthorizedTabUrl(state.tabId);
  if (!tabUrl || safePageUrl(tabUrl) !== state.landingUrl) {
    return state;
  }
  const navigationDiagnostics = sanitizedCatalogSubjectNavigationDiagnostics(
    signal.diagnostics,
  );
  if (!navigationDiagnostics) return state;
  state = {
    ...state,
    lastSubjectNavigationDiagnostics: navigationDiagnostics,
  };
  return stopForError(
    state,
    new CatalogBatchError(
      "BATCH_CATALOG_SEARCH_NAVIGATION_TIMEOUT",
      "The authorized Catalog tab remained on the landing page after the subject search was requested.",
    ),
    driver,
    "WATCH_SUBJECT_NAVIGATION",
  );
}

export async function recordCatalogTabUpdate(
  tabId: number,
  status: "loading" | "complete",
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState | null> {
  let state = await driver.loadState("");
  if (!state || state.status !== "RUNNING" || state.tabId !== tabId) {
    return state;
  }
  state = {
    ...state,
    currentNavigationRevision:
      state.expectedNavigationRevision > 0
        ? state.expectedNavigationRevision
        : state.currentNavigationRevision,
    lastTabUpdateStatus: status,
    ...(state.lastTransition === "SUBJECT_NAVIGATION_REQUESTED" &&
    status === "loading"
      ? {
          stateMachineCheckpoint: "SEARCH_SUBMITTED" as const,
          lastSuccessfulCheckpoint: "SEARCH_SUBMITTED" as const,
        }
      : {}),
    updatedAt: driver.now(),
    providerActionsWritten: "NO",
  };
  await driver.persistState(state);
  return state;
}

export async function handleCatalogTabLoaded(
  tabId: number,
  loadedUrl: string,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState | null> {
  const stored = await driver.loadState("");
  if (!stored || stored.status !== "RUNNING" || stored.tabId !== tabId) {
    return stored;
  }
  let state = stored;
  let operation: CatalogBatchOperation = "GET_AUTHORIZED_TAB";
  try {
    const safeLoadedUrl = safePageUrl(loadedUrl);
    const classification = classifyCatalogTabUrl(safeLoadedUrl);
    state = {
      ...state,
      currentSchoolTabUrlClassification: classification,
    };
    if (classification === "AUTHENTICATION") {
      state = pauseCatalogBatchForReason(
        state,
        "MANUAL_REAUTH_REQUIRED",
        driver.now(),
        "The authorized Catalog tab reached an authentication page. Sign in manually before starting a fresh bounded run.",
        "BATCH_CATALOG_AUTH_REDIRECT",
      );
      operation = "PERSIST_STATE";
      await driver.persistState(state);
      return state;
    }
    if (classification === "OUT_OF_SCOPE") {
      state = pauseCatalogBatchForReason(
        state,
        "AUTHORIZED_TAB_OUT_OF_SCOPE",
        driver.now(),
        "The authorized tab left the reviewed Kean Catalog scope. The extension did not scan another tab.",
        "BATCH_CATALOG_TAB_OUT_OF_SCOPE",
      );
      operation = "PERSIST_STATE";
      await driver.persistState(state);
      return state;
    }
    if (
      state.lastTransition === "LANDING_NAVIGATION_REQUESTED" &&
      safeLoadedUrl === state.landingUrl
    ) {
      return beginCatalogSubject(state, driver);
    }
    const resultUrls = new Set([
      "https://kean-ss.colleague.elluciancloud.com/Student/Courses/SearchResult",
      "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult",
    ]);
    if (
      [
        "WAITING_FOR_RESULT_PAGE",
        "PAGE_NAVIGATION_REQUESTED",
        "PAGE_READY",
        "PAGE_CAPTURED",
        "SUBJECT_PROCESSING",
      ].includes(state.lastTransition) &&
      !resultUrls.has(safeLoadedUrl)
    ) {
      state = pauseCatalogBatchForReason(
        state,
        "AUTHORIZED_TAB_NAVIGATED_AWAY",
        driver.now(),
        "The authorized tab left the reviewed Catalog result page. The batch did not follow or replace it.",
      );
      operation = "PERSIST_STATE";
      await driver.persistState(state);
      return state;
    }
    if (state.lastTransition !== "SUBJECT_NAVIGATION_REQUESTED") {
      return state;
    }
    if (safeLoadedUrl === state.landingUrl) {
      // A late or duplicate landing `complete` event belongs to the landing
      // checkpoint that already started this revision. The revisioned
      // watchdog, not the stale tab event, decides whether navigation stalled.
      return state;
    }
    if (!resultUrls.has(safeLoadedUrl)) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_PROVENANCE_INVALID",
        "The authorized tab completed navigation outside the reviewed Kean Catalog result page.",
      );
    }
    state = {
      ...state,
      lastSuccessfulCheckpoint: "SEARCH_SUBMITTED",
    };
    state = recordCatalogBatchTransition(
      state,
      "WAITING_FOR_RESULT_PAGE",
      driver.now(),
      { stateMachineCheckpoint: "SEARCHRESULT_NAVIGATING" },
    );
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    operation = "WATCH_RESULT_PAGE";
    await driver.watchResultPage(
      state,
      state.currentPage,
      state.previousFirstCourseMarker,
    );
    return state;
  } catch (error: unknown) {
    return stopForError(state, error, driver, operation);
  }
}

const signalErrors: Record<
  Exclude<CatalogPageSignal["signal"], "READY">,
  { code: string; message: string }
> = {
  TIMEOUT: {
    code: "BATCH_CATALOG_PAGE_TIMEOUT",
    message:
      "The Catalog result page did not become ready within the bounded timeout.",
  },
  RATE_LIMIT: {
    code: "BATCH_CATALOG_RATE_LIMIT",
    message:
      "The school portal displayed a rate-limit signal. The batch stopped without retrying.",
  },
  PROVIDER_ERROR: {
    code: "BATCH_CATALOG_PROVIDER_ERROR",
    message:
      "The school portal displayed an error. The batch stopped without retrying.",
  },
  RESULT_VIEW_MISMATCH: {
    code: "BATCH_CATALOG_RESULT_VIEW_MISMATCH",
    message:
      "Kean returned Section Listing instead of the requested Catalog Listing.",
  },
  PARSER_DRIFT: {
    code: "BATCH_CATALOG_PARSER_DRIFT",
    message:
      "The reviewed Catalog result structure did not match the visible page.",
  },
  SUBJECT_MISMATCH: {
    code: "BATCH_CATALOG_PAGE_SUBJECT_MISMATCH",
    message:
      "The visible Catalog subject did not match the expected page checkpoint.",
  },
  PAGE_NUMBER_MISMATCH: {
    code: "BATCH_CATALOG_PAGE_NUMBER_MISMATCH",
    message:
      "The visible Catalog page number did not match the expected page checkpoint.",
  },
  PROVENANCE_INVALID: {
    code: "BATCH_CATALOG_PROVENANCE_INVALID",
    message:
      "The page-ready signal did not come from the reviewed Catalog result page.",
  },
};

export async function handleCatalogPageSignal(
  signal: CatalogPageSignal,
  senderTabId: number,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState | null> {
  const stored = await driver.loadState(signal.batchId);
  if (
    !stored ||
    stored.batchId !== signal.batchId ||
    stored.status !== "RUNNING" ||
    stored.tabId !== senderTabId ||
    signal.providerActionsWritten !== "NO"
  ) {
    return stored;
  }
  let state = stored;
  let operation: CatalogBatchOperation = "HANDLE_PAGE_SIGNAL";
  try {
    if (signal.navigationRevision !== state.expectedNavigationRevision) {
      return state;
    }
    state = { ...state, lastPageDiagnostics: signal.diagnostics };
    if (signal.signal !== "READY") {
      const details = signalErrors[signal.signal];
      return stopForError(
        state,
        new CatalogBatchError(details.code, details.message),
        driver,
        "HANDLE_PAGE_SIGNAL",
      );
    }
    if (
      !["WAITING_FOR_RESULT_PAGE", "PAGE_NAVIGATION_REQUESTED"].includes(
        state.lastTransition,
      )
    ) {
      return state;
    }
    if (
      signal.pageNumber !== state.currentPage &&
      signal.pageNumber !== null &&
      signal.pageNumber < state.currentPage
    ) {
      return state;
    }
    if (
      signal.pageNumber !== state.currentPage ||
      signal.totalPages === null ||
      signal.totalPages < signal.pageNumber ||
      signal.totalPages > 50 ||
      !signal.firstCourseMarker ||
      !signal.lastCourseMarker ||
      !signal.resultFingerprint ||
      signal.visibleCourseCount === null ||
      signal.visibleCourseCount < 1
    ) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_PAGINATION_INVALID",
        "The page-ready checkpoint did not match the expected Catalog page.",
      );
    }
    const subject = state.subjects[state.currentSubjectIndex];
    if (!subject) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_SUBJECT_DISCOVERY_INVALID",
        "The current Catalog subject was unavailable at the page-ready checkpoint.",
      );
    }
    if (signal.subjectCode !== subject.code) {
      throw new CatalogBatchError(
        "BATCH_CATALOG_PAGE_SUBJECT_MISMATCH",
        `The visible SearchResult subject did not match ${subject.code}.`,
      );
    }
    state = recordCatalogBatchTransition(state, "PAGE_READY", driver.now(), {
      totalPagesForCurrentSubject: signal.totalPages,
      contentReadyRevision: signal.navigationRevision,
      stateMachineCheckpoint: "SEARCHRESULT_DOM_READY",
    });
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    operation = "CAPTURE_PAGE";
    const captured = await driver.capturePage(
      state,
      subject,
      state.currentPage,
      signal.resultFingerprint,
    );
    state = acceptCatalogPage(state, captured);
    state = recordCatalogBatchTransition(state, "PAGE_CAPTURED", driver.now(), {
      totalPagesForCurrentSubject: captured.totalPages,
      previousFirstCourseMarker: signal.firstCourseMarker,
      stateMachineCheckpoint: "PAGE_CAPTURED",
    });
    operation = "PERSIST_STATE";
    await driver.persistState(state);

    if (state.currentPage < captured.totalPages) {
      const targetPage = state.currentPage + 1;
      const previousMarker = signal.firstCourseMarker;
      const nextNavigationRevision = state.expectedNavigationRevision + 1;
      state = recordCatalogBatchTransition(
        state,
        "PAGE_NAVIGATION_REQUESTED",
        driver.now(),
        {
          currentPage: targetPage,
          previousFirstCourseMarker: previousMarker,
          expectedNavigationRevision: nextNavigationRevision,
          currentNavigationRevision: nextNavigationRevision,
          contentReadyRevision: null,
          navigationTimeoutRevision: nextNavigationRevision,
          stateMachineCheckpoint: "NEXT_PAGE",
        },
      );
      operation = "PERSIST_STATE";
      await driver.persistState(state);
      operation = "ADVANCE_PAGE";
      await driver.advancePage(state, targetPage, previousMarker);
      return state;
    }

    state = recordCatalogBatchTransition(
      state,
      "LAST_PAGE_CONFIRMED",
      driver.now(),
      {
        processingStage: "CAPTURE_COMPLETED",
        stateMachineCheckpoint: "LAST_PAGE_CONFIRMED",
      },
    );
    state = {
      ...state,
      completedProcessingStages: [
        ...new Set([
          ...state.completedProcessingStages,
          "CAPTURE_COMPLETED" as const,
        ]),
      ],
    };
    operation = "PERSIST_STATE";
    await driver.persistState(state);

    state = recordCatalogBatchTransition(
      state,
      "SUBJECT_PROCESSING",
      driver.now(),
      { processingStage: "LOCAL_STAGING" },
    );
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    const extraction = buildCatalogSubjectExtraction(state);
    operation = "PROCESS_SUBJECT";
    const outcome = await driver.processSubject(state, extraction);
    const controlState = await latestState(state, driver);
    state = completeCatalogSubject(state, outcome);
    if (state.status !== "COMPLETED" && controlState.status !== "RUNNING") {
      state = {
        ...state,
        status: controlState.status,
        leaseStatus: controlState.leaseStatus,
        pauseReason: controlState.pauseReason,
        lastErrorCode: controlState.lastErrorCode,
        lastErrorMessage: controlState.lastErrorMessage,
        lastErrorContext: controlState.lastErrorContext,
        lastTransition: controlState.lastTransition,
        stateMachineCheckpoint: controlState.stateMachineCheckpoint,
        lastTransitionAt: controlState.lastTransitionAt,
      };
    }
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    if (state.status !== "RUNNING") return state;

    state = recordCatalogBatchCheckpoint(state, "NEXT_SUBJECT", driver.now());
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    state = recordCatalogBatchTransition(
      state,
      "LANDING_NAVIGATION_REQUESTED",
      driver.now(),
      {
        currentPage: 0,
        totalPagesForCurrentSubject: null,
        previousFirstCourseMarker: null,
        stateMachineCheckpoint: "LANDING_NAVIGATING",
      },
    );
    operation = "PERSIST_STATE";
    await driver.persistState(state);
    operation = "NAVIGATE_TO_LANDING";
    await driver.navigateToLanding(state);
    return state;
  } catch (error: unknown) {
    return stopForError(state, error, driver, operation);
  }
}

export async function handleAuthorizedCatalogTabClosed(
  tabId: number,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState | null> {
  const state = await driver.loadState("");
  if (!state || state.status !== "RUNNING" || state.tabId !== tabId) {
    return state;
  }
  const paused = pauseCatalogBatchForReason(
    state,
    "AUTHORIZED_CATALOG_TAB_CLOSED",
    driver.now(),
    "The authorized Kean Catalog tab was closed. The batch did not open another school page.",
    "BATCH_CATALOG_TAB_CLOSED",
  );
  await driver.persistState(paused);
  return paused;
}

export async function resumeCatalogBatchEventDriven(
  pausedState: CatalogBatchState,
  driver: CatalogBatchEventDriver,
): Promise<CatalogBatchState> {
  let state = await latestState(pausedState, driver);
  if (state.status !== "PAUSED") return state;
  if (state.runnerRevision !== CATALOG_BATCH_ACCEPTANCE_REVISION) {
    state = failCatalogBatch(
      state,
      "BATCH_CATALOG_CHECKPOINT_INVALID",
      "The paused checkpoint belongs to a different Catalog runner revision.",
      driver.now(),
    );
    await driver.persistState(state);
    return state;
  }
  const checkpointError = checkpointValidationError(state);
  if (checkpointError) {
    state = failCatalogBatch(
      state,
      "BATCH_CATALOG_CHECKPOINT_INVALID",
      checkpointError,
      driver.now(),
    );
    await driver.persistState(state);
    return state;
  }
  const tabUrl = await driver.getAuthorizedTabUrl(state.tabId);
  if (!tabUrl) {
    const failedAt = driver.now();
    state = {
      ...state,
      lastErrorCode: "BATCH_CATALOG_TAB_CLOSED",
      lastErrorMessage:
        "The original authorized Kean tab is unavailable. The extension will not open an authenticated page.",
      lastErrorContext: catalogBatchErrorContext(state, failedAt),
      pauseReason: "AUTHORIZED_CATALOG_TAB_CLOSED",
      warnings: [...new Set([...state.warnings, "BATCH_CATALOG_TAB_CLOSED"])],
    };
    await driver.persistState(state);
    return state;
  }
  const classification = classifyCatalogTabUrl(safePageUrl(tabUrl));
  if (classification === "AUTHENTICATION") {
    const stoppedAt = driver.now();
    state = {
      ...state,
      currentSchoolTabUrlClassification: "AUTHENTICATION",
      lastErrorCode: "BATCH_CATALOG_AUTH_REDIRECT",
      lastErrorMessage:
        "The authorized Catalog tab still shows authentication. Restore the official Catalog manually before resuming.",
      pauseReason: "MANUAL_REAUTH_REQUIRED",
      warnings: [
        ...new Set([...state.warnings, "BATCH_CATALOG_AUTH_REDIRECT"]),
      ],
    };
    state = {
      ...state,
      lastErrorContext: catalogBatchErrorContext(state, stoppedAt),
    };
    await driver.persistState(state);
    return state;
  }
  if (classification === "OUT_OF_SCOPE") {
    const stoppedAt = driver.now();
    state = {
      ...state,
      currentSchoolTabUrlClassification: "OUT_OF_SCOPE",
      lastErrorCode: "BATCH_CATALOG_TAB_OUT_OF_SCOPE",
      lastErrorMessage:
        "The authorized tab is outside the reviewed Catalog scope. Return it manually before resuming.",
      pauseReason: "AUTHORIZED_TAB_OUT_OF_SCOPE",
      warnings: [
        ...new Set([...state.warnings, "BATCH_CATALOG_TAB_OUT_OF_SCOPE"]),
      ],
    };
    state = {
      ...state,
      lastErrorContext: catalogBatchErrorContext(state, stoppedAt),
    };
    await driver.persistState(state);
    return state;
  }
  state = resumeCatalogBatch(state);
  state = recordCatalogBatchTransition(state, "RESUMED", driver.now(), {
    currentPage: 0,
    totalPagesForCurrentSubject: null,
    previousFirstCourseMarker: null,
    pauseReason: null,
    currentSchoolTabUrlClassification: classification,
    stateMachineCheckpoint: "RESUMED",
  });
  await driver.persistState(state);
  state = recordCatalogBatchTransition(
    state,
    "LANDING_NAVIGATION_REQUESTED",
    driver.now(),
    { stateMachineCheckpoint: "LANDING_NAVIGATING" },
  );
  await driver.persistState(state);
  await driver.navigateToLanding(state);
  return state;
}
