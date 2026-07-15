import type {
  AcademicPageSnapshot,
  ExtractedRecord,
  ExtensionExtractionWarning,
  TableSnapshot,
} from "../shared/types.js";

export type SectionValidationState =
  | "AUTO_VERIFIED"
  | "REQUIRES_EXCEPTION_REVIEW"
  | "FAILED";

type Meeting = {
  component: string;
  days: string;
  start_time: string;
  end_time: string;
  start_date: string;
  end_date: string;
  building: string;
  room: string;
  location: string;
  instructor_display: string;
  modality: string;
  is_async: boolean;
  is_tba: boolean;
  is_arranged: boolean;
  raw_text: string;
  source_row_index: number;
};

const aliases: Record<string, readonly string[]> = {
  term: ["term", "term_code", "semester", "academic_term"],
  institution: ["institution", "institution_code", "school"],
  campus: ["campus", "campus_code", "campus_label"],
  course: ["course", "course_code", "code", "course_id"],
  subject: ["subject", "subject_code", "department"],
  number: ["number", "course_number", "catalog_number"],
  title: ["title", "course_title", "name"],
  section: ["section", "section_code", "class_section"],
  external_reference: ["crn", "external_reference", "external_id", "class_id"],
  component: ["component", "component_type", "activity", "meeting_type"],
  credits: ["credits", "credit_hours", "units"],
  modality: ["modality", "instruction_method", "instruction_mode", "delivery"],
  status: ["status", "section_status", "lifecycle"],
  days: ["meeting_days", "days", "day", "day_of_week"],
  time: ["meeting_time", "time", "hours"],
  start_time: ["start_time", "start"],
  end_time: ["end_time", "end"],
  dates: ["date_range", "dates", "meeting_dates"],
  start_date: ["start_date"],
  end_date: ["end_date"],
  location: ["location", "building_room", "room", "building"],
  building: ["building"],
  room: ["room"],
  instructor: ["instructor", "instructor_display", "faculty"],
  seats_available: ["seats_available", "available_seats", "available", "open_seats"],
  seats_capacity: ["seats_capacity", "capacity", "total_seats"],
  waitlist_available: ["waitlist_available", "waitlist", "waitlist_open", "waitlist_seats"],
  waitlist_capacity: ["waitlist_capacity", "waitlist_total", "waitlist_cap"],
};

function clean(value: string | undefined): string {
  return (value ?? "")
    .replace(/\b(Add|Drop|Register|Waitlist)\s+(Section|Course)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

function key(value: string): string {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function enumLike(value: string): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function columnMap(headers: readonly string[]): Map<string, number> {
  const normalized = headers.map(key);
  const result = new Map<string, number>();
  for (const [field, names] of Object.entries(aliases)) {
    const index = normalized.findIndex((header) => names.includes(header));
    if (index >= 0) result.set(field, index);
  }
  return result;
}

function value(row: readonly string[], map: Map<string, number>, field: string): string {
  const index = map.get(field);
  return index === undefined ? "" : clean(row[index]);
}

function splitCourse(valueText: string): { code: string; title: string } | null {
  const match = clean(valueText).match(/^([A-Z]{2,8})[*\s-]*(\d{3,4}[A-Z]?)(?:\s*[-:]\s*|\s+)?(.*)$/i);
  return match?.[1] && match[2]
    ? { code: `${match[1].toUpperCase()} ${match[2].toUpperCase()}`, title: clean(match[3]) }
    : null;
}

function parseTime(valueText: string): string {
  const value = clean(valueText).toUpperCase().replace(/\./g, "");
  if (!value || /^(TBA|ARRANGED|ASYNC|N\/A)$/.test(value)) return "";
  const match = value.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$/);
  if (!match) return "";
  let hour = Number(match[1]);
  const minute = Number(match[2] ?? "00");
  const meridiem = match[3];
  if (minute > 59 || hour > 23 || (meridiem && hour > 12) || (meridiem && hour === 0)) return "";
  if (meridiem === "AM" && hour === 12) hour = 0;
  if (meridiem === "PM" && hour < 12) hour += 12;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function parseTimeRange(valueText: string): [string, string] {
  const parts = clean(valueText).split(/\s*(?:-|–|—|to)\s*/i);
  if (parts.length !== 2) return ["", ""];
  const start = parseTime(parts[0] ?? "");
  const end = parseTime(parts[1] ?? "");
  return [start, end];
}

function normalizeDays(valueText: string): string {
  const map: Record<string, string> = {
    M: "MONDAY", MO: "MONDAY", MON: "MONDAY", MONDAY: "MONDAY", TU: "TUESDAY", TUE: "TUESDAY", T: "TUESDAY", TUESDAY: "TUESDAY",
    W: "WEDNESDAY", WE: "WEDNESDAY", WED: "WEDNESDAY", WEDNESDAY: "WEDNESDAY", R: "THURSDAY", TH: "THURSDAY", THU: "THURSDAY", THURSDAY: "THURSDAY",
    F: "FRIDAY", FR: "FRIDAY", FRI: "FRIDAY", FRIDAY: "FRIDAY", SA: "SATURDAY", SAT: "SATURDAY", SATURDAY: "SATURDAY", SU: "SUNDAY", SUN: "SUNDAY", SUNDAY: "SUNDAY",
  };
  const tokens = clean(valueText).toUpperCase().split(/[\s,/]+/).filter(Boolean);
  if (tokens.some((token) => ["TBA", "ARRANGED"].includes(token))) return "";
  return [...new Set(tokens.flatMap((token) => map[token] ? [map[token]] : []))].join(",");
}

function meetingFromRow(row: readonly string[], map: Map<string, number>, rowIndex: number): Meeting {
  const rawDays = value(row, map, "days");
  const rawTime = value(row, map, "time");
  const [rangeStart, rangeEnd] = parseTimeRange(rawTime);
  const start = parseTime(value(row, map, "start_time")) || rangeStart;
  const end = parseTime(value(row, map, "end_time")) || rangeEnd;
  const location = value(row, map, "location");
  const modality = enumLike(value(row, map, "modality"));
  return {
    component: enumLike(value(row, map, "component")) || "OTHER",
    days: normalizeDays(rawDays),
    start_time: start,
    end_time: end,
    start_date: value(row, map, "start_date"),
    end_date: value(row, map, "end_date"),
    building: value(row, map, "building"),
    room: value(row, map, "room"),
    location,
    instructor_display: value(row, map, "instructor"),
    modality,
    is_async: /ASYNC/i.test(`${modality} ${rawDays} ${rawTime} ${location}`),
    is_tba: /^(TBA|ARRANGED)$/i.test(rawDays) || /^(TBA|ARRANGED)$/i.test(rawTime),
    is_arranged: /ARRANGED/i.test(`${rawDays} ${rawTime}`),
    raw_text: clean(row.join(" ")),
    source_row_index: rowIndex + 1,
  };
}

function provenance(record: ExtractedRecord, fields: string[], rowIndex: number): void {
  const result: Record<string, object> = {};
  for (const field of fields) {
    const raw = record[field] ?? "";
    result[field] = {
      value: raw,
      rawText: raw,
      source: `visible row ${rowIndex + 1}`,
      valueType: "DIRECT",
      confidence: raw ? "high" : "low",
      requiresReview: !raw,
    };
  }
  record.field_provenance_json = JSON.stringify(result);
}

export function parseSectionTables(
  snapshot: AcademicPageSnapshot,
  tables: readonly TableSnapshot[],
  warnings: ExtensionExtractionWarning[],
): ExtractedRecord[] {
  const grouped = new Map<string, ExtractedRecord>();
  const seenRows = new Set<string>();
  let unsupported = false;
  for (const table of tables) {
    const map = columnMap(table.headers);
    const hasIdentity = map.has("term") && map.has("course") && map.has("section");
    if (!hasIdentity) continue;
    for (const [rowIndex, row] of table.rows.entries()) {
      const rawText = clean(row.join(" "));
      if (!rawText || row.map(key).join(" ") === table.headers.map(key).join(" ")) continue;
      let course = value(row, map, "course");
      const combined = splitCourse(course);
      const title = value(row, map, "title") || combined?.title || "";
      course = combined?.code || course.toUpperCase();
      const term = value(row, map, "term");
      const section = value(row, map, "section");
      if (!term || !course || !section) {
        const current = [...grouped.values()].at(-1);
        const continuation = current && (value(row, map, "days") || value(row, map, "time") || value(row, map, "location"));
        if (continuation) {
          const meetings = JSON.parse(String(current.meetings_json ?? "[]")) as Meeting[];
          meetings.push(meetingFromRow(row, map, rowIndex));
          current.meetings_json = JSON.stringify(meetings);
          current.raw_evidence = `${current.raw_evidence} | ${rawText}`;
          current.validation_state = "REQUIRES_EXCEPTION_REVIEW";
          continue;
        }
        unsupported = true;
        continue;
      }
      const identity = `${term.toUpperCase()}|${course.toUpperCase()}|${section}`;
      if (seenRows.has(`${identity}|${rawText}`)) {
        warnings.push({ code: "SECTION_DUPLICATE_VISIBLE_ROW", severity: "WARNING", message: `Duplicate visible Section row retained for review: ${identity}.` });
      }
      seenRows.add(`${identity}|${rawText}`);
      const meeting = meetingFromRow(row, map, rowIndex);
      const existing = grouped.get(identity);
      if (existing) {
        const meetings = JSON.parse(String(existing.meetings_json ?? "[]")) as Meeting[];
        if (!meetings.some((item) => item.raw_text === meeting.raw_text)) meetings.push(meeting);
        existing.meetings_json = JSON.stringify(meetings);
        existing.raw_evidence = `${existing.raw_evidence} | ${rawText}`;
        continue;
      }
      const record: ExtractedRecord = {
        term_code: term,
        course_code: course,
        course_title: title,
        section_code: section,
        external_reference: value(row, map, "external_reference"),
        component: enumLike(value(row, map, "component")),
        campus: value(row, map, "campus"),
        institution: value(row, map, "institution"),
        credits: value(row, map, "credits"),
        modality: enumLike(value(row, map, "modality")),
        status: enumLike(value(row, map, "status")),
        instructor_display: value(row, map, "instructor"),
        seats_available: value(row, map, "seats_available"),
        seats_capacity: value(row, map, "seats_capacity"),
        waitlist_available: value(row, map, "waitlist_available"),
        waitlist_capacity: value(row, map, "waitlist_capacity"),
        meeting_days: meeting.days,
        day_of_week: meeting.days.split(",")[0] ?? "",
        start_time: meeting.start_time,
        end_time: meeting.end_time,
        meeting_time: meeting.start_time && meeting.end_time ? `${meeting.start_time}-${meeting.end_time}` : value(row, map, "time"),
        location: meeting.location,
        meetings_json: JSON.stringify([meeting]),
        raw_evidence: rawText,
        availability_evidence_json: JSON.stringify({
          seats_available: value(row, map, "seats_available"),
          seats_capacity: value(row, map, "seats_capacity"),
          waitlist_available: value(row, map, "waitlist_available"),
          waitlist_capacity: value(row, map, "waitlist_capacity"),
        }),
        mapping_candidates_json: JSON.stringify({
          institution: { value: value(row, map, "institution"), match_type: "MANUAL_REQUIRED" },
          campus: { value: value(row, map, "campus"), match_type: "MANUAL_REQUIRED" },
          academic_term: { value: term, match_type: term ? "TERM_MATCH" : "MANUAL_REQUIRED" },
          course: { value: course, match_type: "EXACT_CODE" },
        }),
        validation_state: "AUTO_VERIFIED",
        completeness: snapshot.snapshotMetadata?.bounded ? "UNCERTAIN" : "COMPLETE",
        source_table_index: String(table.index + 1),
        source_row_index: String(rowIndex + 1),
        source_label: table.caption || `visible table ${table.index + 1}`,
      };
      provenance(record, ["term_code", "course_code", "course_title", "section_code", "campus", "credits", "modality", "status"], rowIndex);
      grouped.set(identity, record);
    }
  }
  if (unsupported) warnings.push({ code: "SECTION_UNSUPPORTED_LAYOUT", severity: "WARNING", message: "Some visible Section rows could not be associated safely with a Section identity." });
  if (snapshot.snapshotMetadata?.bounded || snapshot.warnings?.some((warning) => warning.code === "EXTRACTION_LIMIT_REACHED")) {
    warnings.push({ code: "SECTION_SNAPSHOT_TRUNCATED", severity: "ERROR", message: "The visible Section snapshot was bounded before parsing completed; review is required and the import is not complete." });
    for (const record of grouped.values()) record.validation_state = "FAILED";
  }
  if (grouped.size === 0 && tables.some((table) => table.rows.length > 0)) {
    warnings.push({ code: "SECTION_UNSUPPORTED_LAYOUT", severity: "ERROR", message: "Visible Section data was found, but its layout is not safely supported." });
  }
  return [...grouped.values()];
}
