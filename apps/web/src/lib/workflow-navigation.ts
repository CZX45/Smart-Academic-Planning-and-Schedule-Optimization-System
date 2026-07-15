export type WorkflowId =
  | "overview"
  | "data-import"
  | "review-apply"
  | "degree-audit"
  | "eligibility"
  | "academic-plan"
  | "what-if"
  | "sections"
  | "schedule-builder"
  | "section-monitoring";

export type WorkflowDefinition = {
  id: WorkflowId;
  label: string;
  anchor: string;
};

/**
 * The workflow list is deliberately limited to currently implemented product
 * surfaces. Hash navigation keeps the exported Web UI usable from static
 * files and Tauri WebViews without a server-side route or rewrite.
 */
export const workflowDefinitions: readonly WorkflowDefinition[] = [
  { id: "overview", label: "概览", anchor: "overview" },
  { id: "data-import", label: "数据导入", anchor: "data-import-preview" },
  { id: "review-apply", label: "审核与应用", anchor: "data-review" },
  { id: "degree-audit", label: "学业审核", anchor: "degree-audit" },
  { id: "eligibility", label: "课程资格", anchor: "eligibility" },
  { id: "academic-plan", label: "长期规划", anchor: "academic-plan" },
  { id: "what-if", label: "假设规划", anchor: "what-if-planning" },
  { id: "sections", label: "课节", anchor: "sections" },
  {
    id: "schedule-builder",
    label: "学期课表",
    anchor: "schedule-builder",
  },
  {
    id: "section-monitoring",
    label: "课节监控",
    anchor: "section-monitoring",
  },
];

export function workflowIdFromHash(hash: string): WorkflowId {
  const anchor = hash.replace(/^#/, "");
  return (
    workflowDefinitions.find((workflow) => workflow.anchor === anchor)?.id ??
    "overview"
  );
}

export function workflowHref(workflow: WorkflowDefinition): string {
  return `#${workflow.anchor}`;
}
