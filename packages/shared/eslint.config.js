import js from "@eslint/js";
import tseslint from "typescript-eslint";

const nodeGlobals = {
  console: "readonly",
  process: "readonly",
};

const webApiGlobals = {
  AbortController: "readonly",
  clearTimeout: "readonly",
  fetch: "readonly",
  Response: "readonly",
  setTimeout: "readonly",
};

export default tseslint.config(
  { ignores: ["dist/**"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["src/**/*.ts"],
    languageOptions: {
      globals: webApiGlobals,
    },
    rules: {},
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: nodeGlobals,
      sourceType: "module",
    },
  },
);
