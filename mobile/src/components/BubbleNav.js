// Floating bottom nav: a white pill of tabs with a grey bubble behind the active one, and a black
// round action button beside it. The bubble springs between tabs; reduce-motion makes it jump.
// While an emailed invoice is being read and run (action.busy), the button's tick becomes a small
// invoice with a teal scan line sweeping over it; when the run ends the tick pops back in.
// Reduce-motion holds the line still and swaps the icons without the pop.
import { useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Circle, Path } from "react-native-svg";

import { colors, radius, space } from "../theme.js";

export const BAR_HEIGHT = 64;

function Icon({ children, color, size = 20 }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </Svg>
  );
}

export const HomeIcon = (p) => (
  <Icon {...p}>
    <Path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" />
  </Icon>
);

export const InboxIcon = (p) => (
  <Icon {...p}>
    <Path d="M4 13.5 6.4 5.6A1 1 0 0 1 7.4 5h9.2a1 1 0 0 1 1 .6l2.4 7.9V18a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" />
    <Path d="M4 13.5h4.5l1.2 2h4.6l1.2-2H20" />
  </Icon>
);

export const ListIcon = (p) => (
  <Icon {...p}>
    <Path d="M9 7h11M9 12h11M9 17h11" />
    <Path d="M4.5 7h.01M4.5 12h.01M4.5 17h.01" strokeWidth={2.6} />
  </Icon>
);

export const ApproveIcon = (p) => (
  <Icon {...p}>
    <Circle cx="12" cy="12" r="8" />
    <Path d="m8.5 12.2 2.4 2.3 4.6-4.8" />
  </Icon>
);

// A sheet with a folded corner and three text lines; a teal line with a soft glow sweeps down
// and back up it, like a scanner reading the page.
const SCAN = 28;
const SCAN_TOP = 5;
const SCAN_BOTTOM = 22;

function Scanner({ color, still }) {
  const [sweep] = useState(() => new Animated.Value(0.5));
  useEffect(() => {
    if (still) {
      sweep.setValue(0.5);
      return undefined;
    }
    sweep.setValue(0);
    const pass = (to) =>
      Animated.timing(sweep, { toValue: to, duration: 850, easing: Easing.inOut(Easing.quad), useNativeDriver: true });
    const loop = Animated.loop(Animated.sequence([pass(1), pass(0)]));
    loop.start();
    return () => loop.stop();
  }, [still, sweep]);
  const translateY = sweep.interpolate({ inputRange: [0, 1], outputRange: [SCAN_TOP, SCAN_BOTTOM] });
  return (
    <View style={{ width: SCAN, height: SCAN }}>
      <Svg width={SCAN} height={SCAN} viewBox="0 0 28 28" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <Path d="M8 4h8.5L21 8.5V23a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
        <Path d="M16.5 4v4.5H21" />
        <Path d="M10.5 13h7M10.5 16.5h7M10.5 20h4.5" strokeOpacity={0.55} />
      </Svg>
      <Animated.View pointerEvents="none" style={[styles.scanLine, { transform: [{ translateY }] }]}>
        <View style={styles.scanGlow} />
        <View style={styles.scanBeam} />
      </Animated.View>
    </View>
  );
}

// The tick, popping back in (scale and fade) after a scan finishes.
function ActionIcon({ busy, still }) {
  const [pop] = useState(() => new Animated.Value(1));
  const wasBusy = useRef(busy);
  useEffect(() => {
    if (wasBusy.current && !busy && !still) {
      pop.setValue(0);
      Animated.spring(pop, { toValue: 1, useNativeDriver: true, damping: 11, stiffness: 260, mass: 0.7 }).start();
    }
    wasBusy.current = busy;
  }, [busy, still, pop]);
  if (busy) return <Scanner color="#fff" still={still} />;
  const scale = pop.interpolate({ inputRange: [0, 1], outputRange: [0.4, 1] });
  return (
    <Animated.View style={{ opacity: pop, transform: [{ scale }] }}>
      <ApproveIcon color="#fff" size={24} />
    </Animated.View>
  );
}

// tabs: [{ key, label, Icon, badge? }]; action: { label, onPress, busy? }.
export default function BubbleNav({ tabs, active, onSelect, action }) {
  const insets = useSafeAreaInsets();
  const [tabWidth, setTabWidth] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [x] = useState(() => new Animated.Value(0));
  const index = Math.max(
    0,
    tabs.findIndex((t) => t.key === active),
  );

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReduceMotion,
    );
    return () => sub.remove();
  }, []);

  useEffect(() => {
    const to = index * tabWidth;
    if (reduceMotion || tabWidth === 0) x.setValue(to);
    else
      Animated.spring(x, {
        toValue: to,
        useNativeDriver: true,
        damping: 18,
        stiffness: 220,
        mass: 0.8,
      }).start();
  }, [index, tabWidth, reduceMotion, x]);

  return (
    <View
      pointerEvents="box-none"
      style={[styles.wrap, { bottom: Math.max(insets.bottom, 12) }]}
    >
      <View
        style={styles.bar}
        accessibilityRole="tablist"
        onLayout={(e) =>
          setTabWidth((e.nativeEvent.layout.width - 12) / tabs.length)
        }
      >
        {tabWidth > 0 && (
          <Animated.View
            style={[
              styles.bubble,
              { width: tabWidth, transform: [{ translateX: x }] },
            ]}
          />
        )}
        {tabs.map((t) => {
          const on = t.key === active;
          const tint = on ? colors.text : colors.muted;
          return (
            <Pressable
              key={t.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: on }}
              accessibilityLabel={t.badge ? `${t.label}, ${t.badge} waiting` : t.label}
              onPress={() => onSelect(t.key)}
              style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
            >
              <View>
                <t.Icon color={tint} />
                {t.badge > 0 && (
                  <View style={styles.tabBadge}>
                    <Text style={styles.tabBadgeText}>{t.badge > 99 ? "99+" : t.badge}</Text>
                  </View>
                )}
              </View>
              <Text
                style={[styles.label, { color: tint }, on && styles.labelOn]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={action.label}
        accessibilityState={{ busy: Boolean(action.busy) }}
        onPress={action.onPress}
        style={({ pressed }) => [styles.action, pressed && styles.pressed]}
      >
        <ActionIcon busy={Boolean(action.busy)} still={reduceMotion} />
      </Pressable>
    </View>
  );
}

// Floating controls cast a soft shadow (they are the one thing on the screen that floats).
const float = {
  shadowColor: "#14161e",
  shadowOpacity: 0.12,
  shadowRadius: 18,
  shadowOffset: { width: 0, height: 8 },
  elevation: 8,
};

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: space.gutter,
    right: space.gutter,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  bar: {
    flex: 1,
    height: BAR_HEIGHT,
    flexDirection: "row",
    alignItems: "center",
    padding: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    ...float,
  },
  bubble: {
    position: "absolute",
    left: 6,
    top: 6,
    bottom: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.panel2,
  },
  tab: {
    flex: 1,
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    borderRadius: radius.pill,
  },
  label: { fontSize: 12, fontWeight: "500" },
  labelOn: { fontWeight: "700" },
  pressed: { transform: [{ scale: 0.96 }] },
  action: {
    width: BAR_HEIGHT,
    height: BAR_HEIGHT,
    borderRadius: BAR_HEIGHT / 2,
    backgroundColor: colors.brandNavy,
    alignItems: "center",
    justifyContent: "center",
    ...float,
  },
  // Waiting count on a tab icon's top-right corner, in red: invoices whose payment is withheld until
  // someone decides. The deeper risk red keeps the small white digits readable.
  tabBadge: {
    position: "absolute",
    top: -6,
    right: -11,
    minWidth: 18,
    height: 18,
    paddingHorizontal: 4,
    borderRadius: 9,
    backgroundColor: colors.riskHigh,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: colors.surface,
  },
  // The scan line spans the sheet's width; its glow trails just above it.
  scanLine: { position: "absolute", left: 4, right: 4, top: 0, height: 2 },
  scanGlow: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brandTeal,
    opacity: 0.3,
  },
  scanBeam: { height: 2, borderRadius: 1, backgroundColor: colors.brandTeal },
  tabBadgeText: { color: "#fff", fontSize: 10, fontWeight: "700", fontVariant: ["tabular-nums"] },
});
