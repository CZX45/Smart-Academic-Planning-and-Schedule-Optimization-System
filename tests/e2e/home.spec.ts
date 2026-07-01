import { expect, test, type Page } from "@playwright/test";

const mockAuditRun = {
  id: "00000000-0000-4000-8000-000000000001",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  program_version_id: "f65bee76-6061-515f-a3df-cdf5567514af",
  status: "COMPLETED_WITH_WARNINGS",
  engine_version: "phase-3a-degree-audit-v1",
  calculation_mode: "PROJECTED",
  started_at: "2026-06-23T00:00:00Z",
  completed_at: "2026-06-23T00:00:01Z",
  total_required_credits: "120.0",
  completed_credits: "18.0",
  in_progress_credits: "3.0",
  planned_credits: "3.0",
  remaining_credits: "96.0",
  completion_percentage: "20.00",
  source_snapshot_hash: "e2e-fixture",
  created_at: "2026-06-23T00:00:00Z",
  updated_at: "2026-06-23T00:00:01Z",
};

const mockRequirements = [
  {
    id: "00000000-0000-4000-8000-000000000011",
    degree_audit_run_id: mockAuditRun.id,
    requirement_node_id: "00000000-0000-4000-8000-000000000012",
    requirement_code: "MOCK-REQ",
    requirement_name: "Mock Finance Foundations",
    requirement_type: "REQUIRED_COURSE",
    status: "SATISFIED",
    required_credits: "3.0",
    satisfied_credits: "3.0",
    remaining_credits: "0.0",
    required_courses: 1,
    satisfied_courses: 1,
    remaining_courses: 0,
    minimum_grade: "C",
    explanation: "Completed by mock coursework.",
    display_order: 10,
    applications: [
      {
        id: "00000000-0000-4000-8000-000000000013",
        course_id: "00000000-0000-4000-8000-000000000014",
        course_code: "FIN 301",
        course_title: "Mock Finance Foundations",
        student_course_attempt_id: "00000000-0000-4000-8000-000000000015",
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
    warnings: [
      {
        id: "00000000-0000-4000-8000-000000000016",
        degree_audit_run_id: mockAuditRun.id,
        requirement_evaluation_id: "00000000-0000-4000-8000-000000000011",
        warning_code: "PENDING_TRANSFER",
        severity: "WARNING",
        message: "Pending transfer credit is not applied.",
        requires_advisor_confirmation: true,
        created_at: "2026-06-23T00:00:00Z",
      },
    ],
  },
];

const mockScenario = {
  id: "00000000-0000-4000-8000-000000000101",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  name: "Add Accounting Minor",
  scenario_type: "ADD_MINOR",
  status: "COMPLETED_WITH_WARNINGS",
  base_program_version_id: "f65bee76-6061-515f-a3df-cdf5567514af",
  engine_version: "phase-3b-academic-scenario-v1",
  created_at: "2026-06-23T00:00:00Z",
  updated_at: "2026-06-23T00:00:01Z",
  completed_at: "2026-06-23T00:00:01Z",
};

const mockScenarioPrograms = [
  {
    id: "00000000-0000-4000-8000-000000000111",
    academic_plan_scenario_id: mockScenario.id,
    program_version_id: "f65bee76-6061-515f-a3df-cdf5567514af",
    relationship_type: "PRIMARY_MAJOR",
    is_existing_program: true,
    is_hypothetical: false,
    priority: 0,
    program_code: "BSFIN",
    program_name: "Mock BS Finance",
    source: { source_type: "MOCK", is_official: false },
    created_at: "2026-06-23T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000112",
    academic_plan_scenario_id: mockScenario.id,
    program_version_id: "00000000-0000-4000-8000-000000000113",
    relationship_type: "MINOR",
    is_existing_program: false,
    is_hypothetical: true,
    priority: 10,
    program_code: "MINACCT",
    program_name: "Mock Accounting Minor",
    source: { source_type: "MOCK", is_official: false },
    created_at: "2026-06-23T00:00:00Z",
  },
];

const mockScenarioAudits = [
  { scenario_program: mockScenarioPrograms[0], degree_audit_run: mockAuditRun },
  {
    scenario_program: mockScenarioPrograms[1],
    degree_audit_run: {
      ...mockAuditRun,
      id: "00000000-0000-4000-8000-000000000114",
      program_version_id: mockScenarioPrograms[1].program_version_id,
      remaining_credits: "9.0",
    },
  },
];

const mockScenarioAllocations = [
  {
    id: "00000000-0000-4000-8000-000000000121",
    academic_plan_scenario_id: mockScenario.id,
    student_course_attempt_id: "00000000-0000-4000-8000-000000000122",
    transfer_credit_id: null,
    course_id: "00000000-0000-4000-8000-000000000123",
    course_code: "ACCT 300",
    course_title: "Mock Accounting Analytics",
    program_version_id: mockScenarioPrograms[1].program_version_id,
    requirement_node_id: "00000000-0000-4000-8000-000000000124",
    requirement_code: "ACCT-MINOR-CORE",
    allocation_type: "SHARED",
    credit_amount: "3.0",
    is_shared: true,
    is_unique_to_program: false,
    allocation_rank: 1,
    reason_code: "SHARED_BY_RULE",
    explanation:
      "Shared because both requirements and the mock rule allow overlap.",
    created_at: "2026-06-23T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000125",
    academic_plan_scenario_id: mockScenario.id,
    student_course_attempt_id: "00000000-0000-4000-8000-000000000126",
    transfer_credit_id: null,
    course_id: "00000000-0000-4000-8000-000000000127",
    course_code: "ECON 250",
    course_title: "Mock Managerial Economics",
    program_version_id: mockScenarioPrograms[1].program_version_id,
    requirement_node_id: "00000000-0000-4000-8000-000000000128",
    requirement_code: "ACCT-MINOR-UNIQUE",
    allocation_type: "UNIQUE_SECONDARY",
    credit_amount: "3.0",
    is_shared: false,
    is_unique_to_program: true,
    allocation_rank: 2,
    reason_code: "UNIQUE_SECONDARY_CREDIT",
    explanation: "Counts only toward the secondary program.",
    created_at: "2026-06-23T00:00:00Z",
  },
];

const mockScenarioWarnings = [
  {
    id: "00000000-0000-4000-8000-000000000131",
    academic_plan_scenario_id: mockScenario.id,
    scenario_program_id: mockScenarioPrograms[1].id,
    warning_code: "ESTIMATED_ADDITIONAL_CREDITS",
    severity: "WARNING",
    message:
      "Additional credits are an estimate and do not predict graduation timing.",
    requires_advisor_confirmation: true,
    created_at: "2026-06-23T00:00:00Z",
  },
];

const mockScenarioComparison = {
  academic_plan_scenario_id: mockScenario.id,
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
};

const mockEligibilityCheck = {
  id: "00000000-0000-4000-8000-000000000301",
  institution_id: "00000000-0000-4000-8000-000000000302",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  course_id: "b59bb40b-e3d0-57e3-a424-0d9b8bd2f305",
  section_id: "404cdd60-5eb4-5128-8ae3-ecbe6430f6d1",
  target_term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
  mode: "REGISTRATION",
  status: "COMPLETED_WITH_WARNINGS",
  engine_version: "phase-4-course-eligibility-v1",
  overall_result: "PERMISSION_REQUIRED",
  academic_eligibility_result: "PERMISSION_REQUIRED",
  started_at: "2026-06-24T00:00:00Z",
  completed_at: "2026-06-24T00:00:01Z",
  source_snapshot_hash: "e2e-eligibility-fixture",
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
          explanation:
            "Permission is required before registration eligibility can be confirmed.",
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
      explanation:
        "Permission is required before registration eligibility can be confirmed.",
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
    availability_note:
      "Section availability is reported separately from academic eligibility.",
  },
  warnings: [
    {
      id: "00000000-0000-4000-8000-000000000311",
      eligibility_check_run_id: "00000000-0000-4000-8000-000000000301",
      rule_evaluation_id: null,
      warning_code: "MOCK_ELIGIBILITY_ESTIMATE",
      severity: "INFO",
      message: "This eligibility result uses mock non-official rules.",
      requires_advisor_confirmation: true,
      created_at: "2026-06-24T00:00:01Z",
    },
  ],
  created_at: "2026-06-24T00:00:00Z",
  updated_at: "2026-06-24T00:00:01Z",
};

const mockAcademicPlan = {
  id: "00000000-0000-4000-8000-000000000401",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  program_version_id: "f65bee76-6061-515f-a3df-cdf5567514af",
  academic_plan_scenario_id: null,
  planning_mode: "CURRENT_PROGRAM",
  status: "COMPLETED_WITH_WARNINGS",
  engine_version: "phase-5a-academic-planner-v1",
  start_term_id: "f0f8e29f-d65a-568c-b2aa-22ca4e5dcaec",
  target_completion_term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
  minimum_credits_per_term: "3.0",
  maximum_credits_per_term: "9.0",
  preferred_credits_per_term: "6.0",
  completed_at: "2026-06-29T00:00:01Z",
  created_at: "2026-06-29T00:00:00Z",
  updated_at: "2026-06-29T00:00:01Z",
  terms: [
    {
      id: "00000000-0000-4000-8000-000000000402",
      academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
      term_id: "f0f8e29f-d65a-568c-b2aa-22ca4e5dcaec",
      term_code: "2024FA",
      sequence_index: 0,
      planned_credits: "3.0",
      status: "PLANNED",
      explanation: "Term is planned with mock remaining coursework.",
      created_at: "2026-06-29T00:00:00Z",
    },
    {
      id: "00000000-0000-4000-8000-000000000403",
      academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
      term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
      term_code: "2025SP",
      sequence_index: 1,
      planned_credits: "6.0",
      status: "PLANNED",
      explanation: "Term is planned with a prerequisite unlock.",
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  planned_courses: [
    {
      id: "00000000-0000-4000-8000-000000000404",
      academic_plan_term_id: "00000000-0000-4000-8000-000000000402",
      term_id: "f0f8e29f-d65a-568c-b2aa-22ca4e5dcaec",
      term_code: "2024FA",
      course_id: "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
      course_code: "FIN 300",
      course_title: "Mock Corporate Finance",
      requirement_node_id: "00000000-0000-4000-8000-000000000501",
      requirement_code: "FIN-PREREQ",
      source: "PREREQUISITE_UNLOCK",
      priority_rank: 0,
      credits: "3.0",
      eligibility_result: "ELIGIBLE",
      planning_status: "PLANNED",
      reason_code: "PREREQUISITE_PLANNED_EARLIER",
      explanation:
        "Placed before FIN 400 so the later course can become eligible.",
      created_at: "2026-06-29T00:00:00Z",
    },
    {
      id: "00000000-0000-4000-8000-000000000405",
      academic_plan_term_id: "00000000-0000-4000-8000-000000000403",
      term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
      term_code: "2025SP",
      course_id: "b59bb40b-e3d0-57e3-a424-0d9b8bd2f305",
      course_code: "FIN 400",
      course_title: "Mock Advanced Finance",
      requirement_node_id: "00000000-0000-4000-8000-000000000502",
      requirement_code: "FIN-CAPSTONE",
      source: "DEGREE_AUDIT_REMAINING",
      priority_rank: 1,
      credits: "3.0",
      eligibility_result: "CONDITIONALLY_ELIGIBLE",
      planning_status: "CONDITIONALLY_PLANNED",
      reason_code: "REQUIREMENT_REMAINING",
      explanation:
        "Placed for a remaining requirement after prerequisite planning.",
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  requirement_coverage: [
    {
      id: "00000000-0000-4000-8000-000000000406",
      academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
      academic_plan_course_id: "00000000-0000-4000-8000-000000000405",
      requirement_node_id: "00000000-0000-4000-8000-000000000502",
      requirement_code: "FIN-CAPSTONE",
      coverage_type: "DIRECT_REQUIREMENT",
      credits: "3.0",
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  warnings: [
    {
      id: "00000000-0000-4000-8000-000000000407",
      academic_plan_run_id: "00000000-0000-4000-8000-000000000401",
      academic_plan_term_id: null,
      academic_plan_course_id: null,
      warning_code: "MOCK_PLAN_NOT_OFFICIAL",
      severity: "INFO",
      message: "This plan uses mock non-official catalog and section data.",
      requires_advisor_confirmation: true,
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
};

const mockAcademicPlanComparison = {
  academic_plan_run_id: mockAcademicPlan.id,
  status: "COMPLETED_WITH_WARNINGS",
  total_planned_credits: "9.0",
  term_count: 2,
  planned_course_count: 2,
  warning_count: 1,
  completed_at: "2026-06-29T00:00:01Z",
};

const mockScheduleOptimization = {
  id: "00000000-0000-4000-8000-000000000601",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  term_id: "f0f8e29f-d65a-568c-b2aa-22ca4e5dcaec",
  academic_plan_run_id: null,
  planning_mode: "CUSTOM_COURSE_SET",
  status: "COMPLETED_WITH_WARNINGS",
  engine_version: "phase-6b-schedule-optimizer-v1",
  minimum_credits: "3.0",
  maximum_credits: "6.0",
  preferred_credits: "6.0",
  requested_option_count: 3,
  completed_at: "2026-06-29T00:00:01Z",
  created_at: "2026-06-29T00:00:00Z",
  updated_at: "2026-06-29T00:00:01Z",
  constraint_set: {
    id: "00000000-0000-4000-8000-000000000602",
    schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
    excluded_days: ["FRIDAY"],
    unavailable_time_blocks: [
      { day_of_week: "TUESDAY", start_time: "11:00", end_time: "11:30" },
    ],
    earliest_start_time: "08:00",
    latest_end_time: "18:00",
    minimum_gap_minutes: null,
    maximum_gap_minutes: null,
    candidate_course_ids: [
      "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
      "9413e6c7-26a0-5acf-9de4-88b132dc802d",
    ],
    allowed_modalities: [],
    excluded_modalities: [],
    required_course_ids: [],
    excluded_course_ids: [],
    required_section_ids: [],
    excluded_section_ids: [],
    prefer_online: false,
    prefer_compact_schedule: true,
    prefer_fewer_days: true,
    prefer_in_person: true,
    avoid_early_start: false,
    avoid_late_end: true,
    allow_permission_required: false,
    preference_weights: { priority: "2.0", gap: "1.5" },
    course_priority_weights: {
      "9413e6c7-26a0-5acf-9de4-88b132dc802d": "2.0",
    },
    section_priority_weights: {
      "b4af4050-6534-5112-8351-c572d43bec95": "5.0",
    },
    prefer_no_gaps: true,
    prefer_morning: true,
    prefer_afternoon: false,
    diversity_mode: "HIGH",
    allow_partial_options: true,
    max_combinations: 500,
    created_at: "2026-06-29T00:00:00Z",
  },
  options: [
    {
      id: "00000000-0000-4000-8000-000000000603",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
      option_rank: 1,
      status: "FEASIBLE_WITH_WARNINGS",
      total_credits: "6.0",
      class_days_count: 2,
      earliest_start_time: "09:00",
      latest_end_time: "12:15",
      total_gap_minutes: 45,
      score: "88.00",
      total_score: "88.00",
      credit_score: "30.00",
      compactness_score: "17.00",
      days_score: "12.00",
      gap_score: "10.50",
      modality_score: "8.00",
      time_preference_score: "3.00",
      priority_score: "20.00",
      penalty_score: "-5.00",
      score_explanation: [
        {
          reason_code: "SECTION_PRIORITY_WEIGHT",
          score: "20.00",
          explanation: "FIN 403 002 has a section priority weight.",
        },
      ],
      score_breakdown: {
        total_score: "88.00",
        credit_score: "30.00",
        compactness_score: "17.00",
        days_score: "12.00",
        gap_score: "10.50",
        modality_score: "8.00",
        time_preference_score: "3.00",
        priority_score: "20.00",
        penalty_score: "-5.00",
        score_explanation: [
          {
            reason_code: "SECTION_PRIORITY_WEIGHT",
            score: "20.00",
            explanation: "FIN 403 002 has a section priority weight.",
          },
        ],
      },
      diversity_rank: 1,
      difference_summary: "Top ranked option.",
      shared_section_count_with_previous_option: 0,
      explanation:
        "Selected deterministic mock sections after applying constraints.",
      selected_sections: [
        {
          id: "00000000-0000-4000-8000-000000000604",
          schedule_option_id: "00000000-0000-4000-8000-000000000603",
          section_id: "c080de5c-b981-54b9-b699-cde089ecce4c",
          course_id: "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
          course_code: "FIN 300",
          course_title: "Mock Managerial Finance",
          section_code: "001",
          section_status: "OPEN",
          modality: "IN_PERSON",
          credits: "3.0",
          eligibility_result: "ELIGIBLE",
          selection_reason: "MANUAL_CANDIDATE",
          meetings: [
            {
              id: "00000000-0000-4000-8000-000000000605",
              section_id: "c080de5c-b981-54b9-b699-cde089ecce4c",
              meeting_type: "LECTURE",
              day_of_week: "MONDAY",
              start_time: "09:00",
              end_time: "10:15",
              start_date: "2024-08-26",
              end_date: "2024-12-13",
              building: "Mock Academic Building",
              room: "101",
              timezone: "America/New_York",
              is_arranged: false,
              is_online: false,
              display_order: 10,
            },
          ],
          created_at: "2026-06-29T00:00:00Z",
        },
        {
          id: "00000000-0000-4000-8000-000000000606",
          schedule_option_id: "00000000-0000-4000-8000-000000000603",
          section_id: "b4af4050-6534-5112-8351-c572d43bec95",
          course_id: "9413e6c7-26a0-5acf-9de4-88b132dc802d",
          course_code: "FIN 403",
          course_title: "Mock International Finance",
          section_code: "002",
          section_status: "OPEN",
          modality: "IN_PERSON",
          credits: "3.0",
          eligibility_result: "ELIGIBLE",
          selection_reason: "MANUAL_CANDIDATE",
          meetings: [
            {
              id: "00000000-0000-4000-8000-000000000607",
              section_id: "b4af4050-6534-5112-8351-c572d43bec95",
              meeting_type: "LECTURE",
              day_of_week: "TUESDAY",
              start_time: "11:00",
              end_time: "12:15",
              start_date: "2024-08-26",
              end_date: "2024-12-13",
              building: "Mock Academic Building",
              room: "204",
              timezone: "America/New_York",
              is_arranged: false,
              is_online: false,
              display_order: 10,
            },
          ],
          created_at: "2026-06-29T00:00:00Z",
        },
      ],
      created_at: "2026-06-29T00:00:00Z",
    },
    {
      id: "00000000-0000-4000-8000-000000000611",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
      option_rank: 2,
      status: "FEASIBLE_WITH_WARNINGS",
      total_credits: "6.0",
      class_days_count: 1,
      earliest_start_time: "15:00",
      latest_end_time: "16:15",
      total_gap_minutes: 0,
      score: "74.00",
      total_score: "74.00",
      credit_score: "30.00",
      compactness_score: "20.00",
      days_score: "15.00",
      gap_score: "15.00",
      modality_score: "6.00",
      time_preference_score: "0.00",
      priority_score: "0.00",
      penalty_score: "0.00",
      score_explanation: [
        {
          reason_code: "NO_GAPS",
          score: "15.00",
          explanation: "No fixed meeting gaps.",
        },
      ],
      score_breakdown: {
        total_score: "74.00",
        credit_score: "30.00",
        compactness_score: "20.00",
        days_score: "15.00",
        gap_score: "15.00",
        modality_score: "6.00",
        time_preference_score: "0.00",
        priority_score: "0.00",
        penalty_score: "0.00",
        score_explanation: [
          {
            reason_code: "NO_GAPS",
            score: "15.00",
            explanation: "No fixed meeting gaps.",
          },
        ],
      },
      diversity_rank: 2,
      difference_summary: "uses FIN 403 section ONL instead of 002",
      shared_section_count_with_previous_option: 1,
      explanation:
        "Alternative keeps the same course set with a different modality.",
      selected_sections: [
        {
          id: "00000000-0000-4000-8000-000000000612",
          schedule_option_id: "00000000-0000-4000-8000-000000000611",
          section_id: "3c836aa0-a147-5702-90c1-5a192554862c",
          course_id: "9413e6c7-26a0-5acf-9de4-88b132dc802d",
          course_code: "FIN 403",
          course_title: "Mock International Finance",
          section_code: "ONL",
          section_status: "OPEN",
          modality: "ONLINE_SYNCHRONOUS",
          credits: "3.0",
          eligibility_result: "ELIGIBLE",
          selection_reason: "SECTION_SATISFIES_HARD_CONSTRAINTS",
          meetings: [
            {
              id: "00000000-0000-4000-8000-000000000613",
              section_id: "3c836aa0-a147-5702-90c1-5a192554862c",
              meeting_type: "LECTURE",
              day_of_week: "WEDNESDAY",
              start_time: "15:00",
              end_time: "16:15",
              start_date: "2024-08-26",
              end_date: "2024-12-13",
              building: null,
              room: null,
              timezone: "America/New_York",
              is_arranged: false,
              is_online: true,
              display_order: 10,
            },
          ],
          created_at: "2026-06-29T00:00:00Z",
        },
      ],
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  conflicts: [
    {
      id: "00000000-0000-4000-8000-000000000608",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
      schedule_option_id: null,
      conflict_type: "TIME_OVERLAP",
      section_id: "c080de5c-b981-54b9-b699-cde089ecce4c",
      other_section_id: "96822dc7-d1c1-5f4c-93c4-bf6afddb981f",
      day_of_week: "MONDAY",
      start_time: "09:30",
      end_time: "10:15",
      message: "FIN 300 001 overlaps with FIN 403 001 in mock section data.",
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  warnings: [
    {
      id: "00000000-0000-4000-8000-000000000609",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
      schedule_option_id: null,
      warning_code: "MOCK_SECTION_DATA_NOT_OFFICIAL",
      severity: "INFO",
      message: "This schedule uses mock non-official section data.",
      requires_advisor_confirmation: true,
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  repair_suggestions: [
    {
      id: "00000000-0000-4000-8000-000000000614",
      schedule_optimization_run_id: "00000000-0000-4000-8000-000000000601",
      suggestion_type: "RELAX_UNAVAILABLE_BLOCK",
      affected_constraint: "unavailable_time_blocks",
      affected_course_id: null,
      affected_section_id: "b4af4050-6534-5112-8351-c572d43bec95",
      estimated_impact: "Could make a blocked section selectable.",
      message: "Relax the unavailable time block.",
      requires_advisor_confirmation: false,
      created_at: "2026-06-29T00:00:00Z",
    },
  ],
  hard_constraint_results: [
    { constraint: "excluded_days", result: "APPLIED", value: ["FRIDAY"] },
  ],
  soft_preference_results: [{ preference: "prefer_no_gaps", value: true }],
};

const mockScheduleRunSummary = {
  id: mockScheduleOptimization.id,
  student_profile_id: mockScheduleOptimization.student_profile_id,
  term_id: mockScheduleOptimization.term_id,
  academic_plan_run_id: mockScheduleOptimization.academic_plan_run_id,
  planning_mode: mockScheduleOptimization.planning_mode,
  status: mockScheduleOptimization.status,
  engine_version: mockScheduleOptimization.engine_version,
  minimum_credits: mockScheduleOptimization.minimum_credits,
  maximum_credits: mockScheduleOptimization.maximum_credits,
  preferred_credits: mockScheduleOptimization.preferred_credits,
  requested_option_count: mockScheduleOptimization.requested_option_count,
  completed_at: mockScheduleOptimization.completed_at,
  created_at: mockScheduleOptimization.created_at,
  updated_at: mockScheduleOptimization.updated_at,
};

const mockDataImportRun = {
  id: "00000000-0000-4000-8000-000000000701",
  student_profile_id: "74874476-4024-5e2d-807a-fbb4ab620249",
  import_type: "UNOFFICIAL_TRANSCRIPT",
  status: "PARSED_WITH_WARNINGS",
  storage_strategy: "METADATA_ONLY",
  file_name: "mock-transcript.csv",
  file_mime_type: "text/csv",
  file_size_bytes: 148,
  file_sha256:
    "7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a7a",
  parser_version: "phase7a-data-import-v1",
  record_count: 2,
  valid_record_count: 1,
  warning_count: 2,
  error_count: 0,
  official_application_ready: false,
  started_at: "2026-06-30T00:00:00Z",
  completed_at: "2026-06-30T00:00:01Z",
  source: { source_type: "STUDENT_PROVIDED", is_official: false },
  created_at: "2026-06-30T00:00:00Z",
  updated_at: "2026-06-30T00:00:01Z",
};

const mockDataImportRecords = [
  {
    id: "00000000-0000-4000-8000-000000000702",
    data_import_run_id: mockDataImportRun.id,
    record_type: "COURSE_ATTEMPT",
    row_number: 2,
    status: "VALID_WITH_WARNINGS",
    external_identifier: "FIN 300",
    raw_label: "FIN 300 Mock Managerial Finance",
    normalized_payload: {
      term: "2024FA",
      course_code: "FIN 300",
      title: "Mock Managerial Finance",
      grade: "B",
      credits: "3.0",
      status: "COMPLETED",
    },
    confidence_score: "0.80",
    created_at: "2026-06-30T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000703",
    data_import_run_id: mockDataImportRun.id,
    record_type: "COURSE_ATTEMPT",
    row_number: 3,
    status: "AMBIGUOUS",
    external_identifier: "FIN 999",
    raw_label: "FIN 999 Unreviewed Special Topic",
    normalized_payload: {
      term: "2024FA",
      course_code: "FIN 999",
      title: "Unreviewed Special Topic",
      grade: "A",
      credits: "3.0",
      status: "COMPLETED",
    },
    confidence_score: "0.35",
    created_at: "2026-06-30T00:00:00Z",
  },
];

const mockDataImportCandidates = [
  {
    id: "00000000-0000-4000-8000-000000000704",
    imported_record_id: mockDataImportRecords[0].id,
    target_entity_type: "COURSE",
    target_entity_id: "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
    match_type: "EXACT_CODE",
    confidence_score: "1.00",
    is_selected: true,
    reason_code: "EXACT_COURSE_CODE",
    explanation: "FIN 300 exactly matches mock catalog course FIN 300.",
    created_at: "2026-06-30T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000705",
    imported_record_id: mockDataImportRecords[1].id,
    target_entity_type: "UNKNOWN",
    target_entity_id: null,
    match_type: "NO_MATCH",
    confidence_score: "0.00",
    is_selected: false,
    reason_code: "UNMATCHED_COURSE_CODE",
    explanation: "FIN 999 requires manual review before academic use.",
    created_at: "2026-06-30T00:00:00Z",
  },
];

const mockDataImportWarnings = [
  {
    id: "00000000-0000-4000-8000-000000000706",
    data_import_run_id: mockDataImportRun.id,
    imported_record_id: null,
    warning_code: "STAGING_ONLY_NOT_OFFICIAL",
    severity: "WARNING",
    message: "Phase 7A imports are preview-only staging records.",
    requires_advisor_confirmation: true,
    created_at: "2026-06-30T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000707",
    data_import_run_id: mockDataImportRun.id,
    imported_record_id: mockDataImportRecords[1].id,
    warning_code: "UNMATCHED_COURSE_CODE",
    severity: "WARNING",
    message: "FIN 999 is staged but not matched to a reviewed course.",
    requires_advisor_confirmation: true,
    created_at: "2026-06-30T00:00:00Z",
  },
];

const mockDataImportPreview = {
  id: "00000000-0000-4000-8000-000000000708",
  data_import_run_id: mockDataImportRun.id,
  record_count: 2,
  valid_record_count: 1,
  warning_count: 2,
  error_count: 0,
  official_application_ready: false,
  disclaimers: [
    "This import preview is staging-only and is not official school policy.",
    "Phase 7A does not change official transcript, catalog, section, registration, seat, or waitlist records.",
  ],
  summary_payload: { staging_only: true },
  created_at: "2026-06-30T00:00:00Z",
};

const mockDataImportReview = {
  id: "00000000-0000-4000-8000-000000000731",
  data_import_run_id: mockDataImportRun.id,
  student_profile_id: mockDataImportRun.student_profile_id,
  status: "IN_REVIEW",
  reviewer_label: "Mock student self-review",
  started_at: "2026-06-30T00:00:00Z",
  completed_at: null,
  created_at: "2026-06-30T00:00:00Z",
  updated_at: "2026-06-30T00:00:00Z",
};

const mockImportedRecordReviews = [
  {
    id: "00000000-0000-4000-8000-000000000732",
    review_session_id: mockDataImportReview.id,
    imported_record_id: mockDataImportRecords[0].id,
    selected_mapping_candidate_id: mockDataImportCandidates[0].id,
    decision: "UNREVIEWED",
    edited_normalized_payload: null,
    review_note: null,
    requires_advisor_confirmation: false,
    imported_record: mockDataImportRecords[0],
    selected_mapping_candidate: mockDataImportCandidates[0],
    created_at: "2026-06-30T00:00:00Z",
    updated_at: "2026-06-30T00:00:00Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000733",
    review_session_id: mockDataImportReview.id,
    imported_record_id: mockDataImportRecords[1].id,
    selected_mapping_candidate_id: mockDataImportCandidates[1].id,
    decision: "UNREVIEWED",
    edited_normalized_payload: null,
    review_note: null,
    requires_advisor_confirmation: true,
    imported_record: mockDataImportRecords[1],
    selected_mapping_candidate: mockDataImportCandidates[1],
    created_at: "2026-06-30T00:00:00Z",
    updated_at: "2026-06-30T00:00:00Z",
  },
];

const mockDataReviewWarnings = [
  {
    id: "00000000-0000-4000-8000-000000000734",
    review_session_id: mockDataImportReview.id,
    imported_record_review_id: null,
    data_application_run_id: null,
    warning_code: "STAGING_ONLY_NOT_OFFICIAL",
    severity: "WARNING",
    message: "Review remains unofficial until advisor or school confirmation.",
    requires_advisor_confirmation: true,
    created_at: "2026-06-30T00:00:00Z",
  },
];

const mockDataApplicationRun = {
  id: "00000000-0000-4000-8000-000000000735",
  review_session_id: mockDataImportReview.id,
  status: "APPLIED_WITH_WARNINGS",
  applied_count: 1,
  skipped_count: 1,
  warning_count: 1,
  error_count: 0,
  started_at: "2026-06-30T00:00:02Z",
  completed_at: "2026-06-30T00:00:03Z",
  created_at: "2026-06-30T00:00:02Z",
  updated_at: "2026-06-30T00:00:03Z",
};

function mockApplicationResult(dryRun: boolean) {
  return {
    review_session: {
      ...mockDataImportReview,
      status: dryRun ? "IN_REVIEW" : "APPLIED_WITH_WARNINGS",
      completed_at: dryRun ? null : "2026-06-30T00:00:03Z",
    },
    dry_run: dryRun,
    application: dryRun ? null : mockDataApplicationRun,
    applied_records: [
      {
        id: dryRun ? null : "00000000-0000-4000-8000-000000000736",
        data_application_run_id: dryRun ? null : mockDataApplicationRun.id,
        imported_record_review_id: mockImportedRecordReviews[0].id,
        imported_record_id: mockDataImportRecords[0].id,
        target_entity_type: "STUDENT_COURSE_ATTEMPT",
        target_entity_id: dryRun
          ? null
          : "00000000-0000-4000-8000-000000000737",
        action: "CREATED",
        status: "SUCCESS",
        reason_code: dryRun
          ? "WOULD_CREATE_STUDENT_COURSE_ATTEMPT"
          : "CREATED_STUDENT_COURSE_ATTEMPT",
        message: dryRun
          ? "Dry run would create an internal student course attempt."
          : "Created an internal student course attempt from a confirmed imported record.",
        created_at: dryRun ? null : "2026-06-30T00:00:03Z",
      },
      {
        id: dryRun ? null : "00000000-0000-4000-8000-000000000738",
        data_application_run_id: dryRun ? null : mockDataApplicationRun.id,
        imported_record_review_id: mockImportedRecordReviews[1].id,
        imported_record_id: mockDataImportRecords[1].id,
        target_entity_type: "UNKNOWN",
        target_entity_id: null,
        action: "SKIPPED_ADVISOR_REVIEW",
        status: "SKIPPED",
        reason_code: "ADVISOR_REVIEW_REQUIRED",
        message: "Imported record requires advisor review before it can be applied.",
        created_at: dryRun ? null : "2026-06-30T00:00:03Z",
      },
    ],
    warnings: mockDataReviewWarnings,
  };
}

async function mockSuccessfulAuditApis(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/students/*/degree-audits/latest",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockAuditRun),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/degree-audits/*/requirements",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockRequirements),
      });
    },
  );
}

async function mockSuccessfulScenarioApis(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockScenario),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/*/programs",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockScenarioPrograms),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/*/audits",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockScenarioAudits),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/*/allocations",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockScenarioAllocations),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/*/warnings",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockScenarioWarnings),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/*/comparison",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockScenarioComparison),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/academic-scenarios",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          mockScenario,
          {
            ...mockScenario,
            id: "00000000-0000-4000-8000-000000000201",
            name: "Add Economics Minor",
          },
        ]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios/compare",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          mockScenarioComparison,
          {
            ...mockScenarioComparison,
            academic_plan_scenario_id: "00000000-0000-4000-8000-000000000201",
            estimated_additional_credits: "15.0",
          },
        ]),
      });
    },
  );
}

async function mockSuccessfulEligibilityApis(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/eligibility-checks",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockEligibilityCheck),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/eligibility-checks",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([mockEligibilityCheck]),
      });
    },
  );
}

async function mockSuccessfulPlannerApis(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/academic-plans",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockAcademicPlan),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/academic-plans",
    async (route) => {
      const summary = {
        ...mockAcademicPlan,
        terms: undefined,
        planned_courses: undefined,
        requirement_coverage: undefined,
        warnings: undefined,
      };
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          summary,
          {
            ...summary,
            id: "00000000-0000-4000-8000-000000000408",
            planning_mode: "WHAT_IF_SCENARIO",
          },
        ]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/academic-plans/compare",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          mockAcademicPlanComparison,
          {
            ...mockAcademicPlanComparison,
            academic_plan_run_id: "00000000-0000-4000-8000-000000000408",
            total_planned_credits: "15.0",
            warning_count: 2,
          },
        ]),
      });
    },
  );
}

async function mockSuccessfulScheduleApis(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/schedule-optimizations",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockScheduleOptimization),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/schedule-optimizations",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          mockScheduleRunSummary,
          {
            ...mockScheduleRunSummary,
            id: "00000000-0000-4000-8000-000000000610",
            requested_option_count: 2,
          },
        ]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/schedule-optimizations/compare",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          {
            schedule_optimization_run_id: mockScheduleOptimization.id,
            status: "COMPLETED_WITH_WARNINGS",
            option_count: 1,
            warning_count: 1,
            best_score: "88.00",
            best_total_credits: "6.0",
            completed_at: "2026-06-29T00:00:01Z",
          },
          {
            schedule_optimization_run_id:
              "00000000-0000-4000-8000-000000000610",
            status: "COMPLETED_WITH_WARNINGS",
            option_count: 2,
            warning_count: 1,
            best_score: "74.00",
            best_total_credits: "3.0",
            completed_at: "2026-06-29T00:00:01Z",
          },
        ]),
      });
    },
  );
}

async function mockSuccessfulDataImportApis(page: Page) {
  let reviewRecords = mockImportedRecordReviews.map((record) => ({
    ...record,
  }));
  let applications = [] as Array<typeof mockDataApplicationRun>;

  await page.route(
    "http://localhost:8000/api/v1/data-imports",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockDataImportRun),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/records",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportRecords),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/mapping-candidates",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportCandidates),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/warnings",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportWarnings),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/preview",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportPreview),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/validate",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportPreview),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-imports",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([
          mockDataImportRun,
          {
            ...mockDataImportRun,
            id: "00000000-0000-4000-8000-000000000709",
            file_name: "saved-degree-audit.json",
            import_type: "DEGREE_AUDIT_EXPORT",
          },
        ]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(mockDataImportReview),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/records/*",
    async (route) => {
      const body = route.request().postDataJSON() as {
        decision?: string;
        edited_normalized_payload?: Record<string, unknown> | null;
        review_note?: string | null;
      };
      const recordReviewId = route.request().url().split("/").at(-1);
      const updatedRecords = reviewRecords.map((record) =>
        record.id === recordReviewId
          ? {
              ...record,
              decision: body.decision ?? record.decision,
              edited_normalized_payload:
                body.edited_normalized_payload ??
                record.edited_normalized_payload,
              review_note: body.review_note ?? record.review_note,
              updated_at: "2026-06-30T00:00:02Z",
            }
          : record,
      );
      reviewRecords = updatedRecords;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(
          reviewRecords.find((record) => record.id === recordReviewId),
        ),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/records",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(reviewRecords),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/warnings",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataReviewWarnings),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/applications",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(applications),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/apply",
    async (route) => {
      const body = route.request().postDataJSON() as { dry_run?: boolean };
      const dryRun = body.dry_run ?? false;
      if (!dryRun) {
        applications = [mockDataApplicationRun];
      }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockApplicationResult(dryRun)),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockDataImportReview),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-applications/*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockApplicationResult(false)),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-import-reviews",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([mockDataImportReview]),
      });
    },
  );
}

test("home page shows degree progress shell and required mock warnings", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Degree Progress/ }),
  ).toBeVisible();
  await expect(page.getByText("API connected")).toBeVisible();
  await expect(
    page.getByText("Mock data — not official university policy.").first(),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Advisor confirmation is required for high-impact academic guidance.",
    ),
  ).toBeVisible();
  await expect(page.getByText("Audit Mode")).toBeVisible();
  await expect(page.getByText("Mock Finance Foundations")).toBeVisible();
  await expect(page.getByText("PENDING_TRANSFER")).toBeVisible();
});

test("home page reports when the API health request is unavailable", async ({
  page,
}) => {
  await page.route("http://localhost:8000/health", async (route) => {
    await route.abort("failed");
  });

  await page.goto("/");

  await expect(page.getByText("API unavailable")).toBeVisible();
  await expect(
    page.locator("section[aria-live='polite'] > p").filter({
      hasText: /Health check request failed|Failed to fetch|NetworkError/,
    }),
  ).toBeVisible();
});

test("home page reports when degree audit responses fail schema validation", async ({
  page,
}) => {
  await page.route(
    "http://localhost:8000/api/v1/students/*/degree-audits/latest",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ unexpected: true }),
      });
    },
  );

  await page.goto("/");

  await expect(page.getByText("Audit unavailable")).toBeVisible();
  await expect(
    page.getByText(/unexpected degree audit response shape/i),
  ).toBeVisible();
});

test("home page creates and compares what-if academic scenarios", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulScenarioApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Explore Programs \/ What-if Analysis/ }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Estimated additional credits do not predict graduation timing.",
    ),
  ).toBeVisible();

  await page.getByLabel("Candidate program").selectOption("accounting-minor");
  await page.getByRole("button", { name: /Create scenario/ }).click();

  const scenarioSummary = page.getByLabel("What-if scenario summary");
  await expect(
    scenarioSummary.getByText("Mock Accounting Minor"),
  ).toBeVisible();
  await expect(scenarioSummary.getByText("Shared Credits")).toBeVisible();
  await expect(
    scenarioSummary.getByText("Unique Secondary Credits"),
  ).toBeVisible();
  await expect(
    scenarioSummary.getByText("Estimated Additional Credits"),
  ).toBeVisible();
  await expect(page.getByText("ACCT 300")).toBeVisible();
  await expect(page.getByText("ESTIMATED_ADDITIONAL_CREDITS")).toBeVisible();

  await page.getByRole("button", { name: /Compare saved scenarios/ }).click();
  await expect(page.getByText("Add Economics Minor")).toBeVisible();
});

test("home page reports what-if API and schema failures", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await page.route(
    "http://localhost:8000/api/v1/academic-scenarios",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ unexpected: true }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: /Create scenario/ }).click();

  await expect(page.getByText("What-if scenario unavailable")).toBeVisible();
  await expect(
    page.getByText(/unexpected academic scenario response shape/i),
  ).toBeVisible();
});

test("home page checks course eligibility without recalculating section seats", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulEligibilityApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Course Eligibility/ }),
  ).toBeVisible();
  await expect(
    page.getByText("Section seats are separate from academic eligibility."),
  ).toBeVisible();

  await page.getByLabel("Course check").selectOption("fin-400-registration");
  await page.getByRole("button", { name: /Check eligibility/ }).click();

  const eligibilitySummary = page.getByLabel("Course eligibility summary");
  await expect(
    eligibilitySummary.getByText(/permission required/i).first(),
  ).toBeVisible();
  await expect(eligibilitySummary.getByText(/waitlist/i)).toBeVisible();
  await expect(eligibilitySummary.getByText("Available Seats")).toBeVisible();
  await expect(page.getByText("PERMISSION_REQUIRED")).toBeVisible();
  await expect(page.getByText("MOCK_ELIGIBILITY_ESTIMATE")).toBeVisible();
});

test("home page reports course eligibility schema failures", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await page.route(
    "http://localhost:8000/api/v1/eligibility-checks",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ unexpected: true }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: /Check eligibility/ }).click();

  await expect(page.getByText("Eligibility schema error")).toBeVisible();
  await expect(
    page.getByText(/unexpected course eligibility response shape/i),
  ).toBeVisible();
});

test("home page creates and compares long-term academic plans", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulPlannerApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Long-Term Academic Planner/ }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Academic planner disclaimers")
      .getByText("Mock data — not official university policy."),
  ).toBeVisible();
  await expect(
    page.getByText("This plan is not registration.").first(),
  ).toBeVisible();
  await expect(
    page.getByText("This plan does not check weekly schedule conflicts."),
  ).toBeVisible();
  await expect(
    page.getByText("Course offering predictions are estimates."),
  ).toBeVisible();
  await expect(
    page.getByText("Advisor confirmation may be required.").first(),
  ).toBeVisible();

  await page.getByLabel("Planning scope").selectOption("current-program");
  await page.getByLabel("Terms").fill("2");
  await page.getByLabel("Min credits").fill("3");
  await page.getByLabel("Preferred credits").fill("6");
  await page.getByLabel("Max credits").fill("9");
  await page.getByRole("button", { name: /Create plan/ }).click();

  const planSummary = page.getByLabel("Academic plan summary");
  await expect(planSummary.getByText(/completed with warnings/i)).toBeVisible();
  await expect(planSummary.getByText("Planned Credits")).toBeVisible();
  await expect(
    page.getByLabel("Term-by-term academic plan").getByText("FIN 400"),
  ).toBeVisible();
  await expect(page.getByText("PREREQUISITE_PLANNED_EARLIER")).toBeVisible();
  await expect(page.getByText("MOCK_PLAN_NOT_OFFICIAL")).toBeVisible();

  await page.getByRole("button", { name: /Compare saved plans/ }).click();
  await expect(page.getByText("WHAT_IF_SCENARIO")).toBeVisible();
});

test("home page reports academic planner schema failures", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await page.route(
    "http://localhost:8000/api/v1/academic-plans",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ unexpected: true }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: /Create plan/ }).click();

  await expect(page.getByText("Academic planner schema error")).toBeVisible();
  await expect(
    page.getByText(/unexpected academic plan response shape/i),
  ).toBeVisible();
});

test("home page builds and compares semester schedules", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulScheduleApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Semester Schedule Builder/ }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Schedule builder disclaimers")
      .getByText("Generated schedules are not registration."),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Schedule builder disclaimers")
      .getByText("Seat availability is separate from academic eligibility."),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Schedule builder disclaimers")
      .getByText("This tool does not perform add/drop or waitlist actions."),
  ).toBeVisible();

  await page.getByLabel("Course set").selectOption("fall-fin-300-403");
  await page.getByLabel("Pinned section").selectOption("fin-403-002");
  await page.getByLabel("Excluded section").selectOption("fin-300-web");
  await page.getByLabel("Diversity").selectOption("HIGH");
  await expect(page.getByLabel("No gaps")).toBeChecked();
  await expect(page.getByLabel("Morning")).toBeChecked();
  await page.getByRole("button", { name: /Build schedule/ }).click();

  const scheduleSummary = page.getByLabel("Schedule optimization summary");
  await expect(
    scheduleSummary.getByText(/completed with warnings/i),
  ).toBeVisible();
  await expect(scheduleSummary.getByText("Best Credits")).toBeVisible();
  await expect(
    page.getByLabel("Schedule options").getByText("FIN 300 001"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Schedule options")
      .getByText("FIN 403 002", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Priority 20.00")).toBeVisible();
  await expect(page.getByText("SECTION_PRIORITY_WEIGHT")).toBeVisible();
  await expect(
    page.getByText("Diversity 2: uses FIN 403 section ONL instead of 002"),
  ).toBeVisible();
  await expect(page.getByLabel("Top schedule option comparison")).toBeVisible();
  await expect(page.getByLabel("Schedule repair suggestions")).toContainText(
    "RELAX UNAVAILABLE BLOCK",
  );
  await expect(page.getByText("TIME_OVERLAP")).toBeVisible();
  await expect(page.getByText("MOCK_SECTION_DATA_NOT_OFFICIAL")).toBeVisible();

  await page.getByRole("button", { name: /Compare saved schedules/ }).click();
  await expect(
    page.getByLabel("Saved schedule comparison").getByText("CUSTOM_COURSE_SET"),
  ).toHaveCount(2);
});

test("home page previews read-only data imports", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulDataImportApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /Data Import Preview/ }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Data import disclaimers")
      .getByText("Imported preview data is not official school policy."),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Data import disclaimers")
      .getByText(
        "No transcript, catalog, section, registration, seat, or waitlist records are changed.",
      ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Browser Extension Import/ }),
  ).toBeVisible();
  await expect(page.getByLabel("Browser extension import status")).toContainText(
    "Experimental",
  );
  await expect(page.getByLabel("Browser extension import status")).toContainText(
    "staging import first",
  );
  await expect(page.getByLabel("Browser extension import status")).toContainText(
    "Phase 7B review is required",
  );
  await expect(page.getByLabel("Browser extension import status")).toContainText(
    "No registration automation",
  );

  await page.getByLabel("Sample import").selectOption("mock-transcript-csv");
  await page.getByRole("button", { name: /Preview import/ }).click();

  const importSummary = page.getByLabel("Data import preview summary");
  await expect(importSummary.getByText(/parsed with warnings/i)).toBeVisible();
  await expect(importSummary.getByText("Mapped Candidates")).toBeVisible();
  await expect(importSummary.getByText("Disabled")).toBeVisible();
  await expect(importSummary.getByText("STUDENT_PROVIDED")).toBeVisible();

  await expect(
    page.getByLabel("Data import records").getByText("FIN 300", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Data import records").getByText("FIN 999", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Data import mapping candidates")
      .getByText("EXACT_COURSE_CODE"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Data import mapping candidates")
      .getByText("UNMATCHED_COURSE_CODE"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Import preview disclaimers")
      .getByText(/not official school policy/i),
  ).toBeVisible();

  await page.getByRole("button", { name: /Load saved imports/ }).click();
  await expect(importSummary.getByText("Saved Imports")).toBeVisible();
});

test("home page reviews and applies confirmed data import records", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulDataImportApis(page);

  await page.goto("/");
  await page.getByLabel("Sample import").selectOption("mock-transcript-csv");
  await page.getByRole("button", { name: /Preview import/ }).click();

  await expect(
    page.getByRole("heading", { name: /Data Review/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Create review$/ }).click();

  const reviewSummary = page.getByLabel("Data review summary");
  await expect(reviewSummary.getByText(/in review/i)).toBeVisible();
  await expect(
    page.getByLabel("Review records").getByText("FIN 300", { exact: true }),
  ).toBeVisible();

  await page
    .getByLabel("Review records")
    .getByRole("button", { name: /^Confirm$/ })
    .first()
    .click();
  await expect(
    page.getByLabel("Review records").getByText(/confirmed/i),
  ).toBeVisible();

  await page.getByRole("button", { name: /^Dry run$/ }).click();
  await expect(
    page
      .getByLabel("Data application result")
      .getByText("WOULD_CREATE_STUDENT_COURSE_ATTEMPT"),
  ).toBeVisible();

  await page.getByRole("button", { name: /^Apply confirmed$/ }).click();
  await expect(
    page
      .getByLabel("Data application result")
      .getByText("CREATED_STUDENT_COURSE_ATTEMPT"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Data application result")
      .getByText("ADVISOR_REVIEW_REQUIRED"),
  ).toBeVisible();
});

test("home page reports schedule optimizer schema failures", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await page.route(
    "http://localhost:8000/api/v1/schedule-optimizations",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ unexpected: true }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: /Build schedule/ }).click();

  await expect(page.getByText("Schedule optimizer schema error")).toBeVisible();
  await expect(
    page.getByText(/unexpected schedule optimization response shape/i),
  ).toBeVisible();
});
