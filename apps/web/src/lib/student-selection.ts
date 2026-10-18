// Only the selected local identity is persisted; demo mode and analysis are ephemeral.
function key(apiBaseUrl: string): string {
  let scope = apiBaseUrl;
  if (typeof window !== "undefined" && "__TAURI_INTERNALS__" in window) {
    const url = new URL(apiBaseUrl);
    if (
      url.protocol === "http:" &&
      ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
    ) {
      // The packaged API gets a new port on restart. Only its preference key
      // is stable; request/result scopes still use the full API URL, and the
      // caller validates the stored student against this API's profile list.
      scope = `desktop:${url.hostname}${url.pathname}${url.search}`;
    }
  }
  return `sapsos.selected-student:${scope}`;
}
export function readSelectedStudent(apiBaseUrl: string): string | undefined {
  try {
    return localStorage.getItem(key(apiBaseUrl)) ?? undefined;
  } catch {
    return undefined;
  }
}
export function saveSelectedStudent(
  apiBaseUrl: string,
  studentId: string,
): void {
  try {
    localStorage.setItem(key(apiBaseUrl), studentId);
  } catch {
    /* A disabled storage area must not prevent local profile selection. */
  }
}
