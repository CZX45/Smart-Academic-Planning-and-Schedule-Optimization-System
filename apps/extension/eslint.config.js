import js from "@eslint/js";
import tseslint from "typescript-eslint";

const browserGlobals = {
  AbortController: "readonly",
  Blob: "readonly",
  Document: "readonly",
  Error: "readonly",
  HTMLTableElement: "readonly",
  Request: "readonly",
  Response: "readonly",
  URL: "readonly",
  clearTimeout: "readonly",
  console: "readonly",
  document: "readonly",
  fetch: "readonly",
  location: "readonly",
  setTimeout: "readonly",
};

const nodeTestGlobals = {
  Buffer: "readonly",
  process: "readonly",
};

export default tseslint.config(
  { ignores: ["dist/**"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["src/**/*.ts"],
    languageOptions: {
      globals: browserGlobals,
    },
  },
  {
    files: ["tests/**/*.ts"],
    languageOptions: {
      globals: nodeTestGlobals,
    },
  },
);
