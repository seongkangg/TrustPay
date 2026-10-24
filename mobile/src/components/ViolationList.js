// Recent policy violations (payments governance blocked), as rows in one card: a red shield, the
// vendor and amount (looked up from the invoice list), ID and how long ago, the reason tags, and a
// chevron to the invoice. Same row shape as the Inbox's ApprovalQueue.
import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { fmtAgo, fmtMoney } from "../api/client.js";
import { colors, radius, space } from "../theme.js";
import { Card, ReasonTag } from "./ui.js";

// violations: summary.recent_violations; invoices: the loaded list, for vendor and amount.
export default function ViolationList({ violations, invoices }) {
  const byId = Object.fromEntries(invoices.map((inv) => [inv.invoice_id, inv]));
  return (
    <Card style={styles.group}>
      {violations.map((v, i) => (
        <ViolationRow key={`${v.invoice_id}-${v.timestamp}`} v={v} inv={byId[v.invoice_id]} first={i === 0} />
      ))}
    </Card>
  );
}

function ViolationRow({ v, inv, first }) {
  const vendor = inv?.vendor_name || v.invoice_id;
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`Blocked payment to ${vendor}, ${fmtAgo(v.timestamp)}`}
      onPress={() => router.push(`/invoices/${v.invoice_id}`)}
      style={({ pressed }) => [styles.row, !first && styles.rule, pressed && { backgroundColor: colors.panel2 }]}
    >
      <View style={styles.icon}>
        <Svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke={colors.riskHigh} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M12 3.5 5 6.2v5.3c0 4.3 2.9 7.7 7 9 4.1-1.3 7-4.7 7-9V6.2z" />
          <Path d="M12 8.5v4.2M12 15.8h.01" />
        </Svg>
      </View>
      <View style={{ flex: 1, gap: 5 }}>
        <View style={styles.top}>
          <Text style={styles.vendor} numberOfLines={1}>
            {vendor}
          </Text>
          {inv && <Text style={styles.amount}>{fmtMoney(inv.amount, inv.currency)}</Text>}
        </View>
        <Text style={styles.sub} numberOfLines={1}>
          {inv ? `${v.invoice_id} · ` : ""}blocked {fmtAgo(v.timestamp)}
        </Text>
        {v.reason_codes.length > 0 && (
          <View style={styles.tags}>
            {v.reason_codes.map((c) => (
              <ReasonTag key={c} code={c} />
            ))}
          </View>
        )}
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
  icon: {
    width: 40,
    height: 40,
    borderRadius: radius.field,
    backgroundColor: colors.riskHighBg,
    alignItems: "center",
    justifyContent: "center",
  },
  top: { flexDirection: "row", alignItems: "baseline", gap: 10 },
  vendor: { flex: 1, fontSize: 15, fontWeight: "700", color: colors.text },
  amount: { fontSize: 15, fontWeight: "700", color: colors.text, fontVariant: ["tabular-nums"] },
  sub: { fontSize: 12, color: colors.muted, fontVariant: ["tabular-nums"] },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chevron: { alignSelf: "center" },
});
