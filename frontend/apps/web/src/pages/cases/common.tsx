import type { Schemas } from "@mezon/api-client";
import { useTranslation } from "react-i18next";
import { Badge } from "@mezon/web-kit";

export type CaseRun = Schemas["CaseDetail"];

export const isActive = (status: string) => status === "QUEUED" || status === "RUNNING";

export function CaseStatusBadge({ run }: { run: Pick<CaseRun, "status" | "status_label" | "progress"> }) {
  if (run.status === "DONE") return <Badge tone="ok">{run.status_label}</Badge>;
  if (run.status === "FAILED") return <Badge tone="bad">{run.status_label}</Badge>;
  return (
    <Badge tone="info">
      {run.status_label} · {run.progress}%
    </Badge>
  );
}

/** Varaq tugmasi: bosilganda PDF ko'rgich shu varaqqa o'tadi */
export function PageButton({ page, onPage }: { page: number; onPage?: (n: number) => void }) {
  const { t } = useTranslation();
  return (
    <button type="button" onClick={() => onPage?.(page)} disabled={!onPage}
      className="mr-1 rounded-md border border-line px-1.5 tabular-nums text-xs font-medium text-primary hover:border-primary disabled:cursor-default disabled:hover:border-line">
      {t("{{n}}-v", { n: page })}
    </button>
  );
}
