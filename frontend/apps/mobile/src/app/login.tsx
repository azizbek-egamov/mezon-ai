/** Kirish ekrani — tezkor, silliq va professional UI. */
import { Link, Redirect } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Keyboard, Platform, ScrollView, View } from "react-native";

import { LanguagePicker } from "@/components/LanguagePicker";
import { Brand } from "@/components/Brand";
import { Button, ErrorNote, PasswordField, PhoneField, Screen, Txt } from "@/components/ui";
import { API_ORIGIN } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/errors";
import { colors, fonts } from "@/lib/theme";

export default function LoginScreen() {
  const { t } = useTranslation();
  const { status, login } = useAuth();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  const scrollRef = useRef<any>(null);

  useEffect(() => {
    const showSub = Keyboard.addListener(
      Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow",
      () => setKeyboardVisible(true)
    );
    const hideSub = Keyboard.addListener(
      Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide",
      () => setKeyboardVisible(false)
    );
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  if (status === "authenticated") return <Redirect href="/" />;

  async function submit() {
    if (!phone || !password) return;
    setBusy(true);
    setError(null);
    try {
      await login(phone, password);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const { general, fields } = errorText(t, error);

  return (
    <Screen
      scrollViewRef={scrollRef}
      style={{
        paddingTop: keyboardVisible ? 8 : 20,
        paddingBottom: keyboardVisible ? 20 : 60,
        gap: keyboardVisible ? 12 : 20
      }}
    >
      <View>
        <Brand size={keyboardVisible ? 32 : 42} />
      </View>

      <View style={{ gap: 4 }}>
        <Txt variant="title" style={{ fontSize: keyboardVisible ? 24 : 28 }}>{t("Kirish")}</Txt>
        {!keyboardVisible ? (
          <Txt variant="muted">{t("Telefon raqamingiz va parolingiz bilan kiring.")}</Txt>
        ) : null}
      </View>

      <View style={{ gap: 14 }}>
        {general ? <ErrorNote>{general}</ErrorNote> : null}
        
        <PhoneField
          label={t("Telefon")}
          value={phone}
          onChangePhone={(normalized) => setPhone(normalized)}
          error={fields.phone_number}
        />

        <PasswordField
          label={t("Parol")}
          revealLabel={t("Parolni koʻrish uchun bosib turing")}
          value={password}
          onChangeText={setPassword}
          autoComplete="password"
          returnKeyType="done"
          error={fields.password}
          onFocus={() => {
            setTimeout(() => {
              scrollRef.current?.scrollToEnd({ animated: true });
            }, 100);
          }}
          onSubmitEditing={() => void submit()}
        />

        <Button
          title={t("Kirish")}
          onPress={() => void submit()}
          loading={busy}
          disabled={!phone || !password || phone.length < 13}
          style={{ marginTop: 6 }}
        />

        <View style={{ flexDirection: "row", justifyContent: "center", gap: 6, paddingVertical: 4 }}>
          <Txt variant="muted">{t("Akkauntingiz yoʻqmi?")}</Txt>
          <Link href="/register">
            <Txt style={{ color: colors.primary, fontFamily: fonts.semibold }}>{t("Roʻyxatdan oʻting")}</Txt>
          </Link>
        </View>
      </View>

      {!keyboardVisible ? (
        <>
          <View style={{ marginTop: 8 }}>
            <LanguagePicker />
          </View>

          <View>
            <Txt variant="small" style={{ textAlign: "center" }}>{t("Tizim yuridik maslahat emas — advokat uchun yordamchi vosita.")}</Txt>
            {__DEV__ ? <Txt variant="small" style={{ textAlign: "center", marginTop: 4 }}>API: {API_ORIGIN}</Txt> : null}
          </View>
        </>
      ) : null}
    </Screen>
  );
}
