import { Link, Redirect } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, Switch, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";

import { Brand } from "@/components/Brand";
import { Button, ErrorNote, Field, PasswordField, PhoneField, Screen, Segmented, Txt } from "@/components/ui";
import { useAuth, type RegisterData } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { colors, fonts } from "@/lib/theme";

export default function RegisterScreen() {
  const { t } = useTranslation();
  const { status, register } = useAuth();
  const [data, setData] = useState<RegisterData>({
    phone_number: "", full_name: "", role: "LAWYER", advocate_license_no: "", password1: "", password2: "", consent: false,
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  if (status === "authenticated") return <Redirect href="/" />;
  const set = <K extends keyof RegisterData>(k: K, v: RegisterData[K]) => setData((d) => ({ ...d, [k]: v }));

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await register(data);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const { general, fields } = errorText(t, error);
  return (
    <Screen style={{ paddingTop: 20, paddingBottom: 160, gap: 18 }}>
      <View>
        <Brand size={42} />
      </View>

      <View style={{ gap: 4 }}>
        <Txt variant="title">{t("Roʻyxatdan oʻtish")}</Txt>
        <Txt variant="muted">{t("SMS orqali tasdiqlash keyingi bosqichda qoʻshiladi.")}</Txt>
      </View>

      <View style={{ gap: 16 }}>
        {general ? <ErrorNote>{general}</ErrorNote> : null}
        
        <Txt variant="label">{t("Kim sifatida")}</Txt>
        <Segmented
          value={data.role}
          onChange={(v) => set("role", v)}
          options={[{ value: "LAWYER", label: t("Advokat / yurist") }, { value: "CLIENT", label: t("Fuqaro") }]}
        />

        <PhoneField
          label={t("Telefon")}
          value={data.phone_number}
          onChangePhone={(normalized) => set("phone_number", normalized)}
          error={fields.phone_number}
        />

        <Field
          label={t("F.I.Sh.")}
          value={data.full_name}
          onChangeText={(v) => set("full_name", v)}
          autoComplete="name"
          error={fields.full_name}
        />

        {data.role === "LAWYER" ? (
          <Field
            label={t("Advokatlik guvohnomasi raqami (advokatlar uchun)")}
            value={data.advocate_license_no}
            onChangeText={(v) => set("advocate_license_no", v)}
            error={fields.advocate_license_no}
          />
        ) : null}

        <PasswordField
          label={t("Parol")}
          revealLabel={t("Parolni koʻrish uchun bosib turing")}
          value={data.password1}
          onChangeText={(v) => set("password1", v)}
          error={fields.password1}
        />

        <PasswordField
          label={t("Parolni takrorlang")}
          revealLabel={t("Parolni koʻrish uchun bosib turing")}
          value={data.password2}
          onChangeText={(v) => set("password2", v)}
          error={fields.password2}
        />

        <Pressable onPress={() => set("consent", !data.consent)} style={{ flexDirection: "row", gap: 10, alignItems: "center", paddingVertical: 4 }}>
          <Switch value={data.consent} onValueChange={(v) => set("consent", v)} trackColor={{ true: colors.primary, false: colors.line }} />
          <Txt style={{ flex: 1, fontSize: 13, lineHeight: 18 }}>{t("Shaxsiy maʼlumotlarimni qayta ishlashga roziman (OʻRQ-547)")}</Txt>
        </Pressable>
        {fields.consent ? <Txt variant="small" style={{ color: colors.red }}>{fields.consent.join(" ")}</Txt> : null}

        <Button title={t("Roʻyxatdan oʻtish")} onPress={() => void submit()} loading={busy} />

        <View style={{ flexDirection: "row", justifyContent: "center", gap: 6, paddingVertical: 4 }}>
          <Txt variant="muted">{t("Akkauntingiz bormi?")}</Txt>
          <Link href="/login"><Txt style={{ color: colors.primary, fontFamily: fonts.semibold }}>{t("Kirish")}</Txt></Link>
        </View>
      </View>
    </Screen>
  );
}
