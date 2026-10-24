// Small shared building blocks: badges, cards, tiles, alerts, section headings.
import { StyleSheet, Text, View } from "react-native";

import { human } from "../api/client.js";
import { RISK, STATUS, colors } from "../theme.js";

export function Badge({ label, fg = colors.muted, bg = colors.neutralBg, outline = false }) {
  return (
    <View style={[styles.badge, { backgroundColor: bg }, outline && { borderWidth: 1, borderColor: fg }]}>
      <Text style={[styles.badgeText, { color: fg }]}>{label}</Text>
    </View>
  );
}

export function RiskBadge({ level }) {
  if (!level) return <Badge label="unscored" />;
  const c = RISK[level] || {};
  return <Badge label={`${level} risk`} fg={c.fg} bg={c.bg} />;
}

export function StatusBadge({ status }) {
  const c = STATUS[status] || {};
  const loud = ["BLOCKED", "FAILED", "REJECTED"].includes(status);
  return <Badge label={human(status)} fg={c.fg} bg={c.bg} outline={loud} />;
}

export function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function H2({ children }) {
  return <Text style={styles.h2}>{children}</Text>;
}

export function Muted({ children, style, small }) {
  return <Text style={[styles.muted, small && styles.small, style]}>{children}</Text>;
}

export function Alert({ kind = "info", children }) {
  const k = ALERT[kind];
  return (
    <View style={[styles.alert, { backgroundColor: k.bg, borderColor: k.border }]}>
      <Text style={{ color: k.text, fontSize: 13 }}>{children}</Text>
    </View>
  );
}

const ALERT = {
  info: { bg: colors.infoBg, border: colors.accent, text: "#0b3a8c" },
  warn: { bg: colors.riskMediumBg, border: colors.riskMedium, text: colors.warnText },
  danger: { bg: colors.blockedBg, border: colors.blocked, text: colors.dangerText },
  ok: { bg: colors.okBg, border: colors.ok, text: "#0e4f22" },
};

export function Tile({ label, value, color, highlight }) {
  return (
    <View style={[styles.tile, highlight && { borderColor: highlight.border, backgroundColor: highlight.bg }]}>
      <Text style={styles.tileLabel}>{label}</Text>
      <Text style={[styles.tileValue, color && { color }]} numberOfLines={1} adjustsFontSizeToFit>
        {value ?? "—"}
      </Text>
    </View>
  );
}

export function Code({ children }) {
  return <Text style={styles.code}>{children}</Text>;
}

const styles = StyleSheet.create({
  badge: { alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  badgeText: { fontSize: 12, fontWeight: "600" },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14 },
  h2: { fontSize: 15, fontWeight: "700", color: colors.text, marginTop: 22, marginBottom: 8 },
  muted: { color: colors.muted, fontSize: 14 },
  small: { fontSize: 12 },
  alert: { padding: 10, borderRadius: 8, borderWidth: 1, marginVertical: 6 },
  tile: {
    flexBasis: "47%",
    flexGrow: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  tileLabel: { color: colors.muted, fontSize: 12 },
  tileValue: { fontSize: 24, fontWeight: "700", color: colors.text, marginTop: 2 },
  code: {
    fontFamily: "Menlo",
    fontSize: 11,
    backgroundColor: colors.neutralBg,
    color: colors.text,
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 3,
    overflow: "hidden",
    marginRight: 4,
    marginBottom: 4,
  },
});
