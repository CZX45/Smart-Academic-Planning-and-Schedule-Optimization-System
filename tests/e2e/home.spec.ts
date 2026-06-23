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
