// Header filter control: a three-line button that opens a small menu anchored under the top-right
// corner. The menu scales in from that corner; reduce-motion makes it appear without movement.
import { useEffect, useState } from "react";
import { AccessibilityInfo, Animated, Easing, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { colors, radius, space } from "../theme.js";

export function FilterButton({ onPress, filtered }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={filtered ? "Filter invoices, filter on" : "Filter invoices"}
      hitSlop={8}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
    >
      <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={colors.text} strokeWidth={2} strokeLinecap="round">
        <Path d="M4 7h16M4 12h16M4 17h16" />
      </Svg>
      {filtered && <View style={styles.dot} />}
    </Pressable>
  );
}

// options: [{ key, label, count }]
export function FilterMenu({ visible, top, options, active, onSelect, onClose }) {
  const [progress] = useState(() => new Animated.Value(0));
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", setReduceMotion);
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (!visible) return;
    progress.setValue(reduceMotion ? 1 : 0);
    if (!reduceMotion) {
      Animated.timing(progress, {
        toValue: 1,
        duration: 180,
        easing: Easing.bezier(0.23, 1, 0.32, 1),
        useNativeDriver: true,
      }).start();
    }
  }, [visible, reduceMotion, progress]);

  const scale = progress.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1] });

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose} statusBarTranslucent>
      <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close filter menu" />
      <Animated.View
        style={[styles.menu, { top, opacity: progress, transform: [{ scale }] }]}
        accessibilityRole="menu"
      >
        {options.map((o) => {
          const on = o.key === active;
          return (
            <Pressable
              key={o.key}
              accessibilityRole="menuitem"
              accessibilityState={{ selected: on }}
              accessibilityLabel={`${o.label}, ${o.count}`}
              onPress={() => onSelect(o.key)}
              style={({ pressed }) => [styles.item, (on || pressed) && { backgroundColor: colors.panel }]}
            >
              <Text style={[styles.label, on && styles.labelOn]}>{o.label}</Text>
              <Text style={styles.count}>{o.count}</Text>
              <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={on ? colors.accent : "transparent"} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
                <Path d="m5 12.5 4.5 4.5L19 7.5" />
              </Svg>
            </Pressable>
          );
        })}
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  button: { width: 40, height: 40, alignItems: "center", justifyContent: "center", borderRadius: radius.pill, marginRight: space.gutter - 10 },
  pressed: { transform: [{ scale: 0.92 }], backgroundColor: colors.panel },
  // Shown while a filter other than All is on.
  dot: {
    position: "absolute",
    top: 8,
    right: 7,
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: colors.accent,
    borderWidth: 2,
    borderColor: colors.surface,
  },
  menu: {
    position: "absolute",
    right: space.gutter - 6,
    width: 216,
    padding: 6,
    borderRadius: radius.panel,
    backgroundColor: colors.surface,
    transformOrigin: "top right",
    // The menu floats, so it carries the one soft shadow.
    shadowColor: "#14161e",
    shadowOpacity: 0.16,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 10,
  },
  item: { flexDirection: "row", alignItems: "center", gap: 8, height: 44, paddingHorizontal: 12, borderRadius: radius.field },
  label: { flex: 1, fontSize: 15, fontWeight: "500", color: colors.text },
  labelOn: { fontWeight: "700" },
  count: { fontSize: 13, fontWeight: "600", color: colors.muted, fontVariant: ["tabular-nums"] },
});
