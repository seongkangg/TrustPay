// Thin fetch wrapper for the backend (docs/api-contracts.md).
// In dev the Vite proxy forwards these prefixes to the backend; in a build set VITE_API_BASE_URL.

const BASE = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message || body?.detail?.[0]?.msg || `HTTP ${status}`);
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
    body = null; // non-JSON error page (e.g. a proxy 404) — ApiError falls back to the HTTP status
  }
  if (!res.ok) throw new ApiError(res.status, body);
  return body;
}

const json = (method, body) => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request("/health"),
  summary: () => request("/dashboard/summary"),
  listInvoices: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== ""));
    return request(`/invoices${qs.toString() ? `?${qs}` : ""}`);
  },
  getInvoice: (id) => request(`/invoices/${id}`),
  createInvoice: (upload) => request("/invoices", json("POST", upload)),
  processInvoice: (id) => request(`/invoices/${id}/process`, json("POST")),
  timeline: (id) => request(`/invoices/${id}/timeline`),
  audit: (id) => request(`/invoices/${id}/audit`),
  approve: (id, reviewer, note) => request(`/invoices/${id}/approve`, json("POST", { reviewer, note })),
  reject: (id, reviewer, note) => request(`/invoices/${id}/reject`, json("POST", { reviewer, note })),
  inboxStatus: () => request("/inbox/status"),
  inboxSync: () => request("/inbox/sync", json("POST")),
};

export const fmtMoney = (amount, currency = "USD") =>
  amount == null
    ? "—"
    : new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);

export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

export const fmtPct = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);

export const human = (s) => (s ? String(s).replace(/_/g, " ") : "—");

export const AWAITING_HUMAN = ["PENDING_APPROVAL", "BLOCKED"];
