// One invoice: masked fields, extraction, AI recommendation vs. explicit human decision,
// agent timeline, tool calls. The approve / reject buttons are the only write action in the app.
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { AWAITING_HUMAN, api, fmtMoney, fmtPct, fmtTime, human } from "../../api/client.js";
import { Alert, Badge, Card, Code, H2, Muted, PillButton, RiskBadge, StatusBadge, sentence } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, radius, space } from "../../theme.js";

export default function InvoiceScreen() {
  const { id } = useLocalSearchParams();
  const dashboard = useDashboard();
  const [invoice, setInvoice] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [inv, tl] = await Promise.all([api.getInvoice(id), api.timeline(id)]);
      setInvoice(inv);
      setTimeline(tl.entries);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    // load() is async: state is set after the fetch resolves, not synchronously in the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  if (error && !invoice) {
    return (
      <View style={styles.page}>
        <Alert kind="danger">{error}</Alert>
      </View>
    );
  }
  if (!invoice) {
    return (
      <View style={styles.page}>
        <Muted>Loading…</Muted>
      </View>
    );
  }

  const decisions = timeline.filter((e) => e.kind === "decision").map((e) => e.data);
  const toolCalls = timeline.filter((e) => e.kind === "tool_call").map((e) => e.data);
  const events = timeline.filter((e) => e.kind === "event").map((e) => e.data);
  const blockedCalls = toolCalls.filter((c) => c.authorization !== "allowed").length;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <Stack.Screen options={{ title: invoice.invoice_id }} />
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
      >
        <View style={styles.badges}>
          <StatusBadge status={invoice.status} />
          <RiskBadge level={invoice.risk_level} />
        </View>
        {error && <Alert kind="danger">{error}</Alert>}

        {invoice.sensitive_data_detected && (
          <Alert kind="warn">
            Sensitive data detected and masked. Banking / tax identifiers are shown as last-four only and were
            never passed to a model or written to a log.
          </Alert>
        )}
        {["BLOCKED", "FAILED"].includes(invoice.status) && (
          <Alert kind="danger">Payment blocked. Governance stopped automatic processing for this invoice.</Alert>
        )}
        {blockedCalls > 0 && (
          <Alert kind="danger">
            {blockedCalls} unauthorized tool call{blockedCalls > 1 ? "s were" : " was"} blocked and recorded.
          </Alert>
        )}

        <H2>Recommendation &amp; approval</H2>
        <ApprovalPanel
          invoice={invoice}
          decisions={decisions}
          events={events}
          onDecided={() => {
            load();
            // Keep the tabs and the bottom nav's waiting count in step with the decision.
            dashboard.load();
          }}
        />

        <H2>Invoice</H2>
        <Card>
          <KV k="Vendor" v={`${invoice.vendor_name || "—"}${invoice.vendor_id ? ` (${invoice.vendor_id})` : ""}`} />
          <KV k="Vendor invoice #" v={invoice.vendor_invoice_number} />
          <KV k="Amount" v={fmtMoney(invoice.amount, invoice.currency)} />
          <KV k="Due date" v={invoice.due_date || "—"} />
          <KV k="Purchase order" v={invoice.purchase_order_id || "—"} />
          <KV k="Bank account" v={invoice.bank_account || "—"} />
          <KV k="Routing number" v={invoice.routing_number || "—"} />
          <KV k="Tax ID" v={invoice.tax_id || "—"} />
          <KV k="Source" v={invoice.source_document || "structured upload"} />
          <KV k="Received" v={fmtTime(invoice.created_at)} last />
        </Card>

        <H2>Extraction</H2>
        <Card>
          {invoice.extraction?.length ? (
            invoice.extraction.map((f, i) => (
              <View key={f.field} style={[styles.kv, i === invoice.extraction.length - 1 && styles.kvLast]}>
                <Text style={styles.k}>{human(f.field)}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.v}>{f.missing ? "Missing" : String(f.value)}</Text>
                  <Muted small>
                    {fmtPct(f.confidence)}
                    {f.malformed ? " · Invalid format" : ""}
                  </Muted>
                </View>
              </View>
            ))
          ) : (
            <Muted>Not extracted yet.</Muted>
          )}
        </Card>

        <H2>Agent timeline</H2>
        <Card>
          {timeline.length === 0 ? (
            <Muted>No activity yet.</Muted>
          ) : (
            timeline.map((e, i) => <TimelineEntry key={i} entry={e} last={i === timeline.length - 1} />)
          )}
        </Card>

        <H2>Tool calls</H2>
        <Card>
          {toolCalls.length === 0 ? (
            <Muted>No tool calls recorded.</Muted>
          ) : (
            toolCalls.map((c, i) => (
              <View key={c.call_id || i} style={[styles.kv, i === toolCalls.length - 1 && styles.kvLast]}>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={styles.v}>
                    {human(c.agent)} → {human(c.tool_name)}
                  </Text>
                  <Muted small>{c.purpose}</Muted>
                  {c.result_summary ? <Muted small>{c.result_summary}</Muted> : null}
                  <Muted small>{fmtTime(c.timestamp)}</Muted>
                </View>
                <AuthBadge authorization={c.authorization} />
              </View>
            ))
          )}
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function KV({ k, v, last }) {
  return (
    <View style={[styles.kv, last && styles.kvLast]}>
      <Text style={styles.k}>{k}</Text>
      <Text style={[styles.v, { flex: 1 }]}>{v}</Text>
    </View>
  );
}

function AuthBadge({ authorization }) {
  const map = {
    allowed: { fg: colors.ok, bg: colors.okBg },
    blocked: { fg: "#fff", bg: colors.blocked },
    escalated: { fg: colors.accentInk, bg: colors.pendingBg },
  };
  const c = map[authorization] || {};
  return <Badge label={authorization ? sentence(authorization) : "—"} fg={c.fg} bg={c.bg} />;
}

function TimelineEntry({ entry, last }) {
  const d = entry.data;
  let title;
  let meta;
  let blocked = false;
  if (entry.kind === "decision") {
    title = `${human(d.agent)}: ${human(d.decision || d.summary || "decision")}`;
    meta = d.confidence != null ? `Confidence ${fmtPct(d.confidence)}` : null;
  } else if (entry.kind === "tool_call") {
    title = `${human(d.agent)} called ${human(d.tool_name).toLowerCase()}`;
    meta = human(d.authorization);
    blocked = d.authorization === "blocked";
  } else {
    title = human(d.event_type);
    meta = d.output_summary || d.input_summary;
    blocked = ["payment_blocked", "tool_call_denied"].includes(d.event_type);
  }
  return (
    <View style={[styles.tl, last && styles.kvLast]}>
      <View style={[styles.dot, { backgroundColor: blocked ? colors.blocked : entry.kind === "decision" ? colors.accent : colors.muted }]} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.v, { fontWeight: "600" }, blocked && { color: colors.blocked }]}>{title}</Text>
        {meta ? <Muted small>{meta}</Muted> : null}
        {d.explanation?.reasons?.map((r, i) => (
          <Muted small key={i}>
            • {r}
          </Muted>
        ))}
        <Muted small>{fmtTime(entry.timestamp)}</Muted>
      </View>
    </View>
  );
}

// AI recommendation above, explicit human decision below — never conflated.
function ApprovalPanel({ invoice, decisions, events, onDecided }) {
  const [reviewer, setReviewer] = useState("finance.reviewer@example.com");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const recommendation = decisions?.find((d) => d.agent === "approval_agent");
  const why = recommendation?.explanation || {};
  const humanEvent = events?.find((e) => e.event_type === "human_decision_recorded");
  const awaiting = AWAITING_HUMAN.includes(invoice.status);

  async function decide(kind) {
    setBusy(true);
    setError(null);
    try {
      const result = await (kind === "approve"
        ? api.approve(invoice.invoice_id, reviewer, note || undefined)
        : api.reject(invoice.invoice_id, reviewer, note || undefined));
      onDecided?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <Text style={styles.h3}>AI recommendation</Text>
      {invoice.recommendation ? (
        <>
          <Text style={styles.big}>{human(invoice.recommendation)}</Text>
          <Muted small>
            Confidence {fmtPct(invoice.recommendation_confidence)} · advisory only — governance decides
          </Muted>
          {why.reasons?.length > 0 && (
            <View style={{ marginTop: 8 }}>
              <Text style={[styles.v, { fontWeight: "600" }]}>Why</Text>
              {why.reasons.map((r, i) => (
                <Text key={i} style={styles.v}>
                  • {r}
                </Text>
              ))}
            </View>
          )}
          {why.policy_rules_triggered?.length > 0 && (
            <View style={styles.codes}>
              {why.policy_rules_triggered.map((r) => (
                <Code key={r}>{r}</Code>
              ))}
            </View>
          )}
          {why.evidence?.length > 0 && (
            <View style={styles.codes}>
              {why.evidence.map((r) => (
                <Code key={r}>{r}</Code>
              ))}
            </View>
          )}
        </>
      ) : (
        <Muted>No recommendation yet — the agents have not run.</Muted>
      )}

      <View style={styles.divider} />
      <Text style={styles.h3}>Human decision</Text>
      {humanEvent ? (
        <Alert kind="info">
          {human(humanEvent.output_summary)}
          {humanEvent.input_summary ? `\n${humanEvent.input_summary}` : ""}
        </Alert>
      ) : awaiting ? (
        <>
          <Alert kind="warn">
            Payment is withheld. This invoice is {human(invoice.status)} and needs a human decision.
          </Alert>
          <TextInput
            style={styles.input}
            value={reviewer}
            onChangeText={setReviewer}
            placeholder="Reviewer email"
            placeholderTextColor={colors.muted}
            autoCapitalize="none"
            keyboardType="email-address"
            accessibilityLabel="reviewer"
          />
          <TextInput
            style={[styles.input, { minHeight: 60 }]}
            value={note}
            onChangeText={setNote}
            placeholder="Note (optional)"
            placeholderTextColor={colors.muted}
            multiline
            accessibilityLabel="note"
          />
          <View style={styles.actions}>
            <PillButton
              label="Approve payment"
              tone="approve"
              style={{ flex: 1 }}
              disabled={busy || !reviewer}
              onPress={() => decide("approve")}
            />
            <PillButton
              label="Reject"
              tone="reject"
              style={{ flex: 1 }}
              disabled={busy || !reviewer}
              onPress={() => decide("reject")}
            />
          </View>
          {error && <Alert kind="danger">{error}</Alert>}
        </>
      ) : (
        <Muted>
          {invoice.status === "COMPLETED"
            ? "Processed automatically — policy permitted and governance authorized payment."
            : "No human decision required at this stage."}
        </Muted>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  page: { paddingHorizontal: space.gutter, paddingTop: 16, paddingBottom: 48 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 6 },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 6 },
  kv: { flexDirection: "row", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.panel2 },
  kvLast: { borderBottomWidth: 0 },
  k: { width: 120, color: colors.muted, fontSize: 13 },
  v: { color: colors.text, fontSize: 13 },
  tl: { flexDirection: "row", gap: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.panel2 },
  dot: { width: 10, height: 10, borderRadius: 5, marginTop: 4 },
  h3: { fontSize: 13, fontWeight: "600", color: colors.muted, marginBottom: 6 },
  big: { fontSize: 22, fontWeight: "700", color: colors.text, textTransform: "capitalize", letterSpacing: -0.4 },
  divider: { height: 1, backgroundColor: colors.panel2, marginVertical: 16 },
  input: {
    borderWidth: 1,
    borderColor: "#dcdde3",
    borderRadius: radius.field,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.text,
    backgroundColor: colors.surface,
    marginBottom: 8,
  },
  actions: { flexDirection: "row", gap: 8, marginTop: 4 },
});
