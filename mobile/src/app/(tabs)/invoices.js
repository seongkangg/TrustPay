// Invoices tab: every invoice, newest first, filterable by outcome; each row opens the invoice screen.
// A summary card leads (total, count, and on All the pending / accepted / rejected split), then the
// invoices grouped by day, a page at a time with a "Show more" pill under the list.
import { router } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { useHeaderHeight } from "expo-router/react-navigation";
import { useMemo, useState } from "react";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { fmtMoney } from "../../api/client.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import { FilterButton, FilterMenu } from "../../components/FilterMenu.js";
import VendorAvatar from "../../components/VendorAvatar.js";
import { Alert, Badge, Card, Muted, RiskBadge, StatusBadge } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, radius, space } from "../../theme.js";

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

const PAGE = 8;

// Colours of the split bar on All, one per outcome filter.
const SPLIT = [
  { key: "pending", color: colors.accent },
  { key: "accepted", color: colors.ok },
  { key: "rejected", color: colors.riskHigh },
];

const wholeDollars = (amount) => `$${Math.round(amount).toLocaleString("en-US")}`;

// "Today", "Yesterday", or "Oct 22" (adds the year when it is not this year), by the phone's date.
function dayHeading(date) {
  const today = new Date();
  const startOf = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((startOf(today) - startOf(date)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(date.getFullYear() !== today.getFullYear() && { year: "numeric" }),
  });
}

// Consecutive invoices (already newest first) grouped under their day's heading.
function groupByDay(items) {
  const groups = [];
  for (const inv of items) {
    const heading = inv.updated_at ? dayHeading(new Date(inv.updated_at)) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.heading === heading) last.items.push(inv);
    else groups.push({ heading, items: [inv] });
  }
  return groups;
}

export default function Invoices() {
  const { invoices, summary, error, refreshing, refresh } = useDashboard();
  const [filterKey, setFilterKey] = useState("all");
  const filter = FILTERS.find((f) => f.key === filterKey);
  const shown = invoices.filter((inv) => matches(filter, inv));
  const [limit, setLimit] = useState(PAGE);
  const visible = shown.slice(0, limit);
  const remaining = shown.length - visible.length;
  const [menuOpen, setMenuOpen] = useState(false);
  const headerHeight = useHeaderHeight();
  const options = FILTERS.map((f) => ({ ...f, count: invoices.filter((inv) => matches(f, inv)).length }));
  const total = shown.reduce((sum, inv) => sum + (inv.amount || 0), 0);

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
          setLimit(PAGE); // a new filter starts back at the first page
          setMenuOpen(false);
        }}
        onClose={() => setMenuOpen(false)}
      />
      {error && <Alert kind="danger">{error}</Alert>}

      {shown.length > 0 && (
        <SummaryCard
          title={filter.key === "all" ? "All invoices" : `${filter.label} invoices`}
          total={total}
          count={shown.length}
          split={filter.key === "all" ? options : null}
        />
      )}

      {invoices.length === 0 ? (
        <Card>
          <Muted>{summary ? "No invoices yet. They appear here as the inbox delivers them." : "Loading…"}</Muted>
        </Card>
      ) : shown.length === 0 ? (
        <Card>
          <Muted>{EMPTY[filter.key]}</Muted>
        </Card>
      ) : (
        <>
          {groupByDay(visible).map((g) => (
            <View key={g.heading}>
              <Text style={styles.dayHeading}>{g.heading}</Text>
              <Card style={styles.group}>
                {g.items.map((inv, i) => (
                  <InvoiceRow key={inv.invoice_id} inv={inv} first={i === 0} />
                ))}
              </Card>
            </View>
          ))}
          {remaining > 0 ? (
            <MoreButton
              label={`Show ${Math.min(PAGE, remaining)} more`}
              note={`${remaining} left`}
              onPress={() => setLimit((n) => n + PAGE)}
            />
          ) : (
            shown.length > PAGE && <MoreButton label="Show less" up onPress={() => setLimit(PAGE)} />
          )}
        </>
      )}
    </ScrollView>
  );
}

// Which list this is (the filter), its total and count, and (on All) how it splits across the
// three outcomes.
function SummaryCard({ title, total, count, split }) {
  const parts = split
    ? SPLIT.map((s) => ({ ...s, ...split.find((o) => o.key === s.key) })).filter((p) => p.count > 0)
    : [];
  return (
    <View style={styles.summary}>
      <Text style={styles.summaryLabel}>{title}</Text>
      <Text style={styles.summaryTotal}>{wholeDollars(total)}</Text>
      <Muted small>
        {count} invoice{count === 1 ? "" : "s"} · total amount
      </Muted>
      {parts.length > 0 && (
        <>
          <View style={styles.splitBar}>
            {parts.map((p) => (
              <View key={p.key} style={{ flex: p.count, backgroundColor: p.color }} />
            ))}
          </View>
          <View style={styles.splitLegend}>
            {parts.map((p) => (
              <View key={p.key} style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: p.color }]} />
                <Text style={styles.legendText}>
                  {p.label} <Text style={styles.legendCount}>{p.count}</Text>
                </Text>
              </View>
            ))}
          </View>
        </>
      )}
    </View>
  );
}

function InvoiceRow({ inv, first }) {
  const time = inv.updated_at
    ? new Date(inv.updated_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
    : null;
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={`${inv.vendor_name || "Unknown vendor"}, ${fmtMoney(inv.amount, inv.currency)}`}
      onPress={() => router.push(`/invoices/${inv.invoice_id}`)}
      style={({ pressed }) => [styles.row, !first && styles.rule, pressed && { backgroundColor: colors.panel2 }]}
    >
      <VendorAvatar name={inv.vendor_name} />
      <View style={{ flex: 1, gap: 5 }}>
        <View style={styles.rowTop}>
          <Text style={styles.vendor} numberOfLines={1}>
            {inv.vendor_name || "Unknown vendor"}
          </Text>
          <Text style={styles.amount}>{fmtMoney(inv.amount, inv.currency)}</Text>
        </View>
        <Text style={styles.sub} numberOfLines={1}>
          {inv.invoice_id}
          {time ? ` · ${time}` : ""}
        </Text>
        <View style={styles.badges}>
          <StatusBadge status={inv.status} />
          <RiskBadge level={inv.risk_level} />
          {inv.sensitive_data_detected && <Badge label="Masked" />}
        </View>
      </View>
    </Pressable>
  );
}

// Standalone pill under the list: reveals the next page (caret down) or folds back (caret up).
function MoreButton({ label, note, up, onPress }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={note ? `${label}, ${note}` : label}
      style={({ pressed }) => [styles.more, pressed && styles.morePressed]}
    >
      <Text style={styles.moreText}>{label}</Text>
      {note ? <Text style={styles.moreNote}>· {note}</Text> : null}
      <Svg
        width={18}
        height={18}
        viewBox="0 0 24 24"
        fill="none"
        stroke={colors.accentInk}
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <Path d={up ? "m6 15 6-6 6 6" : "m6 9 6 6 6-6"} />
      </Svg>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: space.gutter, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  // The same spacing as a panel (space.card on every side) but no grey box behind it.
  summary: { gap: 2, padding: space.card },
  // Names the list being shown (the filter), so it reads as the page heading.
  summaryLabel: { fontSize: 15, fontWeight: "700", color: colors.text, letterSpacing: -0.15 },
  summaryTotal: { fontSize: 30, fontWeight: "700", letterSpacing: -0.9, color: colors.text, fontVariant: ["tabular-nums"] },
  splitBar: { flexDirection: "row", height: 8, gap: 3, borderRadius: radius.pill, overflow: "hidden", marginTop: 14 },
  splitLegend: { flexDirection: "row", flexWrap: "wrap", columnGap: 16, rowGap: 4, marginTop: 10 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12, color: colors.muted },
  legendCount: { color: colors.text, fontWeight: "700", fontVariant: ["tabular-nums"] },
  dayHeading: { fontSize: 13, fontWeight: "700", color: colors.muted, marginTop: 22, marginBottom: 8, marginLeft: 4 },
  group: { paddingVertical: 0, paddingHorizontal: 0, overflow: "hidden" },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 12, paddingVertical: 14, paddingHorizontal: space.card },
  rowTop: { flexDirection: "row", alignItems: "baseline", gap: 10 },
  vendor: { flex: 1, fontSize: 15, fontWeight: "700", color: colors.text },
  amount: { fontSize: 15, fontWeight: "700", color: colors.text, fontVariant: ["tabular-nums"] },
  sub: { fontSize: 12, color: colors.muted, fontVariant: ["tabular-nums"] },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  more: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    alignSelf: "center",
    height: 44,
    paddingHorizontal: 20,
    marginTop: 18,
    borderRadius: radius.pill,
    backgroundColor: colors.panel,
  },
  morePressed: { transform: [{ scale: 0.97 }], backgroundColor: colors.panel2 },
  moreText: { fontSize: 14, fontWeight: "600", color: colors.accentInk },
  moreNote: { fontSize: 13, color: colors.muted, fontVariant: ["tabular-nums"] },
});
