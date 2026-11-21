import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useRouteError } from "react-router";

import { Button } from "../ui/button";

/** Marshrut xatosi (render xatosi, deploydan keyin topilmagan eski bo'lak): React Router ning inglizcha standart
 * sahifasi o'rniga tarjima qilingan, "yangilash" tugmali sahifa. */
export function RouteError() {
  const { t } = useTranslation();
  const error = useRouteError();
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div className="grid min-h-dvh place-items-center px-4 text-center">
      <div role="alert" className="max-w-sm">
        <h1 className="font-serif text-2xl font-semibold">{t("Sahifani yuklab boʻlmadi")}</h1>
        <p className="mt-2 text-muted">{t("Sahifani yangilang. Muammo takrorlansa, administratorga murojaat qiling.")}</p>
        <Button className="mt-5" onClick={() => window.location.reload()}>
          {t("Sahifani yangilash")}
        </Button>
      </div>
    </div>
  );
}
