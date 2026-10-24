import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = process.env.VITE_API_BASE_URL || "http://localhost:8000";

// Every backend prefix is proxied so the dashboard can call relative paths in dev.
// Browser navigations (Accept: text/html) to e.g. /invoices/INV-1001 must still get the SPA,
// so only non-HTML requests (fetch) are forwarded to the backend.
const serveSpaForNavigation = (req) =>
  req.headers.accept?.includes("text/html") ? "/index.html" : undefined;

const proxy = Object.fromEntries(
  ["/invoices", "/dashboard", "/governance", "/mock", "/health"].map((p) => [
    p,
    { target: API, changeOrigin: true, bypass: serveSpaForNavigation },
  ]),
);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy,
    // the demo-scenario buttons import the fixtures straight from ../data so there is one source of truth
    fs: { allow: [".."] },
  },
});
