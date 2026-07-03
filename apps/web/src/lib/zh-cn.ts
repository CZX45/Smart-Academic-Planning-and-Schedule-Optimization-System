import {
  getAcademicStatusBadge,
  type AcademicAdvisoryLabel,
  type AcademicEmptyStateCopy,
  type AcademicEmptyStateKey,
  type AcademicStatusBadge,
  type AdvisoryLabelKey,
} from "@sapsos/shared";

const statusCopy: Record<string, string> = {
  ACKNOWLEDGED: "已确认",
  ACTIVE: "启用中",
  ACADEMIC_TERM: "学期",
  ADD_CERTIFICATE: "添加证书",
  ADD_CONCENTRATION: "添加方向",
  ADD_MINOR: "添加辅修",
  ADD_SECOND_MAJOR: "添加第二专业",
  ADVISOR_REVIEW: "顾问审核",
  ALTERNATIVE: "替代项",
  AMBIGUOUS: "存在歧义",
  AFTERNOON: "下午",
  APPLIED: "已应用",
  APPLIED_WITH_WARNINGS: "已应用但有警告",
  APPLYING: "正在应用",
  ARRANGED: "待安排",
  ARCHIVED: "已归档",
  BLOCKED: "已阻止",
  BROWSER_EXTENSION: "浏览器插件导入",
  CANCELLED: "已取消",
  CERTIFICATE: "证书",
  CHANGE_PRIMARY_MAJOR: "更改主修专业",
  CLOSED: "已关闭",
  COMPLETED: "已完成",
  COMPLETED_WITH_WARNINGS: "已完成但有警告",
  CONCENTRATION: "方向",
  CONDITIONALLY_ELIGIBLE: "有条件符合",
  CONDITIONALLY_PLANNED: "有条件规划",
  CONDITIONALLY_SATISFIED: "有条件满足",
  CONFIRMED: "已确认",
  COREQUISITE_MISSING: "缺少共同修读课程",
  COREQUISITE_PAIR: "共同修读组合",
  COURSE: "课程",
  COURSE_ATTEMPT: "课程尝试记录",
  COURSE_CATALOG: "课程目录",
  COURSE_OFFERING_PATTERN: "课程开设模式",
  CREATED: "已创建",
  CREDIT_LIMIT: "学分限制",
  CURRENT: "当前",
  CURRENT_PROGRAM: "当前项目",
  CUSTOM_COMBINATION: "自定义组合",
  CUSTOM_COURSE_SET: "自选课程集合",
  DEFERRED: "暂缓",
  DEGREE_AUDIT_EXPORT: "学业审核导出",
  DEGREE_AUDIT_REMAINING: "学业审核剩余项",
  DIRECT_REQUIREMENT: "直接要求",
  DISABLED: "已禁用",
  DRAFT: "草稿",
  DUPLICATE: "重复",
  DUPLICATE_COURSE: "重复课程",
  EDITED_AND_CONFIRMED: "已编辑并确认",
  ELECTIVE_POOL: "选修池",
  ELIGIBILITY_BLOCKED: "资格被阻止",
  ELIGIBLE: "符合",
  EMPTY: "暂无数据",
  ERROR: "错误",
  EQUIVALENCY: "等效项",
  EXAM: "考试",
  EXACT_CODE: "精确代码匹配",
  EXCLUDED_DAY: "排除日期",
  EXTERNAL_OBJECT_REFERENCE: "外部对象引用",
  FAILED: "失败",
  FEASIBLE: "可行",
  FEASIBLE_WITH_WARNINGS: "可行但有警告",
  FRIDAY: "周五",
  FROM_DEGREE_AUDIT: "来自学业审核",
  FROM_LONG_TERM_PLAN: "来自长期规划",
  GENERIC_CSV: "通用 CSV",
  GENERIC_JSON: "通用 JSON",
  HIGH: "高",
  HYBRID: "混合授课",
  IDLE: "未开始",
  IMPORTED: "已导入",
  IN_PROGRESS: "进行中",
  IN_REVIEW: "审核中",
  IN_PERSON: "线下授课",
  INFEASIBLE: "不可行",
  INFERRED: "推断",
  INFO: "信息",
  INSTRUCTOR_CHANGED: "教师已变化",
  INVALID: "无效",
  LAB: "实验课",
  LECTURE: "讲座课",
  LOADING: "加载中",
  LOCAL_DEV_FIXTURE: "本地开发 fixture",
  LOCATION_CHANGED: "地点已变化",
  MANUAL_PLACEHOLDER: "人工占位项",
  MANUAL_REQUIRED: "需要人工处理",
  MANUAL_REVIEW_REQUIRED: "需要人工审核",
  MEETING_TIME_CHANGED: "上课时间已变化",
  METADATA_ONLY: "仅元数据",
  MINOR: "辅修",
  MOCK: "模拟数据",
  MONDAY: "周一",
  NEEDS_ADVISOR_REVIEW: "需要顾问审核",
  NO_MATCH: "无匹配",
  NO_SECTION_AVAILABLE: "无可用课节",
  NONE: "无",
  NORMALIZED_CODE: "规范化代码匹配",
  NOT_APPLICABLE: "不适用",
  NOT_ELIGIBLE: "不符合",
  NOT_REPORTED: "未报告",
  NOT_SATISFIED: "未满足",
  NOT_STARTED: "尚未开始",
  NOT_STORED: "未保存",
  OFFLINE: "离线",
  OFFICIAL: "官方",
  ONLINE_ASYNC: "在线异步",
  ONLINE_SYNC: "在线同步",
  ONLINE_ASYNCHRONOUS: "在线异步",
  ONLINE_SYNCHRONOUS: "在线同步",
  OPEN: "开放",
  OTHER: "其他",
  PARSED: "已解析",
  PARSED_WITH_WARNINGS: "已解析但有警告",
  PARSING: "解析中",
  PARTIAL: "部分完成",
  PARTIALLY_SATISFIED: "部分满足",
  PENDING: "待处理",
  PERMISSION_REQUIRED: "需要许可",
  PLANNED: "已规划",
  PREREQUISITE_ONLY: "仅先修",
  PREREQUISITE_UNLOCK: "先修解锁",
  PRIMARY: "主要",
  PRIMARY_MAJOR: "主修专业",
  PROGRAM: "项目",
  PROGRAM_VERSION: "项目版本",
  PROJECTED: "预测",
  READY_TO_APPLY: "可应用",
  RECITATION: "习题课",
  READY: "就绪",
  REGISTRATION: "注册检查",
  REJECTED: "已拒绝",
  REQUIREMENT: "要求",
  REQUIREMENT_NODE: "要求节点",
  REVIEW_REQUIRED: "需要审核",
  ROLLED_BACK: "已回滚",
  RUNNING: "运行中",
  SATISFIED: "已满足",
  SATURDAY: "周六",
  SCHEMA_ERROR: "结构错误",
  SECTION: "课节",
  SECTION_CLOSED: "课节已关闭",
  SECTION_MEETING: "课节上课时间",
  SECTION_OPENED: "课节已开放",
  SECTION_SCHEDULE: "课节时间表",
  SECOND_MAJOR: "第二专业",
  SEMINAR: "研讨课",
  SHARED: "共享",
  SKIPPED: "已跳过",
  SKIPPED_ADVISOR_REVIEW: "已跳过顾问审核项",
  SKIPPED_DEFERRED: "已跳过暂缓项",
  SKIPPED_DUPLICATE: "已跳过重复项",
  SKIPPED_REJECTED: "已跳过拒绝项",
  SKIPPED_UNSUPPORTED: "已跳过不支持项",
  STANDARD: "标准",
  STATUS_CHANGED: "状态已变化",
  STUDENT_COURSE_ATTEMPT: "学生课程尝试记录",
  STUDENT_PROVIDED: "学生提供",
  STUDENT_REVIEWABLE: "学生可审核",
  SUBSTITUTION: "替代",
  SUCCESS: "成功",
  SUNDAY: "周日",
  TERM_MATCH: "学期匹配",
  THURSDAY: "周四",
  TIME_OVERLAP: "时间重叠",
  TITLE_SIMILARITY: "标题相似度",
  TOTAL_CREDIT_ONLY: "仅总学分",
  TOTAL_CREDITS: "总学分",
  TRANSFER_CREDIT: "转学分",
  TUESDAY: "周二",
  UNALLOCATED: "未分配",
  UNOFFICIAL_TRANSCRIPT: "非官方成绩单",
  UNAVAILABLE_TIME: "不可用时间",
  UNIQUE_SECONDARY: "第二项目独有",
  UNKNOWN: "未知",
  UNKNOWN_CHANGE: "未知变化",
  UNREVIEWED: "未审核",
  UNSUPPORTED: "不支持",
  UPDATED: "已更新",
  VALID: "有效",
  VALID_WITH_WARNINGS: "有效但有警告",
  WAIVED: "已豁免",
  WAIVER: "豁免",
  WAITLIST_CHANGED: "候补名单已变化",
  WAITLIST: "候补名单",
  WARNING: "有警告",
  WEDNESDAY: "周三",
  WHAT_IF_REMAINING: "假设方案剩余项",
  WHAT_IF_REQUIREMENT: "假设方案要求",
  WHAT_IF_SCENARIO: "假设方案",
};

const advisoryLabelCopy: Record<AdvisoryLabelKey, AcademicAdvisoryLabel> = {
  NON_OFFICIAL_IMPORTED_DATA: {
    text: "非官方导入数据",
    tone: "warning",
  },
  MANUAL_REVIEW_REQUIRED: {
    text: "需要人工审核",
    tone: "warning",
  },
  ADVISORY_ONLY: { text: "仅供参考", tone: "info" },
  VERIFY_IN_OFFICIAL_PORTAL: {
    text: "请在官方门户人工核对",
    tone: "danger",
  },
};

const emptyStateCopy: Record<AcademicEmptyStateKey, AcademicEmptyStateCopy> = {
  NO_DATA_IMPORTS: {
    title: "还没有数据导入",
    explanation: "当前还没有为模拟学生创建或加载 staging 导入。",
    reason: "只有学生手动选择要进入 staging 的数据后，导入预览才会显示内容。",
    nextAction: "先手动预览一次导入，再进入人工审核。",
    disclaimer:
      "非官方数据。需要人工审核。导入数据先进入 staging，不直接写入正式记录。",
  },
  NO_CONFIRMED_IMPORTS: {
    title: "还没有已确认的导入",
    explanation: "当前还没有经过人工审核并确认的导入记录。",
    reason: "必须先预览 staging 导入，之后才能应用审核决定。",
    nextAction: "预览或加载 staging 导入，然后逐条人工审核记录。",
    disclaimer: "需要人工审核。仅供参考。",
  },
  NO_SECTION_MONITORING_TARGETS: {
    title: "还没有监控的课节",
    explanation: "当前没有选择任何课节用于参考性监控。",
    reason: "只有学生从导入数据中手动选择课节后，监控才会开始。",
    nextAction: "导入 section-search 数据，并手动选择要监控的课节。",
    disclaimer: "非官方导入数据。请在官方门户人工核对。",
  },
  NO_SECTION_MONITORING_ALERTS: {
    title: "还没有课节提醒",
    explanation: "当前还没有检测到任何仅供参考的课节变化。",
    reason: "导入的课节快照中还没有可展示的前后变化。",
    nextAction:
      "导入新的 section-search 快照，然后在官方门户人工核对任何变化。",
    disclaimer: "仅供参考。请在官方门户人工核对。",
  },
  NO_GENERATED_SCHEDULE_PLANS: {
    title: "还没有生成课表方案",
    explanation: "当前还没有生成任何学期课表优化结果。",
    reason: "只有学生手动运行优化后，课表生成器才会显示方案。",
    nextAction: "选择课程集合并生成课表，用于比较仅供参考的课表选项。",
    disclaimer: "仅供参考。不会注册课程，也不会 add/drop/swap/waitlist。",
  },
  NO_WHAT_IF_SCENARIOS: {
    title: "还没有假设方案",
    explanation: "当前还没有创建任何项目变更假设方案。",
    reason: "只有学生手动创建方案后，假设方案比较才会显示内容。",
    nextAction: "选择候选项目并创建假设方案。",
    disclaimer: "仅供参考。高风险学业建议可能需要顾问确认。",
  },
};

export type DemoOptionLabelKind =
  | "candidateCourse"
  | "candidateProgram"
  | "dataImportSample"
  | "plannerScope"
  | "schedulePreset"
  | "scheduleSectionChoice"
  | "term";

const demoOptionLabels: Record<DemoOptionLabelKind, Record<string, string>> = {
  candidateCourse: {
    "fin-300-current": "FIN 300 · 当前先修通过",
    "fin-350-projected": "FIN 350 · 预测条件先修",
    "fin-400-registration": "FIN 400 HYB · 需要许可且有候补名单",
    "fin-410-coreq": "FIN 410 · 明确规划 corequisite",
    "fin-450-current": "FIN 450 · 缺少先修",
    "free-100-closed": "FREE 100 · 无已保存限制，课节已关闭",
  },
  candidateProgram: {
    "accounting-minor": "模拟会计辅修",
    "economics-minor": "模拟经济学辅修",
    "second-major": "模拟第二专业",
    certificate: "模拟证书",
    "change-major": "模拟替代主修专业",
  },
  dataImportSample: {
    "mock-degree-audit-json": "模拟学业审核 JSON",
    "mock-transcript-csv": "模拟成绩单 CSV",
  },
  plannerScope: {
    "current-program": "当前模拟金融学士",
    "what-if-accounting-minor": "假设：添加模拟会计辅修",
  },
  schedulePreset: {
    "fall-fin-300": "2024 秋季：仅 FIN 300",
    "fall-fin-300-403": "2024 秋季：FIN 300 + FIN 403",
  },
  scheduleSectionChoice: {
    none: "无",
    "fin-403-002": "固定 FIN 403 002",
    "fin-403-friday": "固定 FIN 403 周五课节",
    "fin-300-afternoon": "排除 FIN 300 下午课节",
    "fin-300-web": "排除 FIN 300 WEB",
  },
  term: {
    "Fall 2024": "2024 秋季",
    "Spring 2025": "2025 春季",
  },
};

function normalizeDisplayKey(value: string | null | undefined): string | null {
  const normalized = value?.trim().replaceAll("-", "_").replaceAll(" ", "_");
  if (!normalized) {
    return null;
  }
  return normalized.toUpperCase();
}

function fallbackStatusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function localizeStatusLabel(status: string): string {
  const key = normalizeDisplayKey(status);
  if (!key) {
    return "未知";
  }
  return statusCopy[key] ?? fallbackStatusLabel(status);
}

export function localizeStatusBadge(
  status: string | null | undefined,
): AcademicStatusBadge {
  const badge = getAcademicStatusBadge(status);
  return {
    ...badge,
    label: localizeStatusLabel(badge.label),
  };
}

export function getZhCnAdvisoryLabels(
  keys: AdvisoryLabelKey[],
): AcademicAdvisoryLabel[] {
  return keys.map((key) => advisoryLabelCopy[key]);
}

export function getZhCnEmptyStateCopy(
  key: AcademicEmptyStateKey,
): AcademicEmptyStateCopy {
  return emptyStateCopy[key];
}

export function localizeDemoOptionLabel(
  kind: DemoOptionLabelKind,
  id: string,
  fallback: string,
): string {
  return demoOptionLabels[kind][id] ?? fallback;
}

function displayBeforeAfterValue(value: string | null | undefined): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return "未知";
  }
  return localizeStatusLabel(trimmed);
}

export function formatZhCnBeforeAfterValue(
  previousValue: string | null | undefined,
  currentValue: string | null | undefined,
): string {
  return `${displayBeforeAfterValue(previousValue)} -> ${displayBeforeAfterValue(
    currentValue,
  )}`;
}
