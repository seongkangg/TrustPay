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

// Users only ever see these short messages; raw detail stays in the dev console / backend dev log.
function userMessage(status, body) {
  if (status === 0) return "Can't reach the server. Please try again.";
  if (body?.error && body?.message) return body.message; // backend's own user-facing text
  if (status === 422) return "Some fields are invalid.";
  return "Something went wrong. Please try again.";
}

export class ApiError extends Error {
  constructor(status, body) {
    super(userMessage(status, body));
    this.status = status;
    this.code = body?.error || "HTTP_ERROR";
    this.body = body;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (err) {
    console.error(`fetch ${BASE + path} failed`, err);
    throw new ApiError(0, null);
  }
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) {
    console.error(`${options.method || "GET"} ${path} -> ${res.status}`, body ?? text);
    throw new ApiError(res.status, body);
  }
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
  // Policy constants from data/approval_limits.json (auto-approve max, confidence threshold, ...).
  thresholds: () => request("/mock/thresholds"),
};

export const fmtMoney = (amount, currency = "USD") =>
  amount == null ? "—" : `${currency === "USD" ? "$" : `${currency} `}${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

// "just now", "5 min ago", "3 h ago", "2 d ago"; "—" when missing.
export const fmtAgo = (iso) => {
  if (!iso) return "—";
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)} h ago`;
  return `${Math.round(mins / (60 * 24))} d ago`;
};

export const fmtPct = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);

// Display wording for enum values the API returns (backend/models/enums.py). Values not listed
// read fine in sentence case: "PENDING_APPROVAL" -> "Pending approval", "vendor_lookup" -> "Vendor lookup".
const LABELS = {
  governance_layer: "Governance",
  human_reviewer: "Reviewer",
  po_lookup: "Purchase order lookup",
  approval_request_create: "Create approval request",
  payment_authorize: "Authorize payment",
  audit_log_write: "Write audit log",
  risk_rules: "Risk rules check",
  tax_id: "Tax ID",
  purchase_order_id: "Purchase order",
  vendor_invoice_number: "Vendor invoice #",
};

// Free text (anything that is not a bare identifier) passes through untouched.
export const human = (s) => {
  if (s == null || s === "") return "—";
  const v = String(s);
  if (LABELS[v]) return LABELS[v];
  if (!/^[A-Za-z0-9_]+$/.test(v)) return v;
  const t = v.replace(/_/g, " ").toLowerCase();
  return t.charAt(0).toUpperCase() + t.slice(1);
};

export const AWAITING_HUMAN = ["PENDING_APPROVAL", "BLOCKED"];
