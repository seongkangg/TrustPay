// Confidence through the pipeline as a candlestick chart, one candle per agent step (Intake →
// Verification → Policy & risk → Approval). A candle's body runs from the previous step's
// confidence (open) to this step's (close): green when it held or rose, red when it fell. Intake's
// wick spans the field-by-field read confidence from extraction; the other steps report one number,
// so their wick is the body. The dashed line is the policy threshold (GET /mock/thresholds, from
// data/approval_limits.json — never hard-coded here). Bodies grow from open to close on mount;
// Reduce Motion shows them at once.
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
const PAD_T = 8;
const PAD_B = 8;
const AXIS_W = 34;
const BODY_W = 22;
const GRID = [0, 0.5, 1];

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// open = previous step's close (the first step opens where it closes); wicks from real data only.
function buildCandles(decisions, extraction) {
  const latest = {};
  for (const d of decisions) latest[d.agent] = d;
  const fieldConf = extraction.filter((f) => f.confidence != null).map((f) => clamp01(f.confidence));
  let prev = null;
  return STEPS.map((s, i) => {
    const raw = latest[s.key]?.confidence;
    if (raw == null) return { ...s, missing: true };
    const close = clamp01(raw);
    const open = prev ?? close;
    prev = close;
    const spread = i === 0 && fieldConf.length ? [...fieldConf, open, close] : [open, close];
    return { ...s, open, close, high: Math.max(...spread), low: Math.min(...spread) };
  });
}

// decisions: AgentDecision objects (oldest first; the latest per agent wins).
// extraction: the invoice's per-field read results, for the intake wick.
export default function ConfidenceChart({ confidence, decisions, extraction = [], threshold }) {
  const reduce = useReduceMotion();
  const [width, setWidth] = useState(0);
  const [grow] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (reduce) {
      grow.setValue(1);
      return undefined;
    }
    grow.setValue(0);
    const run = Animated.timing(grow, {
      toValue: 1,
      duration: 700,
      easing: Easing.bezier(0.23, 1, 0.32, 1),
      useNativeDriver: true,
    });
    run.start();
    return () => run.stop();
  }, [reduce, grow]);

  const candles = buildCandles(decisions, extraction);

  const value = confidence ?? 0;
  const unsure = candles.filter((c) => !c.missing && threshold != null && c.close < threshold);
  const H = CHART_H - PAD_T - PAD_B;
  const y = (v) => PAD_T + (1 - v) * H;
  const slot = width > AXIS_W ? (width - AXIS_W) / STEPS.length : 0;
  const cx = (i) => AXIS_W + slot * (i + 0.5);

  return (
    <View>
      <Text style={styles.title}>Confidence through the pipeline</Text>
      <Text style={[styles.note, threshold != null && value < threshold && { color: colors.riskMedium }]}>
        Final {fmtPct(value)}
        {threshold != null ? ` · ${value < threshold ? "below" : "above"} the ${fmtPct(threshold)} policy threshold` : ""}
      </Text>
      <Text style={styles.note}>
        {unsure.length === 0
          ? "Every step was confident."
          : `${unsure.map((c) => c.label).join(", ")} ${unsure.length === 1 ? "was" : "were"} unsure.`}
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
              {threshold != null && (
                <>
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
                </>
              )}
              {candles.map((c, i) =>
                c.missing ? null : (
                  <Line
                    key={c.key}
                    x1={cx(i)}
                    x2={cx(i)}
                    y1={y(c.high)}
                    y2={y(c.low)}
                    stroke={c.close >= c.open ? colors.ok : colors.riskHigh}
                    strokeWidth={2}
                    strokeLinecap="round"
                  />
                ),
              )}
            </Svg>
            {candles.map((c, i) => {
              if (c.missing) return null;
              const up = c.close >= c.open;
              const top = y(Math.max(c.open, c.close));
              const height = Math.max(3, Math.abs(c.close - c.open) * H);
              return (
                <Animated.View
                  key={`b${c.key}`}
                  pointerEvents="none"
                  style={[
                    styles.body,
                    {
                      left: cx(i) - BODY_W / 2,
                      top,
                      height,
                      backgroundColor: up ? colors.ok : colors.riskHigh,
                      // Grow from the open edge toward the close, like a price moving.
                      transformOrigin: up ? "bottom" : "top",
                      transform: [{ scaleY: grow }],
                    },
                  ]}
                />
              );
            })}
          </>
        )}
      </View>

      <View style={[styles.labels, { paddingLeft: AXIS_W }]}>
        {candles.map((c) => (
          <View key={c.key} style={styles.labelCell}>
            <Text style={styles.stepLabel}>{c.label}</Text>
            <Text
              style={[
                styles.stepValue,
                !c.missing && c.close < c.open && { color: colors.riskHigh },
                !c.missing && threshold != null && c.close < threshold && { color: colors.riskMedium },
              ]}
            >
              {c.missing ? "—" : fmtPct(c.close)}
            </Text>
          </View>
        ))}
      </View>

      <Text style={styles.legend}>
        Each candle runs from the previous step’s confidence to this one’s: green held or rose, red fell. The
        Intake wick spans how confidently each field was read.
        {threshold != null ? ` Dashed line: the ${fmtPct(threshold)} threshold; below it a person must review.` : ""}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 14, fontWeight: "700", color: colors.text },
  note: { fontSize: 12, color: colors.muted, lineHeight: 17, marginTop: 2 },
  body: { position: "absolute", width: BODY_W, borderRadius: 4 },
  labels: { flexDirection: "row", marginTop: 6 },
  labelCell: { flex: 1, alignItems: "center" },
  stepLabel: { fontSize: 11, color: colors.muted, fontWeight: "600" },
  stepValue: { fontSize: 13, color: colors.text, fontWeight: "700", fontVariant: ["tabular-nums"] },
  legend: { fontSize: 11, color: colors.muted, lineHeight: 16, marginTop: 10 },
});
