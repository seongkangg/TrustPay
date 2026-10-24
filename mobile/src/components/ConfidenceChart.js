// Confidence by agent step as a bar chart (Intake → Verify → Risk → Approval): bar height is that
// step's confidence, value on top, step underneath. The dashed line is the policy threshold
// (GET /mock/thresholds, from data/approval_limits.json — never hard-coded here); bars under it are
// amber. Bars grow up from the baseline on mount (height on absolutely positioned, childless views,
// so the rounded tops keep their shape); Reduce Motion shows them at once.
import { useEffect, useState } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import Svg, { Line, Text as SvgText } from "react-native-svg";

import { fmtPct } from "../api/client.js";
import { colors } from "../theme.js";
import useReduceMotion from "../useReduceMotion.js";

const STEPS = [
  { key: "intake_agent", label: "Intake" },
  { key: "verification_agent", label: "Verify" },
  { key: "policy_risk_agent", label: "Risk" },
  { key: "approval_agent", label: "Approval" },
];

const CHART_H = 150;
const PAD_T = 18; // room for the value above a full bar
const PAD_B = 4;
const AXIS_W = 34;
const BAR_W = 28;
const GRID = [0, 0.5, 1];

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// decisions: AgentDecision objects (oldest first; the latest per agent wins).
export default function ConfidenceChart({ confidence, decisions, threshold }) {
  const reduce = useReduceMotion();
  const [width, setWidth] = useState(0);
  const [grow] = useState(() => STEPS.map(() => new Animated.Value(0)));

  useEffect(() => {
    if (reduce) {
      grow.forEach((v) => v.setValue(1));
      return undefined;
    }
    grow.forEach((v) => v.setValue(0));
    const run = Animated.stagger(
      70,
      grow.map((v) =>
        Animated.timing(v, { toValue: 1, duration: 600, easing: Easing.bezier(0.23, 1, 0.32, 1), useNativeDriver: false }),
      ),
    );
    run.start();
    return () => run.stop();
  }, [reduce, grow]);

  const latest = {};
  for (const d of decisions) latest[d.agent] = d;
  const bars = STEPS.map((s) => {
    const c = latest[s.key]?.confidence;
    return { ...s, value: c == null ? null : clamp01(c) };
  });
  const value = confidence ?? 0;
  const below = (v) => threshold != null && v != null && v < threshold;
  const unsure = bars.filter((b) => below(b.value));

  const H = CHART_H - PAD_T - PAD_B;
  const y = (v) => PAD_T + (1 - v) * H;
  const slot = width > AXIS_W ? (width - AXIS_W) / STEPS.length : 0;
  const cx = (i) => AXIS_W + slot * (i + 0.5);

  return (
    <View>
      <Text style={styles.title}>Confidence by step</Text>
      <Text style={[styles.note, below(value) && { color: colors.riskMedium }]}>
        Final {fmtPct(value)}
        {threshold != null ? ` · ${below(value) ? "below" : "above"} the ${fmtPct(threshold)} policy threshold` : ""}
      </Text>
      <Text style={styles.note}>
        {unsure.length === 0
          ? "Every step was confident."
          : `${unsure.map((b) => b.label).join(", ")} ${unsure.length === 1 ? "was" : "were"} unsure.`}
      </Text>

      <View style={{ height: CHART_H, marginTop: 12 }} onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
        {width > 0 && (
          <>
            <Svg width={width} height={CHART_H}>
              {GRID.map((g) => (
                <Line key={g} x1={AXIS_W} x2={width} y1={y(g)} y2={y(g)} stroke={colors.grid} strokeWidth={1} />
              ))}
              {GRID.map((g) => (
                <SvgText key={`l${g}`} x={AXIS_W - 6} y={y(g) + 4} fontSize={10} fill={colors.muted} textAnchor="end">
                  {`${g * 100}%`}
                </SvgText>
              ))}
            </Svg>
            {bars.map((b, i) => {
              if (b.value == null) return null;
              const h = Math.max(3, b.value * H);
              return (
                <View key={b.key} pointerEvents="none" style={[styles.slot, { left: cx(i) - BAR_W / 2, top: PAD_T, height: H }]}>
                  <Animated.View
                    style={[
                      styles.bar,
                      { backgroundColor: below(b.value) ? colors.riskMedium : colors.accent },
                      { height: grow[i].interpolate({ inputRange: [0, 1], outputRange: [0, h] }) },
                    ]}
                  />
                  <Animated.Text
                    style={[
                      styles.barValue,
                      below(b.value) && { color: colors.riskMedium },
                      { bottom: grow[i].interpolate({ inputRange: [0, 1], outputRange: [2, h + 2] }), opacity: grow[i] },
                    ]}
                  >
                    {fmtPct(b.value)}
                  </Animated.Text>
                </View>
              );
            })}
            {/* Threshold drawn last so it reads across the bars. */}
            {threshold != null && (
              <Svg width={width} height={CHART_H} style={StyleSheet.absoluteFill} pointerEvents="none">
                <Line
                  x1={AXIS_W}
                  x2={width}
                  y1={y(threshold)}
                  y2={y(threshold)}
                  stroke={colors.text}
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
                <SvgText x={AXIS_W - 6} y={y(threshold) + 4} fontSize={10} fontWeight="700" fill={colors.text} textAnchor="end">
                  {fmtPct(threshold)}
                </SvgText>
              </Svg>
            )}
          </>
        )}
      </View>

      <View style={[styles.labels, { paddingLeft: AXIS_W }]}>
        {bars.map((b) => (
          <View key={b.key} style={styles.labelCell}>
            <Text style={styles.stepLabel}>{b.label}</Text>
            {b.value == null && <Text style={styles.missing}>Did not run</Text>}
          </View>
        ))}
      </View>

      {threshold != null && (
        <Text style={styles.legend}>
          Dashed line: the {fmtPct(threshold)} policy threshold. A step below it means a person must review.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 14, fontWeight: "700", color: colors.text },
  note: { fontSize: 12, color: colors.muted, lineHeight: 17, marginTop: 2 },
  slot: { position: "absolute", width: BAR_W },
  bar: { position: "absolute", left: 0, right: 0, bottom: 0, borderTopLeftRadius: 6, borderTopRightRadius: 6, borderBottomLeftRadius: 2, borderBottomRightRadius: 2 },
  barValue: {
    position: "absolute",
    left: -12,
    right: -12,
    textAlign: "center",
    fontSize: 12,
    fontWeight: "700",
    color: colors.text,
    fontVariant: ["tabular-nums"],
  },
  labels: { flexDirection: "row", marginTop: 6 },
  labelCell: { flex: 1, alignItems: "center" },
  stepLabel: { fontSize: 12, color: colors.muted, fontWeight: "600" },
  missing: { fontSize: 11, color: colors.muted },
  legend: { fontSize: 11, color: colors.muted, lineHeight: 16, marginTop: 10 },
});
