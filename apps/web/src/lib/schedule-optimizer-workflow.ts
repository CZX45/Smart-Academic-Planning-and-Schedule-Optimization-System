import { createMutationReplayGuard } from "./workflow-module-guards";

export type OptimizerRunIdentity = {
  studentId: string;
  termId: string;
  inputSnapshotHash: string;
};

export function optimizerRunKey(identity: OptimizerRunIdentity): string {
  return `${identity.studentId}:${identity.termId}:${identity.inputSnapshotHash}`;
}

export function createOptimizerRunGuard(): ReturnType<typeof createMutationReplayGuard> {
  return createMutationReplayGuard();
}
