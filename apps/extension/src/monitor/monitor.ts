import {
  CATALOG_BATCH_ACCEPTANCE_REVISION,
  type CatalogBatchLifecycleNotice,
  type CatalogBatchState,
} from "../content/catalog-batch.js";
import {
  catalogBatchPublicState,
  type CatalogBatchPublicState,
} from "../content/catalog-batch-lifecycle.js";
import { isLocalApiBaseUrl } from "../shared/local-api.js";

type ApiResponse = { ok: boolean; status: number; payload: unknown };

type MonitorChromeApi = {
  runtime: {
    lastError?: { message?: string };
    sendMessage: (
      message: unknown,
      callback: (response: unknown) => void,
    ) => void;
  };
  storage: {
    local: {
      get: (
        keys: string[],
        callback: (settings: {
          apiBaseUrl?: string;
          catalogBatch?: unknown;
          catalogBatchLifecycleNotice?: unknown;
        }) => void,
      ) => void;
    };
    onChanged: {
      addListener: (
        listener: (changes: Record<string, unknown>, areaName: string) => void,
      ) => void;
    };
  };
};

declare const chrome: MonitorChromeApi;

let apiBaseUrl = "";
let latestState: CatalogBatchPublicState | null = null;
let latestPersistedBatch: CatalogBatchState | null = null;
let latestLifecycleNotice: CatalogBatchLifecycleNotice | null = null;

function element(id: string): HTMLElement | null {
  return document.getElementById(id);
}

function setText(id: string, value: string): void {
  const target = element(id);
  if (target) target.textContent = value;
}

function setButton(id: string, enabled: boolean): void {
  const target = element(id);
  if (target instanceof HTMLButtonElement) target.disabled = !enabled;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function publicState(value: unknown): CatalogBatchPublicState | null {
  if (
    !isObject(value) ||
    typeof value.batchRunId !== "string" ||
    typeof value.batchStatus !== "string" ||
    typeof value.authorizedTabId !== "number" ||
    value.providerActionsWritten !== "NO"
  ) {
    return null;
  }
  return value as CatalogBatchPublicState;
}

function persistedBatch(value: unknown): CatalogBatchState | null {
  if (
    !isObject(value) ||
    typeof value.batchId !== "string" ||
    typeof value.status !== "string" ||
    !Array.isArray(value.subjects) ||
    !Array.isArray(value.completedSubjects) ||
    typeof value.startedAt !== "string" ||
    typeof value.lastTransition !== "string" ||
    typeof value.lastTransitionAt !== "string" ||
    value.providerActionsWritten !== "NO"
  ) {
    return null;
  }
  return value as CatalogBatchState;
}

function lifecycleNotice(value: unknown): CatalogBatchLifecycleNotice | null {
  if (
    !isObject(value) ||
    value.kind !== "SUPERSEDED" ||
    typeof value.batchRunId !== "string" ||
    typeof value.previousRunnerRevision !== "string" ||
    typeof value.currentRunnerRevision !== "string" ||
    value.reason !== "SUPERSEDED_BY_NEW_REVISION" ||
    typeof value.archivedAt !== "string" ||
    value.providerActionsWritten !== "NO"
  ) {
    return null;
  }
  return value as CatalogBatchLifecycleNotice;
}

function publicPersistedState(): CatalogBatchPublicState | null {
  if (!latestPersistedBatch) return null;
  try {
    return catalogBatchPublicState(
      latestPersistedBatch,
      new Date().toISOString(),
    );
  } catch {
    return null;
  }
}

function duration(seconds: number | null): string {
  if (seconds === null) return "Unavailable";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function yesNo(value: boolean | undefined): string {
  return value === undefined ? "-" : value ? "YES" : "NO";
}

function safeDiagnosticText(value: string | null | undefined): string {
  if (!value) return "-";
  return value.replace(/\s+/g, " ").trim().slice(0, 240) || "-";
}

function resumeAvailability(state: CatalogBatchPublicState | null): {
  enabled: boolean;
  text: string;
} {
  if (state?.batchStatus !== "PAUSED") {
    return {
      enabled: false,
      text: "NO_PAUSED_RUN — Resume requires a paused run.",
    };
  }
  if (state.runnerRevision !== CATALOG_BATCH_ACCEPTANCE_REVISION) {
    return {
      enabled: false,
      text: "REVISION_MISMATCH — This checkpoint belongs to an older runner.",
    };
  }
  if (state.leaseStatus !== "RELEASED") {
    return {
      enabled: false,
      text: "CHECKPOINT_INVALID — A paused run cannot retain an active lease.",
    };
  }
  if (state.lastError?.code === "BATCH_CATALOG_CHECKPOINT_INVALID") {
    return {
      enabled: false,
      text: "CHECKPOINT_INVALID — Cancel this run; it cannot resume safely.",
    };
  }
  if (
    state.lastError?.code === "BATCH_CATALOG_TAB_CLOSED" ||
    state.currentSchoolTabUrlClassification === "UNAVAILABLE"
  ) {
    return {
      enabled: false,
      text: "AUTHORIZED_TAB_MISSING — The original school tab no longer exists.",
    };
  }
  if (state.currentSchoolTabUrlClassification === "AUTHENTICATION") {
    return {
      enabled: false,
      text: "MANUAL_REAUTH_REQUIRED — Restore the official Catalog tab manually first.",
    };
  }
  if (state.currentSchoolTabUrlClassification === "OUT_OF_SCOPE") {
    return {
      enabled: false,
      text: "AUTHORIZED_TAB_OUT_OF_SCOPE — Return the authorized tab to Catalog first.",
    };
  }
  return {
    enabled: true,
    text: "READY — The persisted checkpoint can resume.",
  };
}

function render(state: CatalogBatchPublicState | null): void {
  latestState = state;
  setText("batchStatus", state?.batchStatus ?? "Not started");
  setText("runId", state?.batchRunId ?? "-");
  setText("runnerRevision", state?.runnerRevision ?? "-");
  setText("acceptanceRevision", state?.acceptanceRevision ?? "-");
  setText("extensionVersion", state?.extensionVersion ?? "-");
  setText("processingStage", state?.processingStage ?? "-");
  setText(
    "schoolTabUrlClassification",
    state?.currentSchoolTabUrlClassification ?? "UNAVAILABLE",
  );
  setText("localStagedCount", String(state?.localStagedCount ?? 0));
  setText("localReviewValidCount", String(state?.localReviewValidCount ?? 0));
  setText(
    "localReviewWarningCount",
    String(state?.localReviewWarningCount ?? 0),
  );
  setText("localAppliedCount", String(state?.localAppliedCount ?? 0));
  setText("myprogressTotal", String(state?.myprogressTotalCount ?? 0));
  setText(
    "myprogressMappedBefore",
    String(state?.myprogressMappedBeforeCount ?? 0),
  );
  setText(
    "myprogressMappedAfter",
    String(state?.myprogressMappedAfterCount ?? 0),
  );
  setText(
    "myprogressUnmatchedAfter",
    String(state?.myprogressUnmatchedAfterCount ?? 0),
  );
  setText("myprogressRemapExecuted", yesNo(state?.myprogressRemapExecuted));
  setText(
    "currentSubjectIndex",
    state
      ? `${Math.min(state.currentSubjectIndex + 1, state.subjectLimit)} / ${state.subjectLimit}`
      : "0 / 0",
  );
  setText("stateMachineCheckpoint", state?.stateMachineCheckpoint ?? "-");
  setText("lastSuccessfulCheckpoint", state?.lastSuccessfulCheckpoint ?? "-");
  setText("failedOperation", state?.failedOperation ?? "-");
  setText("leaseStatus", state?.leaseStatus ?? "RELEASED");
  setText(
    "lastSubjectPreparationResultKind",
    state?.lastSubjectPreparationResultKind ?? "-",
  );
  setText(
    "lastSubjectSearchResultKind",
    state?.lastSubjectSearchResultKind ?? "-",
  );
  setText(
    "preparationCheckpointRevision",
    String(state?.preparationCheckpointRevision ?? "-"),
  );
  setText("currentSubject", state?.currentSubject ?? "-");
  setText("currentPage", String(state?.currentPage ?? 0));
  setText("subjectsDiscovered", String(state?.discoveredSubjectCount ?? 0));
  setText(
    "subjectsCompleted",
    state
      ? `${state.completedSubjectCount} / ${state.subjectLimit} (${state.discoveredSubjectCount} discovered)`
      : "0 / 0",
  );
  setText("coursesCaptured", String(state?.capturedRecordCount ?? 0));
  setText("uniqueCourses", String(state?.uniqueRecordCount ?? 0));
  setText("duplicates", String(state?.duplicateRecordCount ?? 0));
  setText("warnings", String(state?.warningCount ?? 0));
  setText("elapsedTime", duration(state?.elapsedSeconds ?? 0));
  setText(
    "estimatedRemaining",
    duration(state?.estimatedRemainingSeconds ?? null),
  );
  setText("lastWarning", state?.lastWarning ?? "-");
  setText(
    "lastError",
    state?.lastError
      ? `${state.lastError.code}${state.lastError.message ? `: ${state.lastError.message}` : ""}`
      : "-",
  );
  setText("lastTransition", state?.lastTransition ?? "-");
  setText("lastTransitionAt", state?.lastTransitionAt ?? "-");
  const failure = state?.lastFailureDiagnostic;
  setText("safeErrorName", failure?.safeErrorName ?? "-");
  setText("safeErrorMessage", failure?.safeErrorMessage ?? "-");
  setText("failurePhase", failure?.phase ?? "-");
  setText("failureOperation", failure?.operation ?? "-");
  setText("failureCheckpoint", failure?.checkpoint ?? "-");
  setText("failureRunRevision", failure?.runRevision ?? "-");
  setText(
    "failureNavigationRevision",
    failure ? String(failure.navigationRevision) : "-",
  );
  setText("failureResultKind", failure?.returnedResultKind ?? "-");
  setText("failureTabUrlClassification", failure?.tabUrlClassification ?? "-");
  setText("failureSubjectCode", failure?.subjectCode ?? "-");
  setText(
    "failureProviderActionsWritten",
    failure?.providerActionsWritten ?? "-",
  );
  setText("failureTimestamp", failure?.timestamp ?? "-");
  setText("safeErrorStack", failure?.safeStack || "-");
  const navigationDiagnostics = state?.lastSubjectNavigationDiagnostics;
  setText(
    "subjectNavigationDocumentReady",
    yesNo(navigationDiagnostics?.documentReady),
  );
  setText(
    "subjectNavigationSubjectControlPresent",
    yesNo(navigationDiagnostics?.subjectControlPresent),
  );
  setText(
    "subjectNavigationExpectedSubjectSelected",
    yesNo(navigationDiagnostics?.expectedSubjectSelected),
  );
  setText(
    "subjectNavigationCatalogListingControlPresent",
    yesNo(navigationDiagnostics?.catalogListingControlPresent),
  );
  setText(
    "subjectNavigationCatalogListingChecked",
    yesNo(navigationDiagnostics?.catalogListingChecked),
  );
  setText(
    "subjectNavigationSubmitControlPresent",
    yesNo(navigationDiagnostics?.submitControlPresent),
  );
  setText(
    "subjectNavigationSubmitControlEnabled",
    yesNo(navigationDiagnostics?.submitControlEnabled),
  );
  setText(
    "subjectNavigationPreparationSignalObserved",
    yesNo(navigationDiagnostics?.preparationSignalObserved),
  );
  setText(
    "subjectNavigationResultSurfacePresent",
    yesNo(navigationDiagnostics?.resultSurfacePresent),
  );
  setText(
    "subjectNavigationResultListPresent",
    yesNo(navigationDiagnostics?.resultListPresent),
  );
  setText(
    "subjectNavigationCourseCardCount",
    String(navigationDiagnostics?.courseCardCount ?? "-"),
  );
  setText(
    "subjectNavigationValidCourseIdentityCount",
    String(navigationDiagnostics?.validCourseIdentityCount ?? "-"),
  );
  setText(
    "subjectNavigationSectionResultPresent",
    yesNo(navigationDiagnostics?.sectionResultPresent),
  );
  const diagnostics = state?.lastPageDiagnostics;
  setText("expectedSubject", diagnostics?.expectedSubject ?? "-");
  setText("expectedPage", String(diagnostics?.expectedPage ?? "-"));
  setText(
    "searchResultNavigationReceived",
    yesNo(diagnostics?.searchResultNavigationReceived),
  );
  setText("searchResultUrlMatch", yesNo(diagnostics?.searchResultUrlMatch));
  setText("searchResultDomReady", yesNo(diagnostics?.searchResultDomReady));
  setText("visibleSubject", diagnostics?.visibleSubject ?? "-");
  setText("visibleSubjectSource", diagnostics?.visibleSubjectSource ?? "-");
  setText("diagnosticPageNumber", String(diagnostics?.pageNumber ?? "-"));
  setText("pageNumberSource", diagnostics?.pageNumberSource ?? "-");
  setText("courseCardCount", String(diagnostics?.courseCardCount ?? "-"));
  setText(
    "validCourseIdentityCount",
    String(diagnostics?.validCourseIdentityCount ?? "-"),
  );
  setText(
    "courseResultContainerPresent",
    yesNo(diagnostics?.courseResultContainerPresent),
  );
  setText(
    "resultContainerConnected",
    yesNo(diagnostics?.resultContainerConnected),
  );
  setText("spinnerPresent", yesNo(diagnostics?.spinnerPresent));
  setText("spinnerVisible", yesNo(diagnostics?.spinnerVisible));
  setText("spinnerSelector", safeDiagnosticText(diagnostics?.spinnerSelector));
  setText("spinnerNodeCount", String(diagnostics?.spinnerNodeCount ?? "-"));
  setText(
    "spinnerComputedDisplay",
    safeDiagnosticText(diagnostics?.spinnerComputedDisplay),
  );
  setText(
    "spinnerComputedVisibility",
    safeDiagnosticText(diagnostics?.spinnerComputedVisibility),
  );
  setText(
    "spinnerComputedOpacity",
    safeDiagnosticText(diagnostics?.spinnerComputedOpacity),
  );
  setText(
    "spinnerClientRect",
    safeDiagnosticText(diagnostics?.spinnerClientRect),
  );
  setText(
    "spinnerAriaHidden",
    safeDiagnosticText(diagnostics?.spinnerAriaHidden),
  );
  setText(
    "spinnerBlocksResultInteraction",
    yesNo(diagnostics?.spinnerBlocksResultInteraction),
  );
  setText(
    "spinnerIsCatalogResultsSpinner",
    yesNo(diagnostics?.spinnerIsCatalogResultsSpinner),
  );
  setText("spinnerHardGateValid", yesNo(diagnostics?.spinnerHardGateValid));
  setText(
    "spinnerClassification",
    safeDiagnosticText(diagnostics?.spinnerClassification),
  );
  setText("resultHeading", safeDiagnosticText(diagnostics?.resultHeading));
  setText("resultSummary", safeDiagnosticText(diagnostics?.resultSummary));
  setText("pageFingerprint", safeDiagnosticText(diagnostics?.pageFingerprint));
  setText(
    "previousPageFingerprint",
    safeDiagnosticText(diagnostics?.previousPageFingerprint),
  );
  setText("knockoutReady", yesNo(diagnostics?.knockoutReady));
  setText("domStable", yesNo(diagnostics?.domStable));
  setText(
    "domStableDurationMs",
    String(diagnostics?.domStableDurationMs ?? "-"),
  );
  setText("contentStable", yesNo(diagnostics?.contentStable));
  setText(
    "contentStabilityDurationMs",
    String(diagnostics?.contentStabilityDurationMs ?? "-"),
  );
  setText(
    "contentScriptRevision",
    safeDiagnosticText(diagnostics?.contentScriptRevision),
  );
  setText(
    "diagnosticRunnerRevision",
    safeDiagnosticText(diagnostics?.runnerRevision),
  );
  setText("expectedRevision", String(diagnostics?.expectedRevision ?? "-"));
  setText(
    "pageReadyGateFailedOn",
    safeDiagnosticText(diagnostics?.pageReadyGateFailedOn),
  );
  setText(
    "readyPredicatesPassing",
    safeDiagnosticText(diagnostics?.readyPredicatesPassing?.join(", ")),
  );
  setText("failedPredicate", safeDiagnosticText(diagnostics?.failedPredicate));
  setText(
    "currentPageTimeoutRootCause",
    safeDiagnosticText(diagnostics?.currentPageTimeoutRootCause),
  );

  const running = state?.batchStatus === "RUNNING";
  const resumable = resumeAvailability(state);
  const cancellable = running || state?.batchStatus === "PAUSED";
  setButton("pauseButton", running);
  setText(
    "pauseReason",
    running
      ? "READY — The active checkpoint can be paused."
      : "NOT_RUNNING — Pause requires an active run.",
  );
  setButton("resumeButton", resumable.enabled);
  setText("resumeReason", resumable.text);
  setButton("cancelButton", cancellable);
  setText(
    "cancelReason",
    cancellable
      ? "READY — Cancel preserves captured local evidence."
      : "NO_ACTIVE_RUN — Cancel requires a running or paused run.",
  );
}

function renderSuperseded(notice: CatalogBatchLifecycleNotice): void {
  render(null);
  setText("batchStatus", "SUPERSEDED");
  setText("runId", notice.batchRunId);
  setText("runnerRevision", notice.previousRunnerRevision);
  setText("acceptanceRevision", notice.currentRunnerRevision);
  setText("lastTransition", notice.reason);
  setText("stateMachineCheckpoint", notice.reason);
  setText("lastTransitionAt", notice.archivedAt);
  setText("leaseStatus", "RELEASED");
}

function send(message: unknown): Promise<ApiResponse> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response: unknown) => {
      const messageError = chrome.runtime.lastError?.message;
      if (messageError) {
        resolve({
          ok: false,
          status: 503,
          payload: { code: "BATCH_BACKGROUND_MESSAGE_FAILED" },
        });
        return;
      }
      if (!isObject(response)) {
        resolve({ ok: false, status: 503, payload: null });
        return;
      }
      resolve({
        ok: response.ok === true,
        status: typeof response.status === "number" ? response.status : 503,
        payload: response.payload,
      });
    });
  });
}

async function refresh(): Promise<void> {
  if (!isLocalApiBaseUrl(apiBaseUrl)) {
    render(null);
    setText("monitorNotice", "Pair with the isolated local app first.");
    return;
  }
  const result = await send({
    type: "SAPSOS_GET_CATALOG_BATCH_STATE",
    apiBaseUrl,
  });
  const workerState = result.ok ? publicState(result.payload) : null;
  const fallbackState = publicPersistedState();
  const state = workerState ?? fallbackState;
  if (state) render(state);
  else if (latestLifecycleNotice) renderSuperseded(latestLifecycleNotice);
  else render(null);
  setText(
    "monitorNotice",
    workerState
      ? "Persisted batch state connected."
      : fallbackState
        ? "Persisted local checkpoint connected; worker commands are temporarily unavailable."
        : latestLifecycleNotice
          ? "The prior run was superseded by a new revision; its evidence remains archived."
          : "Persisted batch state is temporarily unavailable.",
  );
}

async function command(
  type:
    | "SAPSOS_PAUSE_CATALOG_BATCH"
    | "SAPSOS_RESUME_CATALOG_BATCH"
    | "SAPSOS_CANCEL_CATALOG_BATCH",
): Promise<void> {
  if (!isLocalApiBaseUrl(apiBaseUrl)) return;
  const result = await send({ type, apiBaseUrl });
  const state = result.ok ? publicState(result.payload) : null;
  if (state) render(state);
  setText(
    "monitorNotice",
    result.ok ? "Batch command saved." : "Batch command was not accepted.",
  );
}

element("pauseButton")?.addEventListener("click", () => {
  void command("SAPSOS_PAUSE_CATALOG_BATCH");
});
element("resumeButton")?.addEventListener("click", () => {
  void command("SAPSOS_RESUME_CATALOG_BATCH");
});
element("cancelButton")?.addEventListener("click", () => {
  void command("SAPSOS_CANCEL_CATALOG_BATCH");
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") return;
  if ("catalogBatch" in changes) {
    const change = changes.catalogBatch;
    if (isObject(change) && "newValue" in change) {
      latestPersistedBatch = persistedBatch(change.newValue);
    }
  }
  if ("catalogBatchLifecycleNotice" in changes) {
    const change = changes.catalogBatchLifecycleNotice;
    if (isObject(change) && "newValue" in change) {
      latestLifecycleNotice = lifecycleNotice(change.newValue);
    }
  }
  void refresh();
});

chrome.storage.local.get(
  ["apiBaseUrl", "catalogBatch", "catalogBatchLifecycleNotice"],
  (settings) => {
    apiBaseUrl = settings.apiBaseUrl ?? "";
    latestPersistedBatch = persistedBatch(settings.catalogBatch);
    latestLifecycleNotice = lifecycleNotice(
      settings.catalogBatchLifecycleNotice,
    );
    void refresh();
  },
);

render(latestState);
