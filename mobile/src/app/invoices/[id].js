// One invoice, laid out around the reviewer's decision: who and how much, what is happening, what the
// AI recommends and why, then the supporting detail (fields, activity, tool calls).
// Approve / reject sit in a bar pinned to the bottom while a decision is needed, behind a confirm;
// they are the only write action in the app. The AI recommendation and the human decision are
// never conflated.
import { Stack, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  Alert as NativeAlert,
  Linking,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Path } from "react-native-svg";

import { AWAITING_HUMAN, BASE, api, fmtMoney, fmtPct, fmtTime, human } from "../../api/client.js";
import {
  Alert,
  Badge,
  Card,
  Code,
  H2,
  Muted,
  ReasonTag,
  RiskBadge,
  StatusBadge,
  sentence,
} from "../../components/ui.js";
import ConfidenceChart from "../../components/ConfidenceChart.js";
import { useDashboard } from "../../data.js";
import { colors, radius, space } from "../../theme.js";

const ACTION_BAR = 76; // the floating approve / reject pill (64) plus its gap above the safe-area inset
const TIMELINE_PREVIEW = 6;

const VERDICT = {
  approve: { fg: colors.ok, bg: colors.okBg },
  escalate: { fg: colors.riskMedium, bg: colors.riskMediumBg },
  reject: { fg: colors.riskHigh, bg: colors.riskHighBg },
};

// "2026-10-14" → "Oct 14, 2026", read as a calendar date (no time zone shift).
const fmtDate = (iso) => {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
};

export default function InvoiceScreen() {
  const { id } = useLocalSearchParams();
  const dashboard = useDashboard();
  const insets = useSafeAreaInsets();
  const [invoice, setInvoice] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [reviewer, setReviewer] = useState("finance.reviewer@example.com");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [decideError, setDecideError] = useState(null);
  const [threshold, setThreshold] = useState(null);

  // The confidence threshold is a policy constant; without it the chart just omits the marker.
  useEffect(() => {
    api
      .thresholds()
      .then((t) => setThreshold(t.confidence_threshold ?? null))
      .catch(() => setThreshold(null));
  }, []);

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
  const recommendation = decisions.find((d) => d.agent === "approval_agent");
  const humanEvent = events.find((e) => e.event_type === "human_decision_recorded");
  const needsDecision = AWAITING_HUMAN.includes(invoice.status) && !humanEvent;
  const amount = fmtMoney(invoice.amount, invoice.currency);

  async function decide(kind) {
    setBusy(true);
    setDecideError(null);
    try {
      await (kind === "approve"
        ? api.approve(invoice.invoice_id, reviewer, note || undefined)
        : api.reject(invoice.invoice_id, reviewer, note || undefined));
      await load();
      // Keep the tabs and the bottom nav's waiting count in step with the decision.
      dashboard.load();
    } catch (err) {
      setDecideError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Approving moves money and rejecting closes the invoice, so both ask first.
  function confirm(kind) {
    const vendor = invoice.vendor_name || "this vendor";
    NativeAlert.alert(
      kind === "approve" ? `Approve ${amount}?` : "Reject this invoice?",
      kind === "approve"
        ? `Payment to ${vendor} will be released.`
        : `${vendor} will not be paid for ${invoice.vendor_invoice_number || invoice.invoice_id}.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: kind === "approve" ? "Approve" : "Reject",
          style: kind === "approve" ? "default" : "destructive",
          onPress: () => decide(kind),
        },
      ],
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.bg }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <Stack.Screen options={{ title: invoice.invoice_id }} />
      <ScrollView
        contentContainerStyle={[
          styles.page,
          { paddingBottom: needsDecision ? ACTION_BAR + insets.bottom + 24 : 48 },
        ]}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
      >
        {error && <Alert kind="danger">{error}</Alert>}

        <Summary invoice={invoice} amount={amount} />
        <StateBanner invoice={invoice} humanEvent={humanEvent} needsDecision={needsDecision} />
        {blockedCalls > 0 && (
          <Alert kind="danger">
            {blockedCalls} unauthorized tool call{blockedCalls > 1 ? "s were" : " was"} blocked and recorded.
          </Alert>
        )}
        {invoice.sensitive_data_detected && (
          <Alert kind="warn">
            Bank or tax details were found and masked. Only the last four digits are shown, and they were never
            passed to a model or written to a log.
          </Alert>
        )}

        <H2>AI recommendation</H2>
        <Recommendation invoice={invoice} recommendation={recommendation} decisions={decisions} threshold={threshold} />

        <H2>Source document</H2>
        <SourceDocument
          invoiceId={invoice.invoice_id}
          name={invoice.source_document}
          hasText={Boolean(invoice.source_text)}
          hasPdf={invoice.has_source_pdf}
        />

        {needsDecision && (
          <>
            <H2>Your decision</H2>
            <Card>
              <Text style={styles.fieldLabel}>Reviewer</Text>
              <TextInput
                style={styles.input}
                value={reviewer}
                onChangeText={setReviewer}
                placeholder="Reviewer email"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                keyboardType="email-address"
                accessibilityLabel="Reviewer email"
              />
              <Text style={styles.fieldLabel}>Note (optional)</Text>
              <TextInput
                style={[styles.input, { minHeight: 72, textAlignVertical: "top" }]}
                value={note}
                onChangeText={setNote}
                placeholder="Why you are approving or rejecting"
                placeholderTextColor={colors.muted}
                multiline
                accessibilityLabel="Note"
              />
              <Muted small>Approve and Reject are at the bottom of the screen.</Muted>
              {decideError && <Alert kind="danger">{decideError}</Alert>}
            </Card>
          </>
        )}

        <H2>Invoice details</H2>
        <Card style={styles.listCard}>
          <KV k="Vendor" v={invoice.vendor_name} sub={invoice.vendor_id || "Not in vendor master"} />
          <KV k="Vendor invoice #" v={invoice.vendor_invoice_number} />
          <KV k="Amount" v={amount} />
          <KV k="Due date" v={fmtDate(invoice.due_date)} />
          <KV k="Purchase order" v={invoice.purchase_order_id} />
          <KV k="Bank account" v={invoice.bank_account} masked />
          <KV k="Routing number" v={invoice.routing_number} masked />
          <KV k="Tax ID" v={invoice.tax_id} masked />
          <KV k="Source" v={invoice.source_document || "Structured upload"} />
          <KV k="Received" v={fmtTime(invoice.created_at)} last />
        </Card>

        <Activity timeline={timeline} />
        <ToolCalls calls={toolCalls} blocked={blockedCalls} />
      </ScrollView>

      {needsDecision && (
        <View style={[styles.actionBar, { bottom: Math.max(insets.bottom, 12) }]}>
          <DecisionBubble kind="reject" label="Reject" disabled={busy || !reviewer} onPress={() => confirm("reject")} />
          <DecisionBubble
            kind="approve"
            label={busy ? "Saving…" : `Approve ${amount}`}
            disabled={busy || !reviewer}
            onPress={() => confirm("approve")}
          />
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

// Who, how much, and when it is due: the first thing a reviewer needs.
function Summary({ invoice, amount }) {
  const due = fmtDate(invoice.due_date);
  const today = new Date().toISOString().slice(0, 10);
  const overdue = invoice.due_date && invoice.due_date < today && !["COMPLETED", "APPROVED"].includes(invoice.status);
  return (
    <View style={styles.summary}>
      <View style={styles.badges}>
        <StatusBadge status={invoice.status} />
        <RiskBadge level={invoice.risk_level} />
        {invoice.sensitive_data_detected && <Badge label="Masked" />}
      </View>
      <Text style={styles.vendor} numberOfLines={2}>
        {invoice.vendor_name || "Unknown vendor"}
      </Text>
      <Text style={styles.amount}>{amount}</Text>
      <Text style={styles.meta}>
        {invoice.invoice_id}
        {invoice.vendor_invoice_number ? ` · ${invoice.vendor_invoice_number}` : ""}
        {due ? " · Due " : ""}
        {due ? <Text style={overdue ? styles.overdue : null}>{due}{overdue ? " (overdue)" : ""}</Text> : null}
      </Text>
    </View>
  );
}

// One sentence on where this invoice stands and what, if anything, is expected of the reviewer.
function StateBanner({ invoice, humanEvent, needsDecision }) {
  let tone;
  let title;
  let body;
  if (humanEvent) {
    const rejected = invoice.status === "REJECTED";
    tone = rejected ? "danger" : "ok";
    title = rejected ? "Rejected" : "Approved";
    body = [human(humanEvent.output_summary), humanEvent.input_summary].filter(Boolean).join("\n");
  } else if (needsDecision) {
    const blocked = invoice.status === "BLOCKED";
    tone = blocked ? "danger" : "info";
    title = blocked ? "Payment blocked — needs your decision" : "Payment on hold until you decide";
    body = blocked
      ? "Governance stopped automatic processing. Review the recommendation and decide below."
      : "This invoice is over a limit or needs a check. Review the recommendation and decide below.";
  } else if (invoice.status === "COMPLETED") {
    tone = "ok";
    title = "Paid automatically";
    body = "Policy permitted it and governance authorized the payment.";
  } else if (invoice.status === "FAILED") {
    tone = "danger";
    title = "Processing failed";
    body = "The automatic checks could not finish; nothing was paid.";
  } else {
    return null;
  }
  const t = BANNER[tone];
  return (
    <View style={[styles.banner, { backgroundColor: t.bg }]}>
      <Text style={[styles.bannerTitle, { color: t.fg }]}>{title}</Text>
      {body ? <Text style={[styles.bannerBody, { color: t.fg }]}>{body}</Text> : null}
    </View>
  );
}

const BANNER = {
  info: { bg: colors.infoBg, fg: colors.infoText },
  danger: { bg: colors.blockedBg, fg: colors.dangerText },
  ok: { bg: colors.okBg, fg: colors.okText },
};

function Recommendation({ invoice, recommendation, decisions, threshold }) {
  const [showEvidence, setShowEvidence] = useState(false);
  if (!invoice.recommendation) {
    return (
      <Card>
        <Muted>No recommendation yet — the agents have not run.</Muted>
      </Card>
    );
  }
  const verdict = VERDICT[invoice.recommendation] || { fg: colors.text, bg: colors.panel2 };
  const why = recommendation?.explanation || {};
  // Bare reason codes are already shown as tags; keep the sentences.
  const reasons = (why.reasons || []).filter((r) => !/^[A-Z_]+$/.test(r));
  const codes = recommendation?.reason_codes || [];
  const evidence = [...(why.policy_rules_triggered || []), ...(why.evidence || [])];
  return (
    <Card>
      <View style={styles.verdictRow}>
        <View style={[styles.verdictPill, { backgroundColor: verdict.bg }]}>
          <Text style={[styles.verdict, { color: verdict.fg }]}>{sentence(invoice.recommendation)}</Text>
        </View>
        <Muted small style={{ flex: 1 }}>
          Advisory only. Governance rules decide what is allowed; you make the final call.
        </Muted>
      </View>
      <View style={styles.divider} />
      <ConfidenceChart
        confidence={invoice.recommendation_confidence}
        decisions={decisions}
        threshold={threshold}
      />
      <View style={styles.divider} />
      {codes.length > 0 && (
        <View style={styles.tags}>
          {codes.map((c) => (
            <ReasonTag key={c} code={c} />
          ))}
        </View>
      )}
      {reasons.length > 0 && (
        <View style={{ marginTop: 12, gap: 6 }}>
          {reasons.map((r, i) => (
            <View key={i} style={styles.reason}>
              <View style={styles.reasonDot} />
              <Text style={styles.reasonText}>{r}</Text>
            </View>
          ))}
        </View>
      )}
      {evidence.length > 0 && (
        <>
          <Pressable
            onPress={() => setShowEvidence((v) => !v)}
            accessibilityRole="button"
            style={({ pressed }) => [styles.toggle, pressed && { opacity: 0.6 }]}
          >
            <Text style={styles.toggleText}>
              {showEvidence ? "Hide evidence" : `Show evidence (${evidence.length})`}
            </Text>
            <Chevron open={showEvidence} />
          </Pressable>
          {showEvidence && (
            <View style={styles.codes}>
              {evidence.map((e, i) => (
                <Code key={`${e}${i}`}>{e}</Code>
              ))}
            </View>
          )}
        </>
      )}
    </Card>
  );
}

function KV({ k, v, sub, masked, last }) {
  return (
    <View style={[styles.kv, last && styles.kvLast]}>
      <Text style={styles.k}>{k}</Text>
      <View style={{ flex: 1, gap: 2 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <Text style={styles.v}>{v || "—"}</Text>
          {masked && v ? <Badge label="Masked" /> : null}
        </View>
        {sub ? <Muted small>{sub}</Muted> : null}
      </View>
    </View>
  );
}

// A section whose body opens on demand, with a one-line summary in the header.
function Collapsible({ title, summary, alert, children }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        style={({ pressed }) => [styles.collapseHead, pressed && { opacity: 0.6 }]}
      >
        <View style={{ flex: 1 }}>
          <Text style={styles.collapseTitle}>{title}</Text>
          {summary ? <Text style={[styles.collapseSummary, alert && { color: colors.riskMedium }]}>{summary}</Text> : null}
        </View>
        <Chevron open={open} />
      </Pressable>
      {open && children}
    </>
  );
}

// Agent decisions, tool calls and governance events in order, joined by a line; latest few first.
function Activity({ timeline }) {
  const [all, setAll] = useState(false);
  if (timeline.length === 0) return null;
  const items = all ? timeline : timeline.slice(-TIMELINE_PREVIEW);
  return (
    <>
      <H2>Activity</H2>
      <Card>
        {!all && timeline.length > TIMELINE_PREVIEW && (
          <Pressable onPress={() => setAll(true)} accessibilityRole="button" style={styles.showAll}>
            <Text style={styles.toggleText}>Show all {timeline.length} steps</Text>
          </Pressable>
        )}
        {items.map((e, i) => (
          <TimelineEntry key={i} entry={e} last={i === items.length - 1} />
        ))}
      </Card>
    </>
  );
}

function TimelineEntry({ entry, last }) {
  const d = entry.data;
  let title;
  let meta;
  let blocked = false;
  if (entry.kind === "decision") {
    title = `${sentence(d.agent)}: ${human(d.decision || d.summary || "decision")}`;
    meta = d.confidence != null ? `Confidence ${fmtPct(d.confidence)}` : null;
  } else if (entry.kind === "tool_call") {
    title = `${sentence(d.agent)} called ${human(d.tool_name).toLowerCase()}`;
    meta = sentence(d.authorization);
    blocked = d.authorization === "blocked";
  } else {
    title = sentence(d.event_type);
    meta = d.output_summary || d.input_summary;
    blocked = ["payment_blocked", "tool_call_denied"].includes(d.event_type);
  }
  const dot = blocked ? colors.blocked : entry.kind === "decision" ? colors.accent : colors.muted;
  return (
    <View style={styles.tl}>
      <View style={styles.rail}>
        <View style={[styles.dot, { backgroundColor: dot }]} />
        {!last && <View style={styles.railLine} />}
      </View>
      <View style={{ flex: 1, paddingBottom: last ? 0 : 14 }}>
        <Text style={[styles.tlTitle, blocked && { color: colors.blocked }]}>{title}</Text>
        {meta ? <Muted small>{meta}</Muted> : null}
        <Muted small>{fmtTime(entry.timestamp)}</Muted>
      </View>
    </View>
  );
}

function ToolCalls({ calls, blocked }) {
  if (calls.length === 0) return null;
  return (
    <Collapsible
      title="Tool calls"
      summary={`${calls.length} call${calls.length === 1 ? "" : "s"}${blocked ? ` · ${blocked} blocked` : " · all allowed"}`}
      alert={blocked > 0}
    >
      <Card style={styles.listCard}>
        {calls.map((c, i) => (
          <View key={c.call_id || i} style={[styles.kv, i === calls.length - 1 && styles.kvLast]}>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={styles.v}>
                {sentence(c.agent)} → {human(c.tool_name).toLowerCase()}
              </Text>
              <Muted small>{c.purpose}</Muted>
              {c.result_summary ? <Muted small>{c.result_summary}</Muted> : null}
              <Muted small>{fmtTime(c.timestamp)}</Muted>
            </View>
            <AuthBadge authorization={c.authorization} />
          </View>
        ))}
      </Card>
    </Collapsible>
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

// A decision button in the bottom nav's bubble style: soft red Reject, deep teal Approve (the same
// colour as "Check inbox now" and today's cell in "Received per day").
function DecisionBubble({ kind, label, disabled, onPress }) {
  const approve = kind === "approve";
  const fg = disabled ? colors.neutralInk : approve ? "#fff" : colors.riskHigh;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.bubble,
        { flex: approve ? 1.6 : 1, backgroundColor: disabled ? colors.panel2 : approve ? colors.accentStrong : colors.blockedBg },
        pressed && !disabled && styles.bubblePressed,
      ]}
    >
      <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={fg} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
        <Path d={approve ? "m5 12.5 4.5 4.5L19 7.5" : "M6 6l12 12M18 6 6 18"} />
      </Svg>
      <Text style={[styles.bubbleText, { color: fg }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
}

// The source invoice as a downloadable PDF (GET /invoices/{id}/document.pdf): the emailed PDF itself
// with bank, routing and tax numbers blacked out when a redacted copy was kept at ingestion
// (`hasPdf`), else a masked copy rebuilt from its text. The unredacted original is never kept.
// The phone opens the PDF in its own viewer to save or share it.
function SourceDocument({ invoiceId, name, hasText, hasPdf }) {
  const [error, setError] = useState(null);
  if (!hasText && !hasPdf) {
    return (
      <Card>
        <Muted>{name ? `${name}: no readable text.` : "Entered as structured data; there is no source document."}</Muted>
      </Card>
    );
  }
  async function download() {
    setError(null);
    try {
      await Linking.openURL(`${BASE}/invoices/${invoiceId}/document.pdf`);
    } catch {
      setError("Couldn't open the PDF on this phone.");
    }
  }
  return (
    <Card>
      <View style={styles.docRow}>
        <View style={styles.docIcon}>
          <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={colors.accentInk} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <Path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
            <Path d="M14 3v5h5M9 13h6M9 17h6" />
          </Svg>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.docName} numberOfLines={2}>
            {`${invoiceId}-${hasPdf ? "redacted" : "masked"}.pdf`}
          </Text>
          <Muted small>{name || "Source document"}</Muted>
        </View>
      </View>
      <Muted small style={{ marginTop: 10 }}>
        {hasPdf
          ? "The original PDF, with bank, routing and tax numbers blacked out."
          : "Masked copy rebuilt from the original's text: bank, routing and tax numbers are hidden."}
      </Muted>
      <Pressable
        onPress={download}
        accessibilityRole="button"
        accessibilityLabel="Download source document PDF"
        style={({ pressed }) => [styles.docButton, pressed && styles.docButtonPressed]}
      >
        <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
        </Svg>
        <Text style={styles.docButtonText}>Download PDF</Text>
      </Pressable>
      {error && <Alert kind="danger">{error}</Alert>}
    </Card>
  );
}

function Chevron({ open }) {
  return (
    <Svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke={colors.muted} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <Path d={open ? "m6 15 6-6 6 6" : "m6 9 6 6 6-6"} />
    </Svg>
  );
}

const styles = StyleSheet.create({
  page: { paddingHorizontal: space.gutter, paddingTop: 16 },
  summary: { gap: 4, marginBottom: 14 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 6 },
  vendor: { fontSize: 20, fontWeight: "700", color: colors.text, letterSpacing: -0.3 },
  amount: { fontSize: 36, fontWeight: "700", color: colors.text, letterSpacing: -1.1, fontVariant: ["tabular-nums"] },
  meta: { fontSize: 13, color: colors.muted },
  overdue: { color: colors.riskHigh, fontWeight: "600" },
  banner: { borderRadius: radius.alert, paddingVertical: 12, paddingHorizontal: 16, gap: 2, marginBottom: 6 },
  bannerTitle: { fontSize: 15, fontWeight: "700" },
  bannerBody: { fontSize: 13, lineHeight: 19 },
  verdictRow: { flexDirection: "row", alignItems: "center", gap: 14 },
  verdictPill: { borderRadius: radius.field, paddingHorizontal: 14, paddingVertical: 8 },
  verdict: { fontSize: 20, fontWeight: "700", letterSpacing: -0.3 },
  divider: { height: 1, backgroundColor: colors.panel2, marginVertical: 16 },
  docRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  docIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.field,
    backgroundColor: colors.accentBg,
    alignItems: "center",
    justifyContent: "center",
  },
  docName: { fontSize: 14, fontWeight: "700", color: colors.text },
  docButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: 44,
    marginTop: 14,
    borderRadius: radius.pill,
    backgroundColor: colors.accentStrong, // deep teal, like "Check inbox now"
  },
  docButtonPressed: { transform: [{ scale: 0.97 }] },
  docButtonText: { fontSize: 15, fontWeight: "700", color: "#fff" },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  reason: { flexDirection: "row", gap: 8 },
  reasonDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.muted, marginTop: 8 },
  reasonText: { flex: 1, fontSize: 14, lineHeight: 20, color: colors.text },
  toggle: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 12, alignSelf: "flex-start" },
  toggleText: { fontSize: 13, fontWeight: "600", color: colors.accentInk },
  codes: { flexDirection: "row", flexWrap: "wrap", marginTop: 8 },
  fieldLabel: { fontSize: 12, fontWeight: "600", color: colors.muted, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: "#dcdde3",
    borderRadius: radius.field,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: colors.text,
    backgroundColor: colors.surface,
    marginBottom: 12,
  },
  listCard: { paddingVertical: 6 },
  kv: { flexDirection: "row", gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.panel2 },
  kvLast: { borderBottomWidth: 0 },
  k: { width: 116, color: colors.muted, fontSize: 13 },
  v: { color: colors.text, fontSize: 14 },
  collapseHead: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 28, marginBottom: 12 },
  collapseTitle: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 },
  collapseSummary: { fontSize: 12, color: colors.muted, marginTop: 2 },
  showAll: { marginBottom: 12 },
  tl: { flexDirection: "row", gap: 12 },
  rail: { width: 10, alignItems: "center" },
  dot: { width: 10, height: 10, borderRadius: 5, marginTop: 5, borderWidth: 2, borderColor: colors.panel },
  railLine: { flex: 1, width: 2, backgroundColor: colors.panel2, marginTop: 2 },
  tlTitle: { fontSize: 14, fontWeight: "600", color: colors.text },
  // Pinned decision bar in the bottom nav's language: a floating white pill holding two bubbles.
  actionBar: {
    position: "absolute",
    left: space.gutter,
    right: space.gutter,
    height: 64,
    flexDirection: "row",
    gap: 6,
    padding: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    shadowColor: "#14161e",
    shadowOpacity: 0.12,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  bubble: { height: "100%", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, borderRadius: radius.pill, paddingHorizontal: 14 },
  bubblePressed: { transform: [{ scale: 0.96 }] },
  bubbleText: { fontSize: 15, fontWeight: "700", fontVariant: ["tabular-nums"] },
});
