import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
import { createIsolatedEnvironment } from "./scripts/e2e-isolation.mjs";

const isolated = createIsolatedEnvironment(__dirname);
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT ?? "3000");
if (!Number.isInteger(webPort) || webPort < 1024 || webPort > 65535) {
  throw new Error("PLAYWRIGHT_WEB_PORT must be an unprivileged TCP port.");
}

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  globalTimeout: 600_000,
  workers: 2,
  outputDir: resolve(isolated.runRoot, "results"),
  use: {
    baseURL: `http://localhost:${webPort}`,
    trace: "retain-on-failure",
    headless: true,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "python -m app.seed_dev && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: resolve(__dirname, "apps/api"),
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 90_000,
      env: {
        ...isolated.env,
        API_PORT: "8000",
        CORS_ORIGINS: `http://localhost:${webPort},http://127.0.0.1:${webPort},http://127.0.0.1:3000`,
      },
    },
    {
      command: `node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port ${webPort}`,
      cwd: resolve(__dirname, "apps/web"),
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
      timeout: 90_000,
      env: { NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" },
    },
  ],
});
