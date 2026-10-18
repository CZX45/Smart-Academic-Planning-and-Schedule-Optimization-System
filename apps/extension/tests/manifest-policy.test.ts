import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const extensionRoot = process.cwd();

function readProjectFile(path: string): string {
  return readFileSync(join(extensionRoot, path), "utf8");
}

describe("browser extension safety policy", () => {
  it("uses Manifest V3 with minimal permissions and local API host permissions only", () => {
    const manifest = JSON.parse(readProjectFile("manifest.json")) as {
      manifest_version: number;
      permissions?: string[];
      host_permissions?: string[];
      optional_host_permissions?: string[];
      content_scripts?: unknown[];
      side_panel?: { default_path?: string };
    };

    expect(manifest.manifest_version).toBe(3);
    expect(manifest.permissions?.sort()).toEqual([
      "activeTab",
      "scripting",
      "sidePanel",
      "storage",
    ]);
    expect(manifest.side_panel?.default_path).toBe("src/monitor/index.html");
    expect(manifest.host_permissions ?? []).toEqual([
      "http://localhost/*",
      "http://127.0.0.1/*",
    ]);
    expect(manifest.optional_host_permissions ?? []).toEqual([
      "https://kean-ss.colleague.elluciancloud.com/*",
    ]);
    expect(manifest.content_scripts ?? []).toEqual([]);
    expect(JSON.stringify(manifest)).not.toContain("<all_urls>");
    expect(JSON.stringify(manifest)).not.toContain("https://*/*");
    expect(JSON.stringify(manifest)).not.toContain("http://*/*");
  });

  it("keeps extraction user-triggered and confirmation-gated", () => {
    const popup = readProjectFile("src/popup/popup.ts");
    const manifest = readProjectFile("manifest.json");
    const serviceWorker = readProjectFile("src/background/service-worker.ts");

    expect(popup).toContain("confirmImportButton");
    expect(popup).toContain("extractCurrentPageButton");
    expect(popup).toContain("startKeanImportButton");
    expect(popup).toContain("createDataImportRequestFromExtraction");
    expect(popup).not.toContain("setInterval");
    expect(popup).not.toContain("setTimeout");
    expect(popup).not.toContain("chrome.alarms");
    expect(popup).not.toContain("chrome.cookies");
    expect(manifest).not.toContain("alarms");
    expect(manifest).not.toContain("cookies");
    expect(serviceWorker).not.toContain("setInterval");
    expect(serviceWorker).not.toContain("chrome.alarms");
    expect(serviceWorker).not.toContain("activeCatalogBatch");
    expect(serviceWorker).not.toContain("conservativeDelay");
    expect(serviceWorker).not.toContain("setTimeout");
    expect(serviceWorker).toContain("chrome.tabs.onUpdated.addListener");
    expect(serviceWorker).toContain("chrome.tabs.onRemoved.addListener");
    expect(serviceWorker).toContain("SAPSOS_PAIR_EXTENSION");
    expect(serviceWorker).toContain("SAPSOS_SUBMIT_IMPORT");
    expect(serviceWorker).toContain("X-SAPSOS-Extension-Credential");
  });

  it("uses direct active-tab script execution instead of a content-script receiver for popup extraction", () => {
    const browserActions = readProjectFile("src/popup/browser-actions.ts");

    expect(browserActions).toContain("chromeApi.scripting.executeScript");
    expect(browserActions).toContain("snapshotVisibleAcademicPage");
    expect(browserActions).not.toContain("tabs.sendMessage");
    expect(browserActions).not.toContain("SAPSOS_EXTRACT_PAGE");
    expect(browserActions).not.toContain("dist/content/content-script.js");
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

  it("shows required Kean import boundary copy in the popup", () => {
    const popupHtml = readProjectFile("src/popup/index.html");
    const normalizedPopupHtml = popupHtml.replace(/\s+/g, " ");

    expect(popupHtml).toContain("Start Kean Academic Import");
    expect(popupHtml).toContain("Detected page type");
    expect(popupHtml).toContain("Non-official data");
    expect(popupHtml).toContain("Manual review required");
    expect(popupHtml).toContain("Local app/API");
    expect(popupHtml).toContain("The extension does not log in for you.");
    expect(popupHtml).toContain(
      "The extension does not collect your password.",
    );
    expect(normalizedPopupHtml).toContain(
      "The extension only reads academic-planning data from Kean Student Portal pages you authorize.",
    );
    expect(popupHtml).toContain(
      "Imported data is non-official and requires manual review.",
    );
    expect(normalizedPopupHtml).toContain(
      "The system does not register, drop, swap, waitlist, reserve seats, or grab seats.",
    );
  });

  it("does not expose credential-like extraction fields or background polling primitives", () => {
    const extractionSource = [
      readProjectFile("src/content/content-script.ts"),
      readProjectFile("src/content/extractors.ts"),
      readProjectFile("src/shared/types.ts"),
    ].join("\n");

    expect(extractionSource).not.toMatch(
      /\b(password|portal_password|credential|session_cookie|saml|mfa|captcha)\b/i,
    );
    const serviceWorker = readProjectFile("src/background/service-worker.ts");
    expect(serviceWorker).not.toMatch(
      /\b(password|portal_password|session_cookie|saml|mfa|captcha)\b/i,
    );
    expect(serviceWorker).not.toMatch(
      /\b(setInterval|setTimeout|chrome\.alarms|MutationObserver)\b/,
    );
  });

  it("limits batch page actions to reviewed Catalog search and pagination controls", () => {
    const batchPage = readProjectFile("src/content/catalog-batch-page.ts");

    expect(batchPage).toContain("#submit-search-form");
    expect(batchPage).toContain("Link to results page");
    expect(batchPage).not.toMatch(
      /add.?course|register|drop|swap|waitlist|seat.?grab/i,
    );
    expect(batchPage).toContain("currentCatalogView.click()");
    expect(batchPage).toContain("CATALOG_SEARCH_PREPARED_AND_SUBMITTED");
    expect(batchPage).toContain("acknowledgedSubmit.click()");
    expect(batchPage.indexOf("currentCatalogView.click()")).toBeLessThan(
      batchPage.indexOf("acknowledgedSubmit.click()"),
    );
    expect(
      batchPage.indexOf("SAPSOS_CATALOG_PREPARATION_ACKNOWLEDGED"),
    ).toBeLessThan(batchPage.indexOf("acknowledgedSubmit.click()"));
    expect(batchPage).not.toContain("catalogView.checked = true");
    expect(batchPage.match(/\.click\(\)/g)).toHaveLength(3);
    expect(batchPage).toContain("new MutationObserver");
    expect(batchPage).toContain("BATCH_CATALOG_RESULT_VIEW_MISMATCH");
  });

  it("ships a persistent monitor with the complete reconnectable batch state", () => {
    const monitorHtml = readProjectFile("src/monitor/index.html");
    const monitorSource = readProjectFile("src/monitor/monitor.ts");
    const popupHtml = readProjectFile("src/popup/index.html");

    for (const field of [
      "Batch status",
      "Current subject",
      "Current page",
      "Subjects completed",
      "Courses captured",
      "Unique courses",
      "Duplicates",
      "Warnings",
      "Elapsed time",
      "Estimated remaining",
      "Pause",
      "Resume",
      "Cancel",
    ]) {
      expect(monitorHtml).toContain(field);
    }
    expect(monitorSource).toContain("chrome.storage.onChanged.addListener");
    expect(monitorSource).not.toContain("setInterval");
    expect(monitorSource).not.toContain("setTimeout");
    expect(popupHtml).toContain("Open batch monitor");
  });

  it("keeps the injected content script standalone for programmatic injection", () => {
    const contentScript = readProjectFile("src/content/content-script.ts");

    expect(contentScript).toContain("chrome?.runtime?.onMessage.addListener");
    expect(contentScript).not.toMatch(/^import\s+(?!type\b)/m);
  });

  it("keeps content-script DOM scanning message-triggered and idempotent", () => {
    const contentScript = readProjectFile("src/content/content-script.ts");

    expect(contentScript).toContain("SAPSOS_CONTENT_SCRIPT_READY");
    expect(contentScript).toContain("EXTRACTION_LIMIT_REACHED");
    expect(
      contentScript.match(/readAcademicPageSnapshot\(document\)/g),
    ).toHaveLength(1);
    expect(
      contentScript.indexOf("readAcademicPageSnapshot(document)"),
    ).toBeGreaterThan(contentScript.indexOf("onMessage.addListener"));
    expect(contentScript).not.toContain("document_start");
    expect(contentScript).not.toContain("document_idle");
    expect(contentScript).not.toContain("window.onload");
  });
});
