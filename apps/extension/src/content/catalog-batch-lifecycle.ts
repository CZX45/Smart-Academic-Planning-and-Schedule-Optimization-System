import type {
  CatalogBatchState,
  CatalogBatchStateMachineCheckpoint,
  CatalogBatchTransition,
} from "./catalog-batch.js";
import { catalogBatchErrorContext } from "./catalog-batch.js";

export type CatalogBatchPublicState = {
  batchStatus: CatalogBatchState["status"];
  batchRunId: string;
  runnerRevision: string;
  acceptanceRevision: string;
  extensionVersion: string;
  createdAt: string;
  mode: CatalogBatchState["mode"];
  subjectLimit: number;
  boundedAcceptancePassed: boolean;
  boundedAcceptanceRevision: string | null;
  currentSubjectIndex: number;
  currentSubject: string | null;
  currentPage: number;
  expectedNavigationRevision: number;
  currentNavigationRevision: number | null;
  contentReadyRevision: number | null;
  navigationTimeoutRevision: number | null;
  preparationCheckpointRevision: number | null;
  lastTabUpdateStatus: "loading" | "complete" | null;
  lastSubjectPreparationResultKind: CatalogBatchState["lastSubjectPreparationResultKind"];
  lastSubjectSearchResultKind: CatalogBatchState["lastSubjectSearchResultKind"];
  lastSubjectNavigationDiagnostics: CatalogBatchState["lastSubjectNavigationDiagnostics"];
  discoveredSubjectCount: number;
  completedSubjectCount: number;
  capturedRecordCount: number;
  uniqueRecordCount: number;
  duplicateRecordCount: number;
  warningCount: number;
  lastWarning: string | null;
  lastError: {
    code: string;
    message: string | null;
    context: CatalogBatchState["lastErrorContext"];
  } | null;
  lastSuccessfulCheckpoint: CatalogBatchState["lastSuccessfulCheckpoint"];
  failedOperation: CatalogBatchState["failedOperation"];
  lastFailureDiagnostic: CatalogBatchState["lastFailureDiagnostic"];
  lastTransition: CatalogBatchTransition;
  stateMachineCheckpoint: CatalogBatchState["stateMachineCheckpoint"];
  lastTransitionAt: string;
  pauseReason: string | null;
  leaseStatus: CatalogBatchState["leaseStatus"];
  elapsedSeconds: number;
  estimatedRemainingSeconds: number | null;
  authorizedTabId: number;
  currentSchoolTabUrlClassification: CatalogBatchState["currentSchoolTabUrlClassification"];
  processingStage: CatalogBatchState["processingStage"];
  completedProcessingStages: CatalogBatchState["completedProcessingStages"];
  localStagedCount: number;
  localReviewValidCount: number;
  localReviewWarningCount: number;
  localAppliedCount: number;
  myprogressTotalCount: number;
  myprogressMappedBeforeCount: number;
  myprogressMappedAfterCount: number;
  myprogressUnmatchedAfterCount: number;
  myprogressRemapExecuted: boolean;
  lastPageDiagnostics: CatalogBatchState["lastPageDiagnostics"];
  providerActionsWritten: "NO";
};

type TransitionUpdates = Partial<
  Pick<
    CatalogBatchState,
    | "currentPage"
    | "expectedNavigationRevision"
    | "currentNavigationRevision"
    | "contentReadyRevision"
    | "navigationTimeoutRevision"
    | "preparationCheckpointRevision"
    | "lastTabUpdateStatus"
    | "lastSubjectPreparationResultKind"
    | "lastSubjectSearchResultKind"
    | "lastSubjectNavigationDiagnostics"
    | "totalPagesForCurrentSubject"
    | "previousFirstCourseMarker"
    | "pauseReason"
    | "currentSchoolTabUrlClassification"
    | "processingStage"
    | "stateMachineCheckpoint"
  >
>;

export function recordCatalogBatchTransition(
  state: CatalogBatchState,
  transition: CatalogBatchTransition,
  transitionedAt: string,
  updates: TransitionUpdates = {},
): CatalogBatchState {
  return {
    ...state,
    ...updates,
    updatedAt: transitionedAt,
    lastTransition: transition,
    lastTransitionAt: transitionedAt,
    providerActionsWritten: "NO",
  };
}

export function recordCatalogBatchCheckpoint(
  state: CatalogBatchState,
  checkpoint: CatalogBatchStateMachineCheckpoint,
  checkpointedAt: string,
): CatalogBatchState {
  return {
    ...state,
    stateMachineCheckpoint: checkpoint,
    updatedAt: checkpointedAt,
    lastTransitionAt: checkpointedAt,
    providerActionsWritten: "NO",
  };
}

export function pauseCatalogBatchForReason(
  state: CatalogBatchState,
  reason: string,
  pausedAt: string,
  message: string | null = null,
  errorCode: string = reason,
): CatalogBatchState {
  if (state.status !== "RUNNING") return state;
  return {
    ...state,
    status: "PAUSED",
    leaseStatus: "RELEASED",
    warnings: [...new Set([...state.warnings, reason])],
    updatedAt: pausedAt,
    lastErrorCode: errorCode,
    lastErrorMessage: message,
    lastErrorContext: catalogBatchErrorContext(state, pausedAt),
    lastTransition: "PAUSED",
    stateMachineCheckpoint: "PAUSED",
    lastTransitionAt: pausedAt,
    pauseReason: reason,
    providerActionsWritten: "NO",
  };
}

function safeElapsedSeconds(startedAt: string, now: string): number {
  const started = Date.parse(startedAt);
  const checked = Date.parse(now);
  if (
    !Number.isFinite(started) ||
    !Number.isFinite(checked) ||
    checked < started
  ) {
    return 0;
  }
  return Math.floor((checked - started) / 1_000);
}

export function catalogBatchPublicState(
  state: CatalogBatchState,
  now: string,
): CatalogBatchPublicState {
  const elapsedSeconds = safeElapsedSeconds(state.startedAt, now);
  const completed = state.completedSubjects.length;
  const remaining = Math.max(0, state.subjectLimit - completed);
  const estimatedRemainingSeconds =
    state.status === "RUNNING" && completed > 0 && remaining > 0
      ? Math.ceil((elapsedSeconds / completed) * remaining)
      : null;
  const subject = state.subjects[state.currentSubjectIndex];
  const warningCodes = [
    ...new Set([
      ...state.warnings,
      ...state.subjectWarnings.map((warning) => warning.code),
    ]),
  ];
  return {
    batchStatus: state.status,
    batchRunId: state.batchId,
    runnerRevision: state.runnerRevision,
    acceptanceRevision: state.acceptanceRevision,
    extensionVersion: state.extensionVersion,
    createdAt: state.createdAt,
    mode: state.mode,
    subjectLimit: state.subjectLimit,
    boundedAcceptancePassed: state.boundedAcceptancePassed,
    boundedAcceptanceRevision: state.boundedAcceptanceRevision,
    currentSubjectIndex: state.currentSubjectIndex,
    currentSubject: subject?.code ?? null,
    currentPage: state.currentPage,
    expectedNavigationRevision: state.expectedNavigationRevision,
    currentNavigationRevision: state.currentNavigationRevision,
    contentReadyRevision: state.contentReadyRevision,
    navigationTimeoutRevision: state.navigationTimeoutRevision,
    preparationCheckpointRevision: state.preparationCheckpointRevision,
    lastTabUpdateStatus: state.lastTabUpdateStatus,
    lastSubjectPreparationResultKind: state.lastSubjectPreparationResultKind,
    lastSubjectSearchResultKind: state.lastSubjectSearchResultKind,
    lastSubjectNavigationDiagnostics: state.lastSubjectNavigationDiagnostics
      ? { ...state.lastSubjectNavigationDiagnostics }
      : null,
    discoveredSubjectCount: state.subjects.length,
    completedSubjectCount: completed,
    capturedRecordCount: state.coursesCaptured,
    uniqueRecordCount: state.uniqueCourses,
    duplicateRecordCount: state.duplicatesIgnored,
    warningCount: warningCodes.length,
    lastWarning: warningCodes.at(-1) ?? null,
    lastError: state.lastErrorCode
      ? {
          code: state.lastErrorCode,
          message: state.lastErrorMessage,
          context: state.lastErrorContext
            ? { ...state.lastErrorContext }
            : null,
        }
      : null,
    lastSuccessfulCheckpoint: state.lastSuccessfulCheckpoint,
    failedOperation: state.failedOperation,
    lastFailureDiagnostic: state.lastFailureDiagnostic
      ? { ...state.lastFailureDiagnostic }
      : null,
    lastTransition: state.lastTransition,
    stateMachineCheckpoint: state.stateMachineCheckpoint,
    lastTransitionAt: state.lastTransitionAt,
    pauseReason: state.pauseReason,
    leaseStatus: state.leaseStatus,
    elapsedSeconds,
    estimatedRemainingSeconds,
    authorizedTabId: state.tabId,
    currentSchoolTabUrlClassification: state.currentSchoolTabUrlClassification,
    processingStage: state.processingStage,
    completedProcessingStages: [...state.completedProcessingStages],
    localStagedCount: state.localStagedCount,
    localReviewValidCount: state.localReviewValidCount,
    localReviewWarningCount: state.localReviewWarningCount,
    localAppliedCount: state.localAppliedCount,
    myprogressTotalCount: state.myprogressTotalCount,
    myprogressMappedBeforeCount: state.myprogressMappedBeforeCount,
    myprogressMappedAfterCount: state.myprogressMappedCount,
    myprogressUnmatchedAfterCount: state.myprogressUnmatchedCount,
    myprogressRemapExecuted: state.myprogressRemapExecuted,
    lastPageDiagnostics: state.lastPageDiagnostics,
    providerActionsWritten: "NO",
  };
}
