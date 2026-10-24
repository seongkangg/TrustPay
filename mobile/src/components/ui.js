// Small shared building blocks: badges, panels, pill buttons, alerts, section headings.
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Path, Stop } from "react-native-svg";

import { human } from "../api/client.js";
import { RISK, STATUS, colors, radius, space } from "../theme.js";

// "PENDING_APPROVAL" -> "Pending approval" (wording lives in human(), api/client.js)
export const sentence = human;

export function Badge({ label, fg = colors.neutralInk, bg = colors.neutralBg }) {
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={[styles.badgeText, { color: fg }]}>{label}</Text>
    </View>
  );
}

export function RiskBadge({ level }) {
  if (!level) return <Badge label="No risk yet" />;
  const c = RISK[level] || {};
  return <Badge label={`${sentence(level)} risk`} fg={c.fg} bg={c.bg} />;
}

export function StatusBadge({ status }) {
  const c = STATUS[status] || {};
  return <Badge label={sentence(status)} fg={c.fg} bg={c.bg} />;
}

// Plain-English wording for ReasonCode (backend/models/enums.py); same text as the web ReasonTag.
const REASONS = {
  AMOUNT_ABOVE_LIMIT: "Over approval limit",
  UNKNOWN_VENDOR: "New vendor",
  VENDOR_UNVERIFIED: "Vendor not verified",
  DUPLICATE_INVOICE: "Possible duplicate",
  PO_AMOUNT_MISMATCH: "Doesn't match PO",
  INVALID_PURCHASE_ORDER: "PO not found",
  SENSITIVE_DATA_DETECTED: "Sensitive info found",
  UNAUTHORIZED_TOOL_CALL: "Action not permitted",
  LOW_CONFIDENCE: "Unclear details",
  MISSING_REQUIRED_FIELD: "Missing information",
  MALFORMED_FIELD: "Invalid format",
  AGENT_FAILURE: "Processing error",
  MOCK_SYSTEM_UNAVAILABLE: "System unavailable",
  INSUFFICIENT_EVIDENCE: "Not enough information",
  POLICY_PASSED: "All checks passed",
};
// Same colour split as the web: green = passed, yellow = needs a check, red = violation.
const UNCERTAIN = new Set([
  "UNKNOWN_VENDOR", "VENDOR_UNVERIFIED", "SENSITIVE_DATA_DETECTED", "LOW_CONFIDENCE", "MISSING_REQUIRED_FIELD",
  "MALFORMED_FIELD", "AGENT_FAILURE", "MOCK_SYSTEM_UNAVAILABLE", "INSUFFICIENT_EVIDENCE",
]);

export function ReasonTag({ code }) {
  const [fg, bg] =
    code === "POLICY_PASSED"
      ? [colors.ok, colors.okBg]
      : UNCERTAIN.has(code)
        ? [colors.riskMedium, colors.riskMediumBg]
        : [colors.blocked, colors.blockedBg];
  return <Badge label={REASONS[code] || human(code)} fg={fg} bg={bg} />;
}

// A soft grey panel: separation by one tone step, never a border or shadow.
export function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function H2({ children, style }) {
  return <Text style={[styles.h2, style]}>{children}</Text>;
}

// Accent when something is waiting; quiet grey for a plain total or a zero.
export function CountPill({ n, quiet = n === 0 }) {
  return (
    <View style={[styles.countPill, quiet && { backgroundColor: colors.panel2 }]}>
      <Text style={[styles.countText, quiet && { color: colors.neutralInk }]}>{n}</Text>
    </View>
  );
}

export function Muted({ children, style, small }) {
  return <Text style={[styles.muted, small && styles.small, style]}>{children}</Text>;
}

export function Alert({ kind = "info", children }) {
  const k = ALERT[kind];
  return (
    <View style={[styles.alert, { backgroundColor: k.bg }]}>
      <Text style={{ color: k.text, fontSize: 13, lineHeight: 19 }}>{children}</Text>
    </View>
  );
}

const ALERT = {
  info: { bg: colors.infoBg, text: colors.infoText },
  warn: { bg: colors.riskMediumBg, text: colors.warnText },
  danger: { bg: colors.blockedBg, text: colors.dangerText },
  ok: { bg: colors.okBg, text: colors.okText },
};

// Pill button with press feedback (scale 0.97). tone: "primary" (near-black), "approve", "reject", "quiet".
export function PillButton({ label, onPress, disabled, tone = "primary", style }) {
  const bg = { primary: colors.brandNavy, approve: colors.ok, reject: colors.blocked, quiet: colors.panel2 }[tone];
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: disabled ? colors.panel2 : bg },
        pressed && !disabled && styles.pressed,
        style,
      ]}
    >
      <Text style={[styles.buttonText, (disabled || tone === "quiet") && { color: colors.neutralInk }]}>{label}</Text>
    </Pressable>
  );
}

export function Code({ children }) {
  return <Text style={styles.code}>{children}</Text>;
}

// TrustPay logo: the teal-to-navy shield with a tick, then "Trust" in navy and "Pay" in teal
// (the same artwork as frontend/public/trustpay-logo.svg).
export function Logo({ height = 26 }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: height * 0.22 }} accessibilityLabel="TrustPay">
      <Svg width={height * 0.86} height={height} viewBox="22 14 96 114">
        <Defs>
          <LinearGradient id="shield" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={colors.brandTeal} />
            <Stop offset="1" stopColor={colors.brandNavy} />
          </LinearGradient>
        </Defs>
        <Path d="M70 14 L118 30 V68 C118 98 98 118 70 128 C42 118 22 98 22 68 V30 Z" fill="url(#shield)" />
        <Path
          d="M48 70 L64 86 L94 54"
          fill="none"
          stroke="#fff"
          strokeWidth={10}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
      <Text style={{ fontSize: height * 0.72, fontWeight: "800", letterSpacing: -0.5, color: colors.brandNavy }}>
        Trust<Text style={{ color: colors.brandTeal }}>Pay</Text>
      </Text>
    </View>
  );
}

export const styles = StyleSheet.create({
  badge: { alignSelf: "flex-start", height: 22, justifyContent: "center", paddingHorizontal: 9, borderRadius: radius.pill },
  badgeText: { fontSize: 12, fontWeight: "600" },
  card: { backgroundColor: colors.panel, borderRadius: radius.panel, padding: space.card },
  h2: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16, marginTop: 28, marginBottom: 12 },
  countPill: {
    minWidth: 22,
    height: 22,
    paddingHorizontal: 7,
    borderRadius: radius.pill,
    backgroundColor: colors.accentStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  countText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  muted: { color: colors.muted, fontSize: 14 },
  small: { fontSize: 12 },
  alert: { paddingVertical: 12, paddingHorizontal: 16, borderRadius: radius.alert, marginVertical: 6 },
  button: { height: 44, paddingHorizontal: 18, borderRadius: radius.pill, alignItems: "center", justifyContent: "center" },
  pressed: { transform: [{ scale: 0.97 }] },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 14 },
  code: {
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
    fontSize: 11,
    backgroundColor: colors.neutralBg,
    color: "#3a3d46",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    overflow: "hidden",
    marginRight: 4,
    marginBottom: 4,
  },
});
