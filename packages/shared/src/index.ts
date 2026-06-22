import { z } from "zod";

export const HealthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  database_configured: z.boolean(),
});

export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const ReadinessResponseSchema = z.object({
  status: z.union([z.literal("ready"), z.literal("not_ready")]),
  service: z.string(),
  database_ready: z.boolean(),
});

export type ReadinessResponse = z.infer<typeof ReadinessResponseSchema>;

export class ApiRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export class ApiResponseSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiResponseSchemaError";
  }
}

export type FetchHealthOptions = {
  fetchFn?: typeof fetch;
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 5_000;

function buildApiUrl(apiBaseUrl: string, path: string): string {
  const trimmedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  if (trimmedBaseUrl.length === 0) {
    throw new ApiRequestError("API base URL is not configured");
  }
  return `${trimmedBaseUrl}${path}`;
}

export async function fetchHealth(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const fetchFn = options.fetchFn ?? fetch;

  try {
    const response = await fetchFn(buildApiUrl(apiBaseUrl, "/health"), {
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiRequestError(
        `Health check failed with status ${response.status}`,
      );
    }

    const parsed = HealthResponseSchema.safeParse(await response.json());
    if (!parsed.success) {
      throw new ApiResponseSchemaError(
        "Health response did not match the expected schema",
      );
    }

    return parsed.data;
  } catch (error: unknown) {
    if (
      error instanceof ApiRequestError ||
      error instanceof ApiResponseSchemaError
    ) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError(`Health check timed out after ${timeoutMs} ms`);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : "Health check request failed",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchReadiness(
  apiBaseUrl: string,
  options: FetchHealthOptions = {},
): Promise<ReadinessResponse> {
  const response = await (options.fetchFn ?? fetch)(
    buildApiUrl(apiBaseUrl, "/ready"),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ApiRequestError(
      `Readiness check failed with status ${response.status}`,
    );
  }

  const parsed = ReadinessResponseSchema.safeParse(await response.json());
  if (!parsed.success) {
    throw new ApiResponseSchemaError(
      "Readiness response did not match the expected schema",
    );
  }

  return parsed.data;
}
