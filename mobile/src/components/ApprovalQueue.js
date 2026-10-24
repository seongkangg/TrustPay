// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED). The decision itself is taken on the
// invoice screen; each row only routes the reviewer there.
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { fmtMoney, fmtTime } from "../api/client.js";
import { colors, radius } from "../theme.js";
import { Muted, ReasonTag, RiskBadge, StatusBadge } from "./ui.js";

export default function ApprovalQueue({ items, reasonCodes = {} }) {
  if (items.length === 0) {
    return <Muted small>Nothing waiting. New invoices are checked automatically.</Muted>;
  }
  return (
    <View style={{ gap: 8 }}>
      {items.map((inv) => (
        <QueueItem key={inv.invoice_id} inv={inv} codes={reasonCodes[inv.invoice_id]} />
      ))}
    </View>
  );
}

function QueueItem({ inv, codes = [] }) {
  const blocked = inv.status === "BLOCKED";
  return (
    <Pressable
      accessibilityRole="link"
      onPress={() => router.push(`/invoices/${inv.invoice_id}`)}
      style={({ pressed }) => [
        styles.item,
        { backgroundColor: blocked ? colors.blockedBg : colors.accentBg },
        pressed && { transform: [{ scale: 0.98 }] },
      ]}
    >
      <View style={styles.head}>
        <Text style={styles.vendor} numberOfLines={1}>
          {inv.vendor_name || "Unknown vendor"}
        </Text>
        <Text style={styles.amount}>{fmtMoney(inv.amount, inv.currency)}</Text>
      </View>
      <View style={styles.badges}>
        <StatusBadge status={inv.status} />
        <RiskBadge level={inv.risk_level} />
      </View>
      {codes.length > 0 && (
        <View style={styles.codes}>
          {codes.map((c) => (
            <ReasonTag key={c} code={c} />
          ))}
        </View>
      )}
      <View style={styles.foot}>
        <Muted small>
          {inv.invoice_id} · {fmtTime(inv.updated_at)}
        </Muted>
        <View style={styles.review}>
          <Text style={styles.reviewText}>Review ›</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  item: { borderRadius: radius.row, paddingVertical: 16, paddingHorizontal: 18, gap: 6 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 8 },
  vendor: { fontWeight: "700", fontSize: 15, color: colors.text, flex: 1 },
  amount: { fontWeight: "700", fontSize: 16, color: colors.text, fontVariant: ["tabular-nums"] },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 2 },
  foot: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  review: { height: 32, paddingHorizontal: 14, borderRadius: radius.pill, backgroundColor: colors.brandNavy, justifyContent: "center" },
  reviewText: { color: "#fff", fontWeight: "600", fontSize: 13 },
});
