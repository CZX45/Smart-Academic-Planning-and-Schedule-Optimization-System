export type WhatIfScenarioIdentity = {
  scenarioId: string;
  studentId: string;
};

export function hypotheticalScenarioKey(identity: WhatIfScenarioIdentity): string {
  return `WHAT_IF:${identity.studentId}:${identity.scenarioId}`;
}

export function isHypotheticalOnly(mode: string): boolean {
  return mode === "WHAT_IF" || mode === "SCENARIO";
}
