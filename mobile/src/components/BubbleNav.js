// Floating bottom nav: a white pill of tabs with a grey bubble behind the active one, and a black
// round action button beside it. The bubble springs between tabs; reduce-motion makes it jump.
import { useEffect, useState } from "react";
import {
  AccessibilityInfo,
  Animated,
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

// tabs: [{ key, label, Icon }]; action: { label, count, onPress }.
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
              accessibilityLabel={t.label}
              onPress={() => onSelect(t.key)}
              style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
            >
              <t.Icon color={tint} />
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
        onPress={action.onPress}
        style={({ pressed }) => [styles.action, pressed && styles.pressed]}
      >
        <ApproveIcon color="#fff" size={24} />
        {action.count > 0 && (
          <View style={styles.count}>
            <Text style={styles.countText}>{action.count}</Text>
          </View>
        )}
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
    backgroundColor: colors.text,
    alignItems: "center",
    justifyContent: "center",
    ...float,
  },
  count: {
    position: "absolute",
    top: 6,
    right: 6,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: colors.text,
  },
  countText: { color: "#fff", fontSize: 11, fontWeight: "700" },
});
