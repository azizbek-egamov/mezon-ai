/**
 * Ish: holat va progress (2 s da yangilanadi), xato → qayta urinish, o'chirish, tahlil hisoboti.
 * PDF telefonda ko'rsatilmaydi va keshlanmaydi (advokatlik siri); rasmiy DOCX/PDF — yuridik tasdiqdan keyin veb-saytda.
 */
import type { CaseReport, Finding } from "@mezon/api-client";
import { unwrap } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, Stack, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, RefreshControl, View } from "react-native";

import { LegalText } from "@/components/LegalText";
import { Badge, Button, Card, Empty, ErrorNote, Progress, Screen, Segmented, Txt, type Tone } from "@/components/ui";
import { api } from "@/lib/api";
import { alertError } from "@/lib/errors";
import { colors, fonts } from "@/lib/theme";

const active = (s?: string) => s === "QUEUED" || s === "RUNNING";
const tone = (s: string): Tone => (s === "DONE" ? "ok" : s === "FAILED" ? "bad" : "info");

function verdict(t: (k: string) => string, v?: string): [string, Tone] {
  switch (v) {
    case "qonun_buzilishi": return [t("Qonun buzilishi"), "bad"];
    case "buzilish_ehtimoli": return [t("Buzilish ehtimoli"), "warn"];
    case "huquqiy_ahamiyatli": return [t("Huquqiy ahamiyatli"), "info"];
    case "asossiz": return [t("Asossiz"), "neutral"];
    default: return [v ?? "", "neutral"];
  }
}

function FindingCard({ f }: { f: Finding }) {
  const { t } = useTranslation();
  const L = f.legal ?? {};
  const sources = Object.fromEntries((L.sources ?? []).map((s) => [s.key, s]));
  const [label, vtone] = verdict(t, L.verdict);
  return (
    <Card accent={f.importance === "high" ? "red" : f.importance === "medium" ? "amber" : undefined}>
      <Txt variant="h2" style={{ fontSize: 17, lineHeight: 24 }}>{f.topic}</Txt>
      <Txt variant="small">{f.pages.map((p) => t("{{n}}-v", { n: p })).join("  ·  ")}</Txt>
      <Txt>{f.explanation}</Txt>
      {L.skipped ? <Txt variant="small">{t("Huquqiy asoslash oʻtkazib yuborildi (muhimligi past).")}</Txt> : null}
      {L.verdict ? (
        <View style={{ gap: 10, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 12 }}>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
            <Badge tone={vtone}>{label}</Badge>
            <Badge tone={L.verification?.ok ? "ok" : "bad"}>{L.verification?.ok ? t("✓ manbalar tekshirildi") : t("⚠ tekshiruvdan oʻtmagan")}</Badge>
          </View>
          <LegalText text={L.assessment ?? ""} sources={sources} />
          {L.defense_action ? <Txt><Txt style={{ fontFamily: fonts.semibold }}>{t("Himoyachi uchun:")} </Txt>{L.defense_action}</Txt> : null}
        </View>
      ) : L.error ? <Txt variant="small" style={{ color: colors.red }}>{t("Huquqiy baho olinmadi:")} {L.error}</Txt> : null}
    </Card>
  );
}

function Report({ report }: { report: CaseReport }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"proc" | "contr" | "time">("proc");
  const facts = Object.fromEntries(report.facts.map((f) => [f.id, f]));
  const proc = report.findings.filter((f) => f.kind === "procedural");
  const contr = report.findings.filter((f) => f.kind === "contradiction");
  const verified = report.facts.filter((f) => f.verified).length;
  return (
    <View style={{ gap: 16 }}>
      <Card>
        <Txt variant="h2">{t("Xulosa.").replace(/\.$/, "")}</Txt>
        <Txt>{report.summary}</Txt>
        <View style={{ flexDirection: "row", flexWrap: "wrap", columnGap: 14, rowGap: 4, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 12 }}>
          <Txt variant="small">{t("{{n}} varaq", { n: report.pages })}</Txt>
          <Txt variant="small">{t("{{n}} fakt · {{v}} iqtibos tasdiqlandi", { n: report.facts.length, v: verified })}</Txt>
          {contr.length ? <Txt variant="small" style={{ color: colors.red }}>{t("{{n}} ziddiyat", { n: contr.length })}</Txt> : null}
          {proc.length ? <Txt variant="small" style={{ color: colors.amber }}>{t("{{n}} protsessual muammo", { n: proc.length })}</Txt> : null}
        </View>
      </Card>
      <Segmented<"proc" | "contr" | "time"> value={tab} onChange={setTab} options={[
        { value: "proc", label: t("Protsessual muammolar") }, { value: "contr", label: t("Ziddiyatlar") }, { value: "time", label: t("Xronologiya") },
      ]} />
      {tab === "proc" && (proc.length ? proc.map((f, i) => <FindingCard key={i} f={f} />) : <Empty>{t("Topilmadi.")}</Empty>)}
      {tab === "contr" && (contr.length ? contr.map((f, i) => <FindingCard key={i} f={f} />) : <Empty>{t("Topilmadi.")}</Empty>)}
      {tab === "time" && report.timeline.map((id) => facts[id]).filter(Boolean).map((f) => (
        <View key={f.id} style={{ flexDirection: "row", gap: 12, borderBottomWidth: 1, borderBottomColor: colors.line, paddingVertical: 12 }}>
          <View style={{ width: 96 }}>
            <Txt variant="mono">{f.date}</Txt>
            <Txt variant="mono">{`${f.time}  ${t("{{n}}-v", { n: f.verified_page || f.page })}`}</Txt>
          </View>
          <Txt style={{ flex: 1 }}>{f.summary}</Txt>
        </View>
      ))}
    </View>
  );
}

export default function CaseScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: ["cases", id],
    queryFn: () => unwrap(api.client.GET("/api/v1/cases/{run_id}", { params: { path: { run_id: id } } })),
    refetchInterval: (q) => (active(q.state.data?.status) ? 2000 : false),
  });
  const done = run.data?.status === "DONE";
  const report = useQuery({
    queryKey: ["cases", id, "report"],
    queryFn: async () => (await (await api.raw(`/cases/${id}/report`)).json()) as CaseReport,
    enabled: done,
    staleTime: Infinity,
  });
  const retry = useMutation({
    mutationFn: () => unwrap(api.client.POST("/api/v1/cases/{run_id}/retry", { params: { path: { run_id: id } } })),
    onSuccess: (data) => queryClient.setQueryData(["cases", id], data),
    onError: (err) => alertError(t, err, () => router.push("/billing")),
  });
  const remove = useMutation({
    mutationFn: () => api.raw(`/cases/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["cases", id] }); // o'chirilgan ishni qayta so'ramaslik (404)
      void queryClient.invalidateQueries({ queryKey: ["cases"] });
      router.back();
    },
    onError: (err) => alertError(t, err),
  });

  const r = run.data;
  const confirmDelete = () => Alert.alert(t("Ishni oʻchirish"), t("Ish, PDF va hisobot butunlay oʻchiriladi. Davom etasizmi?"), [
    { text: t("Bekor qilish"), style: "cancel" },
    { text: t("Ishni oʻchirish"), style: "destructive", onPress: () => remove.mutate() },
  ]);

  return (
    <Screen header refreshControl={<RefreshControl refreshing={run.isRefetching} onRefresh={() => void run.refetch()} tintColor={colors.primary} />}>
      <Stack.Screen options={{ title: "" }} />
      {run.isLoading ? <Empty>…</Empty> : !r ? <ErrorNote>{run.error?.message ?? t("Topilmadi")}</ErrorNote> : (
        <>
          <View style={{ gap: 8 }}>
            <Txt variant="title" style={{ fontSize: 24, lineHeight: 31 }}>{r.title}</Txt>
            <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
              <Badge tone={tone(r.status)}>{r.status_label}</Badge>
              <Txt variant="small">{r.category_label}</Txt>
              <Txt variant="small">{t("{{n}} varaq", { n: r.pages })}</Txt>
            </View>
          </View>
          {active(r.status) ? (
            <Card>
              <Txt variant="muted">{`${r.status_label} · ${r.stage || "…"}`}</Txt>
              <Progress value={r.progress} />
            </Card>
          ) : null}
          {r.status === "FAILED" ? (
            <View style={{ gap: 10 }}>
              <ErrorNote>{`${t("Xato:")} ${r.error}`}</ErrorNote>
              <Button title={t("Qayta urinish")} onPress={() => retry.mutate()} loading={retry.isPending} />
            </View>
          ) : null}
          {done ? (report.data ? <Report report={report.data} /> : report.error ? <ErrorNote>{report.error.message}</ErrorNote> : <Empty>…</Empty>) : null}
          {done ? (
            <Card>
              <Txt variant="small">{r.confirmed_at ? t("✓ tasdiqlangan:") + " " + new Date(r.confirmed_at).toLocaleString() : t("avval yuridik tasdiq talab qilinadi")}</Txt>
              <Txt variant="small">{t("Rasmiy DOCX/PDF hisobot — veb-saytda (yuridik tasdiqdan keyin).")}</Txt>
            </Card>
          ) : null}
          <Button title={t("Ishni oʻchirish")} variant="danger" onPress={confirmDelete} disabled={r.status === "RUNNING"} loading={remove.isPending} />
        </>
      )}
    </Screen>
  );
}
