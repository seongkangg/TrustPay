import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { DashboardProvider } from "../data.js";
import { colors } from "../theme.js";

export default function RootLayout() {
  return (
    <DashboardProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerShadowVisible: false,
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: "700" },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false, title: "TrustPay" }} />
        {/* Back shows just the arrow, not the previous screen's "TrustPay" title. */}
        <Stack.Screen name="invoices/[id]" options={{ title: "Invoice", headerBackButtonDisplayMode: "minimal" }} />
      </Stack>
    </DashboardProvider>
  );
}
