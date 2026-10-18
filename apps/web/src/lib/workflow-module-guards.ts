export type WorkflowRequestGuard = {
  begin: () => number;
  isCurrent: (requestId: number) => boolean;
};

export function createWorkflowRequestGuard(): WorkflowRequestGuard {
  let currentRequestId = 0;
  return {
    begin: () => {
      currentRequestId += 1;
      return currentRequestId;
    },
    isCurrent: (requestId) => requestId === currentRequestId,
  };
}

export function createMutationReplayGuard(): () => boolean {
  let running = false;
  return () => {
    if (running) {
      return false;
    }
    running = true;
    return true;
  };
}
