export type ImportWorkflowKey = { studentId: string; importId: string };

export function importWorkflowKey(studentId: string, importId: string): string {
  return `${studentId}:${importId}`;
}

export function isUsableImportPreview(
  preview: { parsedRowCount: number; visibleRowCount: number } | null,
): boolean {
  return Boolean(
    preview && preview.parsedRowCount > 0 && preview.visibleRowCount > 0,
  );
}
