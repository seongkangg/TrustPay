// Gmail inbox that feeds invoices in: connection state, when it last checked, the last check's
// result as four small stats, and "Check inbox now".
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { api, fmtAgo } from "../api/client.js";
import { colors, radius } from "../theme.js";
import { Alert, Card, Muted } from "./ui.js";

export default function InboxCard({ status, unavailable, onSynced }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (unavailable) {
    return (
      <Card>
        <Muted>Inbox not available on this backend.</Muted>
      </Card>
    );
  }
  if (!status) {
    return (
      <Card>
        <Muted>Loading…</Muted>
      </Card>
    );
  }

  async function sync() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.inboxSync());
      onSynced?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const last = result || status.last_result;
  // Red only for the error state; a switched-off inbox is neutral.
  const state = !status.enabled
    ? { label: "Off", dot: colors.muted }
    : status.authorized
      ? { label: "Connected", dot: colors.ok }
      : { label: "Not authorized", dot: colors.blocked };
  const stats = last
    ? [
        { label: "Checked", value: last.checked ?? 0 },
        { label: "Created", value: last.created?.length ?? 0 },
        { label: "Skipped", value: last.skipped ?? 0 },
        { label: "Failed", value: last.failed?.length ?? 0, alert: (last.failed?.length ?? 0) > 0 },
      ]
    : null;

  return (
    <Card>
      <View style={styles.head}>
        <View style={styles.mailIcon}>
          <Svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke={colors.accentInk} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <Path d="M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z" />
            <Path d="m3.5 7 8.5 6 8.5-6" />
          </Svg>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <View style={styles.stateRow}>
            <View style={[styles.dot, { backgroundColor: state.dot }]} />
            <Text style={styles.stateText}>{state.label}</Text>
          </View>
          <Muted small>
            Last checked {fmtAgo(status.last_sync_at)}
            {status.poll_seconds ? ` · checks every ${status.poll_seconds}s` : ""}
          </Muted>
        </View>
      </View>

      {stats && (
        <View style={styles.stats}>
          {stats.map((s) => (
            <View key={s.label} style={styles.stat}>
              <Text style={[styles.statValue, s.alert && { color: colors.riskHigh }]}>{s.value}</Text>
              <Text style={styles.statLabel}>{s.label}</Text>
            </View>
          ))}
        </View>
      )}
      {stats && <Muted small style={{ marginTop: 6 }}>{result ? "From the check just now." : "From the last check."}</Muted>}

      {error && <Alert kind="danger">{error}</Alert>}
      {!error && status.last_error && <Alert kind="warn">{status.last_error}</Alert>}

      <Pressable
        onPress={sync}
        disabled={busy || !status.enabled}
        accessibilityRole="button"
        style={({ pressed }) => [
          styles.button,
          (busy || !status.enabled) && styles.buttonDisabled,
          pressed && !busy && styles.buttonPressed,
        ]}
      >
        <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={busy || !status.enabled ? colors.neutralInk : "#fff"} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16M20 20v-4h-4" />
        </Svg>
        <Text style={[styles.buttonText, (busy || !status.enabled) && { color: colors.neutralInk }]}>
          {busy ? "Checking…" : "Check inbox now"}
        </Text>
      </Pressable>
    </Card>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "center", gap: 12 },
  mailIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.field,
    backgroundColor: colors.accentBg,
    alignItems: "center",
    justifyContent: "center",
  },
  stateRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  stateText: { fontSize: 15, fontWeight: "700", color: colors.text },
  stats: { flexDirection: "row", gap: 8, marginTop: 16 },
  stat: { flex: 1, alignItems: "center", paddingVertical: 10, borderRadius: radius.field, backgroundColor: colors.surface },
  statValue: { fontSize: 18, fontWeight: "700", color: colors.text, fontVariant: ["tabular-nums"] },
  statLabel: { fontSize: 11, color: colors.muted, marginTop: 1 },
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 44,
    marginTop: 14,
    borderRadius: radius.pill,
    backgroundColor: colors.brandNavy,
  },
  buttonDisabled: { backgroundColor: colors.panel2 },
  buttonPressed: { transform: [{ scale: 0.97 }] },
  buttonText: { fontSize: 15, fontWeight: "700", color: "#fff" },
});
