export function isLocalApiBaseUrl(apiBaseUrl: string): boolean {
  try {
    const parsed = new URL(apiBaseUrl);
    return (
      parsed.protocol === "http:" &&
      ["localhost", "127.0.0.1"].includes(parsed.hostname) &&
      parsed.username === "" &&
      parsed.password === "" &&
      parsed.search === "" &&
      parsed.hash === "" &&
      ["", "/"].includes(parsed.pathname)
    );
  } catch {
    return false;
  }
}
