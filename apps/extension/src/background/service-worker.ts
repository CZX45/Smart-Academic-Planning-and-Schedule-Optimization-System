type PairingRecord = {
  apiBaseUrl: string;
  credential: string;
  protocolVersion: number;
};

type Message =
  | { type: "SAPSOS_PAIR_EXTENSION"; apiBaseUrl: string; code: string }
  | { type: "SAPSOS_GET_PAIRING_STATUS"; apiBaseUrl: string }
  | {
      type: "SAPSOS_SUBMIT_IMPORT";
      apiBaseUrl: string;
      request: Record<string, unknown>;
    };

type ChromeRuntime = {
  id?: string;
  onInstalled: { addListener: (listener: () => void) => void };
  onMessage: {
    addListener: (
      listener: (
        message: Message,
        sender: { id?: string },
        sendResponse: (response: unknown) => void,
      ) => boolean,
    ) => void;
  };
};

type ChromeStorage = {
  local: {
    get: (
      keys: string[],
      callback: (value: { sapsosPairing?: PairingRecord }) => void,
    ) => void;
    set: (value: { sapsosPairing?: PairingRecord }) => void;
    remove: (keys: string[]) => void;
  };
};

declare const chrome: { runtime: ChromeRuntime; storage: ChromeStorage };

async function responsePayload(response: Response): Promise<Record<string, unknown>> {
  const payload: unknown = await response.json().catch(() => ({}));
  return typeof payload === "object" && payload !== null
    ? (payload as Record<string, unknown>)
    : {};
}

function extensionRequestHeaders(credential: string): Record<string, string> {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const nonce = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return {
    "content-type": "application/json",
    "X-SAPSOS-Extension-Credential": credential,
    "X-SAPSOS-Extension-Nonce": nonce,
    "X-SAPSOS-Extension-Timestamp": String(Date.now()),
  };
}

function sendJson(
  sendResponse: (response: unknown) => void,
  response: Response,
): Promise<void> {
  return responsePayload(response).then((payload) => {
    sendResponse({ ok: response.ok, status: response.status, payload });
  });
}

async function handleMessage(message: Message, sendResponse: (response: unknown) => void): Promise<void> {
  if (message.type === "SAPSOS_PAIR_EXTENSION") {
    const response = await fetch(`${message.apiBaseUrl.replace(/\/+$/, "")}/local/pairing/complete`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ code: message.code, protocol_version: 1 }),
    });
    const payload = await responsePayload(response);
    if (response.ok && typeof payload.credential === "string") {
      chrome.storage.local.set({
        sapsosPairing: {
          apiBaseUrl: message.apiBaseUrl,
          credential: payload.credential,
          protocolVersion: Number(payload.protocol_version),
        },
      });
    }
    sendResponse({ ok: response.ok, status: response.status, payload });
    return;
  }
  if (message.type === "SAPSOS_GET_PAIRING_STATUS") {
    const response = await fetch(`${message.apiBaseUrl.replace(/\/+$/, "")}/local/pairing/status`);
    await sendJson(sendResponse, response);
    return;
  }
  chrome.storage.local.get(["sapsosPairing"], async (stored) => {
    const pairing = stored.sapsosPairing;
    if (!pairing || pairing.apiBaseUrl !== message.apiBaseUrl) {
      sendResponse({ ok: false, status: 401, payload: { code: "pairing_required" } });
      return;
    }
    const response = await fetch(`${message.apiBaseUrl.replace(/\/+$/, "")}/api/v1/data-imports`, {
      method: "POST",
      headers: extensionRequestHeaders(pairing.credential),
      body: JSON.stringify(message.request),
    });
    await sendJson(sendResponse, response);
  });
}

chrome.runtime.onInstalled.addListener(() => undefined);
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== undefined && sender.id !== chrome.runtime.id) {
    sendResponse({ ok: false, status: 403, payload: { code: "invalid_sender" } });
    return false;
  }
  void handleMessage(message, sendResponse).catch(() => {
    sendResponse({ ok: false, status: 503, payload: { code: "local_api_unavailable" } });
  });
  return true;
});
