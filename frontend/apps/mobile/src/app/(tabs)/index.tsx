/**
 * Huquqiy savol-javob: SSE oqimi (expo/fetch ReadableStream) — yo'nalishlar, manbalar, javob, tekshiruv.
 * Animatsiyalar va zamonaviy UI/UX bilan boyitilgan.
 */
import { ask, type ChatSource, type Verification } from "@mezon/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, { FadeIn, FadeInDown, FadeInUp } from "react-native-reanimated";

import { LegalText } from "@/components/LegalText";
import { Badge, Card, noOutline, Segmented, Txt } from "@/components/ui";
import { api } from "@/lib/api";
import { alertError } from "@/lib/errors";
import { useLanguage } from "@/lib/i18n";
import { colors, fonts, radius, tint } from "@/lib/theme";

interface Turn {
  id: number;
  question: string;
  status: string;
  sources: ChatSource[];
  text: string;
  verification?: Verification;
  error?: string;
  streaming: boolean;
}

type Effort = "low" | "medium" | "high";

function TurnView({ turn }: { turn: Turn }) {
  const { t } = useTranslation();
  const sources = Object.fromEntries(turn.sources.map((s) => [s.key, s]));
  const v = turn.verification;

  return (
    <Animated.View entering={FadeIn.duration(150)} style={{ gap: 12 }}>
      <View style={{
        alignSelf: "flex-end", maxWidth: "88%", backgroundColor: colors.primary,
        borderRadius: 18, borderBottomRightRadius: 6, paddingHorizontal: 16, paddingVertical: 12,
        shadowColor: "#000", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2
      }}>
        <Txt style={{ color: colors.primaryFg, fontSize: 15, lineHeight: 22 }}>{turn.question}</Txt>
      </View>

      <Card noAnimation>
        {turn.error || turn.streaming ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 4 }}>
            {!turn.error ? <ActivityIndicator size="small" color={colors.primary} /> : null}
            <Txt variant="small" style={turn.error ? { color: colors.red } : { color: colors.primary }}>
              {turn.error ?? turn.status}
            </Txt>
          </View>
        ) : null}

        {turn.sources.length ? (
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {turn.sources.map((s) => (
              <Pressable key={s.key} onPress={() => void WebBrowser.openBrowserAsync(s.lex_url)}
                style={({ pressed }) => ({
                  flexDirection: "row", gap: 5, alignItems: "center", borderWidth: 1, borderColor: tint(colors.gold, 0.35),
                  borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6, backgroundColor: tint(colors.gold, 0.08),
                  maxWidth: "100%", opacity: pressed ? 0.75 : 1
                })}>
                <Text style={{ color: colors.gold, fontFamily: fonts.semibold, fontSize: 13 }}>{s.key}</Text>
                <Text style={{ color: colors.gold, fontFamily: fonts.regular, fontSize: 13, flexShrink: 1 }} numberOfLines={1}>{s.label}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}

        {turn.text ? (
          <View style={{ marginTop: 6 }}>
            <LegalText text={turn.text} sources={sources} cited={new Set(v?.citations ?? [])} streaming={turn.streaming} />
          </View>
        ) : null}

        {v ? (
          <View style={{ gap: 6, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 12, marginTop: 6 }}>
            <Badge tone={v.ok ? "ok" : "bad"}>{v.ok ? t("✓ Tekshiruvdan oʻtdi") : t("⚠ Xato topildi")}</Badge>
            {v.issues.map((i, n) => (
              <Txt key={n} variant="small" style={{ color: i.severity === "error" ? colors.red : i.severity === "warning" ? colors.amber : colors.muted }}>
                {i.detail}
              </Txt>
            ))}
          </View>
        ) : null}
      </Card>
    </Animated.View>
  );
}

export default function ChatScreen() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const queryClient = useQueryClient();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [effort, setEffort] = useState<Effort>("medium");
  const [inputFocused, setInputFocused] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const busy = turns.some((x) => x.streaming);

  const examples = [
    t("Aldab pul olgan odamga qanday jazo beriladi?"),
    t("Gumon qilinuvchini necha soatgacha ushlab turish mumkin?"),
  ];

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const id = Date.now();
    const update = (patch: Partial<Turn> | ((x: Turn) => Partial<Turn>)) =>
      setTurns((all) => all.map((x) => (x.id === id ? { ...x, ...(typeof patch === "function" ? patch(x) : patch) } : x)));
    setTurns((all) => [...all, { id, question: q, status: t("Qidirilmoqda…"), sources: [], text: "", streaming: true }]);
    setQuestion("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await ask(api, { question: q, lang: language, effort, on_date: null }, {
        aspects: (list) => update({ status: t("{{n}} ta yoʻnalish: {{topics}} · qidirilmoqda…", { n: list.length, topics: list.map((a) => a.topic).join(" · ") }) }),
        sources: (list) => update({ sources: list, status: t("{{n}} ta manba topildi · javob yozilmoqda…", { n: list.length }) }),
        delta: (chunk) => update((x) => ({ text: x.text + chunk })),
        reset: () => update({ text: "" }),
        verification: (v) => update({ verification: v }),
        done: () => update({ status: t("Tayyor") }),
        error: (message) => update({ error: message }),
        incomplete: () => update({ status: "", error: t("Aloqa uzildi: javob toʻliq emas va tekshirilmagan. Savolni qayta yuboring.") }),
      }, controller.signal);
    } catch (err) {
      if (controller.signal.aborted) update({ status: t("Toʻxtatildi") });
      else {
        update({ error: err instanceof Error && "status" in err ? err.message : t("Server bilan aloqa uzildi.") });
        alertError(t, err, () => router.push("/billing"));
      }
    } finally {
      update({ streaming: false });
      void queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.canvas }} edges={["top", "left", "right"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }} keyboardVerticalOffset={80}>
        <View style={{ paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <Txt variant="title" style={{ fontSize: 24, lineHeight: 30 }}>{t("Savol-javob")}</Txt>
          <View style={{ width: 140 }}>
            <Segmented
              value={effort}
              options={[{ value: "low", label: t("Tez") }, { value: "medium", label: t("Oʻrtacha") }, { value: "high", label: t("Chuqur") }]}
              onChange={(e) => setEffort(e as Effort)}
            />
          </View>
        </View>

        <ScrollView
          ref={scrollRef}
          contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 10, paddingBottom: 24, gap: 16 }}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          keyboardShouldPersistTaps="handled"
        >
          {!turns.length ? (
            <View style={{ gap: 16, paddingTop: 16 }}>
              <Txt variant="body">
                {t("Savolingizni yozing: qonunchilik bazasidan moddalar topiladi va iqtiboslar bilan asoslab beriladi.")}
              </Txt>
              <View style={{ gap: 8 }}>
                <Txt variant="small">{t("Namunaviy savollar:")}</Txt>
                {examples.map((ex) => (
                  <View key={ex}>
                    <Pressable
                      onPress={() => void send(ex)}
                      style={({ pressed }) => ({
                        paddingHorizontal: 14, paddingVertical: 12, borderRadius: radius.sm + 2,
                        backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line,
                        opacity: pressed ? 0.75 : 1
                      })}
                    >
                      <Txt style={{ color: colors.ink }}>{ex}</Txt>
                    </Pressable>
                  </View>
                ))}
              </View>
            </View>
          ) : null}

          {turns.map((turn) => <TurnView key={turn.id} turn={turn} />)}
        </ScrollView>

        <View style={{
          paddingHorizontal: 16, paddingVertical: 12, borderTopWidth: 1, borderTopColor: colors.line,
          backgroundColor: colors.canvas, flexDirection: "row", gap: 10, alignItems: "flex-end"
        }}>
          <View style={{
            flex: 1, backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1,
            borderColor: inputFocused ? colors.primary : colors.line, paddingHorizontal: 14, paddingVertical: 8, minHeight: 46
          }}>
            <TextInput
              value={question}
              onChangeText={setQuestion}
              placeholder={t("Savolingizni yozing…")}
              placeholderTextColor={colors.muted}
              multiline
              maxLength={1000}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              style={[{ color: colors.ink, fontSize: 15, fontFamily: fonts.regular, maxHeight: 110 }, noOutline]}
            />
          </View>

          {busy ? (
            <Pressable
              onPress={stop}
              style={({ pressed }) => ({
                width: 46, height: 46, borderRadius: 23, backgroundColor: colors.red,
                alignItems: "center", justifyContent: "center", opacity: pressed ? 0.8 : 1
              })}
              accessibilityRole="button"
              accessibilityLabel={t("Toʻxtatish")}
            >
              <MaterialCommunityIcons name="stop" size={22} color="#fff" />
            </Pressable>
          ) : (
            <Pressable
              onPress={() => void send(question)}
              disabled={!question.trim()}
              style={({ pressed }) => ({
                width: 46, height: 46, borderRadius: 23,
                backgroundColor: question.trim() ? colors.primary : colors.subtle,
                alignItems: "center", justifyContent: "center",
                opacity: !question.trim() ? 0.5 : pressed ? 0.85 : 1
              })}
              accessibilityRole="button"
              accessibilityLabel={t("Yuborish")}
            >
              <MaterialCommunityIcons
                name="arrow-up"
                size={24}
                color={question.trim() ? colors.primaryFg : colors.muted}
              />
            </Pressable>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
