/**
 * Ishlar: tezkor skaner — kamera bilan ketma-ket varaqlar, galereya, fayllar →
 * bitta ish va ishlar ro'yxati (silliq animatsiyalar bilan).
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { unwrap } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "expo-image";
import { router } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, Pressable, RefreshControl, ScrollView, Switch, Text, View } from "react-native";
import Animated, { FadeInRight } from "react-native-reanimated";

import { Badge, Button, Card, Empty, Field, Progress, Screen, Txt, type Tone } from "@/components/ui";
import { api } from "@/lib/api";
import { alertError } from "@/lib/errors";
import { colors, fonts, radius } from "@/lib/theme";
import { pickDocuments, pickImages, takePhoto, uploadCase, type PickedFile } from "@/lib/upload";

const active = (s: string) => s === "QUEUED" || s === "RUNNING";

function statusTone(status: string): Tone {
  return status === "DONE" ? "ok" : status === "FAILED" ? "bad" : "info";
}

function Scanner() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<PickedFile[]>([]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("criminal");
  const [zeroRetention, setZeroRetention] = useState(false);
  const options = useQuery({ queryKey: ["cases", "options"], queryFn: () => unwrap(api.client.GET("/api/v1/cases/options")), staleTime: Infinity });

  const upload = useMutation({
    mutationFn: () => uploadCase(files, { title, category, zeroRetention }),
    onSuccess: (run) => {
      setFiles([]);
      setTitle("");
      void queryClient.invalidateQueries({ queryKey: ["cases"] });
      void queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
      router.push(`/case/${run.id}`);
    },
    onError: (err) => alertError(t, err, () => router.push("/billing")),
  });

  async function camera() {
    const r = await takePhoto();
    if (r === "denied") Alert.alert(t("Xato"), t("Kameradan foydalanishga ruxsat berilmagan"));
    else if (r) setFiles((f) => [...f, r]);
  }
  const add = (list: PickedFile[]) => setFiles((f) => [...f, ...list]);
  const totalMb = files.reduce((s, f) => s + (f.size ?? 0), 0) / 1024 / 1024;
  const limits = options.data;

  return (
    <Card style={{ gap: 16 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Txt variant="h2">{t("Hujjat varaqlari")}</Txt>
        <Badge>{`${files.length} / ${limits?.max_files ?? 20}`}</Badge>
      </View>

      {files.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10, paddingVertical: 4 }}>
          {files.map((f, i) => (
            <View key={`${f.uri}-${i}`} style={{ width: 88, gap: 4 }}>
              {f.mimeType.startsWith("image/") ? (
                <Image
                  source={{ uri: f.uri }}
                  style={{ width: 88, height: 116, borderRadius: radius.sm, backgroundColor: colors.subtle }}
                  contentFit="cover"
                />
              ) : (
                <View style={{ width: 88, height: 116, borderRadius: radius.sm, backgroundColor: colors.subtle, alignItems: "center", justifyContent: "center" }}>
                  <MaterialCommunityIcons name={f.mimeType.includes("pdf") ? "file-pdf-box" : "file-word-box"} size={40} color={colors.primary} />
                </View>
              )}
              <Text style={{ color: colors.muted, fontSize: 11, fontFamily: fonts.regular }} numberOfLines={1}>{`${i + 1}. ${f.name}`}</Text>
            </View>
          ))}
        </ScrollView>
      ) : (
        <Txt variant="muted">{t("Varaqlarni kamera bilan ketma-ket suratga oling yoki galereya / fayllardan tanlang — hammasi bitta ishga birlashtiriladi.")}</Txt>
      )}

      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-around", paddingVertical: 8 }}>
        <Pressable
          onPress={() => setFiles((f) => f.slice(0, -1))}
          disabled={!files.length}
          style={({ pressed }) => ({ alignItems: "center", gap: 3, opacity: !files.length ? 0.35 : pressed ? 0.7 : 1 })}
          accessibilityRole="button"
          accessibilityLabel={t("Oxirgisini oʻchirish")}
        >
          <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.subtle, alignItems: "center", justifyContent: "center" }}>
            <MaterialCommunityIcons name="undo-variant" size={22} color={colors.ink} />
          </View>
          <Txt variant="small">{t("Qaytarish")}</Txt>
        </Pressable>

        <Pressable
          onPress={() => void camera()}
          accessibilityRole="button"
          accessibilityLabel={t("Suratga olish")}
          style={({ pressed }) => ({
            width: 76, height: 76, borderRadius: 38, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center",
            elevation: 4, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.2, shadowRadius: 4,
            transform: [{ scale: pressed ? 0.94 : 1 }]
          })}
        >
          <MaterialCommunityIcons name="camera-outline" size={36} color={colors.primaryFg} />
        </Pressable>

        <Pressable
          onPress={() => void pickImages().then(add)}
          style={({ pressed }) => ({ alignItems: "center", gap: 3, opacity: pressed ? 0.7 : 1 })}
          accessibilityRole="button"
          accessibilityLabel={t("Galereya")}
        >
          <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.subtle, alignItems: "center", justifyContent: "center" }}>
            <MaterialCommunityIcons name="image-multiple-outline" size={22} color={colors.ink} />
          </View>
          <Txt variant="small">{t("Galereya")}</Txt>
        </Pressable>

        <Pressable
          onPress={() => void pickDocuments().then(add)}
          style={({ pressed }) => ({ alignItems: "center", gap: 3, opacity: pressed ? 0.7 : 1 })}
          accessibilityRole="button"
          accessibilityLabel={t("Fayllar")}
        >
          <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.subtle, alignItems: "center", justifyContent: "center" }}>
            <MaterialCommunityIcons name="file-document-multiple-outline" size={22} color={colors.ink} />
          </View>
          <Txt variant="small">{t("Fayllar")}</Txt>
        </Pressable>
      </View>

      <Field label={t("Ish nomi (ixtiyoriy)")} value={title} onChangeText={setTitle} placeholder={t("Masalan: 1-sonli jinoyat ishi")} />

      <View style={{ gap: 8 }}>
        <Txt variant="label">{t("Ish turi")}</Txt>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
          {(limits?.case_types ?? [
            { code: "criminal", label: t("Jinoyat") },
            { code: "civil", label: t("Fuqarolik") },
            { code: "economic", label: t("Iqtisodiy") },
            { code: "administrative", label: t("Maʼmuriy") },
            { code: "other", label: t("Boshqa") },
          ]).map((c: { code: string; label: string }) => (
            <Pressable
              key={c.code}
              onPress={() => setCategory(c.code)}
              style={({ pressed }) => ({
                paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999,
                backgroundColor: category === c.code ? colors.primary : colors.surface,
                borderWidth: 1, borderColor: category === c.code ? colors.primary : colors.line,
                opacity: pressed ? 0.8 : 1
              })}
            >
              <Text style={{ color: category === c.code ? colors.primaryFg : colors.ink, fontFamily: fonts.medium, fontSize: 14 }}>
                {c.label}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>

      <Pressable onPress={() => setZeroRetention(!zeroRetention)} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 4 }}>
        <View style={{ flex: 1, paddingRight: 12 }}>
          <Txt variant="label">{t("Tahlildan soʻng fayllarni oʻchirish")}</Txt>
          <Txt variant="small">{t("Zero-retention: server faqat hisobotni saqlaydi, asl fayllar oʻchiriladi.")}</Txt>
        </View>
        <Switch value={zeroRetention} onValueChange={setZeroRetention} trackColor={{ true: colors.primary, false: colors.line }} />
      </Pressable>

      <Button
        title={t("Tahlilni boshlash ({{n}} varaq)", { n: files.length })}
        onPress={() => upload.mutate()}
        loading={upload.isPending}
        disabled={!files.length || (limits ? totalMb > limits.max_mb : false)}
      />
    </Card>
  );
}

export default function CasesScreen() {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["cases"],
    queryFn: () => unwrap(api.client.GET("/api/v1/cases/")),
    refetchInterval: (q) => (q.state.data?.results?.some((c) => active(c.status)) ? 2500 : false),
  });

  const list = query.data?.results ?? [];
  return (
    <Screen refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => void query.refetch()} tintColor={colors.primary} />}>
      <Txt variant="title">{t("Ishlar")}</Txt>
      <Scanner />
      <Txt variant="h2" style={{ marginTop: 12 }}>{t("Mening ishlarim")}</Txt>

      {!list.length ? (
        <Empty>{t("Hozircha ishlar yoʻq. Yuqoridagi skaner orqali yangi ish yuklang.")}</Empty>
      ) : (
        list.map((c, index: number) => (
          <Pressable key={c.id} onPress={() => router.push(`/case/${c.id}`)}>
            <Card delay={index * 60}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                <Txt variant="h2" numberOfLines={1} style={{ flex: 1, paddingRight: 8 }}>{c.title}</Txt>
                <Badge tone={statusTone(c.status)}>{c.status_label}</Badge>
              </View>
              <View style={{ flexDirection: "row", gap: 12, alignItems: "center" }}>
                <Txt variant="small">{c.category_label}</Txt>
                <Txt variant="small">·</Txt>
                <Txt variant="small">{`${c.pages} ${t("varaq")}`}</Txt>
                <Txt variant="small">·</Txt>
                <Txt variant="small">{new Date(c.created_at).toLocaleDateString()}</Txt>
              </View>
              {active(c.status) ? (
                <View style={{ gap: 6, marginTop: 4 }}>
                  <Txt variant="small" style={{ color: colors.primary }}>{c.status_label || t("Bajarilmoqda…")}</Txt>
                  <Progress value={c.progress ?? 20} />
                </View>
              ) : null}
            </Card>
          </Pressable>
        ))
      )}
    </Screen>
  );
}
