import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { colors } from "../theme.js";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: "700" },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="index" options={{ title: "TrustPay" }} />
        <Stack.Screen name="invoices/[id]" options={{ title: "Invoice" }} />
      </Stack>
    </>
  );
}
