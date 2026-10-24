// Invoices waiting on a human (PENDING_APPROVAL / BLOCKED), as rows in one card: vendor avatar,
// vendor and amount, ID and how long it has waited, status / risk and up to two reason tags, and a
// chevron. The decision itself is taken on the invoice screen; each row only routes the reviewer
// there.
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { fmtAgo, fmtMoney } from "../api/client.js";
import { colors, space } from "../theme.js";
import { Badge, Card, ReasonTag, RiskBadge, StatusBadge } from "./ui.js";
import VendorAvatar from "./VendorAvatar.js";

const MAX_TAGS = 2;

export default function ApprovalQueue({ items, reasonCodes = {} }) {
  return (
    <Card style={styles.group}>
      {items.map((inv, i) => (
        <QueueRow key={inv.invoice_id} inv={inv} codes={reasonCodes[inv.invoice_id] || []} first={i === 0} />
      ))}
    </Card>
  );
}

function QueueRow({ inv, codes, first }) {
  const extra = codes.length - MAX_TAGS;
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`Review ${inv.vendor_name || "unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
      onPress={() => router.push(`/invoices/${inv.invoice_id}`)}
      style={({ pressed }) => [styles.row, !first && styles.rule, pressed && { backgroundColor: colors.panel2 }]}
    >
      <VendorAvatar name={inv.vendor_name} />
      <View style={{ flex: 1, gap: 5 }}>
        <View style={styles.top}>
          <Text style={styles.vendor} numberOfLines={1}>
            {inv.vendor_name || "Unknown vendor"}
          </Text>
          <Text style={styles.amount}>{fmtMoney(inv.amount, inv.currency)}</Text>
        </View>
        <Text style={styles.sub} numberOfLines={1}>
          {inv.invoice_id} · waiting {fmtAgo(inv.updated_at).replace(" ago", "")}
        </Text>
        <View style={styles.tags}>
          <StatusBadge status={inv.status} />
          <RiskBadge level={inv.risk_level} />
          {codes.slice(0, MAX_TAGS).map((c) => (
            <ReasonTag key={c} code={c} />
          ))}
          {extra > 0 && <Badge label={`+${extra} more`} />}
        </View>
      </View>
      <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.muted} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={styles.chevron}>
        <Path d="m9.5 6 6 6-6 6" />
      </Svg>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  group: { paddingVertical: 0, paddingHorizontal: 0, overflow: "hidden" },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 12, paddingVertical: 14, paddingLeft: space.card, paddingRight: 12 },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  top: { flexDirection: "row", alignItems: "baseline", gap: 10 },
  vendor: { flex: 1, fontSize: 15, fontWeight: "700", color: colors.text },
  amount: { fontSize: 15, fontWeight: "700", color: colors.text, fontVariant: ["tabular-nums"] },
  sub: { fontSize: 12, color: colors.muted, fontVariant: ["tabular-nums"] },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chevron: { alignSelf: "center" },
});
