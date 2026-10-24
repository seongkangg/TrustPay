// Inbox tab: the Gmail intake that feeds invoices in, and what it delivered recently.
import { RefreshControl, ScrollView, StyleSheet } from "react-native";

import { BAR_HEIGHT } from "../../components/BubbleNav.js";
import InboxCard from "../../components/InboxCard.js";
import { Alert } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors } from "../../theme.js";

export default function Inbox() {
  const { inbox, error, refreshing, refresh, load } = useDashboard();
  return (
    <ScrollView
      style={{ backgroundColor: colors.bg }}
      contentContainerStyle={styles.page}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} />}
    >
      {error && <Alert kind="danger">{error}</Alert>}
      <InboxCard status={inbox.status} unavailable={inbox.unavailable} onSynced={load} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  // Bottom padding clears the floating nav (bar + its gap from the screen edge).
  page: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: BAR_HEIGHT + 64 },
});
