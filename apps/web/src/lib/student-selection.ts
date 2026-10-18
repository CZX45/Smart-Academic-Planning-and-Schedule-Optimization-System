// Only the selected local identity is persisted; demo mode and analysis are ephemeral.
const key = (apiBaseUrl: string) => `sapsos.selected-student:${apiBaseUrl}`;
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
