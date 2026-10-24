// Inbox tab: what is waiting on you (a summary of the count and money on hold, then the invoices
// behind the count on this tab's icon), then the Gmail intake that feeds invoices in.
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { fmtMoney } from "../../api/client.js";
import ApprovalQueue from "../../components/ApprovalQueue.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import InboxCard from "../../components/InboxCard.js";
import { Alert, Card, H2, Muted } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, space } from "../../theme.js";

export default function Inbox() {
  const { summary, inbox, awaiting, error, refreshing, refresh, load } = useDashboard();
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  const onHold = awaiting.reduce((sum, inv) => sum + (inv.amount || 0), 0);
  const blocked = awaiting.filter((inv) => inv.status === "BLOCKED").length;

  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}

      {awaiting.length === 0 ? (
        <Card style={styles.clear}>
          <View style={styles.clearIcon}>
            <Svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={colors.ok} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
              <Path d="m5 12.5 4.5 4.5L19 7.5" />
            </Svg>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.clearTitle}>All caught up</Text>
            <Muted small>{summary ? "Nothing needs your approval. New invoices are checked automatically." : "Loading…"}</Muted>
          </View>
        </Card>
      ) : (
        <>
          <View style={styles.summary}>
            <Text style={styles.summaryLabel}>Needs your approval</Text>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryCount}>{awaiting.length}</Text>
              <Text style={styles.summaryUnit}>invoice{awaiting.length === 1 ? "" : "s"} waiting</Text>
            </View>
            <Text style={styles.summaryMoney}>
              {fmtMoney(onHold)} on hold{blocked ? ` · ${blocked} blocked` : ""}
            </Text>
          </View>
          <ApprovalQueue items={awaiting} reasonCodes={reasonCodes} />
        </>
      )}

      <H2>Email inbox</H2>
      <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: space.gutter, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  clear: { flexDirection: "row", alignItems: "center", gap: 14 },
  clearIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.okBg,
    alignItems: "center",
    justifyContent: "center",
  },
  clearTitle: { fontSize: 16, fontWeight: "700", color: colors.text, marginBottom: 2 },
  // Sits straight on the page, no panel, so the invoices card below is the only box.
  summary: { gap: 2, marginBottom: 14, paddingHorizontal: 4 },
  summaryLabel: { fontSize: 13, fontWeight: "500", color: colors.muted },
  summaryRow: { flexDirection: "row", alignItems: "baseline", gap: 8 },
  summaryCount: { fontSize: 34, fontWeight: "700", letterSpacing: -1, color: colors.text, fontVariant: ["tabular-nums"] },
  summaryUnit: { fontSize: 15, fontWeight: "600", color: colors.text },
  summaryMoney: { fontSize: 13, color: colors.muted, fontVariant: ["tabular-nums"] },
});
