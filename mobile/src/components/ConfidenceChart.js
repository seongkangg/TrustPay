// Agent steps as a bar chart (Intake → Verify → Risk → Approval), same as the web dashboard. One
// reading for every bar: higher is better, and a bar under the threshold needs a person. Intake: how
// fields were read; Verify: share of vendor / PO / duplicate checks confirmed; Risk: how clear the
// invoice is by policy (the Risk agent's own confidence is always 100%, so the bar shows the risk
// level the rules assigned, minus a step per extra issue); Approval: share of 5 model answers
// matching the final one. Value on top, step underneath; tapping a step's "i" shows what it
// measures and why it reads what it does for this invoice. The dashed line is the policy threshold
// (GET /mock/thresholds, from data/approval_limits.json — never hard-coded here); bars under it are
// amber. Bars grow up from the baseline on mount (height on absolutely positioned, childless views,
// so the rounded tops keep their shape); Reduce Motion shows them at once.
import { useEffect, useState } from "react";
import { Animated, Easing, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Line, Text as SvgText } from "react-native-svg";

import { fmtPct, human } from "../api/client.js";
import { colors } from "../theme.js";
import useReduceMotion from "../useReduceMotion.js";
import { reasonLabel } from "./ui.js";

const STEPS = [
  {
    key: "intake_agent",
    label: "Intake",
    about: "How reliably the invoice was read: the lowest confidence among the required fields.",
  },
  {
    key: "verification_agent",
    label: "Verify",
    about: "Share of the vendor, purchase-order and duplicate checks that came back confirmed.",
  },
  {
    key: "policy_risk_agent",
    label: "Risk",
    about:
      "How safe this invoice is to accept under the policy rules. Low risk 100%, medium 60%, high 30%; each extra issue takes off 10 points.",
  },
  {
    key: "approval_agent",
    label: "Approval",
    about: "How often the AI gave the same recommendation when asked 5 times.",
  },
];

// Display scale for the Risk bar (not policy: the rules have already decided the level).
const RISK_CLEARANCE = { low: 1, medium: 0.6, high: 0.3 };
const PER_EXTRA_ISSUE = 0.1;

const CHART_H = 150;
const PAD_T = 18; // room for the value above a full bar
const PAD_B = 4;
const AXIS_W = 34;
const BAR_W = 28;
const GRID = [0, 0.5, 1];

const clamp01 = (v) => Math.min(1, Math.max(0, v));

// Low risk counts no issues (its codes are the "passed" kind).
function riskIssues(d) {
  return d.risk_level === "low" ? [] : (d.reason_codes || []).filter((c) => c !== "POLICY_PASSED");
}

function riskClearance(d) {
  const base = RISK_CLEARANCE[d.risk_level];
  if (base == null) return null;
  return clamp01(base - PER_EXTRA_ISSUE * Math.max(0, riskIssues(d).length - 1));
}

// The invoice-specific line under the general description.
function detail(key, d) {
  if (!d) return "This step did not run for this invoice.";
  if (key === "policy_risk_agent") {
    const issues = riskIssues(d);
    return `${human(d.risk_level)} risk${issues.length ? `: ${issues.map(reasonLabel).join(", ")}` : ", every rule passed"}.`;
  }
  const missing = d.explanation?.missing_information || [];
  if (key === "intake_agent" && missing.length) return `Missing: ${missing.map(human).join(", ")}.`;
  const codes = (d.reason_codes || []).filter((c) => c !== "POLICY_PASSED");
  if (codes.length) return `Flagged: ${codes.map(reasonLabel).join(", ")}.`;
  return "Nothing flagged at this step.";
}

// decisions: AgentDecision objects (oldest first; the latest per agent wins).
export default function ConfidenceChart({ confidence, decisions, threshold }) {
  const reduce = useReduceMotion();
  const [width, setWidth] = useState(0);
  const [grow] = useState(() => STEPS.map(() => new Animated.Value(0)));
  const [info, setInfo] = useState(null); // key of the step whose explanation is open

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
    const d = latest[s.key];
    const raw = d == null ? null : s.key === "policy_risk_agent" ? riskClearance(d) : d.confidence;
    return {
      ...s,
      value: raw == null ? null : clamp01(raw),
      high: s.key === "policy_risk_agent" && d?.risk_level === "high",
      detail: detail(s.key, d),
    };
  });
  const value = confidence ?? 0;
  const below = (v) => threshold != null && v != null && v < threshold;
  const unsure = bars.filter((b) => below(b.value));
  const tone = (b) => (b.high ? colors.riskHigh : below(b.value) ? colors.riskMedium : null);
  const open = bars.find((b) => b.key === info);

  const H = CHART_H - PAD_T - PAD_B;
  const y = (v) => PAD_T + (1 - v) * H;
  const slot = width > AXIS_W ? (width - AXIS_W) / STEPS.length : 0;
  const cx = (i) => AXIS_W + slot * (i + 0.5);

  return (
    <View>
      <Text style={styles.title}>Confidence by step</Text>
      <Text style={[styles.note, below(value) && { color: colors.riskMedium }]}>
        AI confidence {fmtPct(value)}
        {threshold != null ? ` · ${below(value) ? "below" : "above"} the ${fmtPct(threshold)} policy threshold` : ""}
      </Text>
      <Text style={styles.note}>
        {unsure.length === 0
          ? "Higher is better. Every step clears the dashed line."
          : `Higher is better. Needs a person: ${unsure.map((b) => b.label).join(", ")}.`}
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
                      { backgroundColor: tone(b) || colors.accent },
                      { height: grow[i].interpolate({ inputRange: [0, 1], outputRange: [0, h] }) },
                    ]}
                  />
                  <Animated.Text
                    style={[
                      styles.barValue,
                      tone(b) && { color: tone(b) },
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
            <Pressable
              onPress={() => setInfo(info === b.key ? null : b.key)}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={`About ${b.label}`}
              accessibilityState={{ expanded: info === b.key }}
              style={styles.labelRow}
            >
              <Text style={styles.stepLabel}>{b.label}</Text>
              <View style={[styles.info, info === b.key && styles.infoOn]}>
                <Text style={[styles.infoText, info === b.key && { color: colors.bg }]}>i</Text>
              </View>
            </Pressable>
            {b.value == null && <Text style={styles.missing}>Did not run</Text>}
          </View>
        ))}
      </View>

      {open && (
        <View style={styles.tip}>
          <Text style={styles.tipTitle}>{open.label}</Text>
          <Text style={styles.tipText}>{open.about}</Text>
          <Text style={[styles.tipText, styles.tipDetail]}>{open.detail}</Text>
        </View>
      )}

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
  labelRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  stepLabel: { fontSize: 12, color: colors.muted, fontWeight: "600" },
  info: { width: 15, height: 15, borderRadius: 8, borderWidth: 1, borderColor: colors.muted, alignItems: "center", justifyContent: "center" },
  infoOn: { backgroundColor: colors.text, borderColor: colors.text },
  infoText: { fontSize: 10, fontWeight: "700", fontStyle: "italic", color: colors.muted, lineHeight: 12 },
  tip: { marginTop: 10, padding: 10, borderRadius: 8, backgroundColor: colors.panel },
  tipTitle: { fontSize: 12, fontWeight: "700", color: colors.text },
  tipText: { fontSize: 12, color: colors.muted, lineHeight: 17, marginTop: 2 },
  tipDetail: { fontWeight: "600", color: colors.text, marginTop: 4 },
  missing: { fontSize: 11, color: colors.muted },
  legend: { fontSize: 11, color: colors.muted, lineHeight: 16, marginTop: 10 },
});
