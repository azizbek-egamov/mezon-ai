import { ApiError } from "@mezon/api-client";
import { Button, Card, ErrorNote, FadeIn, FieldError, fieldErrors, Label, LanguageSelect, Logo, PasswordInput, PhoneInput, Spinner, useAuth } from "@mezon/web-kit";
import { LockIcon, LogInIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router";

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(phone, password);
      const next = params.get("next");
      navigate(next && next.startsWith("/") && !next.startsWith("//") ? next : "/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const fields = fieldErrors(error);
  const general = error instanceof ApiError
    ? (fields.non_field_errors?.join(" ") ?? (!Object.keys(fields).length ? error.message : ""))
    : error ? t("Server bilan aloqa uzildi.") : "";

  return (
    <div className="grid min-h-dvh place-items-center px-5 py-10">
      <div className="flex w-full max-w-[400px] flex-col gap-6">
        <FadeIn className="flex items-center justify-between">
          <Logo subtitle={t("Boshqaruv paneli")} />
          <LanguageSelect className="w-36" />
        </FadeIn>
        <FadeIn delay={60}>
        <Card className="p-8">
          <h1 className="font-serif text-[26px] font-semibold leading-tight">{t("Admin panelga kirish")}</h1>
          <p className="mt-2 flex items-center gap-1.5 text-sm text-muted"><LockIcon className="size-4" /> {t("Faqat yurist-moderator yoki superadmin uchun")}</p>
          <form onSubmit={submit} className="mt-7 flex flex-col gap-5" noValidate>
            {general && <ErrorNote>{general}</ErrorNote>}
            <div>
              <Label htmlFor="phone">{t("Telefon")}</Label>
              <PhoneInput id="phone" autoComplete="username" value={phone} onChangePhone={setPhone}
                aria-invalid={!!fields.phone_number} autoFocus />
              <FieldError messages={fields.phone_number} />
            </div>
            <div>
              <Label htmlFor="password">{t("Parol")}</Label>
              <PasswordInput id="password" revealLabel={t("Parolni koʻrish uchun bosib turing")}
                autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} aria-invalid={!!fields.password} />
              <FieldError messages={fields.password} />
            </div>
            <Button type="submit" size="lg" disabled={busy}>
              {busy ? <Spinner className="text-primary-foreground" /> : <LogInIcon />} {t("Kirish")}
            </Button>
          </form>
        </Card>
        </FadeIn>
      </div>
    </div>
  );
}
