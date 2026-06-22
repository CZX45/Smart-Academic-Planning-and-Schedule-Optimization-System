import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  use: { baseURL: 'http://localhost:3000', trace: 'on-first-retry' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: 'pnpm --filter @sapsos/api dev', url: 'http://127.0.0.1:8000/health', reuseExistingServer: true },
    { command: 'pnpm --filter @sapsos/web dev', url: 'http://127.0.0.1:3000', reuseExistingServer: true },
  ],
});
