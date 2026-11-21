import { ApiError } from "@mezon/api-client";
import { Alert } from "react-native";

/** Forma xatolari: umumiy xabar va maydonlar bo'yicha */
export function errorText(t: (k: string) => string, error: unknown): { general: string; fields: Record<string, string[]> } {
  if (error instanceof ApiError) {
    const fields = error.fields;
    return { fields, general: fields.non_field_errors?.join(" ") ?? (Object.keys(fields).length ? "" : error.message) };
  }
  return { fields: {}, general: error ? t("Server bilan aloqa uzildi.") : "" };
}

/** Xato oynasi; tarif limiti (429 quota_*) bo'lsa — "Tarif" tugmasi */
export function alertError(t: (k: string) => string, error: unknown, goBilling?: () => void) {
  if (__DEV__ && !(error instanceof ApiError)) console.warn("alertError:", error); // dev: Metro logida asl sabab
  const message = error instanceof ApiError ? error.message : t("Server bilan aloqa uzildi.");
  if (error instanceof ApiError && error.isQuota && goBilling) {
    Alert.alert(t("Xato"), message, [{ text: t("Bekor qilish"), style: "cancel" }, { text: t("Tarif"), onPress: goBilling }]);
  } else {
    Alert.alert(t("Xato"), message);
  }
}
