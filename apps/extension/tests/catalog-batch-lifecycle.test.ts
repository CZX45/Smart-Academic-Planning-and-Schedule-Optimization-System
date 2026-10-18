import { describe, expect, it } from "vitest";

import {
  createCatalogBatchState,
  restoreCatalogBatchState,
} from "../src/content/catalog-batch.js";
import {
  catalogBatchPublicState,
  pauseCatalogBatchForReason,
  recordCatalogBatchTransition,
} from "../src/content/catalog-batch-lifecycle.js";

const startedAt = "2026-08-27T09:00:00.000Z";

function state() {
  return createCatalogBatchState({
    apiBaseUrl: "http://127.0.0.1:8000",
    studentProfileId: "00000000-0000-4000-8000-000000000702",
    tabId: 41,
    landingUrl:
      "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses",
    subjects: [
      { code: "ACCT", label: "Accounting" },
      { code: "ANTH", label: "Anthropology" },
      { code: "ART", label: "Art" },
    ],
    startedAt,
    mode: "BOUNDED_ACCEPTANCE",
    subjectLimit: 2,
    extensionVersion: "0.1.7",
  } as Parameters<typeof createCatalogBatchState>[0] & {
    extensionVersion: string;
  });
}

describe("Catalog batch lifecycle checkpoints", () => {
  it("persists the exact current page and last transition for monitor reconnect", () => {
    const transitioned = recordCatalogBatchTransition(
      state(),
      "PAGE_NAVIGATION_REQUESTED",
      "2026-08-27T09:00:05.000Z",
      { currentPage: 2, stateMachineCheckpoint: "NEXT_PAGE" },
    );

    expect(
      catalogBatchPublicState(transitioned, "2026-08-27T09:01:05.000Z"),
    ).toMatchObject({
      batchStatus: "RUNNING",
      batchRunId: transitioned.batchId,
      runnerRevision: "phase15b-main-world-checkpoint-v9",
      acceptanceRevision: "phase15b-main-world-checkpoint-v9",
      extensionVersion: "0.1.7",
      createdAt: startedAt,
      processingStage: "CAPTURE_RUNNING",
      currentSchoolTabUrlClassification: "CATALOG_LANDING",
      currentSubjectIndex: 0,
      currentSubject: "ACCT",
      currentPage: 2,
      boundedAcceptancePassed: false,
      boundedAcceptanceRevision: null,
      discoveredSubjectCount: 3,
      completedSubjectCount: 0,
      capturedRecordCount: 0,
      uniqueRecordCount: 0,
      warningCount: 0,
      lastWarning: null,
      lastError: null,
      lastTransition: "PAGE_NAVIGATION_REQUESTED",
      stateMachineCheckpoint: "NEXT_PAGE",
      lastTransitionAt: "2026-08-27T09:00:05.000Z",
      elapsedSeconds: 65,
      estimatedRemainingSeconds: null,
      authorizedTabId: 41,
      providerActionsWritten: "NO",
    });
  });

  it("pauses fail-closed when the authorized tab closes", () => {
    const paused = pauseCatalogBatchForReason(
      state(),
      "AUTHORIZED_CATALOG_TAB_CLOSED",
      "2026-08-27T09:00:08.000Z",
      "The authorized Catalog tab closed.",
      "BATCH_CATALOG_TAB_CLOSED",
    );

    expect(paused).toMatchObject({
      status: "PAUSED",
      pauseReason: "AUTHORIZED_CATALOG_TAB_CLOSED",
      lastErrorCode: "BATCH_CATALOG_TAB_CLOSED",
      lastErrorContext: {
        phase: "SUBJECTS_DISCOVERED",
        subject: "ACCT",
        page: 1,
        urlClassification: "CATALOG_LANDING",
        revision: 0,
        timestamp: "2026-08-27T09:00:08.000Z",
        diagnostics: null,
      },
      lastTransition: "PAUSED",
      stateMachineCheckpoint: "PAUSED",
      lastTransitionAt: "2026-08-27T09:00:08.000Z",
      providerActionsWritten: "NO",
    });
    expect(
      catalogBatchPublicState(paused, "2026-08-27T09:00:09.000Z").lastError,
    ).toMatchObject({
      code: "BATCH_CATALOG_TAB_CLOSED",
      context: { phase: "SUBJECTS_DISCOVERED", revision: 0 },
    });
  });

  it("restores an interrupted worker as paused with every checkpoint retained", () => {
    const running = recordCatalogBatchTransition(
      state(),
      "WAITING_FOR_RESULT_PAGE",
      "2026-08-27T09:00:06.000Z",
      { currentPage: 1 },
    );

    const restored = restoreCatalogBatchState(
      structuredClone(running),
      "2026-08-27T09:00:10.000Z",
    );

    expect(restored).toMatchObject({
      status: "PAUSED",
      currentPage: 1,
      lastTransition: "PAUSED",
      lastTransitionAt: "2026-08-27T09:00:10.000Z",
      pauseReason: "WORKER_RESTART_RECOVERY_REQUIRED",
      lastErrorCode: "BATCH_CATALOG_WORKER_RESTART",
    });
  });

  it("keeps full-catalog execution locked until bounded acceptance completes", () => {
    const initial = state();

    expect(initial.mode).toBe("BOUNDED_ACCEPTANCE");
    expect(initial.subjectLimit).toBe(2);
    expect(initial.boundedAcceptancePassed).toBe(false);
    expect(initial.boundedAcceptanceRevision).toBeNull();
  });

  it("invalidates an unversioned legacy bounded-acceptance flag on restore", () => {
    const legacy = {
      ...state(),
      status: "COMPLETED" as const,
      boundedAcceptancePassed: true,
    };
    Reflect.deleteProperty(legacy, "boundedAcceptanceRevision");

    const restored = restoreCatalogBatchState(
      legacy,
      "2026-08-27T09:00:10.000Z",
    );

    expect(restored.boundedAcceptancePassed).toBe(false);
    expect(restored.boundedAcceptanceRevision).toBeNull();
  });

  it("marks a stored run without a runner revision as legacy evidence", () => {
    const legacy = structuredClone(state()) as ReturnType<typeof state> & {
      runnerRevision?: string;
    };
    Reflect.deleteProperty(legacy, "runnerRevision");

    const restored = restoreCatalogBatchState(
      legacy,
      "2026-08-27T09:00:10.000Z",
    ) as ReturnType<typeof state> & { runnerRevision?: string };

    expect(restored.runnerRevision).toBe("LEGACY_UNVERSIONED");
  });
});
