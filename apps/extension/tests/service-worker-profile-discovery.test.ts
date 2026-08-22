import { afterEach, describe, expect, it, vi } from "vitest";

type MessageListener = (
  message: unknown,
  sender: { id?: string },
  sendResponse: (response: unknown) => void,
) => boolean;

async function loadWorker(options: { paired: boolean }) {
  vi.resetModules();
  let listener: MessageListener | undefined;
  const fetchMock = vi.fn<typeof fetch>(async () =>
    Response.json([
      {
        student: {
          id: "44444444-4444-4444-8444-444444444444",
          display_name: "Local learner",
        },
      },
    ]),
  );
  const chromeApi = {
    runtime: {
      id: "extension-id",
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
          callback(
            options.paired
              ? {
                  sapsosPairing: {
                    apiBaseUrl: "http://localhost:8000",
                    credential: "worker-only-credential",
                    protocolVersion: 1,
                  },
                }
              : {},
          );
        },
        set: vi.fn(),
        remove: vi.fn(),
      },
    },
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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("service worker local profile discovery", () => {
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
});
