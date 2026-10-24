// Thin fetch wrapper for the TrustPay backend (docs/api-contracts.md), same shape as
// frontend/src/api/client.js. The phone cannot use a Vite proxy, so it needs a full base URL:
//   1. EXPO_PUBLIC_API_URL (e.g. http://10.250.220.0:8000) when set, else
//   2. the host Expo Go loaded the JS bundle from, on port 8000 — i.e. the laptop running
//      `expo start`, which is normally also the laptop running uvicorn.
import Constants from "expo-constants";

function defaultBase() {
  const hostUri = Constants.expoConfig?.hostUri || Constants.manifest2?.extra?.expoGo?.debuggerHost;
  const host = hostUri ? hostUri.split(":")[0] : "localhost";
  return `http://${host}:8000`;
}

export const BASE = (process.env.EXPO_PUBLIC_API_URL || defaultBase()).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message || body?.detail?.[0]?.msg || body?.detail || `HTTP ${status}`);
    this.status = status;
    this.code = body?.error || "HTTP_ERROR";
    this.body = body;
  }
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) throw new ApiError(res.status, body);
  return body;
}

const json = (method, body) => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request("/health"),
  summary: () => request("/dashboard/summary"),
  listInvoices: (params = {}) => {
    const qs = Object.entries(params)
      .filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    return request(`/invoices${qs ? `?${qs}` : ""}`);
  },
  getInvoice: (id) => request(`/invoices/${id}`),
  timeline: (id) => request(`/invoices/${id}/timeline`),
  approve: (id, reviewer, note) => request(`/invoices/${id}/approve`, json("POST", { reviewer, note })),
  reject: (id, reviewer, note) => request(`/invoices/${id}/reject`, json("POST", { reviewer, note })),
  inboxStatus: () => request("/inbox/status"),
  inboxSync: () => request("/inbox/sync", json("POST")),
};

export const fmtMoney = (amount, currency = "USD") =>
  amount == null ? "—" : `${currency === "USD" ? "$" : `${currency} `}${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

export const fmtPct = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);

export const human = (s) => (s ? String(s).replace(/_/g, " ") : "—");

export const AWAITING_HUMAN = ["PENDING_APPROVAL", "BLOCKED"];
