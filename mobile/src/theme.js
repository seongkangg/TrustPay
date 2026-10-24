// Same palette as frontend/src/styles/dashboard.css so the phone and the web dashboard agree.
export const colors = {
  bg: "#f5f6f8",
  surface: "#ffffff",
  text: "#1b1f24",
  muted: "#5c6670",
  border: "#e1e4e8",
  accent: "#0f62fe",

  riskLow: "#198038",
  riskLowBg: "#defbe6",
  riskMedium: "#b28600",
  riskMediumBg: "#fff4cc",
  riskHigh: "#da1e28",
  riskHighBg: "#ffe0e0",

  blocked: "#da1e28",
  blockedBg: "#ffe0e0",
  ok: "#198038",
  okBg: "#defbe6",
  pending: "#8a3ffc",
  pendingBg: "#efe4ff",
  neutralBg: "#eef1f4",
  infoBg: "#e5f0ff",
  warnText: "#5a4500",
  dangerText: "#7a0b12",
};

export const RISK = {
  low: { fg: colors.riskLow, bg: colors.riskLowBg },
  medium: { fg: colors.riskMedium, bg: colors.riskMediumBg },
  high: { fg: colors.riskHigh, bg: colors.riskHighBg },
};

export const STATUS = {
  COMPLETED: { fg: colors.ok, bg: colors.okBg },
  APPROVED: { fg: colors.ok, bg: colors.okBg },
  PENDING_APPROVAL: { fg: colors.pending, bg: colors.pendingBg },
  BLOCKED: { fg: colors.blocked, bg: colors.blockedBg },
  FAILED: { fg: colors.blocked, bg: colors.blockedBg },
  REJECTED: { fg: colors.blocked, bg: colors.blockedBg },
};

export const STATUS_ORDER = [
  "RECEIVED",
  "EXTRACTED",
  "VERIFYING",
  "VERIFIED",
  "RISK_REVIEW",
  "PENDING_APPROVAL",
  "APPROVED",
  "COMPLETED",
  "BLOCKED",
  "REJECTED",
  "FAILED",
];
