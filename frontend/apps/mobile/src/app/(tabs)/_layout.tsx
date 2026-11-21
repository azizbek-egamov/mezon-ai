/** Pastki navigatsiya (dizayn: advokat_ishchi_stoli): Savol-javob, Ishlar, Tarif, Profil. Faqat kirganlar uchun. */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import { ActivityIndicator, View, type ColorValue } from "react-native";
import { useTranslation } from "react-i18next";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { OfflineScreen } from "@/components/Offline";
import { useAuth } from "@/lib/auth";
import { colors, fonts } from "@/lib/theme";

export default function TabsLayout() {
  const { t } = useTranslation();
  const { status } = useAuth();
  // Android imo-ishora chizig'i ustida yozuvlar qolmasin: pastki chekinma aniq beriladi
  const bottom = Math.max(useSafeAreaInsets().bottom, 8) + 6;
  if (status === "loading") {
    return <View style={{ flex: 1, backgroundColor: colors.canvas, justifyContent: "center" }}><ActivityIndicator color={colors.primary} /></View>;
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (status === "offline") return <OfflineScreen />;

  const icon = (name: keyof typeof MaterialCommunityIcons.glyphMap) => ({ color, size }: { color: ColorValue; size: number }) =>
    <MaterialCommunityIcons name={name} color={color as string} size={size} />;
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.primary,
      tabBarInactiveTintColor: colors.muted,
      tabBarLabelStyle: { fontSize: 12, fontFamily: fonts.medium },
      tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.line, paddingTop: 6, paddingBottom: bottom, height: 58 + bottom },
      sceneStyle: { backgroundColor: colors.canvas },
    }}>
      <Tabs.Screen name="index" options={{ title: t("Savol-javob"), tabBarIcon: icon("message-text-outline") }} />
      <Tabs.Screen name="cases" options={{ title: t("Ishlar"), tabBarIcon: icon("briefcase-outline") }} />
      <Tabs.Screen name="billing" options={{ title: t("Tarif"), tabBarIcon: icon("credit-card-outline") }} />
      <Tabs.Screen name="profile" options={{ title: t("Profil"), tabBarIcon: icon("account-outline") }} />
    </Tabs>
  );
}
