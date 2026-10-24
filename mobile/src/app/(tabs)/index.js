// Overview tab: approval queue → invoice volume → counts → risk mix and days → policy violations.
// Read-only; approve / reject happens on the invoice screen.
import { Link, router } from "expo-router";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";

import { fmtMoney, fmtTime } from "../../api/client.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import { DayCalendar, RiskBars, Sparkline, VolumeChart, dayLabel } from "../../components/Charts.js";
import { Alert, Badge, Card, Code, CountPill, H2, Muted, RiskBadge, StatusBadge } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, radius } from "../../theme.js";

const GUTTER = 16;

const wholeDollars = (amount) => `$${Math.round(amount).toLocaleString("en-US")}`;

export default function Overview() {
  const { width } = useWindowDimensions();
  const { summary, invoices, awaiting, error, refreshing, refresh } = useDashboard();

  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const amounts = summary?.amounts;
  const days = summary?.by_day || [];
  const latest = days[days.length - 1];
  const paidShare = amounts?.total ? Math.round((amounts.paid / amounts.total) * 100) : null;
  // by_day is bucketed by UTC calendar day on the backend; say so wherever a day is named.
  const range = days.length ? `${dayLabel(days[0].date)} – ${dayLabel(latest.date)} (UTC)` : "";
  const contentWidth = width - GUTTER * 2;
  const kpiWidth = (contentWidth - 8 * 2) / 3;

  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}

      <View style={styles.sectionHead}>
        <Text style={styles.h2Inline}>Needs your approval</Text>
        <CountPill n={awaiting.length} />
      </View>
      {awaiting.length === 0 ? (
        <Muted small>Nothing waiting. New invoices are checked automatically.</Muted>
      ) : (
        <View style={{ gap: 8 }}>
          {awaiting.map((inv) => (
            <QueueItem key={inv.invoice_id} inv={inv} codes={reasonCodes[inv.invoice_id]} />
          ))}
        </View>
      )}

      <View style={styles.hero}>
        <Text style={styles.heroLabel}>Invoice volume</Text>
        <View style={styles.figureRow}>
          <Text style={styles.figure} numberOfLines={1} adjustsFontSizeToFit>
            {amounts ? wholeDollars(amounts.total) : "—"}
          </Text>
          {paidShare !== null && <Badge label={`${paidShare}% paid`} fg={colors.ok} bg={colors.okBg} />}
        </View>
        {amounts && (
          <View style={styles.split}>
            <Text style={styles.splitText}>
              <Text style={{ color: colors.ok }}>● </Text>Paid{" "}
              <Text style={styles.splitValue}>{fmtMoney(amounts.paid)}</Text>
            </Text>
            <Text style={styles.splitText}>
              <Text style={{ color: colors.blocked }}>● </Text>Withheld{" "}
              <Text style={styles.splitValue}>{fmtMoney(amounts.withheld)}</Text>
            </Text>
          </View>
        )}
        <View style={styles.legendRow}>
          <View style={styles.rangePill}>
            <Text style={styles.rangeText}>Last 14 days</Text>
          </View>
          <View style={styles.legend}>
            <Key color={colors.accent} label="Received" />
            <Key color={colors.accentSoft} label="Completed" />
          </View>
        </View>
        {summary ? (
          <VolumeChart days={days} width={contentWidth} />
        ) : (
          <View style={[styles.skeleton, { height: 180 }]} />
        )}
      </View>

      <View style={styles.kpis}>
        <Kpi
          label="Received"
          value={summary?.total_invoices}
          values={days.map((d) => d.received)}
          width={kpiWidth}
          note={latest?.received > 0 ? `↑ ${latest.received} on ${dayLabel(latest.date)}` : null}
        />
        <Kpi
          label="Completed"
          value={summary ? (summary.by_status.COMPLETED ?? 0) : null}
          values={days.map((d) => d.completed)}
          width={kpiWidth}
        />
        <Kpi
          label="Blocked"
          value={summary ? (summary.by_status.BLOCKED ?? 0) : null}
          values={days.map((d) => d.blocked)}
          width={kpiWidth}
          color={summary?.by_status.BLOCKED ? colors.blocked : colors.accent}
        />
      </View>

      <Card style={{ marginTop: 8 }}>
        <View style={styles.panelHead}>
          <Text style={styles.panelTitle}>Risk mix</Text>
          <Muted small>All invoices</Muted>
        </View>
        <RiskBars invoices={invoices} />
        {summary && (
          <Muted small style={{ marginTop: 12 }}>
            {summary.blocked_actions} blocked tool call{summary.blocked_actions === 1 ? "" : "s"} ·{" "}
            {summary.sensitive_data_detections} invoice{summary.sensitive_data_detections === 1 ? "" : "s"} with masked
            bank or tax data
          </Muted>
        )}
      </Card>

      <Card style={{ marginTop: 8 }}>
        <View style={styles.panelHead}>
          <Text style={styles.panelTitle}>Received per day</Text>
          <Muted small>{range}</Muted>
        </View>
        <DayCalendar days={days} />
      </Card>

      {summary?.recent_violations?.length > 0 && (
        <>
          <H2>Recent policy violations</H2>
          <Card style={{ paddingVertical: 4 }}>
            {summary.recent_violations.map((v, i) => (
              <View key={i} style={[styles.violation, i > 0 && styles.rule]}>
                <Link href={`/invoices/${v.invoice_id}`} style={styles.link}>
                  {v.invoice_id}
                </Link>
                <View style={styles.codes}>
                  {v.reason_codes.map((c) => (
                    <Code key={c}>{c}</Code>
                  ))}
                </View>
                <Muted small>{fmtTime(v.timestamp)}</Muted>
              </View>
            ))}
          </Card>
        </>
      )}
    </ScrollView>
  );
}

function Key({ color, label }) {
  return (
    <View style={styles.key}>
      <View style={[styles.keyDot, { backgroundColor: color }]} />
      <Text style={styles.keyText}>{label}</Text>
    </View>
  );
}

function Kpi({ label, value, values, width, note, color }) {
  return (
    <View style={[styles.kpi, { width }]}>
      <Text style={styles.kpiLabel} numberOfLines={1}>
        {label}
      </Text>
      <Text style={styles.kpiValue}>{value ?? "—"}</Text>
      {note ? (
        <Text style={styles.kpiNote} numberOfLines={1}>
          {note}
        </Text>
      ) : (
        <Text style={styles.kpiNote}> </Text>
      )}
      <Sparkline values={values} width={width - 24} color={color} />
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
        styles.queueItem,
        { backgroundColor: blocked ? colors.blockedBg : colors.accentBg },
        pressed && { transform: [{ scale: 0.98 }] },
      ]}
    >
      <View style={styles.queueHead}>
        <Text style={styles.queueVendor} numberOfLines={1}>
          {inv.vendor_name || "Unknown vendor"}
        </Text>
        <Text style={styles.queueAmount}>{fmtMoney(inv.amount, inv.currency)}</Text>
      </View>
      <View style={styles.badges}>
        <StatusBadge status={inv.status} />
        <RiskBadge level={inv.risk_level} />
      </View>
      {codes.length > 0 && (
        <View style={styles.codes}>
          {codes.map((c) => (
            <Code key={c}>{c}</Code>
          ))}
        </View>
      )}
      <View style={styles.queueFoot}>
        <Muted small>
          {inv.invoice_id} · {fmtTime(inv.updated_at)}
        </Muted>
        <View style={styles.reviewPill}>
          <Text style={styles.reviewText}>Review ›</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: GUTTER, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  h2Inline: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 },
  hero: { marginTop: 28 },
  heroLabel: { fontSize: 13, fontWeight: "500", color: colors.muted },
  figureRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 2 },
  figure: {
    flexShrink: 1,
    fontSize: 38,
    fontWeight: "700",
    letterSpacing: -1.3,
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  split: { flexDirection: "row", flexWrap: "wrap", columnGap: 18, marginTop: 4 },
  splitText: { fontSize: 13, color: colors.muted },
  splitValue: { color: colors.text, fontWeight: "600", fontVariant: ["tabular-nums"] },
  legendRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14 },
  rangePill: { height: 30, paddingHorizontal: 12, borderRadius: radius.pill, backgroundColor: colors.panel, justifyContent: "center" },
  rangeText: { fontSize: 13, fontWeight: "600", color: colors.text },
  legend: { flexDirection: "row", gap: 12 },
  key: { flexDirection: "row", alignItems: "center", gap: 5 },
  keyDot: { width: 8, height: 8, borderRadius: 4 },
  keyText: { fontSize: 12, color: colors.muted },
  skeleton: { backgroundColor: colors.panel, borderRadius: radius.panel, marginTop: 8 },
  kpis: { flexDirection: "row", gap: 8, marginTop: 16 },
  kpi: { backgroundColor: colors.panel, borderRadius: radius.panel, paddingHorizontal: 12, paddingVertical: 12 },
  kpiLabel: { fontSize: 12, fontWeight: "500", color: colors.muted },
  kpiValue: { fontSize: 26, fontWeight: "700", letterSpacing: -0.8, color: colors.text, fontVariant: ["tabular-nums"] },
  kpiNote: { fontSize: 11, fontWeight: "600", color: colors.ok, marginBottom: 4 },
  panelHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 10, marginBottom: 14 },
  panelTitle: { fontSize: 14, fontWeight: "700", color: colors.text },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 2 },
  link: { color: colors.accentInk, fontSize: 13, fontWeight: "600" },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  queueItem: { borderRadius: radius.row, padding: 14, gap: 6 },
  queueHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 8 },
  queueVendor: { fontWeight: "700", fontSize: 15, color: colors.text, flex: 1 },
  queueAmount: { fontWeight: "700", fontSize: 16, color: colors.text, fontVariant: ["tabular-nums"] },
  queueFoot: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  reviewPill: { height: 32, paddingHorizontal: 14, borderRadius: radius.pill, backgroundColor: colors.text, justifyContent: "center" },
  reviewText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  violation: { paddingVertical: 10, gap: 4 },
});
