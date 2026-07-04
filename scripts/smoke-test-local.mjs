import { stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const webPort =
  process.env.LOCAL_WEB_PORT ?? process.env.PLAYWRIGHT_WEB_PORT ?? "3000";
const webUrl = process.env.LOCAL_WEB_URL ?? `http://localhost:${webPort}`;

const checks = [
  {
    name: "Web app",
    url: webUrl,
    suggestion:
      "Start the local stack with corepack pnpm app:up and confirm Docker Desktop is running. Set LOCAL_WEB_PORT when using a non-3000 web port.",
  },
  {
    name: "API health",
    url: "http://localhost:8000/health",
    suggestion:
      "Check Docker Compose logs with docker compose logs api and confirm port 8000 is free.",
  },
  {
    name: "API docs",
    url: "http://localhost:8000/docs",
    suggestion:
      "Confirm the FastAPI container is healthy and exposing /docs on port 8000.",
  },
  {
    name: "API readiness and database",
    url: "http://localhost:8000/ready",
    suggestion:
      "Confirm the PostgreSQL container is healthy and migrations completed.",
  },
];

const extensionFiles = [
  "manifest.json",
  "src/popup/index.html",
  "dist/content/content-script.js",
  "dist/popup/popup.js",
  "dist/background/service-worker.js",
].map((path) => join(repoRoot, "dist", "extension-unpacked", path));

async function fetchWithTimeout(url, timeoutMs = 5000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function checkEndpoint(check) {
  try {
    const response = await fetchWithTimeout(check.url);
    await response.arrayBuffer().catch(() => undefined);
    if (response.ok) {
      console.log(`[PASS] ${check.name}: ${check.url}`);
      return true;
    }
    console.error(
      `[FAIL] ${check.name}: HTTP ${response.status} at ${check.url}`,
    );
    console.error(`       ${check.suggestion}`);
    return false;
  } catch (error) {
    console.error(`[FAIL] ${check.name}: ${check.url}`);
    console.error(
      `       ${error instanceof Error ? error.message : "Request failed."}`,
    );
    console.error(`       ${check.suggestion}`);
    return false;
  }
}

async function checkExtensionPackage() {
  const missing = [];
  for (const file of extensionFiles) {
    try {
      await stat(file);
    } catch {
      missing.push(file);
    }
  }
  if (missing.length === 0) {
    console.log("[PASS] Browser extension package: dist/extension-unpacked");
    return true;
  }
  console.error("[FAIL] Browser extension package is incomplete.");
  for (const file of missing) {
    console.error(`       Missing: ${file}`);
  }
  console.error("       Run: corepack pnpm extension:package");
  return false;
}

console.log("Running local smoke test.");
console.log("");

const endpointResults = [];
for (const check of checks) {
  endpointResults.push(await checkEndpoint(check));
}
endpointResults.push(await checkExtensionPackage());

if (endpointResults.every(Boolean)) {
  console.log("");
  console.log("Local smoke test passed.");
} else {
  console.error("");
  console.error(
    "Local smoke test failed. Fix the failed checks above and re-run:",
  );
  console.error("corepack pnpm app:smoke");
  process.exitCode = 1;
}
