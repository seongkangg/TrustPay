// Gmail inbox that feeds invoices in: authorization state, "Check inbox now", last result, and
// the recent messages with links to the invoices they created.
import { Link } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { api, fmtTime } from "../api/client.js";
import { colors } from "../theme.js";
import { Alert, Badge, Card, Muted, PillButton, sentence } from "./ui.js";

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
    <>
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

      <Text style={styles.h2}>Recent messages</Text>
      {status.recent?.length ? (
        <Card style={{ paddingVertical: 4 }}>
          {status.recent.map((m, i) => (
            <View key={m.message_id} style={[styles.mail, i > 0 && styles.rule]}>
              <Text style={styles.subject} numberOfLines={1}>
                {m.subject || "—"}
              </Text>
              <Muted small>
                {m.sender || "—"} · {fmtTime(m.received_at)}
                {m.attachment_name ? ` · ${m.attachment_name}` : ""}
              </Muted>
              {m.invoice_id ? (
                <Link href={`/invoices/${m.invoice_id}`} style={styles.link}>
                  {m.invoice_id}
                </Link>
              ) : (
                <Muted small>{m.error || sentence(m.status)}</Muted>
              )}
            </View>
          ))}
        </Card>
      ) : (
        <Muted small>No messages yet. Invoices emailed to the inbox show up here.</Muted>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 12 },
  h2: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16, marginTop: 28, marginBottom: 12 },
  mail: { paddingVertical: 10, gap: 2 },
  rule: { borderTopWidth: 1, borderTopColor: colors.panel2 },
  subject: { fontSize: 14, fontWeight: "600", color: colors.text },
  link: { color: colors.accentInk, fontSize: 13, fontWeight: "600" },
});
