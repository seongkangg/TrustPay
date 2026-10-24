// Same tokens as frontend/src/styles/dashboard.css (recorded in DESIGN.md) so the phone and the web
// dashboard agree: a white screen, soft grey panels, the logo's teal on data and its navy on ink.
export const colors = {
  canvas: "#e9eaee",
  bg: "#ffffff",
  surface: "#ffffff",
  panel: "#f5f5f7",
  panel2: "#ebebef",
  text: "#0f2233",
  muted: "#6b6f7b",
  neutralInk: "#565a65",
  border: "#ececf0",

  // Brand: the logo's teal and navy. Bright teal is for the logo only; it is too light for text.
  brandTeal: "#14b8a6",
  brandNavy: "#0f3d5e",
  accent: "#0d9488", // teal on data: chart line, sparklines, highlighted bar
  accentStrong: "#0f766e", // filled teal that carries white text: count pill, today
  accentInk: "#0f3d5e", // links and accent text
  accentSoft: "#99ddd3",
  accentBg: "#e3f5f2",

  riskLow: "#18794e",
  riskLowBg: "#e3f5ea",
  riskMedium: "#8f6100",
  riskMediumBg: "#fdf1d6",
  riskHigh: "#c4202d",
  riskHighBg: "#fde7e8",

  blocked: "#d92d3a",
  blockedBg: "#fde7e8",
  ok: "#18794e",
  okBg: "#e3f5ea",
  pending: "#0d9488",
  pendingBg: "#e3f5f2",
  neutralBg: "#f0f0f3",
  infoBg: "#e3f5f2",
  infoText: "#0f3d5e",
  warnText: "#5a3d00",
  dangerText: "#7a0f19",
  okText: "#0d4a2f",
};

export const radius = { panel: 18, row: 16, alert: 14, field: 12, cell: 12, pill: 999 };

// Screen margin on both sides, and the inset inside a rounded panel so content clears its corners.
export const space = { gutter: 22, card: 20 };

export const RISK = {
  low: { fg: colors.riskLow, bg: colors.riskLowBg },
  medium: { fg: colors.riskMedium, bg: colors.riskMediumBg },
  high: { fg: colors.riskHigh, bg: colors.riskHighBg },
};

// Blocked / failed / rejected are the only solid-filled badges ("loud block").
export const STATUS = {
  COMPLETED: { fg: colors.ok, bg: colors.okBg },
  APPROVED: { fg: colors.ok, bg: colors.okBg },
  PENDING_APPROVAL: { fg: colors.accentInk, bg: colors.pendingBg },
  BLOCKED: { fg: "#ffffff", bg: colors.blocked },
  FAILED: { fg: "#ffffff", bg: colors.blocked },
  REJECTED: { fg: "#ffffff", bg: colors.blocked },
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
