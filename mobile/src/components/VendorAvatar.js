// Round vendor badge with initials, in a pale tint picked stably from the vendor name, so the same
// vendor always looks the same across the Invoices and Inbox tabs.
import { StyleSheet, Text, View } from "react-native";

import { colors } from "../theme.js";

// Pale tints from the teal family plus neutral.
const TINTS = [
  { bg: colors.accentBg, fg: colors.accentInk },
  { bg: colors.accentFaint, fg: colors.accentInk },
  { bg: colors.panel2, fg: colors.text },
  { bg: colors.okBg, fg: colors.okText },
];

export function initials(name) {
  const words = (name || "?").replace(/[^A-Za-z0-9 ]/g, " ").trim().split(/\s+/);
  return ((words[0]?.[0] || "?") + (words[1]?.[0] || "")).toUpperCase();
}

function tintFor(name) {
  let h = 0;
  for (const ch of name || "") h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return TINTS[h % TINTS.length];
}

export default function VendorAvatar({ name, size = 40 }) {
  const tint = tintFor(name);
  return (
    <View style={[styles.avatar, { width: size, height: size, borderRadius: size / 2, backgroundColor: tint.bg }]}>
      <Text style={[styles.text, { color: tint.fg, fontSize: size * 0.35 }]}>{initials(name)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  avatar: { alignItems: "center", justifyContent: "center" },
  text: { fontWeight: "700" },
});
