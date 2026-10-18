import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";
import { createIsolatedEnvironment } from "../e2e-isolation.mjs";

test("E2E ignores inherited database settings and allocates distinct synthetic roots", () => {
  const root = mkdtempSync(join(tmpdir(), "sapsos-isolation-test-"));
  const first = createIsolatedEnvironment(root);
  const second = createIsolatedEnvironment(root);
  assert.notEqual(first.runRoot, second.runRoot);
  assert.ok(
    first.runRoot.startsWith(resolve(root, ".cache", "e2e") + "/") ||
      first.runRoot.startsWith(resolve(root, ".cache", "e2e") + "\\"),
  );
  assert.equal(
    first.env.DATABASE_URL,
    `sqlite+pysqlite:///${join(first.runRoot, "synthetic.db").replaceAll("\\", "/")}`,
  );
  assert.equal(first.env.LOCALAPPDATA, join(first.runRoot, "appdata"));
  assert.equal(first.env.PRODUCT_MODE, "LOCAL_DESKTOP");
  assert.equal(first.env.ENVIRONMENT, "test");
});

test("both E2E entrypoints prohibit service reuse and have finite deadlines", () => {
  const config = readFileSync(
    new URL("../../playwright.config.ts", import.meta.url),
    "utf8",
  );
  const runner = readFileSync(
    new URL("../run-e2e.mjs", import.meta.url),
    "utf8",
  );
  assert.equal((config.match(/reuseExistingServer: false/g) ?? []).length, 2);
  assert.match(config, /globalTimeout:/);
  assert.doesNotMatch(runner, /PLAYWRIGHT_SKIP_WEBSERVER/);
  assert.match(runner, /setTimeout/);
});
