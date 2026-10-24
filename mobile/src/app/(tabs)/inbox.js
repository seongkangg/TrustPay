// Inbox tab: invoices waiting for a human decision (the count on this tab's icon), then the Gmail
// intake that feeds invoices in and what it delivered recently.
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import ApprovalQueue from "../../components/ApprovalQueue.js";
import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import InboxCard from "../../components/InboxCard.js";
import { Alert, CountPill, H2 } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors, space } from "../../theme.js";

export default function Inbox() {
  const { summary, inbox, awaiting, error, refreshing, refresh, load } = useDashboard();
  const reasonCodes = Object.fromEntries(
    (summary?.recent_violations || []).map((v) => [v.invoice_id, v.reason_codes]),
  );
  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}

      <View style={styles.head}>
        <Text style={styles.title}>Needs your approval</Text>
        <CountPill n={awaiting.length} />
      </View>
      <ApprovalQueue items={awaiting} reasonCodes={reasonCodes} />

      <H2>Email inbox</H2>
      <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: space.gutter, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
  head: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 12 },
  title: { fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 },
});
