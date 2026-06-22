import { describe, expect, it } from "vitest";
import {
  ApiRequestError,
  ApiResponseSchemaError,
  HealthResponseSchema,
  ReadinessResponseSchema,
  fetchHealth,
} from "./index.js";

describe("HealthResponseSchema", () => {
  it("validates API health payloads", () => {
    expect(
      HealthResponseSchema.parse({
        status: "ok",
        service: "api",
        database_configured: true,
      }),
    ).toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });
});

describe("ReadinessResponseSchema", () => {
  it("validates API readiness payloads", () => {
    expect(
      ReadinessResponseSchema.parse({
        status: "ready",
        service: "api",
        database_ready: true,
      }),
    ).toEqual({
      status: "ready",
      service: "api",
      database_ready: true,
    });
  });
});

describe("fetchHealth", () => {
  it("returns parsed health payloads", async () => {
    const fetchFn = async () =>
      new Response(
        JSON.stringify({
          status: "ok",
          service: "api",
          database_configured: true,
        }),
      );

    await expect(fetchHealth("http://api.test", { fetchFn })).resolves.toEqual({
      status: "ok",
      service: "api",
      database_configured: true,
    });
  });

  it("reports non-2xx health responses", async () => {
    const fetchFn = async () => new Response("nope", { status: 500 });

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiRequestError,
    );
  });

  it("reports invalid health response schemas", async () => {
    const fetchFn = async () => new Response(JSON.stringify({ status: "ok" }));

    await expect(fetchHealth("http://api.test", { fetchFn })).rejects.toThrow(
      ApiResponseSchemaError,
    );
  });
});
