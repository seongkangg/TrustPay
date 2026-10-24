// Overview charts, drawn with react-native-svg and plain Views. Same marks as the web dashboard:
// a smooth indigo volume line, KPI sparklines, risk bars with high risk in the accent, and the
// 14 by_day days as a calendar. Series colours are the theme tokens.
import { StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Path, Stop, Text as SvgText } from "react-native-svg";

import { fmtMoney } from "../api/client.js";
import { colors, radius } from "../theme.js";

// by_day dates are UTC calendar days ("YYYY-MM-DD"); keep them in UTC so the labels never shift.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const utcDate = (iso) => new Date(`${iso}T00:00:00Z`);
export const dayLabel = (iso) => {
  const d = utcDate(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
};

// Catmull-Rom through the points, as cubic Béziers, so lines have the reference's soft curves.
// Control points are clamped to the baseline so a curve never dips below zero.
function smoothPath(pts, floor) {
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [p0, p1, p2, p3] = [pts[i - 1] || pts[i], pts[i], pts[i + 1], pts[i + 2] || pts[i + 1]];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, Math.min(floor, p1[1] + (p2[1] - p0[1]) / 6)];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, Math.min(floor, p2[1] - (p3[1] - p1[1]) / 6)];
    d += ` C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`;
  }
  return d;
}

// The big chart under the hero figure: received per day, completed as the quiet line.
export function VolumeChart({ days, width, height = 180 }) {
  if (days.length < 2 || width <= 0) return <View style={{ height }} />;
  const padT = 10;
  const padB = 22;
  const innerH = height - padT - padB;
  const floor = padT + innerH;
  const max = Math.max(2, Math.ceil(Math.max(...days.map((d) => d.received)) * 1.15));
  const x = (i) => 2 + (i / (days.length - 1)) * (width - 4);
  const y = (v) => floor - (v / max) * innerH;
  const received = smoothPath(days.map((d, i) => [x(i), y(d.received)]), floor);
  const completed = smoothPath(days.map((d, i) => [x(i), y(d.completed)]), floor);
  const area = `${received} L${x(days.length - 1)},${floor} L${x(0)},${floor} Z`;
  const ticks = [0, Math.round((days.length - 1) / 2), days.length - 1];

  return (
    <Svg width={width} height={height}>
      <Defs>
        <LinearGradient id="volumeFade" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={colors.accent} stopOpacity={0.16} />
          <Stop offset="1" stopColor={colors.accent} stopOpacity={0} />
        </LinearGradient>
      </Defs>
      <Path d={area} fill="url(#volumeFade)" />
      <Path d={completed} stroke={colors.accentSoft} strokeWidth={2} fill="none" strokeLinecap="round" />
      <Path d={received} stroke={colors.accent} strokeWidth={2.5} fill="none" strokeLinecap="round" />
      {ticks.map((i, k) => (
        <SvgText
          key={days[i].date}
          x={x(i)}
          y={height - 4}
          fontSize={11}
          fill={colors.muted}
          textAnchor={k === 0 ? "start" : k === ticks.length - 1 ? "end" : "middle"}
        >
          {dayLabel(days[i].date)}
        </SvgText>
      ))}
    </Svg>
  );
}

// Smooth sparkline for a KPI card; flat at the baseline when every value is zero.
export function Sparkline({ values, width, height = 28, color = colors.accent }) {
  if (values.length < 2 || width <= 0) return <View style={{ height }} />;
  const pad = 3;
  const max = Math.max(1, ...values);
  const floor = height - pad;
  const pts = values.map((v, i) => [pad + (i / (values.length - 1)) * (width - pad * 2), floor - (v / max) * (height - pad * 2)]);
  return (
    <Svg width={width} height={height}>
      <Path d={smoothPath(pts, floor)} stroke={color} strokeWidth={2} fill="none" strokeLinecap="round" />
    </Svg>
  );
}

const RISK_LABEL = { low: "Low risk", medium: "Medium risk", high: "High risk" };

// Risk mix as three soft blocks; the high-risk block is the one in colour because it needs eyes.
export function RiskBars({ invoices }) {
  const rows = ["low", "medium", "high"].map((level) => {
    const items = invoices.filter((inv) => inv.risk_level === level);
    return { level, count: items.length, amount: items.reduce((sum, inv) => sum + (inv.amount || 0), 0) };
  });
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <View style={styles.riskbars}>
      {rows.map((r) => (
        <View key={r.level} style={styles.riskbar}>
          <View style={styles.track}>
            <View
              style={[
                styles.fill,
                { height: `${Math.max(10, (r.count / max) * 100)}%` },
                r.level === "high" && { backgroundColor: colors.accent },
              ]}
            />
          </View>
          <Text style={styles.riskName}>{RISK_LABEL[r.level]}</Text>
          <Text style={styles.riskCount}>
            {r.count} invoice{r.count === 1 ? "" : "s"}
          </Text>
          <Text style={styles.riskAmount}>{fmtMoney(r.amount)}</Text>
        </View>
      ))}
    </View>
  );
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

// The last 14 days as a calendar: invoices received per day, the latest day in the accent.
export function DayCalendar({ days }) {
  if (days.length === 0) return null;
  const lead = utcDate(days[0].date).getUTCDay();
  const cells = [...Array.from({ length: lead }, () => null), ...days];
  while (cells.length % 7) cells.push(null);
  const weeks = Array.from({ length: cells.length / 7 }, (_, w) => cells.slice(w * 7, w * 7 + 7));
  const last = days[days.length - 1].date;
  return (
    <View style={{ gap: 6 }}>
      <View style={styles.week}>
        {WEEKDAYS.map((w, i) => (
          <Text key={i} style={styles.wd}>
            {w}
          </Text>
        ))}
      </View>
      {weeks.map((week, w) => (
        <View key={w} style={styles.week}>
          {week.map((d, i) => {
            if (!d) return <View key={i} style={[styles.cell, { backgroundColor: "transparent" }]} />;
            const today = d.date === last;
            return (
              <View
                key={d.date}
                style={[styles.cell, today && { backgroundColor: colors.accent }]}
                accessibilityLabel={`${dayLabel(d.date)}: ${d.received} received, ${d.completed} completed, ${d.blocked} blocked`}
              >
                <Text style={[styles.cellDate, today && { color: "rgba(255,255,255,0.85)" }]}>
                  {utcDate(d.date).getUTCDate()}
                </Text>
                <Text style={[styles.cellN, d.received === 0 && styles.cellZero, today && { color: "#fff" }]}>
                  {d.received}
                </Text>
              </View>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  riskbars: { flexDirection: "row", gap: 8 },
  riskbar: { flex: 1, alignItems: "center" },
  track: { height: 120, width: "100%", justifyContent: "flex-end" },
  fill: { width: "100%", backgroundColor: colors.panel2, borderRadius: 14 },
  riskName: { marginTop: 10, fontSize: 12, color: colors.muted },
  riskCount: { fontSize: 14, fontWeight: "700", color: colors.text },
  riskAmount: { fontSize: 12, color: colors.muted, fontVariant: ["tabular-nums"] },
  week: { flexDirection: "row", gap: 6 },
  wd: { flex: 1, textAlign: "center", fontSize: 11, fontWeight: "600", color: colors.muted },
  cell: {
    flex: 1,
    height: 48,
    borderRadius: radius.cell,
    backgroundColor: colors.panel2,
    alignItems: "center",
    justifyContent: "center",
  },
  cellDate: { position: "absolute", top: 4, left: 6, fontSize: 11, color: colors.neutralInk },
  cellN: { fontSize: 16, fontWeight: "700", color: colors.text, fontVariant: ["tabular-nums"], marginTop: 6 },
  cellZero: { color: "#a3a6b0", fontWeight: "600" },
});
