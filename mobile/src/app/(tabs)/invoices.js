// Invoices tab: every invoice, newest first, each row opening the invoice screen.
import { router } from "expo-router";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { fmtMoney, fmtTime } from "../../api/client.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import { Alert, Badge, Card, CountPill, Muted, RiskBadge, StatusBadge, sentence } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors } from "../../theme.js";

export default function Invoices() {
  const { invoices, summary, error, refreshing, refresh } = useDashboard();
  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}

      <View style={styles.head}>
        <Text style={styles.title}>All invoices</Text>
        {invoices.length > 0 && <CountPill n={invoices.length} quiet />}
      </View>

      {invoices.length === 0 ? (
        <Card>
          <Muted>{summary ? "No invoices yet. They appear here as the inbox delivers them." : "Loading…"}</Muted>
        </Card>
      ) : (
        <Card style={{ paddingVertical: 0, paddingHorizontal: 0 }}>
          {invoices.map((inv, i) => (
            <Pressable
              key={inv.invoice_id}
              accessibilityRole="link"
              onPress={() => router.push(`/invoices/${inv.invoice_id}`)}
              style={({ pressed }) => [styles.row, i > 0 && styles.rule, pressed && { backgroundColor: colors.panel2 }]}
            >
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={styles.rowTitle} numberOfLines={1}>
                  {inv.vendor_name || "—"} <Text style={styles.rowId}>{inv.invoice_id}</Text>
                </Text>
                <View style={styles.badges}>
                  <StatusBadge status={inv.status} />
                  <RiskBadge level={inv.risk_level} />
                  {inv.sensitive_data_detected && <Badge label="Masked" />}
                </View>
                <Muted small>
                  {inv.recommendation ? `${sentence(inv.recommendation)} · ` : ""}
                  {fmtTime(inv.updated_at)}
                </Muted>
              </View>
              <Text style={styles.rowAmount}>{fmtMoney(inv.amount, inv.currency)}</Text>
            </Pressable>
          ))}
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  head: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 12 },
  title: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 12, paddingHorizontal: 16, gap: 10 },
  rowTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  rowId: { fontWeight: "400", color: colors.muted, fontSize: 12 },
  rowAmount: { fontWeight: "700", fontSize: 14, color: colors.text, fontVariant: ["tabular-nums"] },
});
