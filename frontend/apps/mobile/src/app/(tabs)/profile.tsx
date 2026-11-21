import Constants from "expo-constants";
import { useTranslation } from "react-i18next";
import { View } from "react-native";

import { LanguagePicker } from "@/components/LanguagePicker";
import { Button, Card, Screen, Segmented, Txt } from "@/components/ui";
import { API_ORIGIN } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatUzPhone } from "@/lib/formatters";
import { colors, fonts, tint } from "@/lib/theme";
import { useTheme, type ThemePref } from "@/lib/themeContext";

function initials(name?: string | null) {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "") || "M").toUpperCase();
}

export default function ProfileScreen() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { pref, setPref } = useTheme();

  const formattedPhone = user?.phone_number ? `+998 ${formatUzPhone(user.phone_number).display}` : "";

  return (
    <Screen>
      <Txt variant="title">{t("Profil")}</Txt>

      <Card delay={60} style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
        <View style={{ width: 54, height: 54, borderRadius: 27, backgroundColor: tint(colors.primary, 0.12), alignItems: "center", justifyContent: "center" }}>
          <Txt style={{ color: colors.primary, fontFamily: fonts.semibold, fontSize: 19 }}>{initials(user?.full_name)}</Txt>
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Txt variant="h2">{user?.full_name}</Txt>
          <Txt variant="small">{formattedPhone || user?.phone_number}</Txt>
          <Txt variant="small" style={{ color: colors.primary, fontFamily: fonts.medium }}>{user?.role_label}</Txt>
        </View>
      </Card>

      {user?.advocate_license_no ? (
        <Txt variant="small" style={{ paddingHorizontal: 4 }}>
          {`${t("Advokatlik guvohnomasi raqami")}: ${user.advocate_license_no}`}
        </Txt>
      ) : null}

      <Card delay={120} style={{ gap: 12 }}>
        <Txt variant="label">{t("Koʻrinish")}</Txt>
        <Segmented<ThemePref>
          value={pref}
          onChange={setPref}
          options={[
            { value: "light", label: t("Yorugʻ") },
            { value: "dark", label: t("Qorongʻi") },
            { value: "system", label: t("Tizim") },
          ]}
        />
      </Card>

      <Card delay={180} style={{ gap: 12 }}>
        <Txt variant="label">{t("Interfeys tili")}</Txt>
        <LanguagePicker />
      </Card>

      <Button title={t("Chiqish")} variant="danger" onPress={() => void logout()} style={{ marginTop: 8 }} />

      <Txt variant="small" style={{ textAlign: "center", marginTop: 8 }}>
        {`Mezon ${Constants.expoConfig?.version ?? ""}${__DEV__ ? ` · ${API_ORIGIN}` : ""}`}
      </Txt>
    </Screen>
  );
}
