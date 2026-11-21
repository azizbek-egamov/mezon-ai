import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button, FadeIn } from "@mezon/web-kit";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-[60vh] place-items-center px-4 text-center">
      <FadeIn>
        <div className="tabular-nums text-5xl font-bold text-gold">404</div>
        <p className="mt-2 text-muted">{t("Topilmadi")}</p>
        <Button asChild className="mt-5">
          <Link to="/chat">{t("Savol-javob")}</Link>
        </Button>
      </FadeIn>
    </div>
  );
}
