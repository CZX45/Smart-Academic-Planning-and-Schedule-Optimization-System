import { expect, test } from '@playwright/test';

test('home page shows API health panel', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Smart Academic Planning/ })).toBeVisible();
  await expect(page.getByText(/Backend health/)).toBeVisible();
});
