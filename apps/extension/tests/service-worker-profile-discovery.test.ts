import { afterEach, describe, expect, it, vi } from "vitest";

type MessageListener = (
  message: unknown,
  sender: { id?: string },
  sendResponse: (response: unknown) => void,
) => boolean;

async function loadWorker(options: {
  paired: boolean;
  fetchFails?: boolean;
  delayedPairingPersistence?: boolean;
}) {
  vi.resetModules();
  let listener: MessageListener | undefined;
  let storedPairing = options.paired
    ? {
        apiBaseUrl: "http://localhost:8000",
        credential: "worker-only-credential",
        protocolVersion: 1,
      }
    : undefined;
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    if (options.fetchFails) {
      throw new TypeError("Local API unavailable");
    }
    const url = String(input);
    if (url.endsWith("/local/pairing/complete")) {
      return Response.json({
        credential: "fresh-worker-only-credential",
        extension_id: "abcdefghijklmnopabcdefghijklmnop",
        protocol_version: 1,
      });
    }
    if (url.endsWith("/local/pairing/status")) {
      const headers = new Headers(init?.headers);
      if (headers.get("x-sapsos-extension-id") !== "extension-id") {
        return Response.json(
          {
            detail: {
              code: "approved_origin_required",
              message: "The local API request Origin is not approved.",
            },
          },
          { status: 403 },
        );
      }
      return Response.json({ paired: true, protocol_version: 1 });
    }
    return Response.json([
      {
        student: {
          id: "44444444-4444-4444-8444-444444444444",
          display_name: "Local learner",
        },
      },
    ]);
  });
  const chromeApi = {
    runtime: {
      id: "extension-id",
      getURL: (path: string) => `chrome-extension://extension-id/${path}`,
      onInstalled: { addListener: vi.fn() },
      onMessage: {
        addListener: (registered: MessageListener) => {
          listener = registered;
        },
      },
    },
    storage: {
      local: {
        get: (_keys: string[], callback: (stored: object) => void) => {
          callback(storedPairing ? { sapsosPairing: storedPairing } : {});
        },
        set: (
          value: { sapsosPairing?: typeof storedPairing },
          callback?: () => void,
        ) => {
          const persist = () => {
            storedPairing = value.sapsosPairing;
            callback?.();
          };
          if (options.delayedPairingPersistence) {
            setTimeout(persist, 10);
          } else {
            persist();
          }
        },
        remove: vi.fn(),
      },
      session: {
        get: (
          _keys: string[],
          callback: (stored: Record<string, unknown>) => void,
        ) => callback({}),
        set: (_value: unknown, callback?: () => void) => callback?.(),
        remove: (_keys: string[], callback?: () => void) => callback?.(),
      },
    },
    tabs: {
      get: vi.fn(),
      update: vi.fn(),
      create: vi.fn(),
      onUpdated: { addListener: vi.fn() },
      onRemoved: { addListener: vi.fn() },
    },
    scripting: { executeScript: vi.fn() },
  };
  vi.stubGlobal("chrome", chromeApi);
  vi.stubGlobal("fetch", fetchMock);
  await import("../src/background/service-worker.js");
  if (!listener) {
    throw new Error("Service worker did not register a message listener.");
  }
  return { listener, fetchMock };
}

async function requestProfiles(listener: MessageListener): Promise<unknown> {
  return await new Promise((resolve) => {
    listener(
      {
        type: "SAPSOS_GET_LOCAL_STUDENT_PROFILES",
        apiBaseUrl: "http://localhost:8000",
      },
      { id: "extension-id" },
      resolve,
    );
  });
}

async function requestPairing(listener: MessageListener): Promise<unknown> {
  return await new Promise((resolve) => {
    listener(
      {
        type: "SAPSOS_PAIR_EXTENSION",
        apiBaseUrl: "http://localhost:8000",
        code: "short-lived-code",
      },
      { id: "extension-id" },
      resolve,
    );
  });
}

async function requestPairingStatus(
  listener: MessageListener,
): Promise<unknown> {
  return await new Promise((resolve) => {
    listener(
      {
        type: "SAPSOS_GET_PAIRING_STATUS",
        apiBaseUrl: "http://localhost:8000",
      },
      { id: "extension-id" },
      resolve,
    );
  });
}

async function requestRemotePairing(
  listener: MessageListener,
): Promise<unknown> {
  return await new Promise((resolve) => {
    listener(
      {
        type: "SAPSOS_PAIR_EXTENSION",
        apiBaseUrl: "https://kean-ss.colleague.elluciancloud.com",
        code: "short-lived-code",
      },
      { id: "extension-id" },
      resolve,
    );
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("service worker local profile discovery", () => {
  it("reports pairing success only after the new credential is persisted", async () => {
    const { listener, fetchMock } = await loadWorker({
      paired: true,
      delayedPairingPersistence: true,
    });

    const pairingResponse = await requestPairing(listener);
    const profileResponse = await requestProfiles(listener);

    expect(pairingResponse).toMatchObject({ ok: true, status: 200 });
    expect(profileResponse).toMatchObject({ ok: true, status: 200 });
    const profileCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/v1/local-onboarding/student-profiles"),
    );
    expect(profileCall?.[1]?.headers).toMatchObject({
      "X-SAPSOS-Extension-Credential": "fresh-worker-only-credential",
      "X-SAPSOS-Extension-Id": "extension-id",
    });
  });

  it("identifies the Extension when Chromium omits Origin on a GET", async () => {
    const { listener } = await loadWorker({ paired: true });

    const response = await requestPairingStatus(listener);

    expect(response).toMatchObject({
      ok: true,
      status: 200,
      payload: { paired: true },
    });
  });

  it("keeps the pairing credential in the worker and signs the local GET", async () => {
    const { listener, fetchMock } = await loadWorker({ paired: true });

    const response = await requestProfiles(listener);

    expect(response).toMatchObject({ ok: true, status: 200 });
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe(
      "http://localhost:8000/api/v1/local-onboarding/student-profiles",
    );
    expect(init).toMatchObject({
      method: "GET",
      headers: expect.objectContaining({
        "X-SAPSOS-Extension-Credential": "worker-only-credential",
      }),
    });
    expect(init?.headers).not.toHaveProperty("authorization");
  });

  it("does not contact the API when no pairing credential exists", async () => {
    const { listener, fetchMock } = await loadWorker({ paired: false });

    const response = await requestProfiles(listener);

    expect(response).toMatchObject({
      ok: false,
      status: 401,
      payload: { code: "pairing_required" },
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a non-local pairing destination before any network request", async () => {
    const { listener, fetchMock } = await loadWorker({ paired: false });

    const response = await requestRemotePairing(listener);

    expect(response).toMatchObject({
      ok: false,
      status: 400,
      payload: { code: "local_api_required" },
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reports local API unavailability without exposing request details", async () => {
    const { listener, fetchMock } = await loadWorker({
      paired: true,
      fetchFails: true,
    });

    const response = await requestProfiles(listener);

    expect(response).toEqual({
      ok: false,
      status: 503,
      payload: { code: "local_api_unavailable" },
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
