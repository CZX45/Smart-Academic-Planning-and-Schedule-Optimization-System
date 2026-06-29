import { describe, expect, it } from "vitest";
import {
  ApiRequestError,
  ApiResponseSchemaError,
  CourseEligibilityCheckSchema,
  HealthResponseSchema,
  ReadinessResponseSchema,
  AcademicScenarioSchema,
  ScenarioComparisonSnapshotSchema,
  ScenarioCourseAllocationSchema,
  ScenarioProgramSchema,
  ScenarioWarningSchema,
  DegreeAuditRunSchema,
  RequirementEvaluationSchema,
  DegreeAuditWarningSchema,
  createCourseEligibilityCheck,
  fetchHealth,
} from "./index.js";

describe("HealthResponseSchema", () => {
  it("validates API health payloads", () => {
    expect(
      HealthResponseSchema.parse({
        status: "ok",
        service: "api",
        database_configured: true,
      }),
    ).toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });
});

describe("ReadinessResponseSchema", () => {
  it("validates API readiness payloads", () => {
    expect(
      ReadinessResponseSchema.parse({
        status: "ready",
        service: "api",
        database_ready: true,
      }),
    ).toEqual({
      status: "ready",
      service: "api",
      database_ready: true,
    });
  });
});

describe("fetchHealth", () => {
  it("returns parsed health payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          status: "ok",
          service: "api",
          database_configured: true,
        }),
      );

    await expect(fetchHealth("http://api.test", { fetchFn })).resolves.toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });

  it("reports non-2xx health responses", async () => {
    const fetchFn = async () => new Response("nope", { status: 500 });

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiRequestError,
    );
  });

  it("reports invalid health response schemas", async () => {
    const fetchFn = async () => new Response(JSON.stringify({ status: "ok" }));

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiResponseSchemaError,
    );
  });
});

describe("degree audit schemas", () => {
  it("validates audit run summaries", () => {
    expect(
      DegreeAuditRunSchema.parse({
        id: "00000000-0000-4000-8000-000000000001",
        student_profile_id: "00000000-0000-4000-8000-000000000002",
        program_version_id: "00000000-0000-4000-8000-000000000003",
        status: "COMPLETED_WITH_WARNINGS",
        engine_version: "phase-3a-degree-audit-v1",
        calculation_mode: "PROJECTED",
        started_at: "2026-06-23T00:00:00Z",
        completed_at: "2026-06-23T00:00:01Z",
        total_required_credits: "120.0",
        completed_credits: "18.0",
        in_progress_credits: "3.0",
        planned_credits: "3.0",
        remaining_credits: "102.0",
        completion_percentage: "15.00",
        source_snapshot_hash: "hash",
        created_at: "2026-06-23T00:00:00Z",
        updated_at: "2026-06-23T00:00:01Z",
      }),
    ).toMatchObject({
      status: "COMPLETED_WITH_WARNINGS",
      calculation_mode: "PROJECTED",
    });
  });

  it("validates requirement evaluations with applications and warnings", () => {
    expect(
      RequirementEvaluationSchema.parse({
        id: "00000000-0000-4000-8000-000000000011",
        degree_audit_run_id: "00000000-0000-4000-8000-000000000001",
        requirement_node_id: "00000000-0000-4000-8000-000000000012",
        requirement_code: "BUS-REQ-A",
        requirement_name: "Required Course A",
        requirement_type: "REQUIRED_COURSE",
        status: "SATISFIED",
        required_credits: "3.0",
        satisfied_credits: "3.0",
        remaining_credits: "0.0",
        required_courses: 1,
        satisfied_courses: 1,
        remaining_courses: 0,
        minimum_grade: "C",
        explanation: "Completed by Mock BUS 101.",
        display_order: 10,
        applications: [
          {
            id: "00000000-0000-4000-8000-000000000013",
            course_id: "00000000-0000-4000-8000-000000000014",
            course_code: "BUS 101",
            course_title: "Mock Business Foundations",
            application_type: "COURSE_ATTEMPT",
            credit_amount: "3.0",
            grade: "B",
            is_completed: true,
            is_in_progress: false,
            is_planned: false,
            is_shared: false,
            explanation: "Applied completed attempt.",
          },
        ],
        warnings: [],
      }),
    ).toMatchObject({
      requirement_code: "BUS-REQ-A",
      status: "SATISFIED",
    });

    expect(
      DegreeAuditWarningSchema.parse({
        id: "00000000-0000-4000-8000-000000000015",
        degree_audit_run_id: "00000000-0000-4000-8000-000000000001",
        requirement_evaluation_id: "00000000-0000-4000-8000-000000000011",
        warning_code: "PENDING_TRANSFER",
        severity: "WARNING",
        message: "Pending transfer credit is not applied.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ warning_code: "PENDING_TRANSFER" });
  });
});

describe("academic scenario schemas", () => {
  it("validates scenario snapshots, allocations, warnings, and comparison summaries", () => {
    const scenario = AcademicScenarioSchema.parse({
      id: "00000000-0000-4000-8000-000000000101",
      student_profile_id: "00000000-0000-4000-8000-000000000102",
      name: "Add Accounting Minor",
      scenario_type: "ADD_MINOR",
      status: "COMPLETED_WITH_WARNINGS",
      base_program_version_id: "00000000-0000-4000-8000-000000000103",
      engine_version: "phase-3b-academic-scenario-v1",
      created_at: "2026-06-23T00:00:00Z",
      updated_at: "2026-06-23T00:00:01Z",
      completed_at: "2026-06-23T00:00:01Z",
    });
    expect(scenario.scenario_type).toBe("ADD_MINOR");

    expect(
      ScenarioProgramSchema.parse({
        id: "00000000-0000-4000-8000-000000000104",
        academic_plan_scenario_id: scenario.id,
        program_version_id: scenario.base_program_version_id,
        relationship_type: "PRIMARY_MAJOR",
        is_existing_program: true,
        is_hypothetical: false,
        priority: 0,
        program_code: "BSFIN",
        program_name: "Mock BS Finance",
        source: { source_type: "MOCK", is_official: false },
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ relationship_type: "PRIMARY_MAJOR" });

    expect(
      ScenarioCourseAllocationSchema.parse({
        id: "00000000-0000-4000-8000-000000000105",
        academic_plan_scenario_id: scenario.id,
        student_course_attempt_id: "00000000-0000-4000-8000-000000000106",
        transfer_credit_id: null,
        course_id: "00000000-0000-4000-8000-000000000107",
        course_code: "ACCT 300",
        course_title: "Mock Accounting Analytics",
        program_version_id: scenario.base_program_version_id,
        requirement_node_id: "00000000-0000-4000-8000-000000000108",
        requirement_code: "ACCT-MINOR-CORE",
        allocation_type: "SHARED",
        credit_amount: "3.0",
        is_shared: true,
        is_unique_to_program: false,
        allocation_rank: 1,
        reason_code: "SHARED_BY_RULE",
        explanation: "Shared by mock rule.",
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ allocation_type: "SHARED", credit_amount: "3.0" });

    expect(
      ScenarioWarningSchema.parse({
        id: "00000000-0000-4000-8000-000000000109",
        academic_plan_scenario_id: scenario.id,
        scenario_program_id: null,
        warning_code: "MISSING_PROGRAM_COMBINATION_RULE",
        severity: "WARNING",
        message: "Advisor review is required.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ requires_advisor_confirmation: true });

    expect(
      ScenarioComparisonSnapshotSchema.parse({
        academic_plan_scenario_id: scenario.id,
        completed_credits: "18.0",
        in_progress_credits: "3.0",
        planned_credits: "3.0",
        remaining_requirement_credits: "12.0",
        shared_credits: "3.0",
        unique_secondary_credits: "6.0",
        estimated_additional_credits: "9.0",
        unresolved_requirements: 4,
        manual_review_count: 1,
        completion_percentage: "82.50",
        is_estimate: true,
        created_at: "2026-06-23T00:00:00Z",
      }),
    ).toMatchObject({ is_estimate: true });
  });
});

describe("course eligibility schemas", () => {
  const eligibilityPayload = {
    id: "00000000-0000-4000-8000-000000000301",
    institution_id: "00000000-0000-4000-8000-000000000302",
    student_profile_id: "00000000-0000-4000-8000-000000000303",
    course_id: "00000000-0000-4000-8000-000000000304",
    section_id: "00000000-0000-4000-8000-000000000305",
    target_term_id: "00000000-0000-4000-8000-000000000306",
    mode: "REGISTRATION",
    status: "COMPLETED_WITH_WARNINGS",
    engine_version: "phase-4-course-eligibility-v1",
    overall_result: "PERMISSION_REQUIRED",
    academic_eligibility_result: "PERMISSION_REQUIRED",
    started_at: "2026-06-24T00:00:00Z",
    completed_at: "2026-06-24T00:00:01Z",
    source_snapshot_hash: "hash",
    rule_evaluations: [
      {
        id: "00000000-0000-4000-8000-000000000307",
        eligibility_check_run_id: "00000000-0000-4000-8000-000000000301",
        course_rule_id: "00000000-0000-4000-8000-000000000308",
        result: "PERMISSION_REQUIRED",
        rule_type: "PERMISSION",
        explanation: "Permission rule evaluated as PERMISSION_REQUIRED.",
        display_order: 0,
        expressions: [
          {
            id: "00000000-0000-4000-8000-000000000309",
            rule_evaluation_id: "00000000-0000-4000-8000-000000000307",
            course_rule_expression_id: "00000000-0000-4000-8000-000000000310",
            node_type: "PERMISSION_REQUIRED",
            result: "PERMISSION_REQUIRED",
            actual_value: null,
            expected_value: "DEPARTMENT_APPROVAL",
            matched_course_id: null,
            matched_attempt_id: null,
            reason_code: "PERMISSION_REQUIRED",
            explanation: "Permission is required.",
            created_at: "2026-06-24T00:00:01Z",
          },
        ],
        created_at: "2026-06-24T00:00:01Z",
      },
    ],
    blocking_reasons: [],
    conditional_reasons: [],
    permissions_required: [
      {
        reason_code: "PERMISSION_REQUIRED",
        explanation: "Permission is required.",
        course_rule_id: "00000000-0000-4000-8000-000000000308",
        course_rule_expression_id: "00000000-0000-4000-8000-000000000310",
        referenced_entity_type: null,
        referenced_entity_id: null,
        expected_value: "DEPARTMENT_APPROVAL",
        actual_value: null,
      },
    ],
    manual_review_reasons: [],
    corequisites_to_add: [],
    corequisite_summary: null,
    registration_availability: {
      section_status: "WAITLIST",
      available_seats: 0,
      waitlist_available: 4,
      availability_note: "Section availability is separate.",
    },
    warnings: [
      {
        id: "00000000-0000-4000-8000-000000000311",
        eligibility_check_run_id: "00000000-0000-4000-8000-000000000301",
        rule_evaluation_id: null,
        warning_code: "MOCK_ELIGIBILITY_ESTIMATE",
        severity: "INFO",
        message: "Mock non-official result.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-24T00:00:01Z",
      },
    ],
    created_at: "2026-06-24T00:00:00Z",
    updated_at: "2026-06-24T00:00:01Z",
  };

  it("validates eligibility check snapshots with expression evidence", () => {
    expect(CourseEligibilityCheckSchema.parse(eligibilityPayload)).toMatchObject({
      overall_result: "PERMISSION_REQUIRED",
      registration_availability: { section_status: "WAITLIST" },
    });
  });

  it("rejects malformed course eligibility API payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          ...eligibilityPayload,
          overall_result: "READY_FOR_SCHEDULING",
        }),
      );

    await expect(
      createCourseEligibilityCheck(
        "http://api.test",
        {
          student_profile_id: eligibilityPayload.student_profile_id,
          course_id: eligibilityPayload.course_id,
          section_id: eligibilityPayload.section_id,
          target_term_id: eligibilityPayload.target_term_id,
          mode: "REGISTRATION",
        },
        { fetchFn },
      ),
    ).rejects.toThrow(ApiResponseSchemaError);
  });
});
