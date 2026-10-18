export type PublicEnvInput = {
  readonly [key: string]: string | undefined;
  NEXT_PUBLIC_API_BASE_URL?: string;
};

export type PublicEnv = {
  apiBaseUrl: string;
};

export function parseRuntimeApiBaseUrl(search: string): string | undefined {
  const value = new URLSearchParams(search).get("api_base_url")?.trim();
  if (!value) {
    return undefined;
  }

  return parsePublicEnv({ NEXT_PUBLIC_API_BASE_URL: value }).apiBaseUrl;
}

export function parsePublicEnv(env: PublicEnvInput): PublicEnv {
  const apiBaseUrl = env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is required");
  }

  let parsed: URL;
  try {
    parsed = new URL(apiBaseUrl);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an http(s) URL");
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an http(s) URL");
  }
  if (parsed.username || parsed.password) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must not contain credentials");
  }

  const path = parsed.pathname.replace(/\/+$/, "");
  return {
    apiBaseUrl: `${parsed.origin}${path}${parsed.search}`,
  };
}
