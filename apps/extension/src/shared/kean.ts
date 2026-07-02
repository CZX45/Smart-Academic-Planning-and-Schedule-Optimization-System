import type { AcademicPageType, DataImportType } from "./types.js";

export const KEAN_SOURCE_LABEL = "KEAN_STUDENT_PORTAL" as const;
export const KEAN_STUDENT_PORTAL_ORIGIN =
  "https://kean-ss.colleague.elluciancloud.com" as const;
export const KEAN_STUDENT_PORTAL_PREFIX =
  `${KEAN_STUDENT_PORTAL_ORIGIN}/Student` as const;
export const KEAN_STUDENT_PORTAL_REQUESTED_PREFIX =
  `${KEAN_STUDENT_PORTAL_PREFIX}/*` as const;
export const KEAN_OPTIONAL_HOST_PERMISSION =
  `${KEAN_STUDENT_PORTAL_ORIGIN}/*` as const;

export type KeanExtractionStrategy =
  | "TRANSCRIPT"
  | "DEGREE_AUDIT"
  | "MY_PROGRESS"
  | "COURSE_CATALOG"
  | "SECTION_SCHEDULE";

export type KeanPageDefinition = {
  key: AcademicPageType;
  importType: DataImportType;
  extractionStrategy: KeanExtractionStrategy;
  routeMarkers: readonly string[];
  visibleTextMarkers: readonly string[];
  expectedFields: readonly string[];
  warningCodesForMissingFields: Readonly<Record<string, string>>;
  safetyRestrictions: readonly string[];
};

const COMMON_SAFETY_RESTRICTIONS = [
  "Use only user-opened pages under the Kean Student Portal prefix.",
  "Read visible academic-planning table text only.",
  "Ignore form controls and action-only columns.",
  "Send data only after preview and explicit confirmation.",
] as const;

export const KEAN_PAGE_DEFINITIONS: readonly KeanPageDefinition[] = [
  {
    key: "KEAN_TRANSCRIPT_PAGE",
    importType: "UNOFFICIAL_TRANSCRIPT",
    extractionStrategy: "TRANSCRIPT",
    routeMarkers: ["AcademicHistory", "Transcript", "Grades"],
    visibleTextMarkers: [
      "Unofficial Transcript",
      "Transcript",
      "Completed Coursework",
    ],
    expectedFields: [
      "term_code",
      "course_code",
      "course_title",
      "credits",
      "grade",
      "attempt_status",
    ],
    warningCodesForMissingFields: {
      term_code: "KEAN_TRANSCRIPT_TERM_MISSING",
      course_code: "KEAN_TRANSCRIPT_COURSE_MISSING",
      course_title: "KEAN_TRANSCRIPT_TITLE_MISSING",
      credits: "KEAN_TRANSCRIPT_CREDITS_MISSING",
      grade: "KEAN_TRANSCRIPT_GRADE_MISSING",
      attempt_status: "KEAN_TRANSCRIPT_STATUS_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_DEGREE_AUDIT_PAGE",
    importType: "DEGREE_AUDIT_EXPORT",
    extractionStrategy: "DEGREE_AUDIT",
    routeMarkers: ["DegreeAudit", "ProgramEvaluation"],
    visibleTextMarkers: ["Degree Audit", "Program Evaluation"],
    expectedFields: [
      "program_code",
      "catalog_year",
      "requirements",
      "completed_courses",
      "remaining_requirements",
    ],
    warningCodesForMissingFields: {
      program_code: "KEAN_AUDIT_PROGRAM_MISSING",
      catalog_year: "KEAN_AUDIT_CATALOG_MISSING",
      requirements: "KEAN_AUDIT_REQUIREMENT_MISSING",
      completed_courses: "KEAN_AUDIT_COMPLETED_MISSING",
      remaining_requirements: "KEAN_AUDIT_REMAINING_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_MY_PROGRESS_PAGE",
    importType: "DEGREE_AUDIT_EXPORT",
    extractionStrategy: "MY_PROGRESS",
    routeMarkers: ["MyProgress", "Progress"],
    visibleTextMarkers: ["MyProgress", "My Progress", "Degree Progress"],
    expectedFields: [
      "status",
      "course_code",
      "course_title",
      "grade",
      "term_code",
      "credits",
      "requirements",
    ],
    warningCodesForMissingFields: {
      status: "KEAN_MY_PROGRESS_STATUS_MISSING",
      course_code: "KEAN_MY_PROGRESS_COURSE_MISSING",
      course_title: "KEAN_MY_PROGRESS_TITLE_MISSING",
      grade: "KEAN_MY_PROGRESS_GRADE_MISSING",
      term_code: "KEAN_MY_PROGRESS_TERM_MISSING",
      credits: "KEAN_MY_PROGRESS_CREDITS_MISSING",
      requirements: "KEAN_MY_PROGRESS_REQUIREMENT_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_COURSE_CATALOG_PAGE",
    importType: "COURSE_CATALOG",
    extractionStrategy: "COURSE_CATALOG",
    routeMarkers: ["CourseCatalog", "Catalog", "Courses"],
    visibleTextMarkers: ["Course Catalog", "Catalog Search", "Courses"],
    expectedFields: [
      "course_code",
      "course_title",
      "credits",
      "course_level",
      "department",
      "description",
      "prerequisites",
      "restrictions",
    ],
    warningCodesForMissingFields: {
      course_code: "KEAN_CATALOG_COURSE_MISSING",
      course_title: "KEAN_CATALOG_TITLE_MISSING",
      credits: "KEAN_CATALOG_CREDITS_MISSING",
      course_level: "KEAN_CATALOG_LEVEL_MISSING",
      department: "KEAN_CATALOG_DEPARTMENT_MISSING",
      description: "KEAN_CATALOG_DESCRIPTION_MISSING",
      prerequisites: "KEAN_CATALOG_PREREQUISITES_MISSING",
      restrictions: "KEAN_CATALOG_RESTRICTIONS_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_SECTION_SEARCH_PAGE",
    importType: "SECTION_SCHEDULE",
    extractionStrategy: "SECTION_SCHEDULE",
    routeMarkers: ["SectionSearch", "CourseSections", "Search"],
    visibleTextMarkers: ["Section Search", "Course Sections", "Sections"],
    expectedFields: [
      "term_code",
      "course_code",
      "section_code",
      "status",
      "seats_available",
      "seats_capacity",
      "waitlist_available",
      "meeting_days",
      "meeting_time",
      "location",
      "instructor_display",
    ],
    warningCodesForMissingFields: {
      term_code: "KEAN_SECTION_TERM_MISSING",
      course_code: "KEAN_SECTION_COURSE_MISSING",
      section_code: "KEAN_SECTION_NUMBER_MISSING",
      status: "KEAN_SECTION_STATUS_MISSING",
      seats_available: "KEAN_SECTION_SEATS_MISSING",
      seats_capacity: "KEAN_SECTION_CAPACITY_MISSING",
      waitlist_available: "KEAN_SECTION_WAITLIST_MISSING",
      meeting_days: "KEAN_SECTION_DAYS_MISSING",
      meeting_time: "KEAN_SECTION_TIME_MISSING",
      location: "KEAN_SECTION_LOCATION_MISSING",
      instructor_display: "KEAN_SECTION_INSTRUCTOR_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_STUDENT_PLANNING_PAGE",
    importType: "SECTION_SCHEDULE",
    extractionStrategy: "SECTION_SCHEDULE",
    routeMarkers: ["StudentPlanning", "Planning", "Plan"],
    visibleTextMarkers: ["Student Planning", "Plan", "Timeline"],
    expectedFields: [
      "term_code",
      "course_code",
      "section_code",
      "status",
      "credits",
      "meeting_days",
      "meeting_time",
      "location",
      "instructor_display",
    ],
    warningCodesForMissingFields: {
      term_code: "KEAN_PLANNING_TERM_MISSING",
      course_code: "KEAN_PLANNING_COURSE_MISSING",
      section_code: "KEAN_PLANNING_SECTION_MISSING",
      status: "KEAN_PLANNING_STATUS_MISSING",
      credits: "KEAN_PLANNING_CREDITS_MISSING",
      meeting_days: "KEAN_PLANNING_DAYS_MISSING",
      meeting_time: "KEAN_PLANNING_TIME_MISSING",
      location: "KEAN_PLANNING_LOCATION_MISSING",
      instructor_display: "KEAN_PLANNING_INSTRUCTOR_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
  {
    key: "KEAN_SCHEDULE_PAGE",
    importType: "SECTION_SCHEDULE",
    extractionStrategy: "SECTION_SCHEDULE",
    routeMarkers: ["Schedule", "MySchedule"],
    visibleTextMarkers: ["Student Schedule", "My Schedule", "Schedule"],
    expectedFields: [
      "term_code",
      "course_code",
      "section_code",
      "status",
      "credits",
      "meeting_days",
      "meeting_time",
      "location",
      "instructor_display",
    ],
    warningCodesForMissingFields: {
      term_code: "KEAN_SCHEDULE_TERM_MISSING",
      course_code: "KEAN_SCHEDULE_COURSE_MISSING",
      section_code: "KEAN_SCHEDULE_SECTION_MISSING",
      status: "KEAN_SCHEDULE_STATUS_MISSING",
      credits: "KEAN_SCHEDULE_CREDITS_MISSING",
      meeting_days: "KEAN_SCHEDULE_DAYS_MISSING",
      meeting_time: "KEAN_SCHEDULE_TIME_MISSING",
      location: "KEAN_SCHEDULE_LOCATION_MISSING",
      instructor_display: "KEAN_SCHEDULE_INSTRUCTOR_MISSING",
    },
    safetyRestrictions: COMMON_SAFETY_RESTRICTIONS,
  },
] as const;

export function isKeanStudentPortalUrl(url: string): boolean {
  const href = safeUrl(url)?.href;
  return (
    href === KEAN_STUDENT_PORTAL_PREFIX ||
    href?.startsWith(`${KEAN_STUDENT_PORTAL_PREFIX}/`) === true
  );
}

export function isKeanHostUrl(url: string): boolean {
  return safeUrl(url)?.origin === KEAN_STUDENT_PORTAL_ORIGIN;
}

export function detectKeanPageDefinition(
  url: string,
  title: string,
  visibleText: string,
): KeanPageDefinition | null {
  if (!isKeanStudentPortalUrl(url)) {
    return null;
  }
  const normalizedPath = safeUrl(url)?.pathname.toLowerCase() ?? "";
  const haystack = `${title} ${visibleText}`.toLowerCase();
  return (
    KEAN_PAGE_DEFINITIONS.find((definition) => {
      const routeMatches = definition.routeMarkers.some((marker) =>
        normalizedPath.includes(marker.toLowerCase()),
      );
      const textMatches = definition.visibleTextMarkers.some((marker) =>
        haystack.includes(marker.toLowerCase()),
      );
      return routeMatches || textMatches;
    }) ?? null
  );
}

function safeUrl(url: string): URL | null {
  try {
    return new URL(url);
  } catch {
    return null;
  }
}
