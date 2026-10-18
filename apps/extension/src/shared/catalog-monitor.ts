export type CatalogMonitorChromeApi = {
  runtime: {
    lastError?: { message?: string };
    getURL: (path: string) => string;
  };
  tabs: {
    create: (
      input: { url: string },
      callback: (tab?: { id?: number }) => void,
    ) => void;
  };
  sidePanel?: {
    open: (options: { tabId?: number; windowId?: number }) => Promise<void>;
  };
};

export type CatalogMonitorOpenTarget =
  | number
  | { tabId: number }
  | { windowId: number };

export type CatalogMonitorOpenResult = {
  ok: boolean;
  method: "SIDE_PANEL" | "MONITOR_TAB" | null;
  sidePanelAvailable: boolean;
  sidePanelError: string | null;
  fallbackError: string | null;
  monitorUrl: string;
};

export function safeExtensionError(error: unknown): string {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : "Unknown extension error";
  return message
    .replace(
      /([?&](?:code|token|credential|nonce|authorization)=)[^&\s]+/gi,
      "$1[REDACTED]",
    )
    .replace(/(authorization:\s*)[^\s,;]+/gi, "$1[REDACTED]")
    .trim()
    .slice(0, 500);
}

export async function openCatalogBatchMonitor(
  chromeApi: CatalogMonitorChromeApi,
  target: CatalogMonitorOpenTarget,
): Promise<CatalogMonitorOpenResult> {
  const monitorUrl = chromeApi.runtime.getURL("src/monitor/index.html");
  const sidePanelAvailable = chromeApi.sidePanel !== undefined;
  let sidePanelError: string | null = null;

  if (chromeApi.sidePanel) {
    try {
      await chromeApi.sidePanel.open(
        typeof target === "number" ? { tabId: target } : target,
      );
      return {
        ok: true,
        method: "SIDE_PANEL",
        sidePanelAvailable,
        sidePanelError: null,
        fallbackError: null,
        monitorUrl,
      };
    } catch (error: unknown) {
      sidePanelError = safeExtensionError(error);
    }
  } else {
    sidePanelError = "SIDEPANEL_API_UNAVAILABLE";
  }

  const fallbackError = await new Promise<string | null>((resolve) => {
    chromeApi.tabs.create({ url: monitorUrl }, () => {
      const message = chromeApi.runtime.lastError?.message;
      resolve(message ? safeExtensionError(message) : null);
    });
  });
  return {
    ok: fallbackError === null,
    method: fallbackError === null ? "MONITOR_TAB" : null,
    sidePanelAvailable,
    sidePanelError,
    fallbackError,
    monitorUrl,
  };
}
