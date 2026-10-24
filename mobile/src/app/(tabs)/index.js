// Overview tab: invoice volume → counts → risk mix and days → policy violations. Read-only; the
// waiting count lives on the Inbox tab in the bottom nav, and approve / reject on the invoice screen.
import { Link, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";

import { fmtMoney, fmtTime } from "../../api/client.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import { DayCalendar, RiskBars, Sparkline, VolumeChart, dayLabel } from "../../components/Charts.js";
import RollingText, { useRolling } from "../../components/RollingText.js";
import { Alert, Badge, Card, H2, Muted, ReasonTag } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, radius, space } from "../../theme.js";

const GUTTER = space.gutter;

const wholeDollars = (amount) => `$${Math.round(amount).toLocaleString("en-US")}`;

export default function Overview() {
  const { width } = useWindowDimensions();
  const { summary, invoices, error, refreshing, refresh } = useDashboard();
  // Bumped each time this tab gains focus, so the volume chart and risk bars animate again.
  const [chartPlay, setChartPlay] = useState(0);
  useFocusEffect(useCallback(() => setChartPlay((n) => n + 1), []));
  // Index of the day being scrubbed on the volume chart, or null.
  const [scrub, setScrub] = useState(null);

  const days = summary?.by_day || [];
  const latest = days[days.length - 1];
  // While a day is scrubbed the hero shows that day's money (from by_day); otherwise the totals.
  // A backend without per-day amounts keeps the totals.
  const scrubDay = scrub !== null && days[scrub]?.amount !== undefined ? days[scrub] : null;
  const amounts = scrubDay
    ? { total: scrubDay.amount, paid: scrubDay.paid, withheld: scrubDay.withheld }
    : summary?.amounts;
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

      <View style={styles.hero}>
        <Text style={styles.heroLabel}>
          Invoice volume{scrubDay ? ` · ${dayLabel(scrubDay.date)} (UTC)` : ""}
        </Text>
        <View style={styles.figureRow}>
          <RollingText
            value={amounts?.total}
            format={wholeDollars}
            style={styles.figure}
            numberOfLines={1}
            adjustsFontSizeToFit
          />
          {paidShare !== null && <PaidPill share={paidShare} />}
        </View>
        {amounts && (
          <View style={styles.split}>
            <Text style={styles.splitText}>
              <Text style={{ color: colors.ok }}>● </Text>Paid{" "}
              <RollingText value={amounts.paid} format={fmtMoney} style={styles.splitValue} />
            </Text>
            <Text style={styles.splitText}>
              <Text style={{ color: colors.blocked }}>● </Text>Withheld{" "}
              <RollingText value={amounts.withheld} format={fmtMoney} style={styles.splitValue} />
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
          <VolumeChart days={days} width={contentWidth} playKey={chartPlay} onScrub={setScrub} />
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
        {/* Keyed on load too, so the bars grow with real data rather than before it arrives. */}
        <RiskBars invoices={invoices} playKey={summary ? chartPlay : -1} />
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
                    <ReasonTag key={c} code={c} />
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

// The "% paid" pill rolls with the hero figures; its own component so only the pill re-renders.
function PaidPill({ share }) {
  const shown = useRolling(share);
  return <Badge label={`${Math.round(shown)}% paid`} fg={colors.ok} bg={colors.okBg} />;
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
      <Sparkline values={values} width={width - 28} color={color} />
    </View>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: GUTTER, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  hero: { marginTop: 8 },
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
  kpi: { backgroundColor: colors.panel, borderRadius: radius.panel, paddingHorizontal: 14, paddingVertical: 14 },
  kpiLabel: { fontSize: 12, fontWeight: "500", color: colors.muted },
  kpiValue: { fontSize: 26, fontWeight: "700", letterSpacing: -0.8, color: colors.text, fontVariant: ["tabular-nums"] },
  kpiNote: { fontSize: 11, fontWeight: "600", color: colors.ok, marginBottom: 4 },
  panelHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 10, marginBottom: 14 },
  panelTitle: { fontSize: 14, fontWeight: "700", color: colors.text },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 2 },
  link: { color: colors.accentInk, fontSize: 13, fontWeight: "600" },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  violation: { paddingVertical: 10, gap: 4 },
});
