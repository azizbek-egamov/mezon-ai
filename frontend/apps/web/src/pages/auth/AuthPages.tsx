import { ApiError } from "@mezon/api-client";
import { BookOpenIcon, GraduationCapIcon, LockIcon, ScaleIcon } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Button, cn, ErrorNote, FadeIn, FieldError, Input, Label, LanguageSelect, Logo, LogoMark, PasswordInput, PhoneInput, type RegisterData, Spinner, staggerDelay, useAuth, Checkbox, safeNext } from "@mezon/web-kit";

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  const { t } = useTranslation();
  const points = [
    { icon: BookOpenIcon, text: t("Javob lex.uz dagi amaldagi moddalarga tayanadi, har bir iqtibos manba bilan solishtiriladi.") },
    { icon: LockIcon, text: t("Fayllar va hisobotlar serverda shifrlangan holda saqlanadi") },
  ];
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {/* Brend paneli (faqat katta ekranda): doim to'q ko'k — rejimdan qat'i nazar */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-[#1F3A5F] p-12 text-[#F4EFE3] lg:flex">
        <FadeIn className="flex items-center gap-3">
          <LogoMark className="size-10 [&_rect]:fill-[#F4EFE3]/10" />
          <span className="font-serif text-2xl font-semibold">Mezon</span>
        </FadeIn>
        <div className="max-w-md">
          <FadeIn as="h2" delay={60} className="font-serif text-[34px] font-semibold leading-tight">{t("Oʻzbekiston qonunchiligi boʻyicha savol bering")}</FadeIn>
          <ul className="mt-8 flex flex-col gap-4">
            {points.map(({ icon: Icon, text }, i) => (
              <FadeIn as="li" key={text} delay={120 + staggerDelay(i, 90)} className="flex gap-3 text-[15px] leading-relaxed text-[#F4EFE3]/80">
                <Icon className="mt-0.5 size-5 shrink-0 text-[#E2C77E]" aria-hidden />
                {text}
              </FadeIn>
            ))}
          </ul>
        </div>
        <p className="text-sm text-[#F4EFE3]/60">{t("Tizim yuridik maslahat emas — advokat uchun yordamchi vosita.")}</p>
      </aside>

      <div className="flex min-h-dvh flex-col px-5 py-6 sm:px-10">
        <FadeIn className="flex items-center justify-between">
          <Logo className="lg:invisible" />
          <LanguageSelect className="w-36" />
        </FadeIn>
        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-10">
          <FadeIn delay={60}>
            <h1 className="font-serif text-[30px] font-semibold leading-tight">{title}</h1>
            <p className="mt-2 text-[15px] text-muted">{subtitle}</p>
          </FadeIn>
          <FadeIn delay={140} className="mt-8">{children}</FadeIn>
        </div>
        <p className="text-center text-xs text-muted lg:hidden">{t("Tizim yuridik maslahat emas — advokat uchun yordamchi vosita.")}</p>
      </div>
    </div>
  );
}

function fieldErrors(error: unknown): Record<string, string[]> {
  return error instanceof ApiError ? error.fields : {};
}

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
      navigate(safeNext(params.get("next"), "/chat"), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const fields = fieldErrors(error);
  const general = error instanceof ApiError ? (fields.non_field_errors?.join(" ") ?? (error.status === 429 || !Object.keys(fields).length ? error.message : "")) : error ? t("Server bilan aloqa uzildi.") : "";

  return (
    <AuthLayout title={t("Kirish")} subtitle={t("Telefon raqamingiz va parolingiz bilan kiring.")}>
      <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
        {general && <ErrorNote>{general}</ErrorNote>}
        <div>
          <Label htmlFor="phone">{t("Telefon")}</Label>
          <PhoneInput id="phone" autoComplete="username" value={phone} onChangePhone={setPhone}
            aria-invalid={!!fields.phone_number} required autoFocus />
          <FieldError messages={fields.phone_number} />
        </div>
        <div>
          <Label htmlFor="password">{t("Parol")}</Label>
          <PasswordInput id="password" revealLabel={t("Parolni koʻrish uchun bosib turing")}
            autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} aria-invalid={!!fields.password} required />
          <FieldError messages={fields.password} />
        </div>
        <Button type="submit" size="lg" disabled={busy}>
          {busy && <Spinner className="text-primary-foreground" />}
          {t("Kirish")}
        </Button>
        <p className="text-center text-sm text-muted">
          {t("Akkauntingiz yoʻqmi?")}{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            {t("Roʻyxatdan oʻting")}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<RegisterData>({
    phone_number: "",
    full_name: "",
    role: "LAWYER",
    advocate_license_no: "",
    university: "",
    study_level: "",
    student_id_no: "",
    password1: "",
    password2: "",
    consent: false,
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof RegisterData>(key: K, value: RegisterData[K]) => setData((d) => ({ ...d, [key]: value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(data);
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const fields = fieldErrors(error);
  const general = error instanceof ApiError ? (fields.non_field_errors?.join(" ") ?? (!Object.keys(fields).length ? error.message : "")) : error ? t("Server bilan aloqa uzildi.") : "";
  const roles = [
    { value: "LAWYER" as const, label: t("Advokat / yurist"), icon: ScaleIcon },
    { value: "STUDENT" as const, label: t("Talaba"), icon: GraduationCapIcon },
  ];

  return (
    <AuthLayout title={t("Roʻyxatdan oʻtish")} subtitle={t("SMS orqali tasdiqlash keyingi bosqichda qoʻshiladi.")}>
      <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
        {general && <ErrorNote>{general}</ErrorNote>}
        <div>
          <Label>{t("Kim sifatida")}</Label>
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-subtle p-1" role="radiogroup">
            {roles.map(({ value, label, icon: Icon }) => (
              <button key={value} type="button" role="radio" aria-checked={data.role === value} onClick={() => set("role", value)}
                className={cn("flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted whitespace-nowrap transition-[background,color,box-shadow,transform] duration-150 active:scale-[0.97]",
                  data.role === value && "bg-surface text-ink shadow-card")}>
                <Icon className={cn("size-4 shrink-0", data.role === value && "text-primary")} />
                <span className="truncate">{label}</span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <Label htmlFor="phone">{t("Telefon")}</Label>
          <PhoneInput id="phone" autoComplete="tel" value={data.phone_number}
            onChangePhone={(normalized) => set("phone_number", normalized)} aria-invalid={!!fields.phone_number} required autoFocus />
          <FieldError messages={fields.phone_number} />
        </div>
        <div>
          <Label htmlFor="full_name">{t("F.I.Sh.")}</Label>
          <Input id="full_name" autoComplete="name" value={data.full_name} onChange={(e) => set("full_name", e.target.value)} aria-invalid={!!fields.full_name} />
          <FieldError messages={fields.full_name} />
        </div>
        {data.role === "LAWYER" && (
          <div>
            <Label htmlFor="license">{t("Advokatlik guvohnomasi raqami (advokatlar uchun)")}</Label>
            <Input id="license" value={data.advocate_license_no} onChange={(e) => set("advocate_license_no", e.target.value)} />
            <FieldError messages={fields.advocate_license_no} />
          </div>
        )}
        {data.role === "STUDENT" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="university">{t("Universitet / OTM")}</Label>
              <Input
                id="university"
                placeholder={t("Masalan: TDYU, SamDU, OʻzMU...")}
                value={data.university || ""}
                onChange={(e) => set("university", e.target.value)}
                aria-invalid={!!fields.university}
              />
              <FieldError messages={fields.university} />
            </div>
            <div>
              <Label htmlFor="study_level">{t("Bosqich / Kurs")}</Label>
              <Input
                id="study_level"
                placeholder={t("Masalan: 3-kurs, Magistratura...")}
                value={data.study_level || ""}
                onChange={(e) => set("study_level", e.target.value)}
                aria-invalid={!!fields.study_level}
              />
              <FieldError messages={fields.study_level} />
            </div>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="p1">{t("Parol")}</Label>
            <PasswordInput id="p1" revealLabel={t("Parolni koʻrish uchun bosib turing")}
              autoComplete="new-password" value={data.password1} onChange={(e) => set("password1", e.target.value)} aria-invalid={!!fields.password1} />
            <FieldError messages={fields.password1} />
          </div>
          <div>
            <Label htmlFor="p2">{t("Parolni takrorlang")}</Label>
            <PasswordInput id="p2" revealLabel={t("Parolni koʻrish uchun bosib turing")}
              autoComplete="new-password" value={data.password2} onChange={(e) => set("password2", e.target.value)} aria-invalid={!!fields.password2} />
            <FieldError messages={fields.password2} />
          </div>
        </div>
        <label className="flex items-start gap-3 text-sm">
          <Checkbox checked={data.consent} onCheckedChange={(v) => set("consent", v === true)} aria-invalid={!!fields.consent} />
          <span>{t("Shaxsiy maʼlumotlarimni qayta ishlashga roziman (OʻRQ-547)")}</span>
        </label>
        <FieldError messages={fields.consent} />
        <Button type="submit" size="lg" disabled={busy}>
          {busy && <Spinner className="text-primary-foreground" />}
          {t("Roʻyxatdan oʻtish")}
        </Button>
        <p className="text-center text-sm text-muted">
          {t("Akkauntingiz bormi?")}{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            {t("Kirish")}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
