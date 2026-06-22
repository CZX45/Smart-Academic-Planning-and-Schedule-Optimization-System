import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
const source = resolve("../../apps/api/openapi.json");
const target = resolve("src/generated/openapi.json");
if (!existsSync(source)) {
  console.error(
    "OpenAPI source not found. Run pnpm --filter @sapsos/api openapi first.",
  );
  process.exit(1);
}
mkdirSync(dirname(target), { recursive: true });
copyFileSync(source, target);
console.log(`Copied ${source} to ${target}`);
