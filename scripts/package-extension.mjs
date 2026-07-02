import { cp, mkdir, rm, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const extensionRoot = join(repoRoot, "apps", "extension");
const compiledDist = join(extensionRoot, "dist");
const outputDir = join(repoRoot, "dist", "extension-unpacked");

async function pathExists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

if (!(await pathExists(compiledDist))) {
  console.error("Extension TypeScript output is missing.");
  console.error("Run: corepack pnpm --filter @sapsos/extension build");
  process.exit(1);
}

await rm(outputDir, { recursive: true, force: true });
await mkdir(join(outputDir, "src", "popup"), { recursive: true });
await cp(join(extensionRoot, "manifest.json"), join(outputDir, "manifest.json"));
await cp(
  join(extensionRoot, "src", "popup", "index.html"),
  join(outputDir, "src", "popup", "index.html"),
);
await cp(compiledDist, join(outputDir, "dist"), { recursive: true });

console.log("Browser extension package is ready.");
console.log("");
console.log(`Generated extension build folder: ${outputDir}`);
console.log("");
console.log("Manual load instructions:");
console.log("1. Open Chrome or Edge.");
console.log("2. Go to chrome://extensions or edge://extensions.");
console.log("3. Enable Developer Mode.");
console.log("4. Click Load unpacked.");
console.log("5. Select the generated extension build folder.");
