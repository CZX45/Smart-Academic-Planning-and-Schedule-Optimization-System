export type AcademicPlanDraftState = {
  savedPlanId: string | null;
  draftFingerprint: string;
  savedFingerprint: string | null;
};

export function hasUnsavedPlanChanges(state: AcademicPlanDraftState): boolean {
  return state.savedFingerprint !== state.draftFingerprint;
}

export function planRouteEntryIsReadOnly(): true {
  return true;
}
