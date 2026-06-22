import { expect, test } from '@playwright/test';

test('home page shows API health panel and required mock warnings', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Smart Academic Planning/ })).toBeVisible();
  await expect(page.getByText(/Backend health/)).toBeVisible();
  await expect(page.getByText('API connected')).toBeVisible();
  await expect(page.getByText('Mock data — not official university policy.')).toBeVisible();
  await expect(page.getByText('Advisor confirmation is required for high-impact academic guidance.')).toBeVisible();
});

test('home page reports when the API health request is unavailable', async ({ page }) => {
  await page.route('http://localhost:8000/health', async (route) => {
    await route.abort('failed');
  });

  await page.goto('/');

  await expect(page.getByText('API unavailable')).toBeVisible();
  await expect(page.getByText(/Health check request failed|Failed to fetch|NetworkError/)).toBeVisible();
});
