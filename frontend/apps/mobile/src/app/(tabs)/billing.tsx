/** Tarif va limitlar: joriy tarif, sarf, tariflar ro'yxati (animatsiyalar va formatlangan narxlar). */
import { unwrap, type Schemas } from "@mezon/api-client";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { RefreshControl, View } from "react-native";

import { Badge, Card, Empty, Progress, Screen, Txt } from "@/components/ui";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/formatters";
import { colors } from "@/lib/theme";

function features(t: TFunction, p: Schemas["Plan"]): string[] {
  const out = [t("Bitta ish — {{n}} varaqgacha", { n: p.max_pages_per_case })];
  out.push(p.lifetime_case_limit ? t("Ish tahlili — jami {{n}} marta", { n: p.lifetime_case_limit })
    : p.daily_case_limit ? t("Ish tahlili — kuniga {{n}} tagacha", { n: p.daily_case_limit }) : t("Ish tahlili — cheklovsiz"));
  out.push(p.lifetime_chat_limit ? t("Savol-javob — jami {{n}} ta savol", { n: p.lifetime_chat_limit })
    : p.daily_chat_limit ? t("Savol-javob — kuniga {{n}} tagacha", { n: p.daily_chat_limit }) : t("Savol-javob — cheklovsiz"));
  if (p.priority_queue) out.push(t("Ish tahlili navbatida oldinda"));
  return out;
}

export default function BillingScreen() {
  const { t } = useTranslation();
  const usage = useQuery({ queryKey: ["billing", "usage"], queryFn: () => unwrap(api.client.GET("/api/v1/billing/usage")) });
  const plans = useQuery({ queryKey: ["billing", "plans"], queryFn: () => unwrap(api.client.GET("/api/v1/billing/plans")) });
  const u = usage.data;

  return (
    <Screen refreshControl={<RefreshControl refreshing={usage.isRefetching} onRefresh={() => void usage.refetch()} tintColor={colors.primary} />}>
      <Txt variant="title">{t("Tarif va limitlar")}</Txt>

      {!u ? <Empty>…</Empty> : (
        <Card delay={50} style={{ gap: 12 }}>
          <Txt variant="small">{t("Joriy tarifingiz")}</Txt>
          <Txt variant="title" style={{ fontSize: 24, lineHeight: 30 }}>{u.plan_name}</Txt>
          {u.unlimited ? <Txt variant="small">{t("Cheklovlarsiz rejim (xodim akkaunti yoki kvotalar oʻchirilgan).")}</Txt>
            : u.expires_at ? <Txt variant="small">{t("Obuna {{d}} gacha amal qiladi.", { d: new Date(u.expires_at).toLocaleDateString() })}</Txt> : null}
          <Txt variant="small">{t("Bitta ish hajmi: {{n}} varaqgacha.", { n: u.max_pages })}</Txt>
          {u.usage.map((row) => (
            <View key={row.label} style={{ gap: 6, marginTop: 4 }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Txt variant="small">{row.label}</Txt>
                <Txt variant="mono">{`${formatNumber(row.used)} / ${formatNumber(row.limit)}`}</Txt>
              </View>
              <Progress value={(row.used / Math.max(1, row.limit)) * 100} tone={row.used >= row.limit ? "red" : "blue"} />
            </View>
          ))}
        </Card>
      )}

      <Txt variant="h2" style={{ marginTop: 12 }}>{t("Tariflar")}</Txt>

      {(plans.data ?? []).map((p, index) => {
        const current = p.code === u?.plan;
        return (
          <Card key={p.code} delay={100 + index * 70} style={current ? { borderColor: colors.primary, borderWidth: 2 } : undefined}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Txt variant="h2">{p.name}</Txt>
              {current ? <Badge tone="info">{t("Joriy tarifingiz")}</Badge> : null}
            </View>
            <Txt variant="title" style={{ fontSize: 22, color: colors.primary, marginTop: 4 }}>
              {p.price_uzs ? `${formatNumber(p.price_uzs)} soʻm / oy` : t("Narx belgilanmagan")}
            </Txt>
            <View style={{ gap: 6, marginTop: 6 }}>
              {features(t, p).map((f) => (
                <View key={f} style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
                  <MaterialCommunityIcons name="check" size={18} color={colors.primary} />
                  <Txt variant="small" style={{ flex: 1 }}>{f}</Txt>
                </View>
              ))}
            </View>
          </Card>
        );
      })}
    </Screen>
  );
}
