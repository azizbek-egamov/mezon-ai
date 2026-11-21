/** Server javob bermaganda (kabel ulanmagan, PC dagi server o'chiq): sessiya saqlanadi, "Qayta urinish" bilan davom etadi. */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { View } from "react-native";

import { Brand } from "@/components/Brand";
import { Button, Card, Screen, Txt } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { colors } from "@/lib/theme";

export function OfflineScreen() {
  const { t } = useTranslation();
  const { retry } = useAuth();
  const [busy, setBusy] = useState(false);
  const onRetry = async () => {
    setBusy(true);
    try {
      await retry();
    } finally {
      setBusy(false);
    }
  };
  return (
    <Screen scroll={false} style={{ justifyContent: "center", gap: 20 }}>
      <Brand />
      <Card accent="red" style={{ gap: 10 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <MaterialCommunityIcons name="lan-disconnect" size={24} color={colors.red} />
          <Txt variant="h2">{t("Server bilan aloqa yoʻq")}</Txt>
        </View>
        <Txt variant="muted">{t("Telefon kompyuterga ulanganini (USB) va kompyuterda MEZON serveri ishlayotganini tekshiring. Kirish maʼlumotlaringiz saqlangan.")}</Txt>
      </Card>
      <Button title={t("Qayta urinish")} onPress={onRetry} loading={busy} />
    </Screen>
  );
}
