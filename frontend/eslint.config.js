import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

const browserGlobals = {
  window: "readonly",
  document: "readonly",
  fetch: "readonly",
  console: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  URLSearchParams: "readonly",
  process: "readonly",
};

export default [
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    plugins: { react, "react-hooks": reactHooks },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: browserGlobals,
    },
    settings: { react: { version: "18.3" } },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
    },
  },
];
