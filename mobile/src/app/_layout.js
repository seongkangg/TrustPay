import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Text, View } from "react-native";

import { Mark } from "../components/ui.js";
import { colors } from "../theme.js";

function BrandTitle() {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <Mark size={24} />
      <Text style={{ fontSize: 16, fontWeight: "700", color: colors.text, letterSpacing: -0.16 }}>TrustPay</Text>
    </View>
  );
}

export default function RootLayout() {
  return (
    <>
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
        <Stack.Screen name="index" options={{ headerTitle: () => <BrandTitle />, title: "TrustPay" }} />
        <Stack.Screen name="invoices/[id]" options={{ title: "Invoice" }} />
      </Stack>
    </>
  );
}
