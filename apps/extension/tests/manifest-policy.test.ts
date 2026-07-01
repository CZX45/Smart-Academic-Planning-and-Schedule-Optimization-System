import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const extensionRoot = process.cwd();

function readProjectFile(path: string): string {
  return readFileSync(join(extensionRoot, path), "utf8");
}

describe("browser extension safety policy", () => {
  it("uses Manifest V3 with minimal permissions and no broad host permissions", () => {
    const manifest = JSON.parse(readProjectFile("manifest.json")) as {
      manifest_version: number;
      permissions?: string[];
      host_permissions?: string[];
    };

    expect(manifest.manifest_version).toBe(3);
    expect(manifest.permissions?.sort()).toEqual([
      "activeTab",
      "scripting",
      "storage",
    ]);
    expect(manifest.host_permissions ?? []).toEqual([]);
  });

  it("keeps extraction user-triggered and confirmation-gated", () => {
    const popup = readProjectFile("src/popup/popup.ts");
    const manifest = readProjectFile("manifest.json");
    const serviceWorker = readProjectFile("src/background/service-worker.ts");

    expect(popup).toContain("confirmImportButton");
    expect(popup).toContain("extractCurrentPageButton");
    expect(popup).toContain("createDataImportRequestFromExtraction");
    expect(popup).not.toContain("setInterval");
    expect(popup).not.toContain("chrome.alarms");
    expect(manifest).not.toContain("alarms");
    expect(serviceWorker).not.toContain("setInterval");
    expect(serviceWorker).not.toContain("chrome.alarms");
    expect(serviceWorker).not.toContain("fetch(");
  });

  it("does not include credential capture, portal submission, or registration automation code", () => {
    const source = [
      readProjectFile("src/content/content-script.ts"),
      readProjectFile("src/content/extractors.ts"),
      readProjectFile("src/popup/popup.ts"),
      readProjectFile("src/background/service-worker.ts"),
    ].join("\n");

    expect(source).not.toMatch(/type=["']password["']/i);
    expect(source).not.toMatch(/querySelectorAll\(["']input/i);
    expect(source).not.toMatch(/\.submit\(/i);
    expect(source).not.toMatch(/\.click\(/i);
    expect(source).not.toMatch(/register|drop|swap|seat.?grab/i);
    expect(source).not.toMatch(
      /waitlist(_join|Join|Action|Automation)|joinWaitlist/i,
    );
  });
});
