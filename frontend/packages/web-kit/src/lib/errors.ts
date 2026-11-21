import { ApiError } from "@mezon/api-client";
import type { TFunction } from "i18next";
import { toast } from "sonner";

/** Xatoni toast bilan ko'rsatadi; tarif limiti bo'lsa — "Tarif" tugmasi bilan. */
export function notifyError(error: unknown, t: TFunction, goBilling?: () => void) {
  if (error instanceof ApiError) {
    if (error.isQuota && goBilling) {
      toast.error(error.message, { action: { label: t("Tarif"), onClick: goBilling }, duration: 10_000 });
    } else {
      toast.error(error.message);
    }
    return;
  }
  toast.error(t("Server bilan aloqa uzildi."));
}

/** Validatsiya xatolari (400) maydonlar bo'yicha; boshqa xato — bo'sh */
export function fieldErrors(error: unknown): Record<string, string[]> {
  return error instanceof ApiError ? error.fields : {};
}
