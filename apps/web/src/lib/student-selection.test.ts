import { afterEach, expect, it, vi } from "vitest";
import { readSelectedStudent, saveSelectedStudent } from "./student-selection";

afterEach(() => vi.unstubAllGlobals());
it("restores only the selected local identity within the same API context", () => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
  saveSelectedStudent("http://localhost:8000", "synthetic-student-a");
  expect(readSelectedStudent("http://localhost:8000")).toBe(
    "synthetic-student-a",
  );
  expect(readSelectedStudent("http://localhost:8001")).toBeUndefined();
  saveSelectedStudent("http://localhost:8000", "synthetic-student-b");
  expect(readSelectedStudent("http://localhost:8000")).toBe(
    "synthetic-student-b",
  );
});
it("remains usable when browser storage is unavailable", () => {
  vi.stubGlobal("localStorage", {
    getItem() {
      throw new Error("disabled");
    },
    setItem() {
      throw new Error("disabled");
    },
  });
  expect(readSelectedStudent("local")).toBeUndefined();
  expect(() => saveSelectedStudent("local", "synthetic-student")).not.toThrow();
});

it("restores desktop selection across dynamic ports while isolating other API contexts", () => {
  const values = new Map<string, string>();
  vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
  saveSelectedStudent("http://127.0.0.1:43127", "synthetic-student-b");
  expect(readSelectedStudent("http://127.0.0.1:43128")).toBe(
    "synthetic-student-b",
  );
  expect(
    readSelectedStudent("http://127.0.0.1:43128/other-api"),
  ).toBeUndefined();
  expect(readSelectedStudent("https://api.example.edu")).toBeUndefined();
  saveSelectedStudent("https://api.example.edu:8443", "synthetic-remote");
  expect(readSelectedStudent("https://api.example.edu:8444")).toBeUndefined();
  vi.stubGlobal("window", {});
  expect(readSelectedStudent("http://127.0.0.1:43128")).toBeUndefined();
});
