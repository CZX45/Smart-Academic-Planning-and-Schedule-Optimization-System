import {
  CATALOG_BATCH_LIMITS,
  CatalogBatchError,
  acceptCatalogPage,
  buildCatalogSubjectExtraction,
  catalogBatchErrorDetails,
  completeCatalogSubject,
  failCatalogBatch,
  type CatalogBatchPage,
  type CatalogBatchFailureDiagnostic,
  type CatalogBatchOperation,
  type CatalogBatchState,
  type CatalogSubject,
  type CatalogSubjectLocalOutcome,
} from "../content/catalog-batch.js";
import type { BrowserExtensionExtraction } from "../shared/types.js";

export type CatalogBatchDriver = {
  now: () => string;
  delay: (milliseconds: number) => Promise<void>;
  loadState: (batchId: string) => Promise<CatalogBatchState | null>;
  persistState: (state: CatalogBatchState) => Promise<void>;
  ensureLandingPage: (state: CatalogBatchState) => Promise<void>;
  startSubjectSearch: (
    state: CatalogBatchState,
    subject: CatalogSubject,
  ) => Promise<void>;
  capturePage: (
    state: CatalogBatchState,
    subject: CatalogSubject,
    expectedPage: number,
    previousFirstCourseMarker: string | null,
  ) => Promise<CatalogBatchPage>;
  advancePage: (
    state: CatalogBatchState,
    targetPage: number,
  ) => Promise<string>;
  processSubject: (
    state: CatalogBatchState,
    extraction: BrowserExtensionExtraction,
  ) => Promise<CatalogSubjectLocalOutcome>;
};

function timedOut(state: CatalogBatchState, now: string): boolean {
  const startedAt = Date.parse(state.startedAt);
  const checkedAt = Date.parse(now);
  return (
    !Number.isFinite(startedAt) ||
    !Number.isFinite(checkedAt) ||
    checkedAt - startedAt > CATALOG_BATCH_LIMITS.timeoutMs
  );
}

async function latestRunningState(
  state: CatalogBatchState,
  driver: CatalogBatchDriver,
): Promise<CatalogBatchState> {
  return (await driver.loadState(state.batchId)) ?? state;
}

export async function runCatalogBatch(
  initialState: CatalogBatchState,
  driver: CatalogBatchDriver,
): Promise<CatalogBatchState> {
  let state = (await driver.loadState(initialState.batchId)) ?? initialState;
  let operation: CatalogBatchOperation = "UNKNOWN";
  try {
    while (state.status === "RUNNING") {
      if (timedOut(state, driver.now())) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_TIMEOUT",
          "The batch exceeded its bounded total runtime.",
        );
      }
      const subject = state.subjects[state.currentSubjectIndex];
      if (!subject) {
        throw new CatalogBatchError(
          "BATCH_CATALOG_SUBJECT_DISCOVERY_INVALID",
          "The next discovered Catalog subject was unavailable.",
        );
      }

      operation = "NAVIGATE_TO_LANDING";
      await driver.ensureLandingPage(state);
      state = await latestRunningState(state, driver);
      if (state.status !== "RUNNING") return state;

      operation = "START_SUBJECT_SEARCH";
      await driver.startSubjectSearch(state, subject);
      await driver.delay(CATALOG_BATCH_LIMITS.pageIntervalMs);
      state = await latestRunningState(state, driver);
      if (state.status !== "RUNNING") return state;

      let expectedPage = 1;
      let totalPages = 1;
      let previousFirstCourseMarker: string | null = null;
      while (true) {
        if (timedOut(state, driver.now())) {
          throw new CatalogBatchError(
            "BATCH_CATALOG_TIMEOUT",
            "The batch exceeded its bounded total runtime.",
          );
        }
        operation = "CAPTURE_PAGE";
        const captured = await driver.capturePage(
          state,
          subject,
          expectedPage,
          previousFirstCourseMarker,
        );
        state = await latestRunningState(state, driver);
        if (state.status !== "RUNNING") return state;
        totalPages = captured.totalPages;
        state = acceptCatalogPage(state, captured);
        await driver.persistState(state);
        state = await latestRunningState(state, driver);
        if (state.status !== "RUNNING") return state;
        if (expectedPage >= totalPages) break;
        await driver.delay(CATALOG_BATCH_LIMITS.pageIntervalMs);
        state = await latestRunningState(state, driver);
        if (state.status !== "RUNNING") return state;
        operation = "ADVANCE_PAGE";
        previousFirstCourseMarker = await driver.advancePage(
          state,
          expectedPage + 1,
        );
        expectedPage += 1;
        await driver.delay(CATALOG_BATCH_LIMITS.pageIntervalMs);
      }

      state = await latestRunningState(state, driver);
      if (state.status !== "RUNNING") return state;
      state = {
        ...state,
        processingStage: "LOCAL_STAGING",
        completedProcessingStages: [
          ...new Set([
            ...state.completedProcessingStages,
            "CAPTURE_COMPLETED" as const,
          ]),
        ],
      };
      await driver.persistState(state);
      const extraction = buildCatalogSubjectExtraction(state);
      operation = "PROCESS_SUBJECT";
      const outcome = await driver.processSubject(state, extraction);
      const controlState = await latestRunningState(state, driver);
      state = completeCatalogSubject(state, outcome);
      if (state.status !== "COMPLETED" && controlState.status !== "RUNNING") {
        state = {
          ...state,
          status: controlState.status,
          lastErrorCode: controlState.lastErrorCode,
          lastErrorMessage: controlState.lastErrorMessage,
        };
      }
      await driver.persistState(state);
      if (state.status !== "RUNNING") {
        return state;
      }
      await driver.delay(CATALOG_BATCH_LIMITS.pageIntervalMs);
      state = await latestRunningState(state, driver);
    }
    return state;
  } catch (error: unknown) {
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
      returnedResultKind: details.returnedResultKind,
      tabUrlClassification: state.currentSchoolTabUrlClassification,
      subjectCode: state.subjects[state.currentSubjectIndex]?.code ?? null,
      providerActionsWritten: "NO",
      timestamp: failedAt,
    };
    state = failCatalogBatch(
      state,
      details.code,
      details.message,
      failedAt,
      diagnostic,
    );
    await driver.persistState(state);
    return state;
  }
}
