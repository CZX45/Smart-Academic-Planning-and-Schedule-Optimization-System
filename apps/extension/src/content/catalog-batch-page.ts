export type CatalogSubjectDiscovery = {
  landingUrl: string;
  subjects: Array<{ code: string; label: string }>;
  providerActionsWritten: "NO";
};

export type CatalogSearchAction = {
  action: "CATALOG_SEARCH_PREPARED";
  subjectCode: string;
  completedCheckpoints: readonly [
    "LANDING_DOM_READY",
    "KNOCKOUT_READY",
    "SUBJECT_SELECTED",
    "SUBJECT_SELECTION_VERIFIED",
    "CATALOG_LISTING_SELECTED",
    "CATALOG_LISTING_VERIFIED",
  ];
  providerActionsWritten: "NO";
};

export type CatalogPreparedAndSubmittedAction = {
  action: "CATALOG_SEARCH_PREPARED_AND_SUBMITTED";
  subjectCode: string;
  completedCheckpoints: readonly [
    "LANDING_DOM_READY",
    "KNOCKOUT_READY",
    "SUBJECT_SELECTED",
    "SUBJECT_SELECTION_VERIFIED",
    "CATALOG_LISTING_SELECTED",
    "CATALOG_LISTING_VERIFIED",
    "SEARCH_SUBMITTED",
  ];
  providerActionsWritten: "NO";
};

export type CatalogResultInspection =
  | {
      ready: true;
      pageNumber: number;
      totalPages: number;
      visibleCourseCount: number;
      subjectCode: string;
      firstCourseMarker: string;
      lastCourseMarker: string;
      resultFingerprint: string;
      fatalSignal: "RATE_LIMIT" | "PROVIDER_ERROR" | null;
      providerActionsWritten: "NO";
    }
  | {
      ready: false;
      errorCode:
        | "BATCH_CATALOG_RATE_LIMIT"
        | "BATCH_CATALOG_PROVIDER_ERROR"
        | "BATCH_CATALOG_PARSER_DRIFT"
        | "BATCH_CATALOG_RESULT_VIEW_MISMATCH"
        | "BATCH_CATALOG_PROVENANCE_INVALID";
      fatalSignal: "RATE_LIMIT" | "PROVIDER_ERROR" | null;
      providerActionsWritten: "NO";
    };

export type CatalogPaginationAction = {
  action: "CATALOG_PAGE_REQUESTED";
  targetPage: number;
  previousFirstCourseMarker: string;
  previousResultFingerprint: string;
  providerActionsWritten: "NO";
};

export type CatalogPageSignal = {
  type: "SAPSOS_CATALOG_PAGE_SIGNAL";
  batchId: string;
  signal:
    | "READY"
    | "TIMEOUT"
    | "RATE_LIMIT"
    | "PROVIDER_ERROR"
    | "RESULT_VIEW_MISMATCH"
    | "PARSER_DRIFT"
    | "SUBJECT_MISMATCH"
    | "PAGE_NUMBER_MISMATCH"
    | "PROVENANCE_INVALID";
  navigationRevision: number;
  pageNumber: number | null;
  totalPages: number | null;
  visibleCourseCount: number | null;
  subjectCode: string | null;
  firstCourseMarker: string | null;
  lastCourseMarker: string | null;
  resultFingerprint: string | null;
  diagnostics: CatalogPageReadyDiagnostics;
  providerActionsWritten: "NO";
};

export type CatalogPageReadyDiagnostics = {
  expectedSubject: string;
  expectedPage: number;
  searchResultNavigationReceived: boolean;
  searchResultUrlMatch: boolean;
  searchResultDomReady: boolean;
  visibleSubject: string | null;
  visibleSubjectSource: "COURSE_CARD_ID" | "CHECKPOINT_BOUND" | "UNAVAILABLE";
  pageNumber: number | null;
  pageNumberSource:
    | "CURRENT_PAGE_INPUT"
    | "FIRST_PAGE_STRUCTURE"
    | "UNAVAILABLE";
  courseCardCount: number;
  validCourseIdentityCount: number;
  courseResultContainerPresent: boolean;
  resultContainerConnected: boolean;
  spinnerPresent: boolean;
  spinnerVisible: boolean;
  spinnerSelector: string;
  spinnerNodeCount: number;
  spinnerComputedDisplay: string | null;
  spinnerComputedVisibility: string | null;
  spinnerComputedOpacity: string | null;
  spinnerClientRect: string | null;
  spinnerAriaHidden: string | null;
  spinnerBlocksResultInteraction: boolean;
  spinnerIsCatalogResultsSpinner: boolean;
  spinnerHardGateValid: boolean;
  spinnerClassification: "BLOCKING" | "NON_BLOCKING" | "UNKNOWN";
  resultHeading: string | null;
  resultSummary: string | null;
  pageFingerprint: string | null;
  previousPageFingerprint: string | null;
  knockoutReady: boolean;
  domStable: boolean;
  domStableDurationMs: number;
  contentStable: boolean;
  contentStabilityDurationMs: number;
  contentScriptRevision: string;
  runnerRevision: string;
  expectedRevision: number;
  pageReadyGateFailedOn: string | null;
  readyPredicatesPassing: string[];
  failedPredicate: string | null;
  currentPageTimeoutRootCause: string | null;
};

export type CatalogSubjectNavigationDiagnostics = {
  documentReady: boolean;
  subjectControlPresent: boolean;
  expectedSubjectSelected: boolean;
  catalogListingControlPresent: boolean;
  catalogListingChecked: boolean;
  submitControlPresent: boolean;
  submitControlEnabled: boolean;
  preparationSignalObserved: boolean;
  resultSurfacePresent: boolean;
  resultListPresent: boolean;
  courseCardCount: number;
  validCourseIdentityCount: number;
  sectionResultPresent: boolean;
};

type CatalogSubjectNavigationSignalBase = {
  type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL";
  batchId: string;
  navigationRevision: number;
  currentPath: string;
  providerActionsWritten: "NO";
};

export type CatalogSubjectNavigationSignal =
  | (CatalogSubjectNavigationSignalBase & {
      signal: "PREPARATION_VERIFIED";
      checkpointToken: string;
      subjectCode: string;
      completedCheckpoints: CatalogSearchAction["completedCheckpoints"];
    })
  | (CatalogSubjectNavigationSignalBase & {
      signal: "TIMEOUT";
      subjectCode: string;
      diagnostics: CatalogSubjectNavigationDiagnostics;
    });

type CatalogPageSignalRuntime = {
  lastError?: { message?: string };
  sendMessage: (
    message: CatalogPageSignal | CatalogSubjectNavigationSignal,
    callback?: (response: unknown) => void,
  ) => void;
};

export function discoverCatalogSubjects(
  expectedUrl: string,
): CatalogSubjectDiscovery {
  const actual = new URL(window.location.href);
  const expected = new URL(expectedUrl);
  const allowedPaths = new Set([
    "/Student/Courses",
    "/Student/Student/Courses",
  ]);
  actual.search = "";
  actual.hash = "";
  expected.search = "";
  expected.hash = "";
  if (
    actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    actual.toString() !== expected.toString() ||
    !allowedPaths.has(actual.pathname)
  ) {
    throw new Error(
      "BATCH_CATALOG_PROVENANCE_INVALID: Expected the visible Kean Course Catalog landing page.",
    );
  }
  const form = document.querySelector<HTMLFormElement>("form#search-form");
  const subject = document.querySelector<HTMLSelectElement>("select#subject-0");
  const formAction = form ? new URL(form.action, actual).pathname : "";
  if (
    !form ||
    form.method.toUpperCase() !== "GET" ||
    !["/Student/Courses/Search", "/Student/Student/Courses/Search"].includes(
      formAction,
    ) ||
    !subject
  ) {
    throw new Error(
      "BATCH_CATALOG_PARSER_DRIFT: Catalog subject controls no longer match the reviewed structure.",
    );
  }
  const subjects: Array<{ code: string; label: string }> = [];
  const seen = new Set<string>();
  for (const option of Array.from(subject.options)) {
    const code = option.value.trim().toUpperCase();
    const label = (option.textContent ?? "").replace(/\s+/g, " ").trim();
    if (!/^[A-Z0-9]{1,8}$/.test(code) || !label || seen.has(code)) {
      continue;
    }
    seen.add(code);
    subjects.push({ code, label });
  }
  if (subjects.length === 0 || subjects.length > 200) {
    throw new Error(
      "BATCH_CATALOG_SUBJECT_DISCOVERY_INVALID: Subject options were empty or exceeded the safety limit.",
    );
  }
  return {
    landingUrl: actual.toString(),
    subjects,
    providerActionsWritten: "NO",
  };
}

export async function prepareCatalogSubjectSearch(input: {
  expectedUrl: string;
  subjectCode: string;
  readyTimeoutMs?: number;
  settleMs?: number;
  submitCheckpoint?: {
    batchId: string;
    navigationRevision: number;
    checkpointToken: string;
    acknowledgmentTimeoutMs: number;
  };
}): Promise<CatalogSearchAction | CatalogPreparedAndSubmittedAction> {
  const actual = new URL(window.location.href);
  const expected = new URL(input.expectedUrl);
  const allowedPaths = new Set([
    "/Student/Courses",
    "/Student/Student/Courses",
  ]);
  actual.search = "";
  actual.hash = "";
  expected.search = "";
  expected.hash = "";
  if (
    actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    actual.toString() !== expected.toString() ||
    !allowedPaths.has(actual.pathname)
  ) {
    throw new Error(
      "BATCH_CATALOG_PROVENANCE_INVALID: Catalog search was not started from the reviewed landing page.",
    );
  }
  const subjectCode = input.subjectCode.trim().toUpperCase();
  const submitCheckpoint = input.submitCheckpoint;
  if (
    submitCheckpoint &&
    (!submitCheckpoint.batchId ||
      !Number.isInteger(submitCheckpoint.navigationRevision) ||
      submitCheckpoint.navigationRevision < 1 ||
      !/^[A-Za-z0-9:._-]{1,256}$/.test(submitCheckpoint.checkpointToken) ||
      !Number.isFinite(submitCheckpoint.acknowledgmentTimeoutMs) ||
      submitCheckpoint.acknowledgmentTimeoutMs < 50 ||
      submitCheckpoint.acknowledgmentTimeoutMs > 2_000)
  ) {
    throw new Error(
      "BATCH_CATALOG_CHECKPOINT_INVALID: Catalog preparation checkpoint input was invalid.",
    );
  }
  const form = document.querySelector<HTMLFormElement>("form#search-form");
  const subject = document.querySelector<HTMLSelectElement>("select#subject-0");
  const catalogView = document.querySelector<HTMLInputElement>(
    'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
  );
  const submit = document.querySelector<HTMLInputElement>(
    'input#submit-search-form[type="button"][value="Search"]',
  );
  const selectedOption = subject
    ? Array.from(subject.options).find(
        (option) => option.value.trim().toUpperCase() === subjectCode,
      )
    : undefined;
  const formAction = form ? new URL(form.action, actual).pathname : "";
  if (
    !form ||
    form.method.toUpperCase() !== "GET" ||
    !["/Student/Courses/Search", "/Student/Student/Courses/Search"].includes(
      formAction,
    ) ||
    !subject ||
    !catalogView ||
    !submit ||
    !selectedOption
  ) {
    throw new Error(
      "BATCH_CATALOG_PARSER_DRIFT: Catalog search controls or the requested subject are unavailable.",
    );
  }
  const readyTimeoutMs =
    Number.isFinite(input.readyTimeoutMs) &&
    Number(input.readyTimeoutMs) >= 50 &&
    Number(input.readyTimeoutMs) <= 60_000
      ? Number(input.readyTimeoutMs)
      : 20_000;
  const settleMs =
    Number.isFinite(input.settleMs) &&
    Number(input.settleMs) >= 50 &&
    Number(input.settleMs) <= 2_000
      ? Number(input.settleMs)
      : 300;
  const startedAt = Date.now();
  const bindingsReady = (...elements: Element[]): boolean => {
    try {
      const ko = (
        globalThis as typeof globalThis & {
          ko?: { contextFor?: (element: Element) => unknown };
        }
      ).ko;
      return (
        typeof ko?.contextFor === "function" &&
        elements.every((element) => ko.contextFor?.(element) != null)
      );
    } catch {
      return false;
    }
  };
  const subjectBindingReady = (subjectElement: HTMLSelectElement): boolean =>
    !subjectElement.hasAttribute("data-bind") || bindingsReady(subjectElement);
  const waitForStable = (
    inspect: () => boolean,
    timeoutCode: string,
    timeoutMessage: string,
  ): Promise<void> =>
    new Promise<void>((resolve, reject) => {
      let readySince: number | null = null;
      const inspectReady = (): void => {
        const now = Date.now();
        let ready = false;
        try {
          ready = inspect();
        } catch {
          ready = false;
        }
        if (ready) {
          readySince ??= now;
          if (now - readySince >= settleMs) {
            resolve();
            return;
          }
        } else {
          readySince = null;
        }
        if (now - startedAt >= readyTimeoutMs) {
          reject(new Error(`${timeoutCode}: ${timeoutMessage}`));
          return;
        }
        window.setTimeout(inspectReady, 25);
      };
      inspectReady();
    });

  await waitForStable(
    () => {
      const currentSubject =
        document.querySelector<HTMLSelectElement>("select#subject-0");
      const currentCatalogView = document.querySelector<HTMLInputElement>(
        'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
      );
      const currentSubmit = document.querySelector<HTMLInputElement>(
        'input#submit-search-form[type="button"][value="Search"]',
      );
      return (
        document.readyState === "complete" &&
        currentSubject?.isConnected === true &&
        currentSubject.disabled === false &&
        currentCatalogView?.isConnected === true &&
        currentCatalogView.disabled === false &&
        currentSubmit?.isConnected === true &&
        currentSubmit.disabled === false &&
        subjectBindingReady(currentSubject) &&
        bindingsReady(currentCatalogView, currentSubmit)
      );
    },
    "BATCH_CATALOG_KNOCKOUT_TIMEOUT",
    "Kean Catalog search bindings did not become ready within the bounded timeout.",
  );

  let signaledSubject: HTMLSelectElement | null = null;
  await waitForStable(
    () => {
      const currentSubject =
        document.querySelector<HTMLSelectElement>("select#subject-0");
      const currentCatalogView = document.querySelector<HTMLInputElement>(
        'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
      );
      const currentSubmit = document.querySelector<HTMLInputElement>(
        'input#submit-search-form[type="button"][value="Search"]',
      );
      const currentOption = currentSubject
        ? Array.from(currentSubject.options).find(
            (option) => option.value.trim().toUpperCase() === subjectCode,
          )
        : undefined;
      if (
        !currentSubject?.isConnected ||
        currentSubject.disabled ||
        !currentCatalogView?.isConnected ||
        currentCatalogView.disabled ||
        !currentSubmit?.isConnected ||
        currentSubmit.disabled ||
        !currentOption ||
        !subjectBindingReady(currentSubject) ||
        !bindingsReady(currentCatalogView, currentSubmit)
      ) {
        return false;
      }
      if (
        signaledSubject !== currentSubject ||
        currentSubject.value.trim().toUpperCase() !== subjectCode
      ) {
        signaledSubject = currentSubject;
        currentSubject.value = currentOption.value;
        currentSubject.dispatchEvent(new Event("input", { bubbles: true }));
        if (!currentSubject.isConnected) return false;
        currentSubject.dispatchEvent(new Event("change", { bubbles: true }));
        if (!currentSubject.isConnected) return false;
      }
      const selectedValues = Array.from(currentSubject.selectedOptions).map(
        (option) => option.value.trim().toUpperCase(),
      );
      return (
        currentSubject.value.trim().toUpperCase() === subjectCode &&
        selectedValues.length === 1 &&
        selectedValues[0] === subjectCode
      );
    },
    "BATCH_CATALOG_SUBJECT_SELECTION_FAILED",
    `The ${subjectCode} subject selection did not stabilize on the current Knockout-bound Catalog controls.`,
  );

  // Kean binds this radio through Knockout's `checked: searchResultsView`.
  // A property assignment changes only the DOM and leaves the view model on
  // SectionListing. A real click updates the reviewed read-only search model.
  let clickedCatalogView: HTMLInputElement | null = null;
  await waitForStable(
    () => {
      const currentSubject =
        document.querySelector<HTMLSelectElement>("select#subject-0");
      const currentCatalogView = document.querySelector<HTMLInputElement>(
        'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
      );
      const currentSubmit = document.querySelector<HTMLInputElement>(
        'input#submit-search-form[type="button"][value="Search"]',
      );
      if (
        currentSubject?.isConnected !== true ||
        currentSubject.value.trim().toUpperCase() !== subjectCode ||
        currentCatalogView?.isConnected !== true ||
        currentCatalogView.disabled ||
        currentSubmit?.isConnected !== true ||
        currentSubmit.disabled ||
        !subjectBindingReady(currentSubject) ||
        !bindingsReady(currentCatalogView, currentSubmit)
      ) {
        return false;
      }
      if (
        clickedCatalogView !== currentCatalogView ||
        !currentCatalogView.checked
      ) {
        clickedCatalogView = currentCatalogView;
        currentCatalogView.focus();
        currentCatalogView.click();
        if (!currentCatalogView.isConnected) return false;
      }
      return currentCatalogView.checked;
    },
    "BATCH_CATALOG_RESULT_VIEW_MISMATCH",
    "Catalog Listing did not become stable on the current Knockout-bound result controls.",
  );

  const readySubmit = document.querySelector<HTMLInputElement>(
    'input#submit-search-form[type="button"][value="Search"]',
  );
  const readySubject =
    document.querySelector<HTMLSelectElement>("select#subject-0");
  const readyCatalogView = document.querySelector<HTMLInputElement>(
    'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
  );
  if (
    readySubject?.isConnected !== true ||
    readySubject.value.trim().toUpperCase() !== subjectCode ||
    readyCatalogView?.isConnected !== true ||
    !readyCatalogView.checked ||
    readySubmit?.isConnected !== true ||
    readySubmit.disabled ||
    !subjectBindingReady(readySubject) ||
    !bindingsReady(readyCatalogView, readySubmit)
  ) {
    throw new Error(
      "BATCH_CATALOG_SUBJECT_SELECTION_FAILED: Catalog search controls changed after the subject-selection checkpoint.",
    );
  }
  readySubmit.focus();
  const focusedSubmit = document.querySelector<HTMLInputElement>(
    'input#submit-search-form[type="button"][value="Search"]',
  );
  if (
    focusedSubmit !== readySubmit ||
    !focusedSubmit.isConnected ||
    focusedSubmit.disabled
  ) {
    throw new Error(
      "BATCH_CATALOG_SUBJECT_SELECTION_FAILED: Catalog submit control changed after focus and preparation did not complete.",
    );
  }
  if (submitCheckpoint) {
    const completedCheckpoints = [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
    ] as const;
    await new Promise<void>((resolve, reject) => {
      let settled = false;
      let timeoutId = 0;
      const receiveAcknowledgment = (event: MessageEvent<unknown>): void => {
        if (event.source !== window || event.origin !== actual.origin) return;
        const data =
          typeof event.data === "object" && event.data !== null
            ? (event.data as Record<string, unknown>)
            : null;
        if (
          data?.type !== "SAPSOS_CATALOG_PREPARATION_ACKNOWLEDGED" ||
          data.batchId !== submitCheckpoint.batchId ||
          data.navigationRevision !== submitCheckpoint.navigationRevision ||
          data.checkpointToken !== submitCheckpoint.checkpointToken ||
          data.subjectCode !== subjectCode ||
          data.providerActionsWritten !== "NO"
        ) {
          return;
        }
        finish();
      };
      const finish = (error?: Error): void => {
        if (settled) return;
        settled = true;
        window.removeEventListener("message", receiveAcknowledgment);
        window.clearTimeout(timeoutId);
        if (error) reject(error);
        else resolve();
      };
      timeoutId = window.setTimeout(
        () =>
          finish(
            new Error(
              "BATCH_CATALOG_PREPARATION_SIGNAL_TIMEOUT: The durable preparation checkpoint was not acknowledged before Search.",
            ),
          ),
        submitCheckpoint.acknowledgmentTimeoutMs,
      );
      window.addEventListener("message", receiveAcknowledgment);
      window.postMessage(
        {
          type: "SAPSOS_CATALOG_PREPARATION_CHECKPOINT",
          batchId: submitCheckpoint.batchId,
          navigationRevision: submitCheckpoint.navigationRevision,
          checkpointToken: submitCheckpoint.checkpointToken,
          subjectCode,
          completedCheckpoints,
          providerActionsWritten: "NO",
        },
        actual.origin,
      );
    });
    const acknowledgedSubject =
      document.querySelector<HTMLSelectElement>("select#subject-0");
    const acknowledgedCatalogView = document.querySelector<HTMLInputElement>(
      'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
    );
    const acknowledgedSubmit = document.querySelector<HTMLInputElement>(
      'input#submit-search-form[type="button"][value="Search"]',
    );
    if (
      acknowledgedSubject?.isConnected !== true ||
      acknowledgedSubject.disabled ||
      acknowledgedSubject.value.trim().toUpperCase() !== subjectCode ||
      acknowledgedCatalogView?.isConnected !== true ||
      acknowledgedCatalogView.disabled ||
      !acknowledgedCatalogView.checked ||
      acknowledgedSubmit?.isConnected !== true ||
      acknowledgedSubmit.disabled ||
      (acknowledgedSubject.hasAttribute("data-bind") &&
        !bindingsReady(acknowledgedSubject)) ||
      !bindingsReady(acknowledgedCatalogView, acknowledgedSubmit)
    ) {
      throw new Error(
        "BATCH_CATALOG_SUBJECT_SELECTION_FAILED: Catalog controls changed after checkpoint acknowledgment and Search was not submitted.",
      );
    }
    acknowledgedSubmit.focus();
    acknowledgedSubmit.click();
    return {
      action: "CATALOG_SEARCH_PREPARED_AND_SUBMITTED",
      subjectCode,
      completedCheckpoints: [...completedCheckpoints, "SEARCH_SUBMITTED"],
      providerActionsWritten: "NO",
    };
  }
  return {
    action: "CATALOG_SEARCH_PREPARED",
    subjectCode,
    completedCheckpoints: [
      "LANDING_DOM_READY",
      "KNOCKOUT_READY",
      "SUBJECT_SELECTED",
      "SUBJECT_SELECTION_VERIFIED",
      "CATALOG_LISTING_SELECTED",
      "CATALOG_LISTING_VERIFIED",
    ],
    providerActionsWritten: "NO",
  };
}

export function watchCatalogSubjectNavigation(input: {
  expectedUrl: string;
  expectedSubject: string;
  batchId: string;
  navigationRevision: number;
  checkpointToken: string;
  timeoutMs: number;
}): {
  action: "CATALOG_SUBJECT_NAVIGATION_WATCH_STARTED";
  providerActionsWritten: "NO";
} {
  const actual = new URL(window.location.href);
  const expected = new URL(input.expectedUrl);
  actual.search = "";
  actual.hash = "";
  expected.search = "";
  expected.hash = "";
  if (
    actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    actual.toString() !== expected.toString() ||
    !["/Student/Courses", "/Student/Student/Courses"].includes(actual.pathname)
  ) {
    throw new Error(
      "BATCH_CATALOG_PROVENANCE_INVALID: Subject navigation watchdog requires the reviewed Catalog landing page.",
    );
  }
  if (
    !input.batchId ||
    !/^[A-Z0-9]{1,8}$/.test(input.expectedSubject) ||
    !Number.isInteger(input.navigationRevision) ||
    input.navigationRevision < 1 ||
    !/^[A-Za-z0-9:._-]{1,256}$/.test(input.checkpointToken) ||
    !Number.isFinite(input.timeoutMs) ||
    input.timeoutMs < 50 ||
    input.timeoutMs > 60_000
  ) {
    throw new Error(
      "BATCH_CATALOG_NAVIGATION_WATCH_INVALID: Subject navigation watchdog input was invalid.",
    );
  }
  const runtime = (
    globalThis as typeof globalThis & {
      chrome?: { runtime?: CatalogPageSignalRuntime };
    }
  ).chrome?.runtime;
  if (!runtime) {
    throw new Error(
      "BATCH_CATALOG_PAGE_ACCESS_FAILED: Extension messaging was unavailable on the visible Catalog page.",
    );
  }
  let preparationSignalObserved = false;
  let preparationSignalPending = false;
  const expectedCheckpoints = [
    "LANDING_DOM_READY",
    "KNOCKOUT_READY",
    "SUBJECT_SELECTED",
    "SUBJECT_SELECTION_VERIFIED",
    "CATALOG_LISTING_SELECTED",
    "CATALOG_LISTING_VERIFIED",
  ] as const;
  const receivePreparationCheckpoint = (event: MessageEvent<unknown>): void => {
    if (
      preparationSignalObserved ||
      preparationSignalPending ||
      event.source !== window ||
      event.origin !== expected.origin
    ) {
      return;
    }
    const data =
      typeof event.data === "object" && event.data !== null
        ? (event.data as Record<string, unknown>)
        : null;
    const checkpoints = Array.isArray(data?.completedCheckpoints)
      ? data.completedCheckpoints
      : [];
    const current = new URL(window.location.href);
    current.search = "";
    current.hash = "";
    if (
      data?.type !== "SAPSOS_CATALOG_PREPARATION_CHECKPOINT" ||
      data.batchId !== input.batchId ||
      data.navigationRevision !== input.navigationRevision ||
      data.checkpointToken !== input.checkpointToken ||
      data.subjectCode !== input.expectedSubject ||
      data.providerActionsWritten !== "NO" ||
      current.toString() !== expected.toString() ||
      checkpoints.length !== expectedCheckpoints.length ||
      checkpoints.some(
        (checkpoint, index) => checkpoint !== expectedCheckpoints[index],
      )
    ) {
      return;
    }
    preparationSignalPending = true;
    runtime.sendMessage(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: input.batchId,
        navigationRevision: input.navigationRevision,
        signal: "PREPARATION_VERIFIED",
        checkpointToken: input.checkpointToken,
        currentPath: current.pathname,
        subjectCode: input.expectedSubject,
        completedCheckpoints: expectedCheckpoints,
        providerActionsWritten: "NO",
      },
      (response) => {
        preparationSignalPending = false;
        const accepted =
          typeof response === "object" &&
          response !== null &&
          (response as { ok?: unknown }).ok === true;
        if (!accepted) {
          void runtime.lastError;
          return;
        }
        preparationSignalObserved = true;
        window.postMessage(
          {
            type: "SAPSOS_CATALOG_PREPARATION_ACKNOWLEDGED",
            batchId: input.batchId,
            navigationRevision: input.navigationRevision,
            checkpointToken: input.checkpointToken,
            subjectCode: input.expectedSubject,
            providerActionsWritten: "NO",
          },
          expected.origin,
        );
      },
    );
  };
  window.addEventListener("message", receivePreparationCheckpoint);
  window.setTimeout(() => {
    window.removeEventListener("message", receivePreparationCheckpoint);
    const current = new URL(window.location.href);
    current.search = "";
    current.hash = "";
    if (current.toString() !== expected.toString()) return;
    const subject =
      document.querySelector<HTMLSelectElement>("select#subject-0");
    const catalogView = document.querySelector<HTMLInputElement>(
      'input#course-catalog-result-view-type-course[type="radio"][value="CatalogListing"]',
    );
    const submit = document.querySelector<HTMLInputElement>(
      'input#submit-search-form[type="button"][value="Search"]',
    );
    const markers = Array.from(
      document.querySelectorAll<HTMLElement>(
        '#course-resultul span[id^="course-"]',
      ),
    );
    const validCourseIdentities = new Set(
      markers
        .map((marker) => {
          const card = marker.closest<HTMLElement>("li, article, section");
          for (const text of [
            card?.querySelector("h3")?.textContent ?? "",
            marker.textContent ?? "",
            marker.id.replace(/^course-/i, "").replace(/-/g, " "),
          ]) {
            const match = text.match(/\b([A-Z]{2,6})[*\s-]?(\d{3,4}[A-Z]?)\b/i);
            if (match)
              return `${match[1]?.toUpperCase()} ${match[2]?.toUpperCase()}`;
          }
          return null;
        })
        .filter((identity): identity is string => identity !== null),
    );
    runtime.sendMessage(
      {
        type: "SAPSOS_CATALOG_SUBJECT_NAVIGATION_SIGNAL",
        batchId: input.batchId,
        navigationRevision: input.navigationRevision,
        signal: "TIMEOUT",
        currentPath: current.pathname,
        subjectCode: input.expectedSubject,
        diagnostics: {
          documentReady: document.readyState !== "loading",
          subjectControlPresent: subject?.isConnected === true,
          expectedSubjectSelected:
            subject?.value.trim().toUpperCase() === input.expectedSubject,
          catalogListingControlPresent: catalogView?.isConnected === true,
          catalogListingChecked: catalogView?.checked === true,
          submitControlPresent: submit?.isConnected === true,
          submitControlEnabled:
            submit?.isConnected === true && submit.disabled === false,
          preparationSignalObserved,
          resultSurfacePresent:
            document.querySelector("#course-results") !== null,
          resultListPresent:
            document.querySelector("#course-resultul") !== null,
          courseCardCount: markers.length,
          validCourseIdentityCount: validCourseIdentities.size,
          sectionResultPresent:
            document.querySelector(
              '[role="grid"][aria-label="Table for sections"], table[aria-label="Table for sections"]',
            ) !== null,
        },
        providerActionsWritten: "NO",
      },
      () => void runtime.lastError,
    );
  }, input.timeoutMs);
  return {
    action: "CATALOG_SUBJECT_NAVIGATION_WATCH_STARTED",
    providerActionsWritten: "NO",
  };
}

export function inspectCatalogResultPage(
  input:
    | string
    | {
        expectedUrl: string;
        expectedSubject?: string;
      },
): CatalogResultInspection {
  const expectedUrl = typeof input === "string" ? input : input.expectedUrl;
  const checkpointSubject =
    typeof input === "string"
      ? null
      : (input.expectedSubject?.toUpperCase() ?? null);
  const checkpointSubjectValid =
    checkpointSubject !== null && /^[A-Z0-9]{1,8}$/.test(checkpointSubject);
  const actual = new URL(window.location.href);
  const expected = new URL(expectedUrl);
  const allowedPaths = new Set([
    "/Student/Courses/SearchResult",
    "/Student/Student/Courses/SearchResult",
  ]);
  actual.search = "";
  actual.hash = "";
  expected.search = "";
  expected.hash = "";
  if (
    actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    actual.toString() !== expected.toString() ||
    !allowedPaths.has(actual.pathname)
  ) {
    return {
      ready: false,
      errorCode: "BATCH_CATALOG_PROVENANCE_INVALID",
      fatalSignal: null,
      providerActionsWritten: "NO",
    };
  }
  const alertText = Array.from(
    document.querySelectorAll<HTMLElement>(
      '[role="alert"], .alert, .esg-alert, .eds-alert',
    ),
  )
    .map((element) => (element.innerText ?? "").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join(" ")
    .slice(0, 4_000);
  if (
    /too many requests|rate limit|temporarily blocked|\b429\b/i.test(alertText)
  ) {
    return {
      ready: false,
      errorCode: "BATCH_CATALOG_RATE_LIMIT",
      fatalSignal: "RATE_LIMIT",
      providerActionsWritten: "NO",
    };
  }
  if (
    /service unavailable|server error|unable to complete|something went wrong/i.test(
      alertText,
    )
  ) {
    return {
      ready: false,
      errorCode: "BATCH_CATALOG_PROVIDER_ERROR",
      fatalSignal: "PROVIDER_ERROR",
      providerActionsWritten: "NO",
    };
  }
  const isRendered = (element: HTMLElement): boolean => {
    const style = window.getComputedStyle(element);
    return (
      element.getClientRects().length > 0 &&
      !element.hidden &&
      element.closest("[hidden]") === null &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );
  };
  const resultListCandidates = Array.from(
    document.querySelectorAll<HTMLElement>("#course-resultul"),
  ).filter(
    (candidate) =>
      candidate.querySelectorAll<HTMLElement>('span[id^="course-"]').length > 0,
  );
  const renderedResultLists = resultListCandidates.filter(isRendered);
  const resultList =
    renderedResultLists.length === 1
      ? renderedResultLists[0]
      : resultListCandidates.length === 1
        ? resultListCandidates[0]
        : null;
  const courseMarkers = resultList
    ? Array.from(
        resultList.querySelectorAll<HTMLElement>('span[id^="course-"]'),
      )
    : [];
  const validCourseIdentities = new Set(
    courseMarkers
      .map((marker) => {
        const card = marker.closest<HTMLElement>("li, article, section");
        const identityTexts = [
          card?.querySelector("h3")?.textContent ?? "",
          marker.textContent ?? "",
          marker.id.replace(/^course-/i, "").replace(/-/g, " "),
        ];
        for (const text of identityTexts) {
          const match = text.match(/\b([A-Z]{2,6})[*\s-]?(\d{3,4}[A-Z]?)\b/i);
          if (match)
            return `${match[1]?.toUpperCase()} ${match[2]?.toUpperCase()}`;
        }
        return null;
      })
      .filter((identity): identity is string => identity !== null),
  );
  if (
    !resultList ||
    !resultList.isConnected ||
    courseMarkers.length === 0 ||
    validCourseIdentities.size === 0
  ) {
    const sectionResult = document.querySelector(
      '[role="grid"][aria-label="Table for sections"], table[aria-label="Table for sections"]',
    );
    return {
      ready: false,
      errorCode: sectionResult
        ? "BATCH_CATALOG_RESULT_VIEW_MISMATCH"
        : "BATCH_CATALOG_PARSER_DRIFT",
      fatalSignal: null,
      providerActionsWritten: "NO",
    };
  }
  const resultSurface =
    resultList?.closest<HTMLElement>("#course-results") ?? null;
  const paginationRoot: ParentNode = resultSurface ?? document;
  const currentInputCandidates = Array.from(
    paginationRoot.querySelectorAll<HTMLInputElement>(
      '#course-results-current-page, input[aria-label="Current Page Number"]',
    ),
  );
  const renderedCurrentInputs = currentInputCandidates.filter(isRendered);
  const currentInput =
    renderedCurrentInputs.length === 1
      ? renderedCurrentInputs[0]
      : currentInputCandidates.length === 1
        ? currentInputCandidates[0]
        : null;
  const pageNumber = Number(currentInput?.value ?? "");
  const pageTargets = Array.from(
    paginationRoot.querySelectorAll<HTMLButtonElement>(
      'button[aria-label^="Link to results page "]',
    ),
  )
    .map((button) =>
      Number(
        button
          .getAttribute("aria-label")
          ?.match(/^Link to results page (\d+)$/)?.[1],
      ),
    )
    .filter((value) => Number.isInteger(value) && value > 0);
  const firstPageFallback =
    !currentInput &&
    pageTargets.every((targetPage) => targetPage > 1) &&
    !paginationRoot.querySelector('[aria-current="page"]');
  const resolvedPageNumber = firstPageFallback ? 1 : pageNumber;
  const totalPages = Math.max(resolvedPageNumber, 1, ...pageTargets);
  const subjectCodes = new Set(
    courseMarkers
      .map((marker) =>
        marker.id.match(/^course-([A-Z0-9]{1,8})-/i)?.[1]?.toUpperCase(),
      )
      .filter((value): value is string => Boolean(value)),
  );
  const visibleSubject =
    subjectCodes.size === 1 ? (Array.from(subjectCodes)[0] ?? null) : null;
  const resolvedSubject =
    visibleSubject ??
    (subjectCodes.size === 0 && checkpointSubjectValid
      ? checkpointSubject
      : null);
  if (
    (!currentInput && !firstPageFallback) ||
    !Number.isInteger(resolvedPageNumber) ||
    resolvedPageNumber < 1 ||
    totalPages > 50 ||
    resolvedPageNumber > totalPages ||
    subjectCodes.size > 1 ||
    !resolvedSubject ||
    (visibleSubject !== null &&
      checkpointSubjectValid &&
      visibleSubject !== checkpointSubject)
  ) {
    return {
      ready: false,
      errorCode: "BATCH_CATALOG_PARSER_DRIFT",
      fatalSignal: null,
      providerActionsWritten: "NO",
    };
  }
  return {
    ready: true,
    pageNumber: resolvedPageNumber,
    totalPages,
    visibleCourseCount: courseMarkers.length,
    subjectCode: resolvedSubject,
    firstCourseMarker: courseMarkers[0]?.id ?? "",
    lastCourseMarker: courseMarkers.at(-1)?.id ?? "",
    resultFingerprint: courseMarkers
      .map((marker) => marker.id)
      .sort()
      .join("\u001f"),
    fatalSignal: null,
    providerActionsWritten: "NO",
  };
}

export function watchCatalogResultPage(input: {
  expectedUrl: string;
  batchId: string;
  expectedPage: number;
  expectedSubject: string;
  navigationRevision: number;
  runnerRevision: string;
  previousFirstCourseMarker: string | null;
  previousResultFingerprint?: string | null;
  timeoutMs: number;
  settleMs?: number;
}): { action: "CATALOG_RESULT_WATCH_STARTED"; providerActionsWritten: "NO" } {
  const runtime = (
    globalThis as typeof globalThis & {
      chrome?: { runtime?: CatalogPageSignalRuntime };
    }
  ).chrome?.runtime;
  if (!runtime) {
    throw new Error(
      "BATCH_CATALOG_PAGE_ACCESS_FAILED: Extension messaging was unavailable on the visible Catalog page.",
    );
  }
  let finished = false;
  let observer: MutationObserver | null = null;
  let timeoutId: number | null = null;
  let pollId: number | null = null;
  let candidateFingerprint: string | null = null;
  let candidateResultList: HTMLElement | null = null;
  let candidateNavigationRevision: number | null = null;
  let candidateSince = 0;
  const settleMs =
    Number.isFinite(input.settleMs) &&
    Number(input.settleMs) >= 50 &&
    Number(input.settleMs) <= 2_000
      ? Number(input.settleMs)
      : 300;
  const contentScriptRevision = "phase15b-main-world-checkpoint-v9";
  const spinnerSelector =
    '[aria-busy="true"], .loading, .spinner, .esg-spinner-container';
  let lastDiagnostics: CatalogPageReadyDiagnostics = {
    expectedSubject: input.expectedSubject,
    expectedPage: input.expectedPage,
    searchResultNavigationReceived: true,
    searchResultUrlMatch: false,
    searchResultDomReady: document.readyState !== "loading",
    visibleSubject: null,
    visibleSubjectSource: "UNAVAILABLE",
    pageNumber: null,
    pageNumberSource: "UNAVAILABLE",
    courseCardCount: 0,
    validCourseIdentityCount: 0,
    courseResultContainerPresent: false,
    resultContainerConnected: false,
    spinnerPresent: false,
    spinnerVisible: false,
    spinnerSelector,
    spinnerNodeCount: 0,
    spinnerComputedDisplay: null,
    spinnerComputedVisibility: null,
    spinnerComputedOpacity: null,
    spinnerClientRect: null,
    spinnerAriaHidden: null,
    spinnerBlocksResultInteraction: false,
    spinnerIsCatalogResultsSpinner: false,
    spinnerHardGateValid: false,
    spinnerClassification: "NON_BLOCKING",
    resultHeading: null,
    resultSummary: null,
    pageFingerprint: null,
    previousPageFingerprint: input.previousResultFingerprint ?? null,
    knockoutReady: false,
    domStable: false,
    domStableDurationMs: 0,
    contentStable: false,
    contentStabilityDurationMs: 0,
    contentScriptRevision,
    runnerRevision: input.runnerRevision,
    expectedRevision: input.navigationRevision,
    pageReadyGateFailedOn: "SEARCHRESULT_URL_MATCH",
    readyPredicatesPassing: [],
    failedPredicate: "SEARCHRESULT_URL_MISMATCH",
    currentPageTimeoutRootCause: null,
  };
  const finish = (signal: CatalogPageSignal): void => {
    if (finished) return;
    finished = true;
    observer?.disconnect();
    if (timeoutId !== null) window.clearTimeout(timeoutId);
    if (pollId !== null) window.clearInterval(pollId);
    runtime.sendMessage(signal, () => void runtime.lastError);
  };
  const unavailableCheckpoint = (
    signal: CatalogPageSignal["signal"],
    diagnostics: CatalogPageReadyDiagnostics = lastDiagnostics,
  ): CatalogPageSignal => ({
    type: "SAPSOS_CATALOG_PAGE_SIGNAL",
    batchId: input.batchId,
    signal,
    navigationRevision: input.navigationRevision,
    pageNumber: null,
    totalPages: null,
    visibleCourseCount: null,
    subjectCode: null,
    firstCourseMarker: null,
    lastCourseMarker: null,
    resultFingerprint: null,
    diagnostics,
    providerActionsWritten: "NO",
  });
  const inspect = (): boolean => {
    const actual = new URL(window.location.href);
    const expected = new URL(input.expectedUrl);
    actual.search = "";
    actual.hash = "";
    expected.search = "";
    expected.hash = "";
    if (
      actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
      actual.toString() !== expected.toString() ||
      ![
        "/Student/Courses/SearchResult",
        "/Student/Student/Courses/SearchResult",
      ].includes(actual.pathname)
    ) {
      lastDiagnostics = {
        ...lastDiagnostics,
        searchResultUrlMatch: false,
        pageReadyGateFailedOn: "SEARCHRESULT_URL_MATCH",
        failedPredicate: "SEARCHRESULT_URL_MISMATCH",
      };
      finish(unavailableCheckpoint("PROVENANCE_INVALID"));
      return true;
    }
    lastDiagnostics = {
      ...lastDiagnostics,
      searchResultUrlMatch: true,
      searchResultDomReady: document.readyState !== "loading",
      pageReadyGateFailedOn:
        document.readyState === "loading" ? "SEARCHRESULT_DOM_READY" : null,
      failedPredicate:
        document.readyState === "loading" ? "SEARCHRESULT_DOM_NOT_READY" : null,
    };
    const alertText = Array.from(
      document.querySelectorAll<HTMLElement>(
        '[role="alert"], .alert, .esg-alert, .eds-alert',
      ),
    )
      .map((element) => (element.innerText ?? "").replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join(" ")
      .slice(0, 4_000);
    const fatalSignal =
      /too many requests|rate limit|temporarily blocked|\b429\b/i.test(
        alertText,
      )
        ? "RATE_LIMIT"
        : /service unavailable|server error|unable to complete|something went wrong/i.test(
              alertText,
            )
          ? "PROVIDER_ERROR"
          : null;
    if (fatalSignal) {
      lastDiagnostics = {
        ...lastDiagnostics,
        pageReadyGateFailedOn: fatalSignal,
        failedPredicate: fatalSignal,
      };
      finish(unavailableCheckpoint(fatalSignal));
      return true;
    }
    if (
      document.querySelector(
        '[role="grid"][aria-label="Table for sections"], table[aria-label="Table for sections"]',
      )
    ) {
      lastDiagnostics = {
        ...lastDiagnostics,
        pageReadyGateFailedOn: "CATALOG_LISTING_VERIFIED",
        failedPredicate: "RESULT_VIEW_MISMATCH",
      };
      finish(unavailableCheckpoint("RESULT_VIEW_MISMATCH"));
      return true;
    }
    const isRendered = (element: HTMLElement): boolean => {
      const style = window.getComputedStyle(element);
      return (
        element.getClientRects().length > 0 &&
        !element.hidden &&
        element.closest("[hidden]") === null &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0"
      );
    };
    const resultListCandidates = Array.from(
      document.querySelectorAll<HTMLElement>("#course-resultul"),
    );
    const renderedResultLists = resultListCandidates.filter(isRendered);
    const resultList =
      renderedResultLists.length === 1
        ? (renderedResultLists[0] ?? null)
        : resultListCandidates.length === 1
          ? (resultListCandidates[0] ?? null)
          : null;
    const markers = Array.from(
      resultList?.querySelectorAll<HTMLElement>('span[id^="course-"]') ?? [],
    );
    const firstCourseMarker = markers[0]?.id ?? null;
    const lastCourseMarker = markers.at(-1)?.id ?? null;
    const resultFingerprint = markers
      .map((marker) => marker.id)
      .sort()
      .join("\u001f");
    const validCourseIdentities = new Set(
      markers
        .map((marker) => {
          const card = marker.closest<HTMLElement>("li, article, section");
          const identityTexts = [
            card?.querySelector("h3")?.textContent ?? "",
            marker.textContent ?? "",
            marker.id.replace(/^course-/i, "").replace(/-/g, " "),
          ];
          for (const text of identityTexts) {
            const match = text.match(/\b([A-Z]{2,6})[*\s-]?(\d{3,4}[A-Z]?)\b/i);
            if (match)
              return `${match[1]?.toUpperCase()} ${match[2]?.toUpperCase()}`;
          }
          return null;
        })
        .filter((identity): identity is string => identity !== null),
    );
    const validCourseIdentityCount = validCourseIdentities.size;
    const subjectCodes = new Set(
      markers
        .map((marker) =>
          marker.id.match(/^course-([A-Z0-9]{1,8})-/i)?.[1]?.toUpperCase(),
        )
        .filter((value): value is string => Boolean(value)),
    );
    const resultSurface =
      resultList?.closest<HTMLElement>("#course-results") ?? null;
    const paginationRoot: ParentNode = resultSurface ?? document;
    const currentInputCandidates = Array.from(
      paginationRoot.querySelectorAll<HTMLInputElement>(
        '#course-results-current-page, input[aria-label="Current Page Number"]',
      ),
    );
    const renderedCurrentInputs = currentInputCandidates.filter(isRendered);
    const currentInput =
      renderedCurrentInputs.length === 1
        ? renderedCurrentInputs[0]
        : currentInputCandidates.length === 1
          ? currentInputCandidates[0]
          : null;
    const pageNumber = Number(currentInput?.value ?? "");
    const pageTargets = Array.from(
      paginationRoot.querySelectorAll<HTMLButtonElement>(
        'button[aria-label^="Link to results page "]',
      ),
    )
      .map((button) =>
        Number(
          button
            .getAttribute("aria-label")
            ?.match(/^Link to results page (\d+)$/)?.[1],
        ),
      )
      .filter((value) => Number.isInteger(value) && value > 0);
    const firstPageFallback =
      input.expectedPage === 1 &&
      input.previousFirstCourseMarker === null &&
      !currentInput &&
      pageTargets.every((targetPage) => targetPage > 1) &&
      !paginationRoot.querySelector('[aria-current="page"]');
    const resolvedPageNumber = firstPageFallback ? 1 : pageNumber;
    const totalPages = Math.max(resolvedPageNumber, 1, ...pageTargets);
    const loadingCandidates = resultSurface
      ? Array.from(
          new Set<HTMLElement>([
            ...Array.from(
              resultSurface.querySelectorAll<HTMLElement>(spinnerSelector),
            ),
            ...(resultSurface.matches(spinnerSelector) ? [resultSurface] : []),
          ]),
        )
      : [];
    const visibleLoadingCandidates = loadingCandidates.filter(
      (element) =>
        isRendered(element) &&
        element.getAttribute("aria-hidden") !== "true" &&
        element.closest('[aria-hidden="true"]') === null,
    );
    const primarySpinner =
      visibleLoadingCandidates[0] ?? loadingCandidates[0] ?? null;
    const primarySpinnerStyle = primarySpinner
      ? window.getComputedStyle(primarySpinner)
      : null;
    const primarySpinnerRect = primarySpinner?.getBoundingClientRect() ?? null;
    const resultRect = resultList?.getBoundingClientRect() ?? null;
    const spinnerBlocksResultInteraction = visibleLoadingCandidates.some(
      (element) => {
        if (element.getAttribute("aria-busy") === "true") return true;
        if (!resultRect || resultRect.width <= 0 || resultRect.height <= 0)
          return false;
        const rect = element.getBoundingClientRect();
        const overlapWidth = Math.max(
          0,
          Math.min(rect.right, resultRect.right) -
            Math.max(rect.left, resultRect.left),
        );
        const overlapHeight = Math.max(
          0,
          Math.min(rect.bottom, resultRect.bottom) -
            Math.max(rect.top, resultRect.top),
        );
        const overlapRatio =
          (overlapWidth * overlapHeight) /
          (resultRect.width * resultRect.height);
        return (
          overlapRatio >= 0.5 &&
          window.getComputedStyle(element).pointerEvents !== "none"
        );
      },
    );
    const spinnerHardGateValid =
      resultSurface?.getAttribute("aria-busy") === "true" ||
      resultList?.getAttribute("aria-busy") === "true" ||
      visibleLoadingCandidates.some(
        (element) => element.getAttribute("aria-busy") === "true",
      );
    const spinnerClassification = spinnerHardGateValid
      ? ("BLOCKING" as const)
      : visibleLoadingCandidates.length > 0 && spinnerBlocksResultInteraction
        ? ("UNKNOWN" as const)
        : ("NON_BLOCKING" as const);
    const visibleSubject =
      subjectCodes.size === 1 ? (Array.from(subjectCodes)[0] ?? null) : null;
    const ko = (
      globalThis as typeof globalThis & {
        ko?: { contextFor?: (element: Element) => unknown };
      }
    ).ko;
    let knockoutReady = markers.length > 0;
    if (resultList?.hasAttribute("data-bind")) {
      try {
        knockoutReady =
          typeof ko?.contextFor === "function" &&
          ko.contextFor(resultList) != null;
      } catch {
        knockoutReady = false;
      }
    }
    const safeText = (element: Element | null): string | null => {
      const value = (element?.textContent ?? "").replace(/\s+/g, " ").trim();
      return value ? value.slice(0, 240) : null;
    };
    const checkpointSubjectValid = /^[A-Z0-9]{1,8}$/.test(
      input.expectedSubject,
    );
    const visibleSubjectSource = visibleSubject
      ? ("COURSE_CARD_ID" as const)
      : subjectCodes.size === 0 && checkpointSubjectValid
        ? ("CHECKPOINT_BOUND" as const)
        : ("UNAVAILABLE" as const);
    const resolvedSubject =
      visibleSubjectSource === "CHECKPOINT_BOUND"
        ? input.expectedSubject
        : visibleSubject;
    const pageNumberSource = currentInput
      ? "CURRENT_PAGE_INPUT"
      : firstPageFallback
        ? "FIRST_PAGE_STRUCTURE"
        : "UNAVAILABLE";
    const now = Date.now();
    const candidate = `${input.navigationRevision}:${resolvedPageNumber}:${totalPages}:${markers.length}:${validCourseIdentityCount}:${resultFingerprint}`;
    const contentCandidateValid =
      resultList !== null &&
      resultList.isConnected &&
      markers.length > 0 &&
      validCourseIdentityCount > 0 &&
      resultFingerprint.length > 0 &&
      Number.isInteger(resolvedPageNumber) &&
      resolvedPageNumber > 0 &&
      resolvedPageNumber <= totalPages;
    if (!contentCandidateValid) {
      candidateFingerprint = null;
      candidateResultList = null;
      candidateNavigationRevision = null;
      candidateSince = 0;
    } else if (
      candidate !== candidateFingerprint ||
      candidateResultList !== resultList ||
      candidateNavigationRevision !== input.navigationRevision
    ) {
      candidateFingerprint = candidate;
      candidateResultList = resultList;
      candidateNavigationRevision = input.navigationRevision;
      candidateSince = now;
    }
    const contentStabilityDurationMs =
      contentCandidateValid &&
      candidate === candidateFingerprint &&
      candidateResultList === resultList &&
      candidateNavigationRevision === input.navigationRevision &&
      resultList?.isConnected === true
        ? Math.max(0, now - candidateSince)
        : 0;
    const contentStable =
      contentCandidateValid &&
      candidate === candidateFingerprint &&
      candidateResultList === resultList &&
      candidateNavigationRevision === input.navigationRevision &&
      resultList?.isConnected === true &&
      contentStabilityDurationMs >= settleMs;
    const previousFingerprintChanged = !input.previousResultFingerprint
      ? true
      : resultFingerprint !== input.previousResultFingerprint;
    const readyPredicatesPassing = [
      ["SEARCHRESULT_URL", true],
      ["SEARCHRESULT_DOM_READY", document.readyState !== "loading"],
      [
        "EXPECTED_NAVIGATION_REVISION",
        candidateNavigationRevision === input.navigationRevision,
      ],
      ["RESULT_CONTAINER", resultList !== null],
      ["RESULT_CONTAINER_CONNECTED", resultList?.isConnected === true],
      ["COURSE_CARD_COUNT", markers.length > 0],
      ["VALID_COURSE_IDENTITY_COUNT", validCourseIdentityCount > 0],
      ["FINGERPRINT_NON_EMPTY", resultFingerprint.length > 0],
      ["SUBJECT_IDENTITY", subjectCodes.size <= 1 && resolvedSubject !== null],
      ["EXPECTED_PAGE", resolvedPageNumber === input.expectedPage],
      ["PREVIOUS_FINGERPRINT_CHANGED", previousFingerprintChanged],
      ["NO_BLOCKING_SPINNER", spinnerClassification !== "BLOCKING"],
      ["CONTENT_STABLE", contentStable],
      ["NO_BLOCKING_ERROR", true],
    ]
      .filter((entry) => entry[1] === true)
      .map((entry) => String(entry[0]));
    lastDiagnostics = {
      expectedSubject: input.expectedSubject,
      expectedPage: input.expectedPage,
      searchResultNavigationReceived: true,
      searchResultUrlMatch: true,
      searchResultDomReady: document.readyState !== "loading",
      visibleSubject,
      visibleSubjectSource,
      pageNumber:
        Number.isInteger(resolvedPageNumber) && resolvedPageNumber > 0
          ? resolvedPageNumber
          : null,
      pageNumberSource,
      courseCardCount: markers.length,
      validCourseIdentityCount,
      courseResultContainerPresent: resultList !== null,
      resultContainerConnected: resultList?.isConnected === true,
      spinnerPresent: loadingCandidates.length > 0,
      spinnerVisible: visibleLoadingCandidates.length > 0,
      spinnerSelector,
      spinnerNodeCount: loadingCandidates.length,
      spinnerComputedDisplay: primarySpinnerStyle?.display ?? null,
      spinnerComputedVisibility: primarySpinnerStyle?.visibility ?? null,
      spinnerComputedOpacity: primarySpinnerStyle?.opacity ?? null,
      spinnerClientRect: primarySpinnerRect
        ? [
            primarySpinnerRect.x,
            primarySpinnerRect.y,
            primarySpinnerRect.width,
            primarySpinnerRect.height,
          ]
            .map((value) => Math.round(value * 100) / 100)
            .join(",")
        : null,
      spinnerAriaHidden:
        primarySpinner?.getAttribute("aria-hidden") ??
        primarySpinner
          ?.closest<HTMLElement>("[aria-hidden]")
          ?.getAttribute("aria-hidden") ??
        null,
      spinnerBlocksResultInteraction,
      spinnerIsCatalogResultsSpinner:
        resultSurface !== null && loadingCandidates.length > 0,
      spinnerHardGateValid,
      spinnerClassification,
      resultHeading: safeText(
        document.querySelector("main h1, main h2, h1, h2"),
      ),
      resultSummary: safeText(
        document.querySelector(
          '#course-results [aria-live="polite"], #course-results .search-results-count, #course-results .pagination',
        ),
      ),
      pageFingerprint: resultFingerprint || null,
      previousPageFingerprint: input.previousResultFingerprint ?? null,
      knockoutReady,
      domStable: contentStable,
      domStableDurationMs: contentStabilityDurationMs,
      contentStable,
      contentStabilityDurationMs,
      contentScriptRevision,
      runnerRevision: input.runnerRevision,
      expectedRevision: input.navigationRevision,
      pageReadyGateFailedOn: null,
      readyPredicatesPassing,
      failedPredicate: null,
      currentPageTimeoutRootCause: null,
    };
    const waitOn = (gate: string, predicate: string): false => {
      lastDiagnostics = {
        ...lastDiagnostics,
        pageReadyGateFailedOn: gate,
        failedPredicate: predicate,
      };
      return false;
    };
    if (!lastDiagnostics.searchResultDomReady)
      return waitOn("SEARCHRESULT_DOM_READY", "SEARCHRESULT_DOM_NOT_READY");
    if (!resultList)
      return waitOn(
        "COURSE_RESULT_CONTAINER_PRESENT",
        "RESULT_CONTAINER_MISSING",
      );
    if (!firstCourseMarker || markers.length === 0)
      return waitOn("COURSE_CARD_COUNT", "COURSE_CARD_COUNT_ZERO");
    if (validCourseIdentityCount === 0)
      return waitOn(
        "VALID_COURSE_IDENTITY_COUNT",
        "VALID_COURSE_IDENTITY_COUNT_ZERO",
      );
    if (subjectCodes.size > 1 || !resolvedSubject)
      return waitOn("VISIBLE_SUBJECT", "SUBJECT_MISMATCH");
    if (visibleSubject && visibleSubject !== input.expectedSubject) {
      lastDiagnostics = {
        ...lastDiagnostics,
        pageReadyGateFailedOn: "EXPECTED_SUBJECT_MATCH",
        failedPredicate: "SUBJECT_MISMATCH",
      };
      finish(unavailableCheckpoint("SUBJECT_MISMATCH"));
      return true;
    }
    if (
      (!currentInput && !firstPageFallback) ||
      !Number.isInteger(resolvedPageNumber) ||
      resolvedPageNumber < 1 ||
      totalPages > 50 ||
      resolvedPageNumber > totalPages
    )
      return waitOn("PAGE_NUMBER_AVAILABLE", "PAGE_NUMBER_MISMATCH");
    if (resolvedPageNumber !== input.expectedPage)
      return waitOn("EXPECTED_PAGE_MATCH", "PAGE_NUMBER_MISMATCH");
    if (
      input.previousResultFingerprint &&
      resultFingerprint === input.previousResultFingerprint
    )
      return waitOn(
        "PAGE_FINGERPRINT_CHANGED",
        "PREVIOUS_PAGE_FINGERPRINT_UNCHANGED",
      );
    if (spinnerClassification === "BLOCKING")
      return waitOn("BLOCKING_SPINNER_HIDDEN", "BLOCKING_SPINNER");
    if (!contentStable)
      return waitOn("DOM_STABLE", "CONTENT_FINGERPRINT_UNSTABLE");
    lastDiagnostics = {
      ...lastDiagnostics,
      domStable: true,
      domStableDurationMs: contentStabilityDurationMs,
      contentStable: true,
      contentStabilityDurationMs,
      pageReadyGateFailedOn: null,
      failedPredicate: null,
    };
    finish({
      type: "SAPSOS_CATALOG_PAGE_SIGNAL",
      batchId: input.batchId,
      signal: "READY",
      navigationRevision: input.navigationRevision,
      pageNumber: resolvedPageNumber,
      totalPages,
      visibleCourseCount: markers.length,
      subjectCode: resolvedSubject,
      firstCourseMarker,
      lastCourseMarker,
      resultFingerprint,
      diagnostics: lastDiagnostics,
      providerActionsWritten: "NO",
    });
    return true;
  };
  observer = new MutationObserver(() => {
    inspect();
  });
  observer.observe(document.documentElement, {
    attributes: true,
    childList: true,
    subtree: true,
  });
  pollId = window.setInterval(
    () => {
      inspect();
    },
    Math.min(50, settleMs),
  );
  timeoutId = window.setTimeout(() => {
    const timeoutSignal =
      lastDiagnostics.pageReadyGateFailedOn === "EXPECTED_PAGE_MATCH"
        ? "PAGE_NUMBER_MISMATCH"
        : "TIMEOUT";
    lastDiagnostics = {
      ...lastDiagnostics,
      currentPageTimeoutRootCause:
        lastDiagnostics.failedPredicate ?? "UNKNOWN_PAGE_READY_GATE",
    };
    const timeoutCheckpoint = unavailableCheckpoint(timeoutSignal);
    finish(
      timeoutSignal === "PAGE_NUMBER_MISMATCH"
        ? {
            ...timeoutCheckpoint,
            pageNumber: lastDiagnostics.pageNumber,
          }
        : timeoutCheckpoint,
    );
  }, input.timeoutMs);
  inspect();
  return {
    action: "CATALOG_RESULT_WATCH_STARTED",
    providerActionsWritten: "NO",
  };
}

export function advanceCatalogResultPage(input: {
  expectedUrl: string;
  targetPage: number;
  batchId?: string;
  expectedSubject?: string;
  navigationRevision?: number;
  runnerRevision?: string;
  timeoutMs?: number;
  settleMs?: number;
}): CatalogPaginationAction {
  const actual = new URL(window.location.href);
  const expected = new URL(input.expectedUrl);
  const allowedPaths = new Set([
    "/Student/Courses/SearchResult",
    "/Student/Student/Courses/SearchResult",
  ]);
  actual.search = "";
  actual.hash = "";
  expected.search = "";
  expected.hash = "";
  if (
    actual.origin !== "https://kean-ss.colleague.elluciancloud.com" ||
    actual.toString() !== expected.toString() ||
    !allowedPaths.has(actual.pathname) ||
    !Number.isInteger(input.targetPage) ||
    input.targetPage < 2 ||
    input.targetPage > 50
  ) {
    throw new Error(
      "BATCH_CATALOG_PROVENANCE_INVALID: Pagination target was not a reviewed Kean Catalog result page.",
    );
  }
  const isRendered = (element: HTMLElement): boolean => {
    const style = window.getComputedStyle(element);
    return (
      element.getClientRects().length > 0 &&
      !element.hidden &&
      element.closest("[hidden]") === null &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );
  };
  const activeResultList = (): HTMLElement | null => {
    const candidates = Array.from(
      document.querySelectorAll<HTMLElement>("#course-resultul"),
    ).filter(
      (candidate) =>
        candidate.querySelectorAll<HTMLElement>('span[id^="course-"]').length >
        0,
    );
    const rendered = candidates.filter(isRendered);
    return rendered.length === 1
      ? (rendered[0] ?? null)
      : candidates.length === 1
        ? (candidates[0] ?? null)
        : null;
  };
  const previousResultList = activeResultList();
  const previousMarkers = Array.from(
    previousResultList?.querySelectorAll<HTMLElement>('span[id^="course-"]') ??
      [],
  );
  const previousFirstCourseMarker = previousMarkers[0]?.id ?? "";
  const previousResultFingerprint = previousMarkers
    .map((marker) => marker.id)
    .sort()
    .join("\u001f");
  const previousResultSurface =
    previousResultList?.closest<HTMLElement>("#course-results") ?? null;
  const previousPaginationRoot: ParentNode = previousResultSurface ?? document;
  const target = Array.from(
    previousPaginationRoot.querySelectorAll<HTMLButtonElement>(
      'button[aria-label^="Link to results page "]',
    ),
  ).find(
    (button) =>
      isRendered(button) &&
      button.getAttribute("aria-label") ===
        `Link to results page ${input.targetPage}`,
  );
  if (!previousFirstCourseMarker || !target || target.disabled) {
    throw new Error(
      "BATCH_CATALOG_PARSER_DRIFT: The explicit next-page control was unavailable.",
    );
  }
  const runtime = (
    globalThis as typeof globalThis & {
      chrome?: { runtime?: CatalogPageSignalRuntime };
    }
  ).chrome?.runtime;
  if (input.batchId && input.timeoutMs && runtime) {
    let finished = false;
    let observer: MutationObserver | null = null;
    let timeoutId: number | null = null;
    let pollId: number | null = null;
    let candidateFingerprint: string | null = null;
    let candidateResultList: HTMLElement | null = null;
    let candidateNavigationRevision: number | null = null;
    let candidateSince = 0;
    const settleMs =
      Number.isFinite(input.settleMs) &&
      Number(input.settleMs) >= 50 &&
      Number(input.settleMs) <= 2_000
        ? Number(input.settleMs)
        : 300;
    const contentScriptRevision = "phase15b-main-world-checkpoint-v9";
    const spinnerSelector =
      '[aria-busy="true"], .loading, .spinner, .esg-spinner-container';
    let lastDiagnostics: CatalogPageReadyDiagnostics = {
      expectedSubject: input.expectedSubject ?? "UNKNOWN",
      expectedPage: input.targetPage,
      searchResultNavigationReceived: true,
      searchResultUrlMatch: true,
      searchResultDomReady: document.readyState !== "loading",
      visibleSubject: null,
      visibleSubjectSource: "UNAVAILABLE",
      pageNumber: null,
      pageNumberSource: "UNAVAILABLE",
      courseCardCount: 0,
      validCourseIdentityCount: 0,
      courseResultContainerPresent:
        document.querySelector("#course-resultul") !== null,
      resultContainerConnected:
        document.querySelector("#course-resultul")?.isConnected === true,
      spinnerPresent: false,
      spinnerVisible: false,
      spinnerSelector,
      spinnerNodeCount: 0,
      spinnerComputedDisplay: null,
      spinnerComputedVisibility: null,
      spinnerComputedOpacity: null,
      spinnerClientRect: null,
      spinnerAriaHidden: null,
      spinnerBlocksResultInteraction: false,
      spinnerIsCatalogResultsSpinner: false,
      spinnerHardGateValid: false,
      spinnerClassification: "NON_BLOCKING",
      resultHeading: null,
      resultSummary: null,
      pageFingerprint: null,
      previousPageFingerprint: previousResultFingerprint || null,
      knockoutReady: false,
      domStable: false,
      domStableDurationMs: 0,
      contentStable: false,
      contentStabilityDurationMs: 0,
      contentScriptRevision,
      runnerRevision: input.runnerRevision ?? contentScriptRevision,
      expectedRevision: input.navigationRevision ?? 0,
      pageReadyGateFailedOn: "PAGE_FINGERPRINT_CHANGED",
      readyPredicatesPassing: [],
      failedPredicate: "PREVIOUS_PAGE_FINGERPRINT_UNCHANGED",
      currentPageTimeoutRootCause: null,
    };
    const finish = (signal: CatalogPageSignal): void => {
      if (finished) return;
      finished = true;
      observer?.disconnect();
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      if (pollId !== null) window.clearInterval(pollId);
      runtime.sendMessage(signal, () => void runtime.lastError);
    };
    const unavailableCheckpoint = (
      signal: CatalogPageSignal["signal"],
    ): CatalogPageSignal => ({
      type: "SAPSOS_CATALOG_PAGE_SIGNAL",
      batchId: input.batchId ?? "",
      signal,
      navigationRevision: input.navigationRevision ?? 0,
      pageNumber: null,
      totalPages: null,
      visibleCourseCount: null,
      subjectCode: null,
      firstCourseMarker: null,
      lastCourseMarker: null,
      resultFingerprint: null,
      diagnostics: lastDiagnostics,
      providerActionsWritten: "NO",
    });
    const inspect = (): void => {
      const alertText = Array.from(
        document.querySelectorAll<HTMLElement>(
          '[role="alert"], .alert, .esg-alert, .eds-alert',
        ),
      )
        .map((element) => (element.innerText ?? "").replace(/\s+/g, " ").trim())
        .filter(Boolean)
        .join(" ")
        .slice(0, 4_000);
      const fatalSignal =
        /too many requests|rate limit|temporarily blocked|\b429\b/i.test(
          alertText,
        )
          ? "RATE_LIMIT"
          : /service unavailable|server error|unable to complete|something went wrong/i.test(
                alertText,
              )
            ? "PROVIDER_ERROR"
            : null;
      if (fatalSignal) {
        lastDiagnostics = {
          ...lastDiagnostics,
          pageReadyGateFailedOn: fatalSignal,
          failedPredicate: fatalSignal,
        };
        finish(unavailableCheckpoint(fatalSignal));
        return;
      }
      if (
        document.querySelector(
          '[role="grid"][aria-label="Table for sections"], table[aria-label="Table for sections"]',
        )
      ) {
        lastDiagnostics = {
          ...lastDiagnostics,
          pageReadyGateFailedOn: "CATALOG_LISTING_VERIFIED",
          failedPredicate: "RESULT_VIEW_MISMATCH",
        };
        finish(unavailableCheckpoint("RESULT_VIEW_MISMATCH"));
        return;
      }

      const resultListCandidates = Array.from(
        document.querySelectorAll<HTMLElement>("#course-resultul"),
      );
      const renderedResultLists = resultListCandidates.filter(isRendered);
      const resultList =
        renderedResultLists.length === 1
          ? (renderedResultLists[0] ?? null)
          : resultListCandidates.length === 1
            ? (resultListCandidates[0] ?? null)
            : null;
      const markers = Array.from(
        resultList?.querySelectorAll<HTMLElement>('span[id^="course-"]') ?? [],
      );
      const firstCourseMarker = markers[0]?.id ?? null;
      const lastCourseMarker = markers.at(-1)?.id ?? null;
      const resultFingerprint = markers
        .map((marker) => marker.id)
        .sort()
        .join("\u001f");
      const validCourseIdentities = new Set(
        markers
          .map((marker) => {
            const card = marker.closest<HTMLElement>("li, article, section");
            const identityTexts = [
              card?.querySelector("h3")?.textContent ?? "",
              marker.textContent ?? "",
              marker.id.replace(/^course-/i, "").replace(/-/g, " "),
            ];
            for (const text of identityTexts) {
              const match = text.match(
                /\b([A-Z]{2,6})[*\s-]?(\d{3,4}[A-Z]?)\b/i,
              );
              if (match)
                return `${match[1]?.toUpperCase()} ${match[2]?.toUpperCase()}`;
            }
            return null;
          })
          .filter((identity): identity is string => identity !== null),
      );
      const validCourseIdentityCount = validCourseIdentities.size;
      const subjectCodes = new Set(
        markers
          .map((marker) =>
            marker.id.match(/^course-([A-Z0-9]{1,8})-/i)?.[1]?.toUpperCase(),
          )
          .filter((value): value is string => Boolean(value)),
      );
      const resultSurface =
        resultList?.closest<HTMLElement>("#course-results") ?? null;
      const paginationRoot: ParentNode = resultSurface ?? document;
      const currentInputCandidates = Array.from(
        paginationRoot.querySelectorAll<HTMLInputElement>(
          '#course-results-current-page, input[aria-label="Current Page Number"]',
        ),
      );
      const renderedCurrentInputs = currentInputCandidates.filter(isRendered);
      const currentInput =
        renderedCurrentInputs.length === 1
          ? renderedCurrentInputs[0]
          : currentInputCandidates.length === 1
            ? currentInputCandidates[0]
            : null;
      const pageNumber = Number(currentInput?.value ?? "");
      const pageTargets = Array.from(
        paginationRoot.querySelectorAll<HTMLButtonElement>(
          'button[aria-label^="Link to results page "]',
        ),
      )
        .map((button) =>
          Number(
            button
              .getAttribute("aria-label")
              ?.match(/^Link to results page (\d+)$/)?.[1],
          ),
        )
        .filter((value) => Number.isInteger(value) && value > 0);
      const totalPages = Math.max(
        Number.isInteger(pageNumber) ? pageNumber : 1,
        1,
        ...pageTargets,
      );

      const loadingCandidates = resultSurface
        ? Array.from(
            new Set<HTMLElement>([
              ...Array.from(
                resultSurface.querySelectorAll<HTMLElement>(spinnerSelector),
              ),
              ...(resultSurface.matches(spinnerSelector)
                ? [resultSurface]
                : []),
            ]),
          )
        : [];
      const visibleLoadingCandidates = loadingCandidates.filter(
        (element) =>
          isRendered(element) &&
          element.getAttribute("aria-hidden") !== "true" &&
          element.closest('[aria-hidden="true"]') === null,
      );
      const primarySpinner =
        visibleLoadingCandidates[0] ?? loadingCandidates[0] ?? null;
      const primarySpinnerStyle = primarySpinner
        ? window.getComputedStyle(primarySpinner)
        : null;
      const primarySpinnerRect =
        primarySpinner?.getBoundingClientRect() ?? null;
      const resultRect = resultList?.getBoundingClientRect() ?? null;
      const spinnerBlocksResultInteraction = visibleLoadingCandidates.some(
        (element) => {
          if (element.getAttribute("aria-busy") === "true") return true;
          if (!resultRect || resultRect.width <= 0 || resultRect.height <= 0)
            return false;
          const rect = element.getBoundingClientRect();
          const overlapWidth = Math.max(
            0,
            Math.min(rect.right, resultRect.right) -
              Math.max(rect.left, resultRect.left),
          );
          const overlapHeight = Math.max(
            0,
            Math.min(rect.bottom, resultRect.bottom) -
              Math.max(rect.top, resultRect.top),
          );
          const overlapRatio =
            (overlapWidth * overlapHeight) /
            (resultRect.width * resultRect.height);
          return (
            overlapRatio >= 0.5 &&
            window.getComputedStyle(element).pointerEvents !== "none"
          );
        },
      );
      const spinnerHardGateValid =
        resultSurface?.getAttribute("aria-busy") === "true" ||
        resultList?.getAttribute("aria-busy") === "true" ||
        visibleLoadingCandidates.some(
          (element) => element.getAttribute("aria-busy") === "true",
        );
      const spinnerClassification = spinnerHardGateValid
        ? ("BLOCKING" as const)
        : visibleLoadingCandidates.length > 0 && spinnerBlocksResultInteraction
          ? ("UNKNOWN" as const)
          : ("NON_BLOCKING" as const);

      const visibleSubject =
        subjectCodes.size === 1 ? (Array.from(subjectCodes)[0] ?? null) : null;
      const expectedSubject = input.expectedSubject?.toUpperCase() ?? null;
      const checkpointSubjectValid =
        expectedSubject !== null && /^[A-Z0-9]{1,8}$/.test(expectedSubject);
      const visibleSubjectSource = visibleSubject
        ? ("COURSE_CARD_ID" as const)
        : subjectCodes.size === 0 && checkpointSubjectValid
          ? ("CHECKPOINT_BOUND" as const)
          : ("UNAVAILABLE" as const);
      const resolvedSubject =
        visibleSubjectSource === "CHECKPOINT_BOUND"
          ? expectedSubject
          : visibleSubject;
      const ko = (
        globalThis as typeof globalThis & {
          ko?: { contextFor?: (element: Element) => unknown };
        }
      ).ko;
      let knockoutReady = markers.length > 0;
      if (resultList?.hasAttribute("data-bind")) {
        try {
          knockoutReady =
            typeof ko?.contextFor === "function" &&
            ko.contextFor(resultList) != null;
        } catch {
          knockoutReady = false;
        }
      }

      const navigationRevision = input.navigationRevision ?? 0;
      const candidate = `${navigationRevision}:${pageNumber}:${totalPages}:${markers.length}:${validCourseIdentityCount}:${resultFingerprint}`;
      const now = Date.now();
      const contentCandidateValid =
        resultList !== null &&
        resultList.isConnected &&
        markers.length > 0 &&
        validCourseIdentityCount > 0 &&
        resultFingerprint.length > 0 &&
        Number.isInteger(pageNumber) &&
        pageNumber > 0 &&
        pageNumber <= totalPages;
      if (!contentCandidateValid) {
        candidateFingerprint = null;
        candidateResultList = null;
        candidateNavigationRevision = null;
        candidateSince = 0;
      } else if (
        candidate !== candidateFingerprint ||
        candidateResultList !== resultList ||
        candidateNavigationRevision !== navigationRevision
      ) {
        candidateFingerprint = candidate;
        candidateResultList = resultList;
        candidateNavigationRevision = navigationRevision;
        candidateSince = now;
      }
      const contentStabilityDurationMs =
        contentCandidateValid &&
        candidate === candidateFingerprint &&
        candidateResultList === resultList &&
        candidateNavigationRevision === navigationRevision &&
        resultList?.isConnected === true
          ? Math.max(0, now - candidateSince)
          : 0;
      const contentStable =
        contentCandidateValid &&
        candidate === candidateFingerprint &&
        candidateResultList === resultList &&
        candidateNavigationRevision === navigationRevision &&
        resultList?.isConnected === true &&
        contentStabilityDurationMs >= settleMs;
      const previousFingerprintChanged =
        resultFingerprint !== previousResultFingerprint;
      const readyPredicatesPassing = [
        ["SEARCHRESULT_URL", true],
        ["SEARCHRESULT_DOM_READY", document.readyState !== "loading"],
        [
          "EXPECTED_NAVIGATION_REVISION",
          candidateNavigationRevision === navigationRevision,
        ],
        ["RESULT_CONTAINER", resultList !== null],
        ["RESULT_CONTAINER_CONNECTED", resultList?.isConnected === true],
        ["COURSE_CARD_COUNT", markers.length > 0],
        ["VALID_COURSE_IDENTITY_COUNT", validCourseIdentityCount > 0],
        ["FINGERPRINT_NON_EMPTY", resultFingerprint.length > 0],
        [
          "SUBJECT_IDENTITY",
          subjectCodes.size <= 1 && resolvedSubject !== null,
        ],
        ["EXPECTED_PAGE", pageNumber === input.targetPage],
        ["PREVIOUS_FINGERPRINT_CHANGED", previousFingerprintChanged],
        ["NO_BLOCKING_SPINNER", spinnerClassification !== "BLOCKING"],
        ["CONTENT_STABLE", contentStable],
        ["NO_BLOCKING_ERROR", true],
      ]
        .filter((entry) => entry[1] === true)
        .map((entry) => String(entry[0]));

      lastDiagnostics = {
        ...lastDiagnostics,
        searchResultDomReady: document.readyState !== "loading",
        visibleSubject,
        visibleSubjectSource,
        pageNumber:
          Number.isInteger(pageNumber) && pageNumber > 0 ? pageNumber : null,
        pageNumberSource: currentInput ? "CURRENT_PAGE_INPUT" : "UNAVAILABLE",
        courseCardCount: markers.length,
        validCourseIdentityCount,
        courseResultContainerPresent: resultList !== null,
        resultContainerConnected: resultList?.isConnected === true,
        spinnerPresent: loadingCandidates.length > 0,
        spinnerVisible: visibleLoadingCandidates.length > 0,
        spinnerSelector,
        spinnerNodeCount: loadingCandidates.length,
        spinnerComputedDisplay: primarySpinnerStyle?.display ?? null,
        spinnerComputedVisibility: primarySpinnerStyle?.visibility ?? null,
        spinnerComputedOpacity: primarySpinnerStyle?.opacity ?? null,
        spinnerClientRect: primarySpinnerRect
          ? [
              primarySpinnerRect.x,
              primarySpinnerRect.y,
              primarySpinnerRect.width,
              primarySpinnerRect.height,
            ]
              .map((value) => Math.round(value * 100) / 100)
              .join(",")
          : null,
        spinnerAriaHidden:
          primarySpinner?.getAttribute("aria-hidden") ??
          primarySpinner
            ?.closest<HTMLElement>("[aria-hidden]")
            ?.getAttribute("aria-hidden") ??
          null,
        spinnerBlocksResultInteraction,
        spinnerIsCatalogResultsSpinner:
          resultSurface !== null && loadingCandidates.length > 0,
        spinnerHardGateValid,
        spinnerClassification,
        pageFingerprint: resultFingerprint || null,
        knockoutReady,
        domStable: contentStable,
        domStableDurationMs: contentStabilityDurationMs,
        contentStable,
        contentStabilityDurationMs,
        pageReadyGateFailedOn: null,
        readyPredicatesPassing,
        failedPredicate: null,
      };
      const waitOn = (gate: string, predicate: string): void => {
        lastDiagnostics = {
          ...lastDiagnostics,
          pageReadyGateFailedOn: gate,
          failedPredicate: predicate,
        };
      };
      if (!lastDiagnostics.searchResultDomReady)
        return waitOn("SEARCHRESULT_DOM_READY", "SEARCHRESULT_DOM_NOT_READY");
      if (!resultList)
        return waitOn(
          "COURSE_RESULT_CONTAINER_PRESENT",
          "RESULT_CONTAINER_MISSING",
        );
      if (!firstCourseMarker || markers.length === 0 || !resultFingerprint)
        return waitOn("COURSE_CARD_COUNT", "COURSE_CARD_COUNT_ZERO");
      if (validCourseIdentityCount === 0)
        return waitOn(
          "VALID_COURSE_IDENTITY_COUNT",
          "VALID_COURSE_IDENTITY_COUNT_ZERO",
        );
      if (resultFingerprint === previousResultFingerprint)
        return waitOn(
          "PAGE_FINGERPRINT_CHANGED",
          "PREVIOUS_PAGE_FINGERPRINT_UNCHANGED",
        );
      if (subjectCodes.size > 1 || !resolvedSubject)
        return waitOn("VISIBLE_SUBJECT", "SUBJECT_MISMATCH");
      if (
        visibleSubject &&
        expectedSubject &&
        visibleSubject !== expectedSubject
      ) {
        lastDiagnostics = {
          ...lastDiagnostics,
          pageReadyGateFailedOn: "EXPECTED_SUBJECT_MATCH",
          failedPredicate: "SUBJECT_MISMATCH",
        };
        finish(unavailableCheckpoint("SUBJECT_MISMATCH"));
        return;
      }
      if (
        !currentInput ||
        !Number.isInteger(pageNumber) ||
        pageNumber < 1 ||
        totalPages > 50 ||
        pageNumber > totalPages
      )
        return waitOn("PAGE_NUMBER_AVAILABLE", "PAGE_NUMBER_MISMATCH");
      if (pageNumber !== input.targetPage)
        return waitOn("EXPECTED_PAGE_MATCH", "PAGE_NUMBER_MISMATCH");
      if (spinnerClassification === "BLOCKING")
        return waitOn("BLOCKING_SPINNER_HIDDEN", "BLOCKING_SPINNER");
      if (!contentStable)
        return waitOn("DOM_STABLE", "CONTENT_FINGERPRINT_UNSTABLE");

      lastDiagnostics = {
        ...lastDiagnostics,
        pageReadyGateFailedOn: null,
        failedPredicate: null,
      };
      finish({
        type: "SAPSOS_CATALOG_PAGE_SIGNAL",
        batchId: input.batchId ?? "",
        signal: "READY",
        navigationRevision: input.navigationRevision ?? 0,
        pageNumber,
        totalPages,
        visibleCourseCount: markers.length,
        subjectCode: resolvedSubject,
        firstCourseMarker,
        lastCourseMarker,
        resultFingerprint,
        diagnostics: lastDiagnostics,
        providerActionsWritten: "NO",
      });
    };
    observer = new MutationObserver(() => {
      inspect();
    });
    observer.observe(document.documentElement, {
      attributes: true,
      childList: true,
      subtree: true,
    });
    pollId = window.setInterval(
      () => {
        inspect();
      },
      Math.min(50, settleMs),
    );
    timeoutId = window.setTimeout(() => {
      lastDiagnostics = {
        ...lastDiagnostics,
        currentPageTimeoutRootCause:
          lastDiagnostics.failedPredicate ?? "UNKNOWN_PAGE_READY_GATE",
      };
      finish(unavailableCheckpoint("TIMEOUT"));
    }, input.timeoutMs);
  }
  target.focus();
  target.click();
  return {
    action: "CATALOG_PAGE_REQUESTED",
    targetPage: input.targetPage,
    previousFirstCourseMarker,
    previousResultFingerprint,
    providerActionsWritten: "NO",
  };
}
