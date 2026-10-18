import { afterEach, describe, expect, it, vi } from "vitest";

import { createCatalogBatchState } from "../src/content/catalog-batch.js";

class FakeElement {
  textContent = "";
  disabled = false;
  readonly listeners = new Map<string, Array<() => void>>();

  addEventListener(name: string, listener: EventListener): void {
    const listeners = this.listeners.get(name) ?? [];
    listeners.push(() => listener(new Event(name)));
    this.listeners.set(name, listeners);
  }
}

class FakeButtonElement extends FakeElement {}

const landingUrl =
  "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses";

function runningBatch() {
  return {
    ...createCatalogBatchState({
      apiBaseUrl: "http://localhost:8000",
      studentProfileId: "00000000-0000-4000-8000-000000000702",
      tabId: 42,
      landingUrl,
      subjects: [
        { code: "ACCT", label: "Accounting" },
        { code: "ANTH", label: "Anthropology" },
      ],
      startedAt: "2026-08-28T00:00:00.000Z",
      extensionVersion: "0.1.7",
      mode: "BOUNDED_ACCEPTANCE",
      subjectLimit: 2,
    }),
    lastSubjectPreparationResultKind: "NULL_RESULT" as const,
    lastSubjectSearchResultKind: "VALUE" as const,
    preparationCheckpointRevision: 1,
    lastSubjectNavigationDiagnostics: {
      documentReady: true,
      subjectControlPresent: true,
      expectedSubjectSelected: true,
      catalogListingControlPresent: true,
      catalogListingChecked: true,
      submitControlPresent: true,
      submitControlEnabled: true,
      preparationSignalObserved: true,
      resultSurfacePresent: false,
      resultListPresent: false,
      courseCardCount: 0,
      validCourseIdentityCount: 0,
      sectionResultPresent: false,
    },
    lastPageDiagnostics: {
      expectedSubject: "ACCT",
      expectedPage: 1,
      searchResultNavigationReceived: true,
      searchResultUrlMatch: true,
      searchResultDomReady: true,
      visibleSubject: "ACCT",
      visibleSubjectSource: "COURSE_CARD_ID" as const,
      pageNumber: 1,
      pageNumberSource: "FIRST_PAGE_STRUCTURE" as const,
      courseCardCount: 30,
      validCourseIdentityCount: 30,
      courseResultContainerPresent: true,
      resultContainerConnected: true,
      spinnerPresent: true,
      spinnerVisible: false,
      spinnerSelector:
        '[aria-busy="true"], .loading, .spinner, .esg-spinner-container',
      spinnerNodeCount: 1,
      spinnerComputedDisplay: "block",
      spinnerComputedVisibility: "visible",
      spinnerComputedOpacity: "1",
      spinnerClientRect: "0,0,24,24",
      spinnerAriaHidden: null,
      spinnerBlocksResultInteraction: false,
      spinnerIsCatalogResultsSpinner: true,
      spinnerHardGateValid: false,
      spinnerClassification: "NON_BLOCKING" as const,
      resultHeading: "Course Catalog",
      resultSummary: "30 results",
      pageFingerprint: "acct-page-1",
      previousPageFingerprint: null,
      knockoutReady: true,
      domStable: true,
      domStableDurationMs: 300,
      contentStable: true,
      contentStabilityDurationMs: 300,
      contentScriptRevision: "phase15b-main-world-checkpoint-v9",
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      expectedRevision: 1,
      pageReadyGateFailedOn: null,
      readyPredicatesPassing: [
        "RESULT_CONTAINER",
        "VALID_COURSE_IDENTITY_COUNT",
        "CONTENT_STABLE",
      ],
      failedPredicate: null,
      currentPageTimeoutRootCause: null,
    },
  };
}

async function loadMonitorWithUnavailableWorker(
  options: {
    storedBatch?: ReturnType<typeof runningBatch> | null;
    lifecycleNotice?: {
      kind: "SUPERSEDED";
      batchRunId: string;
      previousStatus: "PAUSED" | "FAILED";
      previousRunnerRevision: string;
      currentRunnerRevision: string;
      reason: "SUPERSEDED_BY_NEW_REVISION";
      archivedAt: string;
      providerActionsWritten: "NO";
    };
  } = {},
) {
  vi.resetModules();
  const ids = [
    "batchStatus",
    "runId",
    "runnerRevision",
    "acceptanceRevision",
    "extensionVersion",
    "processingStage",
    "schoolTabUrlClassification",
    "subjectsDiscovered",
    "localStagedCount",
    "localReviewValidCount",
    "localReviewWarningCount",
    "localAppliedCount",
    "myprogressTotal",
    "myprogressMappedBefore",
    "myprogressMappedAfter",
    "myprogressUnmatchedAfter",
    "myprogressRemapExecuted",
    "currentSubjectIndex",
    "stateMachineCheckpoint",
    "lastSuccessfulCheckpoint",
    "failedOperation",
    "safeErrorName",
    "safeErrorMessage",
    "failurePhase",
    "failureOperation",
    "failureCheckpoint",
    "failureRunRevision",
    "failureNavigationRevision",
    "failureResultKind",
    "failureTabUrlClassification",
    "failureSubjectCode",
    "failureProviderActionsWritten",
    "failureTimestamp",
    "safeErrorStack",
    "leaseStatus",
    "lastSubjectPreparationResultKind",
    "lastSubjectSearchResultKind",
    "preparationCheckpointRevision",
    "subjectNavigationDocumentReady",
    "subjectNavigationSubjectControlPresent",
    "subjectNavigationExpectedSubjectSelected",
    "subjectNavigationCatalogListingControlPresent",
    "subjectNavigationCatalogListingChecked",
    "subjectNavigationSubmitControlPresent",
    "subjectNavigationSubmitControlEnabled",
    "subjectNavigationPreparationSignalObserved",
    "subjectNavigationResultSurfacePresent",
    "subjectNavigationResultListPresent",
    "subjectNavigationCourseCardCount",
    "subjectNavigationValidCourseIdentityCount",
    "subjectNavigationSectionResultPresent",
    "expectedSubject",
    "expectedPage",
    "searchResultNavigationReceived",
    "searchResultUrlMatch",
    "searchResultDomReady",
    "visibleSubject",
    "visibleSubjectSource",
    "diagnosticPageNumber",
    "pageNumberSource",
    "courseCardCount",
    "validCourseIdentityCount",
    "courseResultContainerPresent",
    "resultContainerConnected",
    "spinnerPresent",
    "spinnerVisible",
    "spinnerSelector",
    "spinnerNodeCount",
    "spinnerComputedDisplay",
    "spinnerComputedVisibility",
    "spinnerComputedOpacity",
    "spinnerClientRect",
    "spinnerAriaHidden",
    "spinnerBlocksResultInteraction",
    "spinnerIsCatalogResultsSpinner",
    "spinnerHardGateValid",
    "spinnerClassification",
    "resultHeading",
    "resultSummary",
    "pageFingerprint",
    "previousPageFingerprint",
    "knockoutReady",
    "domStable",
    "domStableDurationMs",
    "contentStable",
    "contentStabilityDurationMs",
    "contentScriptRevision",
    "diagnosticRunnerRevision",
    "expectedRevision",
    "pageReadyGateFailedOn",
    "readyPredicatesPassing",
    "failedPredicate",
    "currentPageTimeoutRootCause",
    "currentSubject",
    "currentPage",
    "subjectsCompleted",
    "coursesCaptured",
    "uniqueCourses",
    "duplicates",
    "warnings",
    "elapsedTime",
    "estimatedRemaining",
    "lastWarning",
    "lastError",
    "lastTransition",
    "lastTransitionAt",
    "monitorNotice",
    "pauseButton",
    "pauseReason",
    "resumeButton",
    "resumeReason",
    "cancelButton",
    "cancelReason",
  ];
  const elements = Object.fromEntries(
    ids.map((id) => [
      id,
      id.endsWith("Button") ? new FakeButtonElement() : new FakeElement(),
    ]),
  ) as Record<string, FakeElement>;
  let storedBatch =
    options.storedBatch === undefined ? runningBatch() : options.storedBatch;
  let storageListener:
    | ((changes: Record<string, unknown>, areaName: string) => void)
    | undefined;
  const runtime: {
    lastError?: { message?: string };
    sendMessage: (
      message: unknown,
      callback: (response: unknown) => void,
    ) => void;
  } = {
    sendMessage: (_message, callback) => {
      runtime.lastError = { message: "Service worker is temporarily asleep" };
      callback(undefined);
      delete runtime.lastError;
    },
  };
  vi.stubGlobal("HTMLElement", FakeElement);
  vi.stubGlobal("HTMLButtonElement", FakeButtonElement);
  vi.stubGlobal("document", {
    getElementById: (id: string) => elements[id] ?? null,
  });
  vi.stubGlobal("chrome", {
    runtime,
    storage: {
      local: {
        get: (
          _keys: string[],
          callback: (settings: Record<string, unknown>) => void,
        ) =>
          callback({
            apiBaseUrl: "http://localhost:8000",
            catalogBatch: storedBatch,
            catalogBatchLifecycleNotice: options.lifecycleNotice,
          }),
      },
      onChanged: {
        addListener: (
          listener: (
            changes: Record<string, unknown>,
            areaName: string,
          ) => void,
        ) => {
          storageListener = listener;
        },
      },
    },
  });
  await import("../src/monitor/monitor.js");
  await new Promise((resolve) => setTimeout(resolve, 0));
  return {
    element: (id: string): FakeElement => {
      const target = elements[id];
      if (!target) throw new Error(`Missing fake monitor element: ${id}`);
      return target;
    },
    updateStoredBatch: () => {
      storedBatch = {
        ...(storedBatch ?? runningBatch()),
        coursesCaptured: 30,
        uniqueCourses: 28,
        lastTransition: "PAGE_CAPTURED",
        lastTransitionAt: "2026-08-28T00:02:00.000Z",
      };
      storageListener?.(
        { catalogBatch: { oldValue: null, newValue: storedBatch } },
        "local",
      );
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("persistent Catalog monitor page", () => {
  it("reconnects from the persisted local checkpoint when the worker message is unavailable", async () => {
    const monitor = await loadMonitorWithUnavailableWorker();

    expect(monitor.element("batchStatus").textContent).toBe("RUNNING");
    expect(monitor.element("runId").textContent).toBe(
      "2026-08-28T00:00:00.000Z:42",
    );
    expect(monitor.element("runnerRevision").textContent).toBe(
      "phase15b-main-world-checkpoint-v9",
    );
    expect(monitor.element("acceptanceRevision").textContent).toBe(
      "phase15b-main-world-checkpoint-v9",
    );
    expect(monitor.element("extensionVersion").textContent).toBe("0.1.7");
    expect(monitor.element("processingStage").textContent).toBe(
      "CAPTURE_RUNNING",
    );
    expect(monitor.element("schoolTabUrlClassification").textContent).toBe(
      "CATALOG_LANDING",
    );
    expect(monitor.element("localStagedCount").textContent).toBe("0");
    expect(monitor.element("localReviewValidCount").textContent).toBe("0");
    expect(monitor.element("localReviewWarningCount").textContent).toBe("0");
    expect(monitor.element("localAppliedCount").textContent).toBe("0");
    expect(monitor.element("myprogressTotal").textContent).toBe("0");
    expect(monitor.element("myprogressMappedBefore").textContent).toBe("0");
    expect(monitor.element("myprogressMappedAfter").textContent).toBe("0");
    expect(monitor.element("myprogressUnmatchedAfter").textContent).toBe("0");
    expect(monitor.element("currentSubjectIndex").textContent).toBe("1 / 2");
    expect(monitor.element("stateMachineCheckpoint").textContent).toBe(
      "SUBJECTS_DISCOVERED",
    );
    expect(monitor.element("lastSuccessfulCheckpoint").textContent).toBe(
      "SUBJECT_DISCOVERY_COMPLETED",
    );
    expect(monitor.element("failedOperation").textContent).toBe("-");
    expect(monitor.element("safeErrorName").textContent).toBe("-");
    expect(monitor.element("safeErrorMessage").textContent).toBe("-");
    expect(monitor.element("failurePhase").textContent).toBe("-");
    expect(monitor.element("failureOperation").textContent).toBe("-");
    expect(monitor.element("failureCheckpoint").textContent).toBe("-");
    expect(monitor.element("failureRunRevision").textContent).toBe("-");
    expect(monitor.element("failureNavigationRevision").textContent).toBe("-");
    expect(monitor.element("failureResultKind").textContent).toBe("-");
    expect(monitor.element("failureTabUrlClassification").textContent).toBe(
      "-",
    );
    expect(monitor.element("failureSubjectCode").textContent).toBe("-");
    expect(monitor.element("failureProviderActionsWritten").textContent).toBe(
      "-",
    );
    expect(monitor.element("failureTimestamp").textContent).toBe("-");
    expect(monitor.element("safeErrorStack").textContent).toBe("-");
    expect(monitor.element("leaseStatus").textContent).toBe("ACTIVE");
    expect(
      monitor.element("lastSubjectPreparationResultKind").textContent,
    ).toBe("NULL_RESULT");
    expect(monitor.element("lastSubjectSearchResultKind").textContent).toBe(
      "VALUE",
    );
    expect(monitor.element("preparationCheckpointRevision").textContent).toBe(
      "1",
    );
    expect(
      monitor.element("subjectNavigationPreparationSignalObserved").textContent,
    ).toBe("YES");
    expect(
      monitor.element("subjectNavigationExpectedSubjectSelected").textContent,
    ).toBe("YES");
    expect(
      monitor.element("subjectNavigationCourseCardCount").textContent,
    ).toBe("0");
    expect(monitor.element("resumeReason").textContent).toContain(
      "NO_PAUSED_RUN",
    );
    expect(monitor.element("currentSubject").textContent).toBe("ACCT");
    expect(monitor.element("subjectsDiscovered").textContent).toBe("2");
    expect(monitor.element("subjectsCompleted").textContent).toContain(
      "2 discovered",
    );
    expect(monitor.element("expectedSubject").textContent).toBe("ACCT");
    expect(monitor.element("expectedPage").textContent).toBe("1");
    expect(monitor.element("pageNumberSource").textContent).toBe(
      "FIRST_PAGE_STRUCTURE",
    );
    expect(monitor.element("courseCardCount").textContent).toBe("30");
    expect(monitor.element("spinnerVisible").textContent).toBe("NO");
    expect(monitor.element("spinnerNodeCount").textContent).toBe("1");
    expect(monitor.element("spinnerComputedDisplay").textContent).toBe("block");
    expect(monitor.element("spinnerBlocksResultInteraction").textContent).toBe(
      "NO",
    );
    expect(monitor.element("spinnerIsCatalogResultsSpinner").textContent).toBe(
      "YES",
    );
    expect(monitor.element("spinnerHardGateValid").textContent).toBe("NO");
    expect(monitor.element("spinnerClassification").textContent).toBe(
      "NON_BLOCKING",
    );
    expect(monitor.element("pageFingerprint").textContent).toBe("acct-page-1");
    expect(monitor.element("domStableDurationMs").textContent).toBe("300");
    expect(monitor.element("validCourseIdentityCount").textContent).toBe("30");
    expect(monitor.element("contentStable").textContent).toBe("YES");
    expect(monitor.element("readyPredicatesPassing").textContent).toContain(
      "VALID_COURSE_IDENTITY_COUNT",
    );
    expect(monitor.element("currentPageTimeoutRootCause").textContent).toBe(
      "-",
    );
    expect(monitor.element("monitorNotice").textContent).toContain(
      "Persisted local checkpoint connected",
    );

    monitor.updateStoredBatch();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(monitor.element("coursesCaptured").textContent).toBe("30");
    expect(monitor.element("uniqueCourses").textContent).toBe("28");
    expect(monitor.element("lastTransition").textContent).toBe("PAGE_CAPTURED");
  });

  it("renders semantic injection-result failure diagnostics", async () => {
    const storedBatch = {
      ...runningBatch(),
      status: "FAILED" as const,
      failedOperation: "START_SUBJECT_SEARCH" as const,
      lastFailureDiagnostic: {
        safeErrorName: "CatalogBatchError",
        safeErrorMessage:
          "The Catalog submit operation returned EMPTY_RESULTS.",
        safeStack: "",
        safeCause: null,
        phase: "SEARCH_SUBMIT_STARTED" as const,
        operation: "START_SUBJECT_SEARCH" as const,
        checkpoint: "CATALOG_LISTING_VERIFIED" as const,
        runRevision: "phase15b-main-world-checkpoint-v9",
        navigationRevision: 1,
        returnedResultKind: "EMPTY_RESULTS" as const,
        tabUrlClassification: "CATALOG_LANDING" as const,
        subjectCode: "ACCT",
        providerActionsWritten: "NO" as const,
        timestamp: "2026-08-31T16:37:20.399Z",
      },
    };

    const monitor = await loadMonitorWithUnavailableWorker({ storedBatch });

    expect(monitor.element("failureResultKind").textContent).toBe(
      "EMPTY_RESULTS",
    );
    expect(monitor.element("failureTabUrlClassification").textContent).toBe(
      "CATALOG_LANDING",
    );
    expect(monitor.element("failureSubjectCode").textContent).toBe("ACCT");
    expect(monitor.element("failureProviderActionsWritten").textContent).toBe(
      "NO",
    );
  });

  it("renders placeholders for omitted failure fields without mutating runner state", async () => {
    const storedBatch = runningBatch() as ReturnType<typeof runningBatch> &
      Record<string, unknown>;
    Reflect.deleteProperty(storedBatch, "lastSuccessfulCheckpoint");
    Reflect.deleteProperty(storedBatch, "failedOperation");
    Reflect.deleteProperty(storedBatch, "lastFailureDiagnostic");
    const before = structuredClone(storedBatch);

    const monitor = await loadMonitorWithUnavailableWorker({ storedBatch });

    expect(monitor.element("lastSuccessfulCheckpoint").textContent).toBe("-");
    expect(monitor.element("failedOperation").textContent).toBe("-");
    expect(monitor.element("safeErrorName").textContent).toBe("-");
    expect(monitor.element("safeErrorMessage").textContent).toBe("-");
    expect(monitor.element("failurePhase").textContent).toBe("-");
    expect(monitor.element("safeErrorStack").textContent).toBe("-");
    expect(storedBatch).toEqual(before);
  });

  it("shows a superseded archived run when no active batch owns the monitor", async () => {
    const monitor = await loadMonitorWithUnavailableWorker({
      storedBatch: null,
      lifecycleNotice: {
        kind: "SUPERSEDED",
        batchRunId: "legacy-run-1",
        previousStatus: "PAUSED",
        previousRunnerRevision: "LEGACY_UNVERSIONED",
        currentRunnerRevision: "phase15b-main-world-checkpoint-v9",
        reason: "SUPERSEDED_BY_NEW_REVISION",
        archivedAt: "2026-08-29T01:00:00.000Z",
        providerActionsWritten: "NO",
      },
    });

    expect(monitor.element("batchStatus").textContent).toBe("SUPERSEDED");
    expect(monitor.element("runId").textContent).toBe("legacy-run-1");
    expect(monitor.element("runnerRevision").textContent).toBe(
      "LEGACY_UNVERSIONED",
    );
    expect(monitor.element("stateMachineCheckpoint").textContent).toBe(
      "SUPERSEDED_BY_NEW_REVISION",
    );
    expect(monitor.element("monitorNotice").textContent).toContain(
      "evidence remains archived",
    );
  });
});
