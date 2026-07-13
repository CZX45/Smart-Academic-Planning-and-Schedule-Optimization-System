import { describe, expect, it } from "vitest";

import { parsePublicEnv, parseRuntimeApiBaseUrl } from "./env";

describe("web public environment validation", () => {
  it("accepts an explicit HTTP API base URL for local development", () => {
    expect(
      parsePublicEnv({
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
      }),
    ).toEqual({
      apiBaseUrl: "http://localhost:8000",
    });
  });

  it("accepts an explicit HTTPS API base URL for production deployments", () => {
    expect(
      parsePublicEnv({
        NEXT_PUBLIC_API_BASE_URL: "https://api.example.edu",
      }),
    ).toEqual({
      apiBaseUrl: "https://api.example.edu",
    });
  });

  it("fails safely when the public API base URL is missing", () => {
    expect(() => parsePublicEnv({})).toThrow(
      "NEXT_PUBLIC_API_BASE_URL is required",
    );
  });

  it("fails safely when the public API base URL is malformed", () => {
    expect(() =>
      parsePublicEnv({
        NEXT_PUBLIC_API_BASE_URL: "ftp://api.example.edu",
      }),
    ).toThrow("NEXT_PUBLIC_API_BASE_URL must be an http(s) URL");
  });

  it("reads the dynamic API base URL from the desktop runtime query bridge", () => {
    expect(
      parseRuntimeApiBaseUrl("?api_base_url=http%3A%2F%2F127.0.0.1%3A43127"),
    ).toBe("http://127.0.0.1:43127");
  });

  it("does not invent an API endpoint when the runtime bridge is absent", () => {
    expect(parseRuntimeApiBaseUrl("")).toBeUndefined();
  });
});
