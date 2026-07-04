import { defineConfig, devices } from "@playwright/test";

const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? "3000";
const webBaseUrl = `http://localhost:${webPort}`;

const webServer =
  process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1"
    ? undefined
    : [
        {
          command:
            "cd apps/api && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
          url: "http://127.0.0.1:8000/health",
          reuseExistingServer: true,
          env: {
            DATABASE_URL:
              "postgresql+psycopg://sapsos:sapsos_dev_password@localhost:5432/sapsos",
          },
        },
        {
          command: `cd apps/web && node ./node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port ${webPort}`,
          url: `http://127.0.0.1:${webPort}`,
          reuseExistingServer: true,
          env: {
            NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
          },
        },
      ];

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: { baseURL: webBaseUrl, trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer,
});
