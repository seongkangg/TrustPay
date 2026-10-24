// Invoices tab: every invoice, newest first, filterable by outcome; each row opens the invoice screen.
import { router } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { useHeaderHeight } from "expo-router/react-navigation";
import { useMemo, useState } from "react";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { fmtMoney, fmtTime } from "../../api/client.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import { FilterButton, FilterMenu } from "../../components/FilterMenu.js";
import { Alert, Badge, Card, CountPill, Muted, RiskBadge, StatusBadge, sentence } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, space } from "../../theme.js";

// Outcome filters over InvoiceStatus. FAILED belongs to none of the three, so it shows under All only.
const FILTERS = [
  { key: "all", label: "All", statuses: null },
  {
    key: "pending",
    label: "Pending",
    statuses: ["RECEIVED", "EXTRACTED", "VERIFYING", "VERIFIED", "RISK_REVIEW", "PENDING_APPROVAL", "BLOCKED"],
  },
  { key: "accepted", label: "Accepted", statuses: ["APPROVED", "COMPLETED"] },
  { key: "rejected", label: "Rejected", statuses: ["REJECTED"] },
];

const EMPTY = {
  pending: "Nothing pending. Every invoice has been decided.",
  accepted: "No accepted invoices yet.",
  rejected: "No rejected invoices.",
};

const matches = (filter, inv) => !filter.statuses || filter.statuses.includes(inv.status);

export default function Invoices() {
  const { invoices, summary, error, refreshing, refresh } = useDashboard();
  const [filterKey, setFilterKey] = useState("all");
  const filter = FILTERS.find((f) => f.key === filterKey);
  const shown = invoices.filter((inv) => matches(filter, inv));
  const [menuOpen, setMenuOpen] = useState(false);
  const headerHeight = useHeaderHeight();
  const options = FILTERS.map((f) => ({ ...f, count: invoices.filter((inv) => matches(f, inv)).length }));

  // Memoized: a new options object on every render would make the navigator re-set the header.
  const screenOptions = useMemo(
    () => ({ headerRight: () => <FilterButton filtered={filterKey !== "all"} onPress={() => setMenuOpen(true)} /> }),
    [filterKey],
  );

  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      <Tabs.Screen options={screenOptions} />
      <FilterMenu
        visible={menuOpen}
        top={headerHeight + 4}
        options={options}
        active={filterKey}
        onSelect={(key) => {
          setFilterKey(key);
          setMenuOpen(false);
        }}
        onClose={() => setMenuOpen(false)}
      />
      {error && <Alert kind="danger">{error}</Alert>}

      <View style={styles.head}>
        <Text style={styles.title}>{filter.key === "all" ? "All invoices" : `${filter.label} invoices`}</Text>
        {shown.length > 0 && <CountPill n={shown.length} quiet />}
      </View>


      {invoices.length === 0 ? (
        <Card>
          <Muted>{summary ? "No invoices yet. They appear here as the inbox delivers them." : "Loading…"}</Muted>
        </Card>
      ) : shown.length === 0 ? (
        <Card>
          <Muted>{EMPTY[filter.key]}</Muted>
        </Card>
      ) : (
        <Card style={{ paddingVertical: 0, paddingHorizontal: 0 }}>
          {shown.map((inv, i) => (
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
  page: { paddingHorizontal: space.gutter, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  head: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 12 },
  title: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 14, paddingHorizontal: space.card, gap: 10 },
  rowTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  rowId: { fontWeight: "400", color: colors.muted, fontSize: 12 },
  rowAmount: { fontWeight: "700", fontSize: 14, color: colors.text, fontVariant: ["tabular-nums"] },
});
