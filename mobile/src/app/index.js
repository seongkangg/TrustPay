// Overview: approval queue → tiles → charts → inbox → invoices. Read-only except the inbox
// sync button; approve / reject happens on the invoice screen.
import { Link } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";

import { AWAITING_HUMAN, BASE, api, fmtMoney, fmtTime } from "../api/client.js";
import { BarChart, TrendChart, riskRows, statusRows } from "../components/Charts.js";
import { Alert, Badge, Card, Code, H2, Muted, RiskBadge, StatusBadge, Tile } from "../components/ui.js";
import { colors } from "../theme.js";

const REFRESH_MS = 15_000;

export default function Overview() {
  const { width } = useWindowDimensions();
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [inbox, setInbox] = useState({ status: null, unavailable: false });
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([api.summary(), api.listInvoices({ limit: 100 })]);
      setSummary(s);
      setInvoices(list.items);
      setError(null);
    } catch (err) {
      setError(`${err.message} (backend: ${BASE})`);
    }
    try {
      setInbox({ status: await api.inboxStatus(), unavailable: false });
    } catch (err) {
      if (err.status === 404) setInbox({ status: null, unavailable: true });
    }
  }, []);

  useEffect(() => {
    // load() is async: state is set after the fetch resolves, not synchronously in the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const amounts = summary?.amounts;
  const chartWidth = width - 16 * 2 - 14 * 2; // page gutter + card padding

  return (
    <ScrollView
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}

      <H2>
        Needs your approval{awaiting.length > 0 ? ` · ${awaiting.length}` : ""}
      </H2>
      {awaiting.length === 0 ? (
        <Muted>Nothing is waiting for a decision.</Muted>
      ) : (
        awaiting.map((inv) => <QueueItem key={inv.invoice_id} inv={inv} codes={reasonCodes[inv.invoice_id]} />)
      )}

      <H2>At a glance</H2>
      <View style={styles.tiles}>
        <Tile label="Total invoices" value={summary?.total_invoices} />
        <Tile label="Low risk" value={summary?.by_risk.low} color={colors.riskLow} />
        <Tile label="Medium risk" value={summary?.by_risk.medium} color={colors.riskMedium} />
        <Tile label="High risk" value={summary?.by_risk.high} color={colors.riskHigh} />
        <Tile
          label="Blocked actions"
          value={summary?.blocked_actions}
          color={colors.blocked}
          highlight={{ border: colors.blocked, bg: colors.blockedBg }}
        />
        <Tile
          label="Pending approvals"
          value={summary?.pending_approvals}
          color={colors.pending}
          highlight={{ border: colors.pending, bg: colors.surface }}
        />
        <Tile label="Sensitive-data detections" value={summary?.sensitive_data_detections} />
      </View>
      <View style={[styles.tiles, { marginTop: 10 }]}>
        <Tile label="Total amount" value={amounts && fmtMoney(amounts.total)} />
        <Tile label="Paid" value={amounts && fmtMoney(amounts.paid)} color={colors.ok} />
        <Tile label="Withheld (pending + blocked)" value={amounts && fmtMoney(amounts.withheld)} color={colors.blocked} />
      </View>

      {summary && (
        <>
          <H2>Graphs</H2>
          <BarChart title="Invoices by risk level" rows={riskRows(summary.by_risk)} />
          <BarChart title="Invoices by status" rows={statusRows(summary.by_status)} />
          <TrendChart title="Last 14 days" days={summary.by_day || []} width={chartWidth} />
        </>
      )}

      <H2>Inbox</H2>
      <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />

      {summary?.recent_violations?.length > 0 && (
        <>
          <H2>Recent policy violations</H2>
          <Card>
            {summary.recent_violations.map((v, i) => (
              <View key={i} style={styles.violation}>
                <Link href={`/invoices/${v.invoice_id}`} style={styles.link}>
                  {v.invoice_id}
                </Link>
                <View style={styles.codes}>
                  {v.reason_codes.map((c) => (
                    <Code key={c}>{c}</Code>
                  ))}
                </View>
                <Muted small>{fmtTime(v.timestamp)}</Muted>
              </View>
            ))}
          </Card>
        </>
      )}

      <H2>Invoices</H2>
      {invoices.length === 0 ? (
        <Muted>No invoices yet. They appear here as the inbox delivers them.</Muted>
      ) : (
        <Card style={{ padding: 0 }}>
          {invoices.map((inv, i) => (
            <Link key={inv.invoice_id} href={`/invoices/${inv.invoice_id}`} asChild>
              <Pressable style={[styles.row, i > 0 && styles.rowBorder]}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowTitle}>
                    {inv.vendor_name || "—"} <Text style={styles.rowId}>{inv.invoice_id}</Text>
                  </Text>
                  <View style={styles.badges}>
                    <StatusBadge status={inv.status} />
                    <RiskBadge level={inv.risk_level} />
                    {inv.sensitive_data_detected && <Badge label="masked" fg={colors.riskMedium} bg={colors.riskMediumBg} />}
                  </View>
                  <Muted small>
                    {inv.recommendation ? `${inv.recommendation} · ` : ""}
                    {fmtTime(inv.updated_at)}
                  </Muted>
                </View>
                <Text style={styles.rowAmount}>{fmtMoney(inv.amount, inv.currency)}</Text>
              </Pressable>
            </Link>
          ))}
        </Card>
      )}
    </ScrollView>
  );
}

function QueueItem({ inv, codes = [] }) {
  const blocked = inv.status === "BLOCKED";
  return (
    <Link href={`/invoices/${inv.invoice_id}`} asChild>
      <Pressable style={[styles.queueItem, { borderColor: blocked ? colors.blocked : colors.pending }]}>
        <View style={styles.queueHead}>
          <Text style={styles.queueVendor}>{inv.vendor_name || "Unknown vendor"}</Text>
          <Text style={styles.queueAmount}>{fmtMoney(inv.amount, inv.currency)}</Text>
        </View>
        <View style={styles.badges}>
          <StatusBadge status={inv.status} />
          <RiskBadge level={inv.risk_level} />
        </View>
        {codes.length > 0 && (
          <View style={styles.codes}>
            {codes.map((c) => (
              <Code key={c}>{c}</Code>
            ))}
          </View>
        )}
        <View style={styles.queueFoot}>
          <Muted small>
            {inv.invoice_id} · {fmtTime(inv.updated_at)}
          </Muted>
          <Text style={styles.link}>Review &amp; decide →</Text>
        </View>
      </Pressable>
    </Link>
  );
}

function InboxCard({ status, unavailable, onSynced }) {
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
  const label = !status.enabled ? "disabled" : status.authorized ? "authorized" : "not authorized";

  return (
    <Card>
      <View style={styles.inboxHead}>
        <Badge
          label={label}
          fg={authorized ? colors.ok : colors.blocked}
          bg={authorized ? colors.okBg : colors.blockedBg}
          outline={!authorized}
        />
        <Muted small style={{ flex: 1 }}>
          Last sync: {fmtTime(status.last_sync_at)}
          {status.poll_seconds ? ` · polls every ${status.poll_seconds}s` : ""}
        </Muted>
      </View>
      <Pressable style={[styles.button, busy && styles.buttonDisabled]} disabled={busy} onPress={sync}>
        <Text style={styles.buttonText}>{busy ? "Checking…" : "Check inbox now"}</Text>
      </Pressable>
      {error && <Alert kind="danger">{error}</Alert>}
      {!error && status.last_error && <Alert kind="warn">{status.last_error}</Alert>}
      {last && (
        <Muted small style={{ marginTop: 8 }}>
          {result ? "Just now: " : "Last result: "}
          {last.checked} checked · {last.created?.length ?? 0} created · {last.skipped} skipped ·{" "}
          {last.failed?.length ?? 0} failed
        </Muted>
      )}
      {status.recent?.map((m) => (
        <View key={m.message_id} style={styles.mail}>
          <Text style={styles.rowTitle} numberOfLines={1}>
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
            <Muted small style={{ color: colors.blocked }}>
              {m.error || m.status}
            </Muted>
          )}
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 48 },
  tiles: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginVertical: 4 },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 2 },
  link: { color: colors.accent, fontSize: 13, fontWeight: "600" },
  queueItem: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderLeftWidth: 4,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  queueHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 8 },
  queueVendor: { fontWeight: "600", fontSize: 15, color: colors.text, flex: 1 },
  queueAmount: { fontWeight: "700", fontSize: 15, color: colors.text, fontVariant: ["tabular-nums"] },
  queueFoot: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 4 },
  violation: { paddingVertical: 6, gap: 2 },
  row: { flexDirection: "row", alignItems: "center", padding: 12, gap: 10 },
  rowBorder: { borderTopWidth: 1, borderTopColor: colors.border },
  rowTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  rowId: { fontWeight: "400", color: colors.muted, fontSize: 12 },
  rowAmount: { fontWeight: "700", fontSize: 14, color: colors.text, fontVariant: ["tabular-nums"] },
  inboxHead: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  button: { backgroundColor: colors.accent, borderRadius: 8, paddingVertical: 10, alignItems: "center" },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 14 },
  mail: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 8, marginTop: 8, gap: 2 },
});
