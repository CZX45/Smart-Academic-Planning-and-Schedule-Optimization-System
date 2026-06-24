import { expect, test, type Page } from '@playwright/test';

const mockAuditRun = {
  id: '00000000-0000-4000-8000-000000000001',
  student_profile_id: '74874476-4024-5e2d-807a-fbb4ab620249',
  program_version_id: 'f65bee76-6061-515f-a3df-cdf5567514af',
  status: 'COMPLETED_WITH_WARNINGS',
  engine_version: 'phase-3a-degree-audit-v1',
  calculation_mode: 'PROJECTED',
  started_at: '2026-06-23T00:00:00Z',
  completed_at: '2026-06-23T00:00:01Z',
  total_required_credits: '120.0',
  completed_credits: '18.0',
  in_progress_credits: '3.0',
  planned_credits: '3.0',
  remaining_credits: '96.0',
  completion_percentage: '20.00',
  source_snapshot_hash: 'e2e-fixture',
  created_at: '2026-06-23T00:00:00Z',
  updated_at: '2026-06-23T00:00:01Z',
};

const mockRequirements = [
  {
    id: '00000000-0000-4000-8000-000000000011',
    degree_audit_run_id: mockAuditRun.id,
    requirement_node_id: '00000000-0000-4000-8000-000000000012',
    requirement_code: 'MOCK-REQ',
    requirement_name: 'Mock Finance Foundations',
    requirement_type: 'REQUIRED_COURSE',
    status: 'SATISFIED',
    required_credits: '3.0',
    satisfied_credits: '3.0',
    remaining_credits: '0.0',
    required_courses: 1,
    satisfied_courses: 1,
    remaining_courses: 0,
    minimum_grade: 'C',
    explanation: 'Completed by mock coursework.',
    display_order: 10,
    applications: [
      {
        id: '00000000-0000-4000-8000-000000000013',
        course_id: '00000000-0000-4000-8000-000000000014',
        course_code: 'FIN 301',
        course_title: 'Mock Finance Foundations',
        student_course_attempt_id: '00000000-0000-4000-8000-000000000015',
        application_type: 'COURSE_ATTEMPT',
        credit_amount: '3.0',
        grade: 'B',
        is_completed: true,
        is_in_progress: false,
        is_planned: false,
        is_shared: false,
        explanation: 'Applied completed attempt.',
      },
    ],
    warnings: [
      {
        id: '00000000-0000-4000-8000-000000000016',
        degree_audit_run_id: mockAuditRun.id,
        requirement_evaluation_id: '00000000-0000-4000-8000-000000000011',
        warning_code: 'PENDING_TRANSFER',
        severity: 'WARNING',
        message: 'Pending transfer credit is not applied.',
        requires_advisor_confirmation: true,
        created_at: '2026-06-23T00:00:00Z',
      },
    ],
  },
];

const mockScenario = {
  id: '00000000-0000-4000-8000-000000000101',
  student_profile_id: '74874476-4024-5e2d-807a-fbb4ab620249',
  name: 'Add Accounting Minor',
  scenario_type: 'ADD_MINOR',
  status: 'COMPLETED_WITH_WARNINGS',
  base_program_version_id: 'f65bee76-6061-515f-a3df-cdf5567514af',
  engine_version: 'phase-3b-academic-scenario-v1',
  created_at: '2026-06-23T00:00:00Z',
  updated_at: '2026-06-23T00:00:01Z',
  completed_at: '2026-06-23T00:00:01Z',
};

const mockScenarioPrograms = [
  {
    id: '00000000-0000-4000-8000-000000000111',
    academic_plan_scenario_id: mockScenario.id,
    program_version_id: 'f65bee76-6061-515f-a3df-cdf5567514af',
    relationship_type: 'PRIMARY_MAJOR',
    is_existing_program: true,
    is_hypothetical: false,
    priority: 0,
    program_code: 'BSFIN',
    program_name: 'Mock BS Finance',
    source: { source_type: 'MOCK', is_official: false },
    created_at: '2026-06-23T00:00:00Z',
  },
  {
    id: '00000000-0000-4000-8000-000000000112',
    academic_plan_scenario_id: mockScenario.id,
    program_version_id: '00000000-0000-4000-8000-000000000113',
    relationship_type: 'MINOR',
    is_existing_program: false,
    is_hypothetical: true,
    priority: 10,
    program_code: 'MINACCT',
    program_name: 'Mock Accounting Minor',
    source: { source_type: 'MOCK', is_official: false },
    created_at: '2026-06-23T00:00:00Z',
  },
];

const mockScenarioAudits = [
  { scenario_program: mockScenarioPrograms[0], degree_audit_run: mockAuditRun },
  {
    scenario_program: mockScenarioPrograms[1],
    degree_audit_run: {
      ...mockAuditRun,
      id: '00000000-0000-4000-8000-000000000114',
      program_version_id: mockScenarioPrograms[1].program_version_id,
      remaining_credits: '9.0',
    },
  },
];

const mockScenarioAllocations = [
  {
    id: '00000000-0000-4000-8000-000000000121',
    academic_plan_scenario_id: mockScenario.id,
    student_course_attempt_id: '00000000-0000-4000-8000-000000000122',
    transfer_credit_id: null,
    course_id: '00000000-0000-4000-8000-000000000123',
    course_code: 'ACCT 300',
    course_title: 'Mock Accounting Analytics',
    program_version_id: mockScenarioPrograms[1].program_version_id,
    requirement_node_id: '00000000-0000-4000-8000-000000000124',
    requirement_code: 'ACCT-MINOR-CORE',
    allocation_type: 'SHARED',
    credit_amount: '3.0',
    is_shared: true,
    is_unique_to_program: false,
    allocation_rank: 1,
    reason_code: 'SHARED_BY_RULE',
    explanation: 'Shared because both requirements and the mock rule allow overlap.',
    created_at: '2026-06-23T00:00:00Z',
  },
  {
    id: '00000000-0000-4000-8000-000000000125',
    academic_plan_scenario_id: mockScenario.id,
    student_course_attempt_id: '00000000-0000-4000-8000-000000000126',
    transfer_credit_id: null,
    course_id: '00000000-0000-4000-8000-000000000127',
    course_code: 'ECON 250',
    course_title: 'Mock Managerial Economics',
    program_version_id: mockScenarioPrograms[1].program_version_id,
    requirement_node_id: '00000000-0000-4000-8000-000000000128',
    requirement_code: 'ACCT-MINOR-UNIQUE',
    allocation_type: 'UNIQUE_SECONDARY',
    credit_amount: '3.0',
    is_shared: false,
    is_unique_to_program: true,
    allocation_rank: 2,
    reason_code: 'UNIQUE_SECONDARY_CREDIT',
    explanation: 'Counts only toward the secondary program.',
    created_at: '2026-06-23T00:00:00Z',
  },
];

const mockScenarioWarnings = [
  {
    id: '00000000-0000-4000-8000-000000000131',
    academic_plan_scenario_id: mockScenario.id,
    scenario_program_id: mockScenarioPrograms[1].id,
    warning_code: 'ESTIMATED_ADDITIONAL_CREDITS',
    severity: 'WARNING',
    message: 'Additional credits are an estimate and do not predict graduation timing.',
    requires_advisor_confirmation: true,
    created_at: '2026-06-23T00:00:00Z',
  },
];

const mockScenarioComparison = {
  academic_plan_scenario_id: mockScenario.id,
  completed_credits: '18.0',
  in_progress_credits: '3.0',
  planned_credits: '3.0',
  remaining_requirement_credits: '12.0',
  shared_credits: '3.0',
  unique_secondary_credits: '6.0',
  estimated_additional_credits: '9.0',
  unresolved_requirements: 4,
  manual_review_count: 1,
  completion_percentage: '82.50',
  is_estimate: true,
  created_at: '2026-06-23T00:00:00Z',
};

async function mockSuccessfulAuditApis(page: Page) {
  await page.route(
    'http://localhost:8000/api/v1/students/*/degree-audits/latest',
    async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify(mockAuditRun),
      });
    },
  );
  await page.route(
    'http://localhost:8000/api/v1/degree-audits/*/requirements',
    async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify(mockRequirements),
      });
    },
  );
}

async function mockSuccessfulScenarioApis(page: Page) {
  await page.route('http://localhost:8000/api/v1/academic-scenarios', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify(mockScenario),
      });
      return;
    }
    await route.continue();
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/*/programs', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(mockScenarioPrograms) });
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/*/audits', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(mockScenarioAudits) });
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/*/allocations', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(mockScenarioAllocations) });
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/*/warnings', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(mockScenarioWarnings) });
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/*/comparison', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(mockScenarioComparison) });
  });
  await page.route('http://localhost:8000/api/v1/students/*/academic-scenarios', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([mockScenario, { ...mockScenario, id: '00000000-0000-4000-8000-000000000201', name: 'Add Economics Minor' }]),
    });
  });
  await page.route('http://localhost:8000/api/v1/academic-scenarios/compare', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        mockScenarioComparison,
        { ...mockScenarioComparison, academic_plan_scenario_id: '00000000-0000-4000-8000-000000000201', estimated_additional_credits: '15.0' },
      ]),
    });
  });
}

test('home page shows degree progress shell and required mock warnings', async ({ page }) => {
  await mockSuccessfulAuditApis(page);

  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Degree Progress/ })).toBeVisible();
  await expect(page.getByText('API connected')).toBeVisible();
  await expect(page.getByText('Mock data — not official university policy.')).toBeVisible();
  await expect(page.getByText('Advisor confirmation is required for high-impact academic guidance.')).toBeVisible();
  await expect(page.getByText('Audit Mode')).toBeVisible();
  await expect(page.getByText('Mock Finance Foundations')).toBeVisible();
  await expect(page.getByText('PENDING_TRANSFER')).toBeVisible();
});

test('home page reports when the API health request is unavailable', async ({ page }) => {
  await page.route('http://localhost:8000/health', async (route) => {
    await route.abort('failed');
  });

  await page.goto('/');

  await expect(page.getByText('API unavailable')).toBeVisible();
  await expect(
    page.locator("section[aria-live='polite'] > p").filter({
      hasText: /Health check request failed|Failed to fetch|NetworkError/,
    }),
  ).toBeVisible();
});

test('home page reports when degree audit responses fail schema validation', async ({ page }) => {
  await page.route('http://localhost:8000/api/v1/students/*/degree-audits/latest', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ unexpected: true }),
    });
  });

  await page.goto('/');

  await expect(page.getByText('Audit unavailable')).toBeVisible();
  await expect(page.getByText(/unexpected degree audit response shape/i)).toBeVisible();
});

test('home page creates and compares what-if academic scenarios', async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await mockSuccessfulScenarioApis(page);

  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Explore Programs \/ What-if Analysis/ })).toBeVisible();
  await expect(page.getByText('Estimated additional credits do not predict graduation timing.')).toBeVisible();

  await page.getByLabel('Candidate program').selectOption('accounting-minor');
  await page.getByRole('button', { name: /Create scenario/ }).click();

  const scenarioSummary = page.getByLabel('What-if scenario summary');
  await expect(scenarioSummary.getByText('Mock Accounting Minor')).toBeVisible();
  await expect(scenarioSummary.getByText('Shared Credits')).toBeVisible();
  await expect(scenarioSummary.getByText('Unique Secondary Credits')).toBeVisible();
  await expect(scenarioSummary.getByText('Estimated Additional Credits')).toBeVisible();
  await expect(page.getByText('ACCT 300')).toBeVisible();
  await expect(page.getByText('ESTIMATED_ADDITIONAL_CREDITS')).toBeVisible();

  await page.getByRole('button', { name: /Compare saved scenarios/ }).click();
  await expect(page.getByText('Add Economics Minor')).toBeVisible();
});

test('home page reports what-if API and schema failures', async ({ page }) => {
  await mockSuccessfulAuditApis(page);
  await page.route('http://localhost:8000/api/v1/academic-scenarios', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ unexpected: true }) });
  });

  await page.goto('/');
  await page.getByRole('button', { name: /Create scenario/ }).click();

  await expect(page.getByText('What-if scenario unavailable')).toBeVisible();
  await expect(page.getByText(/unexpected academic scenario response shape/i)).toBeVisible();
});
