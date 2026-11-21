/** Amallar jurnali: kim, qachon, nimani o'zgartirdi (AuditEvent). */
import { unwrap } from "@mezon/api-client";
import { api, Card, CardContent, Empty, Spinner } from "@mezon/web-kit";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader } from "@/components/AdminShell";
import { AuditList, Pager } from "@/components/common";
import { adminKeys } from "@/lib/admin";

export function AuditPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: adminKeys.audit(page),
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/audit/", { params: { query: { page } } })),
    placeholderData: keepPreviousData,
  });
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title={t("Amallar jurnali")} subtitle={t("Rol, tarif, toʻlov, shablon va sinxronizatsiya amallari")} />
      <Card><CardContent className="pt-3">{isLoading || !data ? <Empty><Spinner /></Empty> : <AuditList events={data.results} />}</CardContent></Card>
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </div>
  );
}
