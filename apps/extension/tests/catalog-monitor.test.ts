import { describe, expect, it, vi } from "vitest";

import { openCatalogBatchMonitor } from "../src/shared/catalog-monitor.js";

function monitorChrome(options: {
  sidePanelError?: string;
  fallbackError?: string;
}) {
  const runtime: {
    lastError?: { message?: string };
    getURL: (path: string) => string;
  } = {
    getURL: (path) => `chrome-extension://extension-id/${path}`,
  };
  const createdTabs: string[] = [];
  const sidePanelOpen = vi.fn(async () => {
    if (options.sidePanelError) throw new Error(options.sidePanelError);
  });
  return {
    api: {
      runtime,
      sidePanel: { open: sidePanelOpen },
      tabs: {
        create: (
          input: { url: string },
          callback: (tab?: { id?: number }) => void,
        ) => {
          createdTabs.push(input.url);
          if (options.fallbackError) {
            runtime.lastError = { message: options.fallbackError };
            callback();
            delete runtime.lastError;
            return;
          }
          callback({ id: 91 });
        },
      },
    },
    createdTabs,
    sidePanelOpen,
  };
}

describe("persistent Catalog monitor opener", () => {
  it("opens Side Panel directly inside the popup user gesture", async () => {
    const chrome = monitorChrome({});

    const result = await openCatalogBatchMonitor(chrome.api, 42);

    expect(result).toEqual({
      ok: true,
      method: "SIDE_PANEL",
      sidePanelAvailable: true,
      sidePanelError: null,
      fallbackError: null,
      monitorUrl: "chrome-extension://extension-id/src/monitor/index.html",
    });
    expect(chrome.sidePanelOpen).toHaveBeenCalledWith({ tabId: 42 });
    expect(chrome.createdTabs).toEqual([]);
  });

  it("falls back to one extension-owned monitor tab and retains the real Side Panel error", async () => {
    const chrome = monitorChrome({
      sidePanelError:
        "sidePanel.open() may only be called in response to a user gesture",
    });

    const result = await openCatalogBatchMonitor(chrome.api, 42);

    expect(result).toEqual({
      ok: true,
      method: "MONITOR_TAB",
      sidePanelAvailable: true,
      sidePanelError:
        "sidePanel.open() may only be called in response to a user gesture",
      fallbackError: null,
      monitorUrl: "chrome-extension://extension-id/src/monitor/index.html",
    });
    expect(chrome.createdTabs).toEqual([
      "chrome-extension://extension-id/src/monitor/index.html",
    ]);
  });

  it("returns both real errors when Side Panel and the monitor tab fail", async () => {
    const chrome = monitorChrome({
      sidePanelError: "Side Panel is unavailable in this Edge window",
      fallbackError: "Tabs cannot be edited right now",
    });

    const result = await openCatalogBatchMonitor(chrome.api, 42);

    expect(result).toEqual({
      ok: false,
      method: null,
      sidePanelAvailable: true,
      sidePanelError: "Side Panel is unavailable in this Edge window",
      fallbackError: "Tabs cannot be edited right now",
      monitorUrl: "chrome-extension://extension-id/src/monitor/index.html",
    });
  });
});
