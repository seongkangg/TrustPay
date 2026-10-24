// Overview charts, drawn with react-native-svg and plain Views. Same marks as the web dashboard:
// a smooth teal volume line, KPI sparklines, risk bars with high risk in the accent, and the
// 14 by_day days as a calendar. Series colours are the theme tokens.
import { useEffect, useState } from "react";
import { AccessibilityInfo, Animated, Easing, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop, Text as SvgText } from "react-native-svg";

import { fmtMoney } from "../api/client.js";
import { colors, radius } from "../theme.js";

const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

// Follows the system Reduce Motion setting, live.
function useReduceMotion() {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduce);
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", setReduce);
    return () => sub.remove();
  }, []);
  return reduce;
}

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
// The grid and day labels stay put; the data draws in left to right (900ms) whenever `playKey` changes
// (each time the Overview tab gains focus). The wipe is two opposing translateX transforms on the
// native driver: the outer view clips and slides in from the left while the inner one slides back,
// so the drawing stays in place and is revealed. Reduce motion swaps it for a short fade.
//
// Touch and drag to scrub (the phone's version of the desktop hover tooltip): the nearest day gets a
// cursor line, dots on both series and a card with its counts. The selection snaps to days, so state
// changes only when the finger crosses into another day, not on every move. A vertical swipe is
// handed to the page's ScrollView, which ends the scrub.
export function VolumeChart({ days, width, height = 180, playKey = 0 }) {
  const [progress] = useState(() => new Animated.Value(0));
  const reduceMotion = useReduceMotion();
  const [active, setActive] = useState(null);

  useEffect(() => {
    progress.setValue(0);
    const run = Animated.timing(progress, {
      toValue: 1,
      duration: reduceMotion ? 150 : 900,
      easing: EASE_OUT,
      useNativeDriver: true,
    });
    run.start();
    return () => run.stop();
  }, [playKey, reduceMotion, progress]);

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

  const wipe = reduceMotion
    ? { outer: { opacity: progress }, inner: null }
    : {
        outer: { transform: [{ translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [-width, 0] }) }] },
        inner: { transform: [{ translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [width, 0] }) }] },
      };

  const pick = (e) => {
    const i = Math.round(((e.nativeEvent.locationX - 2) / (width - 4)) * (days.length - 1));
    setActive(Math.min(days.length - 1, Math.max(0, i)));
  };
  const clear = () => setActive(null);
  const day = active === null ? null : days[active];
  const TIP_W = 132;
  const tipLeft = day ? Math.min(width - TIP_W, Math.max(0, x(active) - TIP_W / 2)) : 0;

  return (
    <View
      style={{ width, height }}
      onStartShouldSetResponder={() => true}
      onResponderGrant={pick}
      onResponderMove={pick}
      onResponderRelease={clear}
      onResponderTerminate={clear}
      accessibilityLabel="Invoices received per day, last 14 days. Touch and drag to see each day."
    >
      {/* Layers ignore touches, so locationX is always measured against this chart's own box. */}
      <Svg width={width} height={height} pointerEvents="none">
        {/* Faint dashed grid behind the data: one vertical line per day, quarters of the height. */}
        {days.map((d, i) => (
          <Line key={`v${d.date}`} x1={x(i)} x2={x(i)} y1={padT} y2={floor} stroke={colors.grid} strokeWidth={1} strokeDasharray="3 5" />
        ))}
        {[0, 1, 2, 3, 4].map((k) => (
          <Line
            key={`h${k}`}
            x1={x(0)}
            x2={x(days.length - 1)}
            y1={padT + (k / 4) * innerH}
            y2={padT + (k / 4) * innerH}
            stroke={colors.grid}
            strokeWidth={1}
            strokeDasharray="3 5"
          />
        ))}
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
      <Animated.View pointerEvents="none" style={[styles.wipe, { width, height }, wipe.outer]}>
        <Animated.View style={[{ width, height }, wipe.inner]}>
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
          </Svg>
        </Animated.View>
      </Animated.View>
      {day && (
        <>
          <Svg width={width} height={height} style={styles.wipe} pointerEvents="none">
            <Line x1={x(active)} x2={x(active)} y1={padT} y2={floor} stroke={colors.accentSoft} strokeWidth={1.5} />
            <Circle cx={x(active)} cy={y(day.completed)} r={4} fill={colors.accentSoft} stroke={colors.surface} strokeWidth={2} />
            <Circle cx={x(active)} cy={y(day.received)} r={5} fill={colors.accent} stroke={colors.surface} strokeWidth={2} />
          </Svg>
          <View pointerEvents="none" style={[styles.tip, { left: tipLeft, width: TIP_W }]}>
            <Text style={styles.tipDate}>{dayLabel(day.date)}</Text>
            <TipRow color={colors.accent} label={`${day.received} received`} />
            <TipRow color={colors.accentSoft} label={`${day.completed} completed`} />
            {day.blocked > 0 && <TipRow color={colors.blocked} label={`${day.blocked} blocked`} />}
          </View>
        </>
      )}
    </View>
  );
}

function TipRow({ color, label }) {
  return (
    <View style={styles.tipRow}>
      <View style={[styles.tipDot, { backgroundColor: color }]} />
      <Text style={styles.tipText}>{label}</Text>
    </View>
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

const RISK_BAR = { low: colors.accentFaint, medium: colors.accentMid, high: colors.accent };

const RISK_LABEL = { low: "Low risk", medium: "Medium risk", high: "High risk" };

// Risk mix as three blocks in one teal family that darkens with risk: light, mid, then the full accent.
// Whenever `playKey` changes the blocks grow up from the baseline, 80ms apart. Height is animated
// rather than scaleY so the rounded tops keep their shape; each block is absolutely positioned
// with no children, so nothing else re-lays out. Reduce Motion swaps the growth for a short fade.
export function RiskBars({ invoices, playKey = 0 }) {
  const [grow] = useState(() => [0, 1, 2].map(() => new Animated.Value(0)));
  const reduceMotion = useReduceMotion();

  useEffect(() => {
    grow.forEach((v) => v.setValue(0));
    const run = Animated.stagger(
      reduceMotion ? 0 : 80,
      grow.map((v) =>
        Animated.timing(v, { toValue: 1, duration: reduceMotion ? 150 : 700, easing: EASE_OUT, useNativeDriver: false }),
      ),
    );
    run.start();
    return () => run.stop();
  }, [playKey, reduceMotion, grow]);

  const rows = ["low", "medium", "high"].map((level) => {
    const items = invoices.filter((inv) => inv.risk_level === level);
    return { level, count: items.length, amount: items.reduce((sum, inv) => sum + (inv.amount || 0), 0) };
  });
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <View style={styles.riskbars}>
      {rows.map((r, i) => {
        const pct = `${Math.max(10, (r.count / max) * 100)}%`;
        return (
          <View key={r.level} style={styles.riskbar}>
            <View style={styles.track}>
              <Animated.View
                style={[
                  styles.fill,
                  { backgroundColor: RISK_BAR[r.level] },
                  reduceMotion
                    ? { height: pct, opacity: grow[i] }
                    : { height: grow[i].interpolate({ inputRange: [0, 1], outputRange: ["0%", pct] }) },
                ]}
              />
            </View>
            <Text style={styles.riskName}>{RISK_LABEL[r.level]}</Text>
            <Text style={styles.riskCount}>
              {r.count} invoice{r.count === 1 ? "" : "s"}
            </Text>
            <Text style={styles.riskAmount}>{fmtMoney(r.amount)}</Text>
          </View>
        );
      })}
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
                style={[styles.cell, today && { backgroundColor: colors.accentStrong }]}
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
  wipe: { position: "absolute", left: 0, top: 0, overflow: "hidden" },
  // The scrub card floats over the chart, so it carries the one soft shadow.
  tip: {
    position: "absolute",
    top: -6,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: radius.field,
    backgroundColor: colors.surface,
    shadowColor: "#14161e",
    shadowOpacity: 0.14,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  tipDate: { fontSize: 12, fontWeight: "700", color: colors.text, marginBottom: 2 },
  tipRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  tipDot: { width: 8, height: 8, borderRadius: 4 },
  tipText: { fontSize: 12, color: colors.text, fontVariant: ["tabular-nums"], lineHeight: 18 },
  riskbars: { flexDirection: "row", gap: 8 },
  riskbar: { flex: 1, alignItems: "center" },
  track: { height: 120, width: "100%", justifyContent: "flex-end" },
  fill: { position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: colors.panel2, borderRadius: 14 },
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
