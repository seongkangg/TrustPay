// Overview, Inbox and Invoices as tabs, with the floating bubble nav as the tab bar.
import { router } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { Text, View } from "react-native";

import BubbleNav, { HomeIcon, InboxIcon, ListIcon } from "../../components/BubbleNav.js";
import { Mark } from "../../components/ui.js";
import { useDashboard } from "../../data.js";
import { colors } from "../../theme.js";

const TABS = {
  index: { label: "Overview", Icon: HomeIcon },
  inbox: { label: "Inbox", Icon: InboxIcon },
  invoices: { label: "Invoices", Icon: ListIcon },
};

function BrandTitle() {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <Mark size={24} />
      <Text style={{ fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 }}>TrustPay</Text>
    </View>
  );
}

function TabBar({ state, emitter, navigateToTab }) {
  const { awaiting } = useDashboard();
  const tabs = state.routes.map((r) => ({ key: r.key, ...TABS[r.name] }));
  const focusedKey = state.routes[state.index].key;

  function onSelect(key) {
    const event = emitter.emit({ type: "tabPress", target: key, canPreventDefault: true });
    if (key !== focusedKey && !event.defaultPrevented) navigateToTab(key);
  }

  // The round button is the approver's main job: open the next invoice that needs a decision.
  function reviewNext() {
    if (awaiting.length > 0) router.push(`/invoices/${awaiting[0].invoice_id}`);
    else navigateToTab(state.routes[0].key);
  }

  return (
    <BubbleNav
      tabs={tabs}
      active={focusedKey}
      onSelect={onSelect}
      action={{
        label: awaiting.length ? `Review next invoice, ${awaiting.length} waiting` : "Nothing waiting for approval",
        count: awaiting.length,
        onPress: reviewNext,
      }}
    />
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerShadowVisible: false,
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: "700" },
        headerTitleAlign: "center",
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Overview", headerTitle: () => <BrandTitle /> }} />
      <Tabs.Screen name="inbox" options={{ title: "Inbox" }} />
      <Tabs.Screen name="invoices" options={{ title: "Invoices" }} />
    </Tabs>
  );
}
