// Loading placeholders: soft grey blocks laid out like the content that is coming, pulsing gently
// (opacity on the native driver) until it arrives. Reduce Motion holds them still.
import { useEffect, useState } from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";

import { colors, radius, space } from "../theme.js";
import useReduceMotion from "../useReduceMotion.js";
import { Card } from "./ui.js";

// One pulse shared by every block on screen, so they breathe together rather than flicker.
function usePulse() {
  const reduce = useReduceMotion();
  const [pulse] = useState(() => new Animated.Value(1));
  useEffect(() => {
    if (reduce) {
      pulse.setValue(1);
      return undefined;
    }
    const ease = Easing.inOut(Easing.ease);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 0.45, duration: 750, easing: ease, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 750, easing: ease, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reduce, pulse]);
  return pulse;
}

export function Bone({ width = "100%", height = 12, round = 6, style }) {
  return <View style={[{ width, height, borderRadius: round, backgroundColor: colors.panel2 }, style]} />;
}

// Wraps a group of bones in the shared pulse.
export function Shimmer({ children, style }) {
  const pulse = usePulse();
  return <Animated.View style={[{ opacity: pulse }, style]}>{children}</Animated.View>;
}

// A list row shaped like the invoice rows: avatar, two lines, two badge pills, amount.
export function RowBones({ first }) {
  return (
    <View style={[styles.row, !first && styles.rule]}>
      <Bone width={40} height={40} round={20} />
      <View style={{ flex: 1, gap: 8 }}>
        <View style={styles.between}>
          <Bone width="52%" height={14} />
          <Bone width={64} height={14} />
        </View>
        <Bone width="36%" height={10} />
        <View style={{ flexDirection: "row", gap: 6 }}>
          <Bone width={72} height={20} round={radius.pill} />
          <Bone width={64} height={20} round={radius.pill} />
        </View>
      </View>
    </View>
  );
}

// A card of invoice-shaped rows.
export function ListSkeleton({ rows = 3 }) {
  return (
    <Shimmer>
      <Card style={styles.group}>
        {Array.from({ length: rows }, (_, i) => (
          <RowBones key={i} first={i === 0} />
        ))}
      </Card>
    </Shimmer>
  );
}

// The invoice review screen while it loads: badges, vendor, amount and meta line, the status
// banner, then the recommendation card with a verdict pill and a few lines of text.
export function ReviewSkeleton() {
  return (
    <Shimmer>
      <View style={{ flexDirection: "row", gap: 6, marginBottom: 12 }}>
        <Bone width={84} height={22} round={radius.pill} />
        <Bone width={70} height={22} round={radius.pill} />
      </View>
      <Bone width="62%" height={20} />
      <Bone width="48%" height={38} round={8} style={{ marginTop: 10 }} />
      <Bone width="70%" height={12} style={{ marginTop: 10 }} />
      <Bone height={58} round={radius.alert} style={{ marginTop: 18 }} />
      <Bone width={150} height={16} style={{ marginTop: 28, marginBottom: 12 }} />
      <Card style={{ gap: 10 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          <Bone width={96} height={40} round={radius.field} />
          <Bone width="45%" height={12} />
        </View>
        <Bone height={130} round={radius.field} style={{ marginTop: 6 }} />
        <Bone width="92%" height={12} />
        <Bone width="80%" height={12} />
        <Bone width="60%" height={12} />
      </Card>
    </Shimmer>
  );
}

const styles = StyleSheet.create({
  group: { paddingVertical: 0, paddingHorizontal: 0, overflow: "hidden" },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 12, paddingVertical: 14, paddingHorizontal: space.card },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  between: { flexDirection: "row", justifyContent: "space-between", gap: 10 },
});
