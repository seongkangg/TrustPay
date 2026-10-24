// Charts for the overview. Bars are plain Views; the 14-day trend is a small SVG line chart.
// Series colors are the same tokens the badges use (theme.js).
import { StyleSheet, Text, View } from "react-native";
import Svg, { Line, Path, Text as SvgText } from "react-native-svg";

import { human } from "../api/client.js";
import { Card } from "./ui.js";
import { RISK, STATUS, STATUS_ORDER, colors } from "../theme.js";

function Title({ children }) {
  return <Text style={styles.title}>{children}</Text>;
}

// Horizontal bars: label on the left, bar + count on the right.
export function BarChart({ title, rows }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <Card style={styles.card}>
      <Title>{title}</Title>
      {rows.map((r) => (
        <View key={r.key} style={styles.barRow}>
          <Text style={styles.barLabel} numberOfLines={1}>
            {r.label}
          </Text>
          <View style={styles.barTrack}>
            <View style={[styles.bar, { width: `${(r.value / max) * 100}%`, backgroundColor: r.color }]} />
          </View>
          <Text style={styles.barValue}>{r.value}</Text>
        </View>
      ))}
    </Card>
  );
}

export function riskRows(byRisk) {
  return ["low", "medium", "high"].map((k) => ({ key: k, label: k, value: byRisk?.[k] ?? 0, color: RISK[k].fg }));
}

export function statusRows(byStatus) {
  return Object.entries(byStatus || {})
    .sort(([a], [b]) => STATUS_ORDER.indexOf(a) - STATUS_ORDER.indexOf(b))
    .map(([k, v]) => ({ key: k, label: human(k).toLowerCase(), value: v, color: STATUS[k]?.fg || colors.muted }));
}

const SERIES = [
  { key: "received", color: colors.accent },
  { key: "completed", color: colors.ok },
  { key: "blocked", color: colors.blocked },
];

export function TrendChart({ title, days, width }) {
  const W = width;
  const H = 160;
  const padL = 24;
  const padB = 18;
  const padT = 8;
  const innerW = W - padL - 8;
  const innerH = H - padB - padT;
  const max = Math.max(1, ...days.flatMap((d) => SERIES.map((s) => d[s.key] ?? 0)));
  const n = days.length;
  const x = (i) => padL + (n > 1 ? (i / (n - 1)) * innerW : innerW / 2);
  const y = (v) => padT + innerH - (v / max) * innerH;
  const path = (key) => days.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d[key] ?? 0).toFixed(1)}`).join(" ");
  const ticks = max <= 4 ? Array.from({ length: max + 1 }, (_, i) => i) : [0, Math.round(max / 2), max];

  return (
    <Card style={styles.card}>
      <Title>{title}</Title>
      <Svg width={W} height={H}>
        {ticks.map((t) => (
          <Line key={t} x1={padL} x2={W - 8} y1={y(t)} y2={y(t)} stroke={colors.border} strokeWidth={1} />
        ))}
        {ticks.map((t) => (
          <SvgText key={`l${t}`} x={padL - 6} y={y(t) + 3} fontSize={9} fill={colors.muted} textAnchor="end">
            {t}
          </SvgText>
        ))}
        {days.map((d, i) =>
          i % 3 === 0 || i === n - 1 ? (
            <SvgText key={d.date} x={x(i)} y={H - 4} fontSize={9} fill={colors.muted} textAnchor="middle">
              {d.date.slice(5)}
            </SvgText>
          ) : null,
        )}
        {SERIES.map((s) => (
          <Path key={s.key} d={path(s.key)} stroke={s.color} strokeWidth={2} fill="none" />
        ))}
      </Svg>
      <View style={styles.legend}>
        {SERIES.map((s) => (
          <View key={s.key} style={styles.legendItem}>
            <View style={[styles.swatch, { backgroundColor: s.color }]} />
            <Text style={styles.legendText}>{s.key}</Text>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: 10 },
  title: { fontSize: 13, fontWeight: "600", color: colors.muted, marginBottom: 8 },
  barRow: { flexDirection: "row", alignItems: "center", marginBottom: 6, gap: 8 },
  barLabel: { width: 110, fontSize: 12, color: colors.text, textTransform: "capitalize" },
  barTrack: { flex: 1, height: 14, backgroundColor: colors.neutralBg, borderRadius: 4, overflow: "hidden" },
  bar: { height: "100%", borderRadius: 4 },
  barValue: { width: 24, textAlign: "right", fontSize: 12, fontWeight: "600", color: colors.text },
  legend: { flexDirection: "row", gap: 14, marginTop: 4 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  swatch: { width: 14, height: 3, borderRadius: 2 },
  legendText: { fontSize: 11, color: colors.muted },
});
