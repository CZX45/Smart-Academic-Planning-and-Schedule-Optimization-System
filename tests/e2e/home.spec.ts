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

const myProgressDataImportRun = {
  ...mockDataImportRun,
  id: "00000000-0000-4000-8000-000000000741",
  import_type: "DEGREE_AUDIT_EXPORT",
  status: "PARSED",
  file_name: "sanitized-kean-myprogress-finance.json",
  file_mime_type: "application/json",
  file_size_bytes: 4096,
  record_count: 87,
  valid_record_count: 86,
  warning_count: 1,
  source: { source_type: "BROWSER_EXTENSION", is_official: false },
};

const myProgressProgramRecord = {
  ...mockDataImportRecords[0],
  id: "00000000-0000-4000-8000-000000000742",
  data_import_run_id: myProgressDataImportRun.id,
  record_type: "PROGRAM",
  row_number: 1,
  status: "VALID",
  external_identifier: "Finance, BS",
  raw_label: "Finance, BS",
  normalized_payload: {
    source_page_type: "KEAN_MY_PROGRESS_PAGE",
    record_kind: "MY_PROGRESS_PROGRAM_SUMMARY",
    requiresReview: false,
  },
  confidence_score: "0.98",
};

const myProgressRequirementRecord = {
  ...mockDataImportRecords[1],
  id: "00000000-0000-4000-8000-000000000743",
  data_import_run_id: myProgressDataImportRun.id,
  record_type: "REQUIREMENT",
  row_number: 2,
  status: "VALID",
  external_identifier: "GE Foundation Requirements 13 S.H.",
  raw_label: "GE Foundation Requirements 13 S.H.",
  normalized_payload: {
    source_page_type: "KEAN_MY_PROGRESS_PAGE",
    record_kind: "MY_PROGRESS_REQUIREMENT_GROUP",
    requiresReview: false,
    requirementGroup: {
      name: "GE Foundation Requirements 13 S.H.",
      statusText: "4 of 5 Completed",
      confidence: "high",
    },
  },
  confidence_score: "0.95",
};

const myProgressSeedCourseRows = [
  {
    course_code: "MATH 1044",
    course_title: "Precalculus for Business",
    status: "NOT_STARTED",
    term: null,
    requirement_group_context: "Quantitative Requirements",
    raw_row_text: "MATH 1044 Precalculus for Business Not Started",
  },
  {
    course_code: "MATH 1054",
    course_title: "Pre-Calculus",
    status: "NOT_STARTED",
    term: null,
    requirement_group_context: "Quantitative Requirements",
    raw_row_text: "MATH 1054 Pre-Calculus Not Started",
  },
  {
    course_code: "ENG 2403",
    course_title: "World Literature",
    status: "PLANNED",
    term: "2026SUW",
    requirement_group_context: "Major Requirements",
    raw_row_text: "ENG 2403 World Literature Planned 2026SUW",
  },
  {
    course_code: "GE 1855",
    course_title: "First Year Seminar",
    status: "NOT_STARTED",
    term: null,
    requirement_group_context: "GE Foundation Requirements 13 S.H.",
    raw_row_text: "GE 1855 First Year Seminar Not Started",
  },
  {
    course_code: "AH 1700",
    course_title: "History of Art",
    status: "COMPLETED",
    term: "2025SP",
    requirement_group_context: "GE Disciplinary Distribution",
    raw_row_text: "AH 1700 History of Art Completed 2025SP",
  },
  {
    course_code: "AH 1701",
    course_title: "World Art",
    status: "IN_PROGRESS",
    term: "2025FA",
    requirement_group_context: "GE Disciplinary Distribution",
    raw_row_text: "AH 1701 World Art In Progress 2025FA",
  },
];

const myProgressGeneratedCourseRows = Array.from({ length: 78 }, (_, index) => {
  const courseNumber = String(2000 + index).padStart(4, "0");
  return {
    course_code: `FIN ${courseNumber}`,
    course_title: `Finance Requirement Row ${index + 1}`,
    status:
      index % 3 === 0
        ? "COMPLETED"
        : index % 3 === 1
          ? "IN_PROGRESS"
          : "PLANNED",
    term: index % 3 === 2 ? "2026SP" : index % 3 === 1 ? "2025FA" : "2024FA",
    requirement_group_context: "Finance Major Requirements",
    raw_row_text: `FIN ${courseNumber} Finance Requirement Row ${index + 1}`,
  };
});

const myProgressExceptionCourseRow = {
  course_code: "",
  course_title: "Unparsed elective row",
  status: "UNKNOWN_STATUS",
  term: null,
  requirement_group_context: "Electives",
  raw_row_text: "Elective row with missing course code",
  requires_review: true,
  reason_codes: ["MISSING_COURSE_CODE", "UNKNOWN_STATUS"],
  warnings: ["Row requires review before downstream use."],
};

const myProgressCourseRows = [
  ...myProgressSeedCourseRows,
  ...myProgressGeneratedCourseRows,
  myProgressExceptionCourseRow,
].map((row, index) => {
  const requiresReview =
    "requires_review" in row && row.requires_review === true;
  return {
    row_number: index + 3,
    source_table_index: index < 40 ? "1" : "2",
    source_row_index: String(index + 1),
    confidence: requiresReview ? "low" : "high",
    warnings: "warnings" in row ? row.warnings : [],
    reason_codes: "reason_codes" in row ? row.reason_codes : [],
    requires_review: requiresReview,
    ...row,
  };
});

function reviewedCourseStateFixtureContent() {
  const courseRows = myProgressCourseRows.map((row, index) => {
    const exactCompletedCourse = index === 6;
    const plannedPrerequisite = index === 7;
    const courseCode = exactCompletedCourse
      ? "FIN 300"
      : plannedPrerequisite
        ? "FIN 200"
        : row.course_code;
    const courseTitle = exactCompletedCourse
      ? "Managerial Finance"
      : plannedPrerequisite
        ? "Finance Foundations"
        : row.course_title;
    const status = exactCompletedCourse
      ? "COMPLETED"
      : plannedPrerequisite
        ? "PLANNED"
        : row.status;
    const termCode = exactCompletedCourse
      ? "2024FA"
      : plannedPrerequisite
        ? "2025SP"
        : (row.term ?? "");
    return {
      requirements: row.requirement_group_context,
      requirement_section: row.requirement_group_context,
      status,
      course_code: courseCode,
      course_title: courseTitle,
      term_code: termCode,
      credits: "3",
      raw_row_text: `${status} ${courseCode} ${courseTitle} ${termCode} 3`,
      source_table_index: row.source_table_index,
      source_row_index: row.source_row_index,
      field_provenance: {
        course_code: {
          rawText: courseCode,
          source: `visible table ${row.source_table_index} row ${row.source_row_index}`,
          confidence: row.confidence,
        },
      },
      confidence: row.confidence,
      warnings: row.warnings,
    };
  });

  return JSON.stringify({
    source_type: "BROWSER_EXTENSION",
    staging_only: true,
    page_type: "KEAN_MY_PROGRESS_PAGE",
    programSummary: myProgressDataImportPreview.summary_payload.program_summary,
    creditSummary: myProgressDataImportPreview.summary_payload.credit_summary,
    requirementGroups:
      myProgressDataImportPreview.summary_payload.requirement_groups,
    courseRows,
    rawSnapshot: {
      diagnostics: {
        tableCount: 17,
        rowCount: 85,
        requirementGroupCount: 1,
        courseLikeRowCount: 85,
        bounded: true,
        truncated: true,
        academicRowsSkipped: 1,
      },
    },
    validation: {
      status: "AUTO_VERIFIED",
      exceptionCount: 0,
      exceptions: [],
      autoConfirmedFieldCount: 14,
      autoConfirmedCourseRowCount: 84,
      overallConfidenceScore: 1,
      downstreamAnalysisAllowed: true,
    },
    warnings: ["sanitized local E2E fixture"],
  });
}

const myProgressDataImportPreview = {
  ...mockDataImportPreview,
  id: "00000000-0000-4000-8000-000000000744",
  data_import_run_id: myProgressDataImportRun.id,
  record_count: 87,
  valid_record_count: 86,
  warning_count: 1,
  official_application_ready: false,
  disclaimers: [
    "Sanitized MyProgress sample data is for local testing only and is not official school policy.",
    "No transcript, catalog, section, registration, seat, or waitlist records are changed.",
  ],
  summary_payload: {
    real_import_status: "REAL_IMPORTED_DATA_AUTO_VERIFIED",
    mock_data_mixed_with_real_import: false,
    can_apply_verified_import: true,
    downstream_analysis_allowed: true,
    exception_count: 0,
    exceptions: [],
    auto_confirmed_field_count: 14,
    auto_confirmed_course_row_count: 84,
    overall_confidence_score: 0.98,
    extracted_degree_audit_row_count: 85,
    parsed_course_like_row_count: 84,
    parsed_requirement_row_count: 1,
    ignored_row_count: 0,
    exception_row_count: 1,
    extraction_bounded: true,
    extraction_truncated: true,
    course_rows: myProgressCourseRows,
    readiness: {
      summary: { status: "AUTO_VERIFIED", reason_codes: [] },
      requirement_summary: { status: "APPLIED_OR_READY", reason_codes: [] },
      course_rows: {
        status: "PARTIAL_REQUIRES_REVIEW",
        reason_codes: ["COURSE_ROW_EXCEPTIONS_PRESENT"],
      },
      planner: {
        status: "BLOCKED",
        reason_codes: ["WAITING_FOR_RELIABLE_MYPROGRESS_COURSE_ROWS"],
      },
      course_eligibility: {
        status: "DEMO_ONLY",
        reason_codes: ["REAL_COURSE_HISTORY_NOT_READY"],
      },
      schedule_builder: {
        status: "DEMO_ONLY",
        reason_codes: ["REAL_SECTION_SEARCH_DATA_NOT_IMPORTED"],
      },
    },
    program_summary: {
      programName: "Finance, BS",
      degree: "Bachelor of Science",
      major: "Finance",
      department: "Accounting & Finance",
      catalogYear: 2024,
      cumulativeGpa: 3.916,
      institutionGpa: 3.916,
      anticipatedCompletionDate: "12/20/2028",
    },
    credit_summary: {
      totalAppliedCredits: 104,
      totalRequiredCredits: 120,
      completedCredits: 67,
      inProgressCredits: 24,
      plannedCredits: 13,
      remainingCredits: 16,
      completionPercent: 86.67,
    },
    requirement_groups: [
      {
        name: "GE Foundation Requirements 13 S.H.",
        statusText: "4 of 5 Completed",
        confidence: "high",
      },
    ],
    field_provenance: {
      programName: {
        source: "sanitized-kean-myprogress-finance-summary.html",
        confidence: "high",
        rawText: "Finance, BS",
      },
      totalAppliedCredits: {
        source: "sanitized-kean-myprogress-finance-summary.html",
        confidence: "high",
        rawText: "104 of 120",
      },
    },
    raw_snapshot: {
      progressBarText: "67 24 13",
      visibleTextSample:
        "My Progress Finance, BS Catalog 2024 GPA 3.916 Total Credits 104 of 120",
    },
  },
};

const myProgressRequiresReviewPreview = {
  ...myProgressDataImportPreview,
  id: "00000000-0000-4000-8000-000000000745",
  warning_count: 1,
  summary_payload: {
    ...myProgressDataImportPreview.summary_payload,
    real_import_status: "REAL_IMPORTED_DATA_REQUIRES_REVIEW",
    can_apply_verified_import: false,
    downstream_analysis_allowed: false,
    exception_count: 1,
    exceptions: [
      {
        code: "LOW_CONFIDENCE_REQUIREMENT_GROUP",
        message:
          "One MyProgress requirement group needs review before downstream use.",
        severity: "WARNING",
        source: "sanitized-kean-myprogress-finance-summary.html",
      },
    ],
    readiness: {
      ...myProgressDataImportPreview.summary_payload.readiness,
      summary: {
        status: "REVIEW_REQUIRED",
        reason_codes: ["MY_PROGRESS_SUMMARY_NOT_VERIFIED"],
      },
      planner: {
        status: "BLOCKED",
        reason_codes: ["MY_PROGRESS_SUMMARY_NOT_VERIFIED"],
      },
    },
  },
};

const myProgressPlanningReadyPreview = {
  ...myProgressDataImportPreview,
  id: "00000000-0000-4000-8000-000000000746",
  summary_payload: {
    ...myProgressDataImportPreview.summary_payload,
    extracted_degree_audit_row_count: 84,
    parsed_course_like_row_count: 84,
    exception_row_count: 0,
    extraction_bounded: false,
    extraction_truncated: false,
    course_rows: myProgressCourseRows.filter((row) => !row.requires_review),
    readiness: {
      ...myProgressDataImportPreview.summary_payload.readiness,
      course_rows: {
        status: "READY",
        reason_codes: [],
      },
      planner: {
        status: "WARNING",
        reason_codes: ["IMPORTED_ROWS_NEED_ADVISOR_CONFIRMATION"],
      },
    },
  },
};

const mockSectionMonitorTarget = {
  id: "00000000-0000-4000-8000-000000000801",
  student_profile_id: mockDataImportRun.student_profile_id,
  course_code: "FIN 403",
  section_code: "001",
  term: "2025FA",
  title: "Mock International Finance",
  instructor: "Mock Instructor",
  status: "OPEN",
  is_active: true,
  is_advisory: true,
  is_official: false,
  latest_snapshot_created_at: "2026-07-01T00:00:00Z",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

const mockSectionMonitorAlert = {
  id: "00000000-0000-4000-8000-000000000803",
  target_id: mockSectionMonitorTarget.id,
  previous_snapshot_id: "00000000-0000-4000-8000-000000000804",
  current_snapshot_id: "00000000-0000-4000-8000-000000000802",
  alert_type: "SECTION_OPENED",
  severity: "INFO",
  field_name: "status",
  previous_value: "CLOSED",
  current_value: "OPEN",
  message:
    "FIN 403 001 appears to have opened in imported data; manually verify in the official portal.",
  is_acknowledged: false,
  acknowledged_at: null,
  is_advisory: true,
  requires_manual_review: true,
  created_at: "2026-07-01T00:00:00Z",
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
        message:
          "Imported record requires advisor review before it can be applied.",
        created_at: dryRun ? null : "2026-06-30T00:00:03Z",
      },
    ],
    warnings: mockDataReviewWarnings,
    summary: {
      source_import_id: mockDataImportReview.data_import_run_id,
      snapshot_id: null,
      applied_count: 1,
      warning_count: 0,
      exception_count: 0,
      rejected_count: 0,
      deferred_count: 0,
      duplicate_count: 0,
    },
  };
}

const myProgressDataImportReview = {
  ...mockDataImportReview,
  id: "00000000-0000-4000-8000-000000000751",
  data_import_run_id: myProgressDataImportRun.id,
  status: "READY_TO_APPLY",
};

const myProgressImportedRecordReviews = [
  {
    ...mockImportedRecordReviews[0],
    id: "00000000-0000-4000-8000-000000000752",
    review_session_id: myProgressDataImportReview.id,
    imported_record_id: myProgressProgramRecord.id,
    selected_mapping_candidate_id: null,
    decision: "CONFIRMED",
    requires_advisor_confirmation: false,
    imported_record: myProgressProgramRecord,
    selected_mapping_candidate: null,
  },
  {
    ...mockImportedRecordReviews[1],
    id: "00000000-0000-4000-8000-000000000753",
    review_session_id: myProgressDataImportReview.id,
    imported_record_id: myProgressRequirementRecord.id,
    selected_mapping_candidate_id: null,
    decision: "CONFIRMED",
    requires_advisor_confirmation: false,
    imported_record: myProgressRequirementRecord,
    selected_mapping_candidate: null,
  },
];

const myProgressDataApplicationRun = {
  ...mockDataApplicationRun,
  id: "00000000-0000-4000-8000-000000000754",
  review_session_id: myProgressDataImportReview.id,
  status: "APPLIED_WITH_WARNINGS",
  applied_count: 2,
  skipped_count: 0,
  warning_count: 1,
};

const myProgressDataReviewWarnings = [
  {
    ...mockDataReviewWarnings[0],
    id: "00000000-0000-4000-8000-000000000755",
    review_session_id: myProgressDataImportReview.id,
    message:
      "Applied MyProgress summaries to the internal imported snapshot; high-risk guidance still needs school confirmation.",
  },
];

function mockMyProgressApplicationResult(dryRun: boolean) {
  return {
    review_session: {
      ...myProgressDataImportReview,
      status: dryRun ? "READY_TO_APPLY" : "APPLIED_WITH_WARNINGS",
      completed_at: dryRun ? null : "2026-06-30T00:00:03Z",
    },
    dry_run: dryRun,
    application: dryRun ? null : myProgressDataApplicationRun,
    applied_records: [
      {
        id: dryRun ? null : "00000000-0000-4000-8000-000000000756",
        data_application_run_id: dryRun
          ? null
          : myProgressDataApplicationRun.id,
        imported_record_review_id: myProgressImportedRecordReviews[0].id,
        imported_record_id: myProgressProgramRecord.id,
        target_entity_type: "UNKNOWN",
        target_entity_id: null,
        action: "UPDATED",
        status: "SUCCESS",
        reason_code: dryRun
          ? "WOULD_APPLY_MYPROGRESS_PROGRAM_SUMMARY"
          : "APPLIED_MYPROGRESS_PROGRAM_SUMMARY",
        message: dryRun
          ? "Dry run would apply the MyProgress program summary to the internal imported planning snapshot."
          : "Applied MyProgress program summary to the internal imported planning snapshot with advisory warnings.",
        created_at: dryRun ? null : "2026-06-30T00:00:03Z",
      },
      {
        id: dryRun ? null : "00000000-0000-4000-8000-000000000757",
        data_application_run_id: dryRun
          ? null
          : myProgressDataApplicationRun.id,
        imported_record_review_id: myProgressImportedRecordReviews[1].id,
        imported_record_id: myProgressRequirementRecord.id,
        target_entity_type: "UNKNOWN",
        target_entity_id: null,
        action: "UPDATED",
        status: "SUCCESS",
        reason_code: dryRun
          ? "WOULD_APPLY_MYPROGRESS_REQUIREMENT_SUMMARY"
          : "APPLIED_MYPROGRESS_REQUIREMENT_SUMMARY",
        message: dryRun
          ? "Dry run would apply the MyProgress requirement summary to the internal imported audit snapshot."
          : "Applied MyProgress requirement summary to the internal imported audit snapshot with advisory warnings.",
        created_at: dryRun ? null : "2026-06-30T00:00:03Z",
      },
    ],
    warnings: myProgressDataReviewWarnings,
    summary: {
      source_import_id: myProgressDataImportReview.data_import_run_id,
      snapshot_id: null,
      applied_count: 2,
      warning_count: 0,
      exception_count: 0,
      rejected_count: 0,
      deferred_count: 0,
      duplicate_count: 0,
    },
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
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/targets*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/alerts*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
}

async function mockNoSavedDataImports(page: Page) {
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-imports",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
}

async function waitForClientReady(page: Page) {
  await expect(page.getByText("API 已连接")).toBeVisible();
}

async function mockSavedMyProgressImportApis(
  page: Page,
  preview = myProgressDataImportPreview,
) {
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-imports",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([myProgressDataImportRun]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(myProgressDataImportRun),
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
        body: JSON.stringify([
          myProgressProgramRecord,
          myProgressRequirementRecord,
        ]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/mapping-candidates",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/warnings",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/preview",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(preview),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-imports/*/validate",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(preview),
      });
    },
  );
}

async function mockMyProgressReviewApis(page: Page) {
  let applications = [] as Array<typeof myProgressDataApplicationRun>;

  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews",
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify(myProgressDataImportReview),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/records",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(myProgressImportedRecordReviews),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*/warnings",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(myProgressDataReviewWarnings),
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
        applications = [myProgressDataApplicationRun];
      }
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(mockMyProgressApplicationResult(dryRun)),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/data-import-reviews/*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(myProgressDataImportReview),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-import-reviews",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([myProgressDataImportReview]),
      });
    },
  );
}

async function mockSuccessfulSectionMonitoringApis(page: Page) {
  await page.unroute(
    "http://localhost:8000/api/v1/section-monitoring/targets*",
  );
  await page.unroute("http://localhost:8000/api/v1/section-monitoring/alerts*");
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/targets*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([mockSectionMonitorTarget]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/alerts*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([mockSectionMonitorAlert]),
      });
    },
  );
}

test.beforeEach(async ({ page }) => {
  await page.route("http://localhost:8000/health", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        service: "api",
        database_configured: true,
      }),
    });
  });
  await page.route(
    "http://localhost:8000/api/v1/students/*/course-state-snapshots/active",
    async (route) => {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "not_found",
            message:
              "No active course-state snapshot in this isolated UI test.",
          },
        }),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/students/*/data-imports",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/targets*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
  await page.route(
    "http://localhost:8000/api/v1/section-monitoring/alerts*",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
});

test("home page shows degree progress shell and required mock warnings", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockNoSavedDataImports(page);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: /学业进度/ })).toBeVisible();
  await expect(page.getByText("API 已连接")).toBeVisible();
  await expect(
    page
      .getByText("高风险学业建议需要 advisor / registrar / 学校确认。")
      .first(),
  ).toBeVisible();
  await expect(page.getByText("审核模式")).toBeVisible();
  await expect(page.getByText("Mock Finance Foundations")).toBeVisible();
  await expect(page.getByText("PENDING_TRANSFER")).toBeVisible();
});

test("home page clearly marks the degree dashboard as demo data when no MyProgress import exists", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockNoSavedDataImports(page);

  await page.goto("/");

  const auditSummary = page.getByLabel("学业审核汇总");
  await expect(auditSummary.getByText("演示 / 模拟数据")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "尚未加载真实 MyProgress 导入" }),
  ).toBeVisible();
  await expect(page.getByText("仅示例数据")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /加载脱敏 MyProgress 示例/ }),
  ).toBeVisible();
  await expect(auditSummary.getByText("Mock BS Finance")).toHaveCount(0);
  await expect(auditSummary.getByText("27.0")).toHaveCount(0);
  await expect(auditSummary.getByText("3.0")).toHaveCount(0);
  await expect(auditSummary.getByText("6.0")).toHaveCount(0);
  await expect(auditSummary.getByText("93.0")).toHaveCount(0);
  await expect(auditSummary.getByText("22.50%")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /创建假设方案/ }),
  ).toBeDisabled();
  await expect(page.getByRole("button", { name: /创建规划/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: /生成课表/ })).toBeDisabled();
  await expect(page.getByLabel("本地诊断")).toContainText("导入来源状态");
  await expect(page.getByLabel("本地诊断")).toContainText("演示 / 模拟数据");
});

test("saved auto-verified MyProgress import overrides mock dashboard values", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSavedMyProgressImportApis(page);

  await page.goto("/");

  const auditSummary = page.getByLabel("学业审核汇总");
  await expect(
    auditSummary.getByText("真实导入数据 - 已自动验证"),
  ).toBeVisible();
  await expect(auditSummary.getByText("Finance, BS")).toBeVisible();
  await expect(auditSummary.getByText("2024")).toBeVisible();
  await expect(auditSummary.getByText("3.916").first()).toBeVisible();
  await expect(auditSummary.getByText("104.0 / 120.0")).toBeVisible();
  await expect(auditSummary.getByText("67.0")).toBeVisible();
  await expect(auditSummary.getByText("24.0")).toBeVisible();
  await expect(auditSummary.getByText("13.0")).toBeVisible();
  await expect(auditSummary.getByText("16.0")).toBeVisible();
  await expect(auditSummary.getByText("86.67%")).toBeVisible();
  await expect(auditSummary.getByText("Mock BS Finance")).toHaveCount(0);
  await expect(auditSummary.getByText("27.0")).toHaveCount(0);
  await expect(auditSummary.getByText("93.0")).toHaveCount(0);
  await expect(auditSummary.getByText("22.50%")).toHaveCount(0);
  const importSummary = page.getByLabel("数据导入预览汇总");
  await expect(
    importSummary
      .locator(".metric")
      .filter({ hasText: "提取的 MyProgress 行" }),
  ).toContainText("85");
  await expect(
    importSummary.locator(".metric").filter({ hasText: "已解析课程行" }),
  ).toContainText("84");
  await expect(
    importSummary.locator(".metric").filter({ hasText: "要求摘要行" }),
  ).toContainText("1");
  await expect(
    importSummary.locator(".metric").filter({ hasText: "异常行" }),
  ).toContainText("1");
  await expect(
    importSummary.locator(".metric").filter({ hasText: "忽略行" }),
  ).toContainText("0");
  await expect(
    importSummary.locator(".metric").filter({ hasText: "提取有边界 / 截断" }),
  ).toContainText("是");
  await expect(page.getByText("截断/边界警告需要重点核对")).toBeVisible();
  const myProgressRows = page.getByLabel("MyProgress 课程行");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "MATH 1044" }),
  ).toContainText("Precalculus for Business");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "MATH 1044" }),
  ).toContainText("尚未开始");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "MATH 1054" }),
  ).toContainText("Pre-Calculus");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "MATH 1054" }),
  ).toContainText("尚未开始");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "ENG 2403" }),
  ).toContainText("World Literature");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "ENG 2403" }),
  ).toContainText("2026SUW");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "ENG 2403" }),
  ).toContainText("已规划");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "GE 1855" }),
  ).toContainText("First Year Seminar");
  await expect(
    myProgressRows.locator(".comparison-row").filter({ hasText: "GE 1855" }),
  ).toContainText("尚未开始");
  await expect(page.getByLabel("MyProgress 分项就绪状态")).toContainText(
    "课程行",
  );
  await expect(page.getByLabel("MyProgress 分项就绪状态")).toContainText(
    "部分解析 / 需要审核",
  );
});

test("home page reviews and applies confirmed MyProgress import summaries", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSavedMyProgressImportApis(page);
  await mockMyProgressReviewApis(page);

  await page.goto("/");
  await waitForClientReady(page);

  await expect(
    page.getByText("真实导入数据 - 已自动验证").first(),
  ).toBeVisible();

  await page.getByRole("button", { name: /^创建审核$/ }).click();
  const reviewSummary = page.getByLabel("数据审核汇总");
  await expect(reviewSummary.getByText("可应用")).toBeVisible();
  await expect(reviewSummary.getByText("已确认记录")).toBeVisible();
  await expect(
    reviewSummary.locator(".metric").filter({ hasText: "已确认记录" }),
  ).toContainText("0");
  await page.getByRole("button", { name: /^加载最新审核$/ }).click();
  await expect(reviewSummary.getByText("可应用")).toBeVisible();

  await page.getByRole("button", { name: /^试运行$/ }).click();
  const applicationResult = page.getByLabel("数据应用结果");
  await expect(
    applicationResult.getByText("WOULD_APPLY_MYPROGRESS_PROGRAM_SUMMARY"),
  ).toBeVisible();
  await expect(
    applicationResult.getByText("WOULD_APPLY_MYPROGRESS_REQUIREMENT_SUMMARY"),
  ).toBeVisible();
  await expect(
    applicationResult.getByText("UNSUPPORTED_TARGET_TYPE"),
  ).toHaveCount(0);
  await expect(applicationResult.getByText("已跳过不支持项")).toHaveCount(0);

  await page.getByRole("button", { name: /^应用已确认记录$/ }).click();
  await expect(reviewSummary.getByText("已应用但有警告").first()).toBeVisible();
  await expect(
    applicationResult.getByText("APPLIED_MYPROGRESS_PROGRAM_SUMMARY"),
  ).toBeVisible();
  await expect(
    applicationResult.getByText("APPLIED_MYPROGRESS_REQUIREMENT_SUMMARY"),
  ).toBeVisible();
  await expect(
    applicationResult.getByText("UNSUPPORTED_TARGET_TYPE"),
  ).toHaveCount(0);
  await expect(applicationResult.getByText("已跳过不支持项")).toHaveCount(0);
});

test("reviewed 85-row MyProgress import drives the active real course-state snapshot", async ({
  page,
  request,
}) => {
  const studentId = mockAuditRun.student_profile_id;
  const localApiHeaders = { Origin: "http://127.0.0.1:3000" };
  const importResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/data-imports",
    {
      headers: localApiHeaders,
      data: {
        student_profile_id: studentId,
        import_type: "DEGREE_AUDIT_EXPORT",
        file_name: "sanitized-myprogress-course-state-e2e.json",
        file_mime_type: "application/json",
        content: reviewedCourseStateFixtureContent(),
        source_type: "BROWSER_EXTENSION",
        source_reference: "Sanitized local MyProgress course-state E2E fixture",
      },
    },
  );
  expect(importResponse.status()).toBe(201);
  const imported = (await importResponse.json()) as { id: string };

  const reviewResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/data-import-reviews",
    {
      headers: localApiHeaders,
      data: {
        data_import_run_id: imported.id,
        reviewer_label: "Sanitized E2E self-review",
      },
    },
  );
  expect(reviewResponse.status()).toBe(201);
  const review = (await reviewResponse.json()) as { id: string };

  const reviewRecordsResponse = await request.get(
    `http://127.0.0.1:8000/api/v1/data-import-reviews/${review.id}/records`,
    { headers: localApiHeaders },
  );
  expect(reviewRecordsResponse.status()).toBe(200);
  const reviewRecords = (await reviewRecordsResponse.json()) as Array<{
    id: string;
    imported_record: {
      normalized_payload: { course_code?: string };
    };
  }>;
  for (const record of reviewRecords) {
    if (!record.imported_record.normalized_payload.course_code) {
      continue;
    }
    const confirmResponse = await request.patch(
      `http://127.0.0.1:8000/api/v1/data-import-reviews/${review.id}/records/${record.id}`,
      {
        headers: localApiHeaders,
        data: { decision: "CONFIRMED" },
      },
    );
    expect(confirmResponse.status()).toBe(200);
  }

  const dryRunResponse = await request.post(
    `http://127.0.0.1:8000/api/v1/data-import-reviews/${review.id}/apply`,
    {
      headers: localApiHeaders,
      data: { dry_run: true, allow_advisor_review_records: false },
    },
  );
  expect(dryRunResponse.status()).toBe(200);
  const dryRun = (await dryRunResponse.json()) as {
    dry_run: boolean;
    course_state_snapshot: null;
  };
  expect(dryRun.dry_run).toBe(true);
  expect(dryRun.course_state_snapshot).toBeNull();

  const applyResponse = await request.post(
    `http://127.0.0.1:8000/api/v1/data-import-reviews/${review.id}/apply`,
    {
      headers: localApiHeaders,
      data: { dry_run: false, allow_advisor_review_records: false },
    },
  );
  expect(applyResponse.status()).toBe(200);
  const applied = (await applyResponse.json()) as {
    course_state_snapshot: { id: string; is_active: boolean };
    summary: { source_import_id: string; snapshot_id: string };
  };
  expect(applied.course_state_snapshot.is_active).toBe(true);
  expect(applied.summary.source_import_id).toBe(imported.id);
  expect(applied.summary.snapshot_id).toBe(applied.course_state_snapshot.id);

  const activeResponse = await request.get(
    `http://127.0.0.1:8000/api/v1/students/${studentId}/course-state-snapshots/active`,
    { headers: localApiHeaders },
  );
  expect(activeResponse.status()).toBe(200);
  const active = (await activeResponse.json()) as {
    snapshot: {
      id: string;
      is_active: boolean;
      extraction_bounded: boolean;
      extraction_truncated: boolean;
      readiness: Record<string, { status: string }>;
    };
    course_states: Array<{
      normalized_course_code: string;
      status: string;
      student_course_attempt_id: string | null;
    }>;
  };
  expect(active.snapshot.id).toBe(applied.course_state_snapshot.id);
  expect(active.snapshot.extraction_bounded).toBe(true);
  expect(active.snapshot.extraction_truncated).toBe(true);
  expect(active.snapshot.readiness.long_term_planner.status).toBe("BLOCKED");
  expect(active.snapshot.readiness.semester_schedule.status).toBe("DEMO_ONLY");
  expect(active.course_states).toHaveLength(84);
  expect(
    active.course_states.find(
      (state) => state.normalized_course_code === "MATH 1044",
    ),
  ).toMatchObject({ status: "NOT_STARTED", student_course_attempt_id: null });
  expect(
    active.course_states.find(
      (state) => state.normalized_course_code === "MATH 1054",
    ),
  ).toMatchObject({ status: "NOT_STARTED", student_course_attempt_id: null });
  expect(
    active.course_states.find(
      (state) => state.normalized_course_code === "ENG 2403",
    ),
  ).toMatchObject({ status: "PLANNED" });

  const eligibilityResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/eligibility-checks",
    {
      headers: localApiHeaders,
      data: {
        student_profile_id: studentId,
        course_id: "e6ab2a34-d85a-5446-875e-83fd36d5b08e",
        target_term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
        mode: "CURRENT",
        planned_corequisite_course_ids: [],
      },
    },
  );
  expect(eligibilityResponse.status()).toBe(201);
  const eligibility = (await eligibilityResponse.json()) as {
    overall_result: string;
    rule_evaluations: Array<{
      expressions: Array<{ reason_code: string }>;
    }>;
  };
  expect(eligibility.overall_result).toBe("NOT_ELIGIBLE");
  expect(
    eligibility.rule_evaluations.flatMap((rule) =>
      rule.expressions.map((evaluation) => evaluation.reason_code),
    ),
  ).toContain("COMPLETED_COURSE_MISSING");

  const plannerResponse = await request.post(
    "http://127.0.0.1:8000/api/v1/academic-plans",
    {
      headers: localApiHeaders,
      data: {
        student_profile_id: studentId,
        program_version_id: "f65bee76-6061-515f-a3df-cdf5567514af",
        academic_plan_scenario_id: null,
        planning_mode: "CURRENT_PROGRAM",
        start_term_id: "fed14bfe-972b-5392-8c72-379ceb879e85",
        terms_to_plan: 2,
        minimum_credits_per_term: "3.0",
        maximum_credits_per_term: "6.0",
        preferred_credits_per_term: "6.0",
      },
    },
  );
  expect(plannerResponse.status()).toBe(400);
  await expect(plannerResponse.json()).resolves.toMatchObject({
    detail: { code: "course_state_snapshot_not_ready" },
  });

  const reapplyResponse = await request.post(
    `http://127.0.0.1:8000/api/v1/data-import-reviews/${review.id}/apply`,
    {
      headers: localApiHeaders,
      data: { dry_run: false, allow_advisor_review_records: false },
    },
  );
  expect(reapplyResponse.status()).toBe(200);
  const reapplied = (await reapplyResponse.json()) as {
    course_state_snapshot: { id: string };
    summary: { duplicate_count: number };
  };
  expect(reapplied.course_state_snapshot.id).toBe(active.snapshot.id);
  expect(reapplied.summary.duplicate_count).toBeGreaterThan(0);

  await page.unroute(
    "http://localhost:8000/api/v1/students/*/course-state-snapshots/active",
  );
  await page.unroute("http://localhost:8000/api/v1/students/*/data-imports");
  await page.goto("/");
  await waitForClientReady(page);
  const courseStatePanel = page.getByRole("region", {
    name: "已应用课程状态",
    exact: true,
  });
  await expect(courseStatePanel.getByText("内部课程状态快照")).toBeVisible();
  await expect(courseStatePanel).toContainText("MATH 1044");
  await expect(courseStatePanel).toContainText("ENG 2403");
  await expect(courseStatePanel).toContainText("来源提取有边界或被截断");
  await expect(courseStatePanel).toContainText("尚未导入真实课节搜索数据");
  await expect(page.getByText("Mock BS Finance")).toHaveCount(0);
  await expect(page.getByText("PENDING_WAIVER")).toHaveCount(0);
  await expect(page.getByText("INCOMPLETE_ATTEMPT")).toHaveCount(0);
});

test("saved MyProgress import with exceptions is marked as requiring review", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSavedMyProgressImportApis(page, myProgressRequiresReviewPreview);

  await page.goto("/");

  const auditSummary = page.getByLabel("学业审核汇总");
  await expect(auditSummary.getByText("真实导入数据 - 需要审核")).toBeVisible();
  await expect(
    page
      .getByLabel("MyProgress 异常队列")
      .getByText("LOW_CONFIDENCE_REQUIREMENT_GROUP"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /创建假设方案/ }),
  ).toBeDisabled();
  await expect(page.getByRole("button", { name: /创建规划/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: /生成课表/ })).toBeDisabled();
});

test("home page shows product status cards with advisory labels", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockNoSavedDataImports(page);
  await mockSuccessfulSectionMonitoringApis(page);

  await page.goto("/");

  const dashboard = page.getByLabel("产品状态概览");
  await expect(dashboard).toBeVisible();

  const degreeAuditCard = page.getByLabel("学业审核状态卡片");
  await expect(degreeAuditCard).toContainText("学业审核");
  await expect(degreeAuditCard).toContainText("已完成但有警告");
  await expect(degreeAuditCard).toContainText("查看要求警告");

  const dataReviewCard = page.getByLabel("数据导入审核状态卡片");
  await expect(dataReviewCard).toContainText("数据导入审核");
  await expect(dataReviewCard).toContainText("尚无已确认导入");
  await expect(dataReviewCard).toContainText("需要人工审核");

  const browserExtensionCard = page.getByLabel("浏览器插件导入状态卡片");
  await expect(browserExtensionCard).toContainText("浏览器插件导入");
  await expect(browserExtensionCard).toContainText("非官方导入数据");
  await expect(browserExtensionCard).toContainText("仅供参考");

  const sectionMonitoringCard = page.getByLabel("课节监控状态卡片");
  await expect(sectionMonitoringCard).toContainText("课节监控");
  await expect(sectionMonitoringCard).toContainText("参考性提醒已就绪");
  await expect(sectionMonitoringCard).toContainText("请在官方门户人工核对");

  const scheduleCard = page.getByLabel("课表优化状态卡片");
  await expect(scheduleCard).toContainText("课表优化");
  await expect(scheduleCard).toContainText("等待真实课节数据 / 演示模式");
  await expect(scheduleCard).toContainText("生成课表");

  const whatIfCard = page.getByLabel("假设规划状态卡片");
  await expect(whatIfCard).toContainText("假设规划");
  await expect(whatIfCard).toContainText("没有假设方案");
  await expect(whatIfCard).toContainText("创建假设方案");
});

test("home page explains empty states with reasons and manual next steps", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);

  await page.goto("/");

  await expect(page.getByLabel("数据导入空状态")).toContainText(
    "还没有数据导入",
  );
  await expect(page.getByLabel("数据导入空状态")).toContainText(
    "当前还没有为模拟学生创建或加载 staging 导入。",
  );
  await expect(page.getByLabel("数据导入空状态")).toContainText(
    "先手动预览一次导入，再进入人工审核。",
  );

  await expect(page.getByLabel("数据审核空状态")).toContainText(
    "还没有已确认的导入",
  );
  await expect(page.getByLabel("数据审核空状态")).toContainText("需要人工审核");

  await expect(page.getByLabel("课节监控目标空状态")).toContainText(
    "还没有监控的课节",
  );
  await expect(page.getByLabel("课节监控提醒空状态")).toContainText(
    "还没有课节提醒",
  );

  await expect(page.getByLabel("课表方案空状态")).toContainText(
    "还没有生成课表方案",
  );
  await expect(page.getByLabel("假设方案空状态")).toContainText(
    "还没有假设方案",
  );
});

test("home page avoids misleading registration and availability wording", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulSectionMonitoringApis(page);

  await page.goto("/");

  const pageText = (await page.locator("main").innerText()).toLowerCase();
  for (const phrase of [
    "auto-register",
    "reserve seat",
    "guaranteed seat",
    "live availability",
    "real-time",
    "seat grabbing",
    "join waitlist automatically",
    "enroll now",
  ]) {
    expect(pageText).not.toContain(phrase);
  }
});

test("home page reports when the API health request is unavailable", async ({
  page,
}) => {
  await page.route("http://localhost:8000/health", async (route) => {
    await route.abort("failed");
  });

  await page.goto("/");

  await expect(page.getByText("API 不可用")).toBeVisible();
  await expect(page.getByText("尚未加载导入", { exact: true })).toBeVisible();
  await expect(
    page
      .locator("section[aria-live='polite'] > p")
      .filter({
        hasText: /Health check request failed|Failed to fetch|NetworkError/,
      })
      .first(),
  ).toBeVisible();
  const diagnostics = page.getByLabel("本地诊断");
  await expect(diagnostics).toContainText("API 基础地址");
  await expect(diagnostics).toContainText("http://localhost:8000");
  await expect(diagnostics).toContainText("网页来源");
  await expect(diagnostics).toContainText("API 可能未重启");
  await expect(diagnostics).toContainText("CORS");
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

  await expect(page.getByText("学业审核不可用")).toBeVisible();
  await expect(page.getByText(/意外的学业审核响应结构/)).toBeVisible();
});

test("home page creates and compares what-if academic scenarios", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulScenarioApis(page);

  await page.goto("/");
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();
  await expect(page.getByText("演示工作流已显式启用")).toBeVisible();

  await expect(
    page
      .getByLabel("假设规划", { exact: true })
      .getByRole("heading", { name: "假设规划" }),
  ).toBeVisible();
  await expect(page.getByText("额外学分估算不会预测毕业时间。")).toBeVisible();

  await page.getByLabel("候选项目").selectOption("accounting-minor");
  await page.getByRole("button", { name: /创建假设方案/ }).click();

  const scenarioSummary = page.getByLabel("假设方案汇总");
  await expect(scenarioSummary.getByText("模拟会计辅修")).toBeVisible();
  await expect(scenarioSummary.getByText("共享学分")).toBeVisible();
  await expect(scenarioSummary.getByText("第二项目独有学分")).toBeVisible();
  await expect(scenarioSummary.getByText("预计额外学分")).toBeVisible();
  await expect(page.getByText("ACCT 300")).toBeVisible();
  await expect(page.getByText("ESTIMATED_ADDITIONAL_CREDITS")).toBeVisible();

  await page.getByRole("button", { name: /比较已保存方案/ }).click();
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
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();
  await page.getByRole("button", { name: /创建假设方案/ }).click();

  await expect(page.getByText("假设方案不可用")).toBeVisible();
  await expect(page.getByText(/意外的假设方案响应结构/)).toBeVisible();
});

test("home page checks course eligibility without recalculating section seats", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulEligibilityApis(page);

  await page.goto("/");
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();

  await expect(page.getByRole("heading", { name: /课程资格/ })).toBeVisible();
  await expect(
    page
      .getByLabel("课程资格检查")
      .getByText("课节座位状态必须在官方门户人工核对。"),
  ).toBeVisible();

  await page.getByLabel("课程检查").selectOption("fin-400-registration");
  await page.getByRole("button", { name: /检查资格/ }).click();

  const eligibilitySummary = page.getByLabel("课程资格汇总");
  await expect(eligibilitySummary.getByText("需要许可").first()).toBeVisible();
  await expect(eligibilitySummary.getByText("候补名单")).toBeVisible();
  await expect(eligibilitySummary.getByText("可用座位")).toBeVisible();
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
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();
  await page.getByRole("button", { name: /检查资格/ }).click();

  await expect(page.getByText("课程资格结构错误")).toBeVisible();
  await expect(page.getByText(/意外的课程资格响应结构/)).toBeVisible();
});

test("home page creates and compares long-term academic plans", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulPlannerApis(page);

  await page.goto("/");
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();

  await expect(
    page.getByRole("heading", { name: /长期学业规划/ }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("长期学业规划边界")
      .getByText("演示数据 / 模拟数据，不是官方学校政策。"),
  ).toBeVisible();
  await expect(page.getByText("这不是注册课程。").first()).toBeVisible();
  await expect(page.getByText("长期规划不检查每周课表冲突。")).toBeVisible();
  await expect(page.getByText("课程开设预测只是估算。")).toBeVisible();
  await expect(
    page
      .getByText("高风险学业建议需要 advisor / registrar / 学校确认。")
      .first(),
  ).toBeVisible();

  await page.getByLabel("规划范围").selectOption("current-program");
  await page.getByLabel("学期数").fill("2");
  await page.getByLabel("最低学分").fill("3");
  await page.getByLabel("偏好学分").fill("6");
  await page.getByLabel("最高学分").fill("9");
  await page.getByRole("button", { name: /创建规划/ }).click();

  const planSummary = page.getByLabel("学业规划汇总");
  await expect(planSummary.getByText("已完成但有警告")).toBeVisible();
  await expect(planSummary.getByText("规划学分")).toBeVisible();
  await expect(
    page.getByLabel("逐学期学业规划").getByText("FIN 400"),
  ).toBeVisible();
  await expect(page.getByText("PREREQUISITE_PLANNED_EARLIER")).toBeVisible();
  await expect(page.getByText("MOCK_PLAN_NOT_OFFICIAL")).toBeVisible();

  await page.getByRole("button", { name: /比较已保存规划/ }).click();
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
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();
  await page.getByRole("button", { name: /创建规划/ }).click();

  await expect(page.getByText("学业规划结构错误")).toBeVisible();
  await expect(page.getByText(/意外的学业规划响应结构/)).toBeVisible();
});

test("home page builds and compares semester schedules", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulScheduleApis(page);

  await page.goto("/");
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();

  await expect(
    page.getByRole("heading", { name: /学期课表生成器/ }),
  ).toBeVisible();
  await expect(
    page.getByLabel("课表生成器边界").getByText("生成课表不是注册课程。"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("课表生成器边界")
      .getByText("课节座位状态必须在官方门户人工核对。"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("课表生成器边界")
      .getByText("不会 add/drop/swap，不会加入 waitlist。"),
  ).toBeVisible();

  await page.getByLabel("课程集合").selectOption("fall-fin-300-403");
  await page.getByLabel("固定课节").selectOption("fin-403-002");
  await page.getByLabel("排除课节").selectOption("fin-300-web");
  await page.getByLabel("差异度").selectOption("HIGH");
  await expect(page.getByLabel("减少空档")).toBeChecked();
  await expect(page.getByLabel("上午")).toBeChecked();
  await page.getByRole("button", { name: /生成课表/ }).click();

  const scheduleSummary = page.getByLabel("课表优化汇总");
  await expect(scheduleSummary.getByText("已完成但有警告")).toBeVisible();
  await expect(scheduleSummary.getByText("最佳学分")).toBeVisible();
  await expect(
    page.getByLabel("课表选项").getByText("FIN 300 001"),
  ).toBeVisible();
  await expect(
    page.getByLabel("课表选项").getByText("FIN 403 002", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("优先级 20.00")).toBeVisible();
  await expect(page.getByText("SECTION_PRIORITY_WEIGHT")).toBeVisible();
  await expect(
    page.getByText("差异度 2: uses FIN 403 section ONL instead of 002"),
  ).toBeVisible();
  await expect(page.getByLabel("课表选项比较")).toBeVisible();
  await expect(page.getByLabel("课表修复建议")).toContainText(
    "RELAX UNAVAILABLE BLOCK",
  );
  await expect(page.getByText("TIME_OVERLAP")).toBeVisible();
  await expect(page.getByText("MOCK_SECTION_DATA_NOT_OFFICIAL")).toBeVisible();

  await page.getByRole("button", { name: /比较已保存课表/ }).click();
  await expect(
    page.getByLabel("已保存课表比较").getByText("CUSTOM_COURSE_SET"),
  ).toHaveCount(2);
});

test("home page previews read-only data imports", async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulDataImportApis(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /数据导入预览/ }),
  ).toBeVisible();
  await expect(
    page.getByLabel("数据导入边界").getByText("导入预览数据不是官方学校政策。"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("数据导入边界")
      .getByText("不会修改成绩单、目录、课节、注册、座位或 waitlist 记录。"),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("数据导入预览")
      .getByRole("heading", { name: /浏览器插件导入/ }),
  ).toBeVisible();
  const browserExtensionStatus = page.getByRole("region", {
    name: "浏览器插件导入状态",
  });
  await expect(browserExtensionStatus).toContainText("非官方导入数据");
  await expect(browserExtensionStatus).toContainText("staging");
  await expect(browserExtensionStatus).toContainText("需要明确点击应用");
  await expect(browserExtensionStatus).toContainText("不会注册课程");

  await page.getByLabel("示例导入").selectOption("mock-transcript-csv");
  await page.getByRole("button", { name: /预览导入/ }).click();

  const importSummary = page.getByLabel("数据导入预览汇总");
  await expect(importSummary.getByText("已解析但有警告")).toBeVisible();
  await expect(importSummary.getByText("映射候选项")).toBeVisible();
  await expect(importSummary.getByText("已禁用")).toBeVisible();
  await expect(importSummary.getByText("学生提供")).toBeVisible();

  await expect(
    page.getByLabel("导入记录").getByText("FIN 300", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("导入记录").getByText("FIN 999", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("导入映射候选项").getByText("EXACT_COURSE_CODE"),
  ).toBeVisible();
  await expect(
    page.getByLabel("导入映射候选项").getByText("UNMATCHED_COURSE_CODE"),
  ).toBeVisible();
  await expect(
    page.getByLabel("数据导入边界").getByText("导入预览数据不是官方学校政策。"),
  ).toBeVisible();

  await page.getByRole("button", { name: /加载已保存导入/ }).click();
  await expect(importSummary.getByText("已保存导入")).toBeVisible();
});

test("home page loads the sanitized MyProgress sample for local verification", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSavedMyProgressImportApis(page);

  await page.goto("/");

  await page.getByRole("button", { name: /加载脱敏 MyProgress 示例/ }).click();

  const auditSummary = page.getByLabel("学业审核汇总");
  await expect(
    auditSummary.getByText("真实导入数据 - 已自动验证"),
  ).toBeVisible();
  await expect(
    page.getByText("脱敏本地测试数据仅为示例").first(),
  ).toBeVisible();
  const importSummary = page.getByLabel("数据导入预览汇总");
  await expect(importSummary.getByText("解析器确认字段")).toBeVisible();
  await expect(importSummary.getByText("异常", { exact: true })).toBeVisible();
  await expect(
    importSummary.getByText("已通过", { exact: true }),
  ).toBeVisible();
  await expect(importSummary.getByText("提取的 MyProgress 行")).toBeVisible();
  await expect(importSummary.getByText("85")).toBeVisible();
  await expect(auditSummary.getByText("Finance, BS")).toBeVisible();
  await expect(auditSummary.getByText("104.0 / 120.0")).toBeVisible();
  await expect(auditSummary.getByText("86.67%")).toBeVisible();
});

test("home page shows read-only section monitoring alerts and manual checklist", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulSectionMonitoringApis(page);

  await page.goto("/");

  await expect(
    page
      .getByLabel("课节监控", { exact: true })
      .getByRole("heading", { name: "课节监控", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "课节监控基于用户触发的导入数据，可能与官方门户不同。 必须在官方注册门户人工核对。",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "本系统不会注册、drop、swap、waitlist、提交表单或执行任何门户操作。",
    ),
  ).toBeVisible();

  await expect(
    page.getByLabel("已监控课节").getByText("FIN 403 001"),
  ).toBeVisible();
  await expect(page.getByLabel("参考性提醒")).toContainText("课节已开放");
  await expect(page.getByLabel("参考性提醒")).toContainText("已关闭 -> 开放");
  await expect(page.getByLabel("人工注册核对清单")).toContainText(
    "手动打开官方注册门户。",
  );
  await expect(page.getByLabel("人工注册核对清单")).toContainText(
    "如适合，必须由学生本人通过官方门户手动注册。",
  );
});

test("home page reviews and applies confirmed data import records", async ({
  page,
}) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulDataImportApis(page);

  await page.goto("/");
  await waitForClientReady(page);
  await page.getByLabel("示例导入").selectOption("mock-transcript-csv");
  await page.getByRole("button", { name: /预览导入/ }).click();

  await expect(
    page.getByRole("heading", { name: /数据审核与确认/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^创建审核$/ }).click();

  const reviewSummary = page.getByLabel("数据审核汇总");
  await expect(reviewSummary.getByText("审核中")).toBeVisible();
  await expect(
    page
      .getByLabel("审核记录")
      .locator(".comparison-row")
      .filter({ hasText: "FIN 300" }),
  ).toBeVisible();

  await page
    .getByLabel("审核记录")
    .getByRole("button", { name: /^确认$/ })
    .first()
    .click();
  await expect(page.getByLabel("审核记录").getByText("已确认")).toBeVisible();

  await page.getByRole("button", { name: /^试运行$/ }).click();
  await expect(
    page
      .getByLabel("数据应用结果")
      .getByText("WOULD_CREATE_STUDENT_COURSE_ATTEMPT"),
  ).toBeVisible();

  await page.getByRole("button", { name: /^应用已确认记录$/ }).click();
  await expect(
    page.getByLabel("数据应用结果").getByText("CREATED_STUDENT_COURSE_ATTEMPT"),
  ).toBeVisible();
  await expect(
    page.getByLabel("数据应用结果").getByText("ADVISOR_REVIEW_REQUIRED"),
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
  await waitForClientReady(page);
  await page.getByRole("button", { name: "启用演示工作流" }).click();
  await page.getByRole("button", { name: /生成课表/ }).click();

  await expect(
    page.getByRole("heading", { name: "课表优化结构错误" }),
  ).toBeVisible();
  await expect(page.getByText(/意外的课表优化响应结构/)).toBeVisible();
});
