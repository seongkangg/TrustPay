// Gmail inbox that feeds invoices in: authorization state, last sync, "Check inbox now" and the
// last sync result.
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { api, fmtTime } from "../api/client.js";
import { colors } from "../theme.js";
import { Alert, Badge, Card, Muted, PillButton } from "./ui.js";

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
  const authorized = status.enabled && status.authorized;
  const label = !status.enabled ? "Disabled" : status.authorized ? "Authorized" : "Not authorized";
  // Red only for the error state; a switched-off inbox is neutral.
  const tone = authorized ? { fg: colors.ok, bg: colors.okBg } : status.enabled ? { fg: "#fff", bg: colors.blocked } : {};

  return (
    <Card>
      <View style={styles.head}>
        <Badge label={label} {...tone} />
        <Muted small style={{ flex: 1 }}>
          Last sync: {fmtTime(status.last_sync_at)}
          {status.poll_seconds ? ` · polls every ${status.poll_seconds}s` : ""}
        </Muted>
      </View>
      <PillButton
        label={busy ? "Checking…" : "Check inbox now"}
        disabled={busy || !status.enabled}
        onPress={sync}
      />
      {error && <Alert kind="danger">{error}</Alert>}
      {!error && status.last_error && <Alert kind="warn">{status.last_error}</Alert>}
      {last && (
        <Muted small style={{ marginTop: 10 }}>
          {result ? "Just now: " : "Last result: "}
          {last.checked} checked · {last.created?.length ?? 0} created · {last.skipped} skipped ·{" "}
          {last.failed?.length ?? 0} failed
        </Muted>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 12 },
});
