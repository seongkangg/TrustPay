// Overall AI confidence for one invoice card: a ring filled to how sure the AI is of its
// recommendation (the same number as the invoice screen), the percent inside, CONFIDENT or UNSURE
// against the policy threshold (GET /mock/thresholds), a hairline, then the recommendation itself.
// Teal on a teal tint when it clears the threshold, amber on amber below it.
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Stop } from "react-native-svg";

import { sentence } from "./ui.js";
import { colors, radius } from "../theme.js";

const SIZE = 54;
const STROKE = 5;
const R = (SIZE - STROKE) / 2;
const C = 2 * Math.PI * R;

const MARK = { approve: "✓", reject: "✕", escalate: "↑" };

export default function ConfidenceRing({ confidence, recommendation, threshold }) {
  const value = Math.min(1, Math.max(0, confidence));
  const unsure = threshold != null && value < threshold;
  const ink = unsure ? colors.riskMedium : colors.accentInk;
  return (
    <View style={[styles.tile, { backgroundColor: unsure ? colors.riskMediumBg : colors.accentBg }]}>
      <View style={styles.ring}>
        <Svg width={SIZE} height={SIZE}>
          <Defs>
            <LinearGradient id="ringTeal" x1="0" y1="0" x2="1" y2="1">
              <Stop offset="0" stopColor={colors.brandTeal} />
              <Stop offset="1" stopColor={colors.accentStrong} />
            </LinearGradient>
          </Defs>
          <Circle cx={SIZE / 2} cy={SIZE / 2} r={R} stroke={colors.bg} strokeWidth={STROKE} fill="none" />
          {value > 0 && (
            <Circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={R}
              stroke={unsure ? colors.riskMedium : "url(#ringTeal)"}
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={`${C * value} ${C}`}
              fill="none"
              transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
            />
          )}
        </Svg>
        <View style={styles.center} pointerEvents="none">
          <Text style={[styles.pct, { color: ink }]}>
            {Math.round(value * 100)}
            <Text style={styles.pctSign}>%</Text>
          </Text>
        </View>
      </View>
      <Text style={[styles.label, { color: ink }]}>{unsure ? "UNSURE" : "CONFIDENT"}</Text>
      {recommendation && (
        <>
          <View style={[styles.rule, { backgroundColor: unsure ? colors.riskMedium : colors.accentSoft }]} />
          <Text style={[styles.rec, { color: colors.text }]} numberOfLines={1}>
            {MARK[recommendation] ? `${MARK[recommendation]} ` : ""}
            {sentence(recommendation)}
          </Text>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { width: 88, alignItems: "center", paddingVertical: 10, paddingHorizontal: 8, borderRadius: radius.cell },
  ring: { width: SIZE, height: SIZE },
  center: { ...StyleSheet.absoluteFillObject, alignItems: "center", justifyContent: "center" },
  pct: { fontSize: 17, fontWeight: "700", letterSpacing: -0.4, fontVariant: ["tabular-nums"] },
  pctSign: { fontSize: 10, fontWeight: "700" },
  label: { marginTop: 6, fontSize: 10, fontWeight: "800", letterSpacing: 0.6 },
  rule: { alignSelf: "stretch", height: StyleSheet.hairlineWidth, marginVertical: 6, opacity: 0.6 },
  rec: { fontSize: 11, fontWeight: "700" },
});
