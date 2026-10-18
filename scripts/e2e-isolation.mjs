import { mkdirSync, mkdtempSync } from "node:fs";
import { join, resolve } from "node:path";

/** Always allocate a fresh synthetic workspace. Never accept a caller's database. */
export function createIsolatedEnvironment(repositoryRoot) {
  const parent = resolve(repositoryRoot, ".cache", "e2e");
  mkdirSync(parent, { recursive: true });
  const runRoot = mkdtempSync(join(parent, "synthetic-"));
  const appdata = join(runRoot, "appdata");
  mkdirSync(appdata);
  return {
    runRoot,
    env: {
      DATABASE_URL: `sqlite+pysqlite:///${join(runRoot, "synthetic.db").replaceAll("\\", "/")}`,
      LOCALAPPDATA: appdata,
      RUNTIME_MANIFEST_PATH: join(runRoot, "runtime.json"),
      PRODUCT_MODE: "LOCAL_DESKTOP",
      AUTH_MODE: "local",
      ENVIRONMENT: "test",
    },
  };
}
