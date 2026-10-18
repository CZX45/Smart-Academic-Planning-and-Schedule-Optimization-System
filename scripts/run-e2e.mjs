import { spawn } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const child = spawn(
  process.execPath,
  [
    resolve(root, "node_modules/@playwright/test/cli.js"),
    "test",
    ...process.argv.slice(2),
  ],
  { cwd: root, stdio: "inherit", windowsHide: true },
);
// The outer deadline also covers config loading and stuck test cleanup.
const timer = setTimeout(() => {
  console.error("E2E exceeded its 12-minute outer deadline.");
  if (process.platform === "win32" && child.pid !== undefined) {
    const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
      windowsHide: true,
      stdio: "inherit",
    });
    killer.on("exit", () => process.exit(124));
    setTimeout(() => process.exit(124), 10_000).unref();
  } else {
    child.kill("SIGKILL");
    process.exitCode = 124;
  }
}, 720_000);
child.on("error", (error) => {
  clearTimeout(timer);
  console.error(error.message);
  process.exitCode = 1;
});
child.on("exit", (code) => {
  clearTimeout(timer);
  process.exitCode = process.exitCode ?? code ?? 1;
});
