import { spawn } from "node:child_process";
import { once } from "node:events";
import { resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const root = resolve(import.meta.dirname, "..");
const isWindows = process.platform === "win32";
const nextCli = resolve(
  root,
  "apps",
  "web",
  "node_modules",
  "next",
  "dist",
  "bin",
  "next",
);
const playwrightCli = resolve(
  root,
  "node_modules",
  "@playwright",
  "test",
  "cli.js",
);
const started = [];

function start(command, args, options = {}) {
  const { env, ...spawnOptions } = options;
  const shell = isWindows && command.toLowerCase().endsWith(".cmd");
  const child = spawn(command, args, {
    cwd: root,
    env: { ...process.env, ...env },
    shell,
    stdio: "inherit",
    windowsHide: true,
    ...spawnOptions,
  });
  started.push(child);
  return child;
}

async function isReady(url) {
  try {
    const response = await fetch(url);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitFor(url, child, label) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`${label} exited before ${url} became ready.`);
    }
    if (await isReady(url)) {
      return;
    }
    await delay(500);
  }
  throw new Error(`${label} did not become ready at ${url}.`);
}

async function run(command, args, options = {}) {
  const { env, ...spawnOptions } = options;
  const shell = isWindows && command.toLowerCase().endsWith(".cmd");
  const child = spawn(command, args, {
    cwd: root,
    env: { ...process.env, ...env },
    shell,
    stdio: "inherit",
    windowsHide: true,
    ...spawnOptions,
  });
  const [code, signal] = await once(child, "exit");
  if (signal) {
    return 1;
  }
  return code ?? 1;
}

async function stop(child) {
  if (
    child.exitCode !== null ||
    child.signalCode !== null ||
    child.pid === undefined
  ) {
    return;
  }

  if (isWindows) {
    const killer = spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
      stdio: "ignore",
      windowsHide: true,
    });
    await Promise.race([once(killer, "exit"), delay(5_000)]);
    if (killer.exitCode === null && killer.signalCode === null) {
      killer.kill("SIGKILL");
    }
    return;
  }

  child.kill("SIGTERM");
  await delay(500);
  if (child.exitCode === null && child.signalCode === null) {
    child.kill("SIGKILL");
  }
}

async function main() {
  const apiUrl = "http://127.0.0.1:8000/health";
  const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? "3000";
  const webUrl = `http://127.0.0.1:${webPort}`;

  let api;
  let web;

  try {
    if (!(await isReady(apiUrl))) {
      api = start(
        "python",
        ["-m", "app.run"],
        {
          cwd: resolve(root, "apps", "api"),
          env: {
            API_HOST: "127.0.0.1",
            API_PORT: "8000",
            PRODUCT_MODE: "LOCAL_DESKTOP",
            AUTH_MODE: "local",
            ...(process.env.DATABASE_URL
              ? { DATABASE_URL: process.env.DATABASE_URL }
              : {}),
          },
        },
      );
      await waitFor(apiUrl, api, "FastAPI test server");
    }

    if (!(await isReady(webUrl))) {
      web = start(
        process.execPath,
        [nextCli, "dev", "--hostname", "127.0.0.1", "--port", webPort],
        {
          cwd: resolve(root, "apps", "web"),
          env: {
            NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
          },
        },
      );
      await waitFor(webUrl, web, "Next.js test server");
    }

    process.exitCode = await run(
      process.execPath,
      [playwrightCli, "test", ...process.argv.slice(2)],
      {
        env: {
          PLAYWRIGHT_SKIP_WEBSERVER: "1",
        },
      },
    );
  } finally {
    await Promise.all(started.reverse().map((child) => stop(child)));
  }
}

main()
  .then(() => {
    process.exit(process.exitCode ?? 0);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
