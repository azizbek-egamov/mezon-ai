/** Ommaviy bosh sahifa (ro'yxatdan o'tishdan oldin ko'rinadi). Tizimga kirgan foydalanuvchi /chat ga yo'naltiriladi (router.tsx).
 * Uslub — designs/mezon_klassik/DESIGN.md: huquqiy jurnal, SaaS-reklama emas; "lex.uz" aniq bir marta tilga olinadi. */
import {
  BookOpenIcon, BriefcaseIcon, CheckIcon, FileTextIcon, LockIcon, MessageSquareTextIcon, ShieldCheckIcon,
} from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Badge, Button, Card, CiteChip, cn, FadeIn, LanguageSelect, Logo, LogoMark, staggerDelay, ThemeSwitch } from "@mezon/web-kit";

function NavAnchor({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className="text-[14px] font-medium text-muted hover:text-ink">
      {children}
    </a>
  );
}

function PreviewCard() {
  const { t } = useTranslation();
  return (
    <Card className="w-full max-w-md p-5">
      <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[14px] text-primary-foreground">
        {t("Ishdan nohaq boʻshatilsam, qanday harakat qilaman?")}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        {/* Modda raqamlari lex.uz bazasidan tekshirilgan (Mehnat kodeksi, amaldagi tahrir): 161 — ish beruvchi tashabbusi bilan
            bekor qilish; 560 — yakka tartibdagi mehnat nizosi bo'yicha sudga murojaat muddatlari (ishga tiklash — 3 oy). */}
        <CiteChip href="#"><b className="mr-1 font-semibold">MK 161-modda</b> {t("Ish beruvchi tashabbusi bilan bekor qilish")}</CiteChip>
        <CiteChip href="#"><b className="mr-1 font-semibold">MK 560-modda</b> {t("Sudga murojaat qilish muddatlari")}</CiteChip>
      </div>
      <p className="mt-3 text-[14px] leading-relaxed text-ink">
        {t("Agar bekor qilish asossiz boʻlsa, ishga tiklash toʻgʻrisidagi daʼvo bilan buyruq nusxasi topshirilgan kundan boshlab uch oy ichida sudga murojaat qilishingiz mumkin…")}
      </p>
      <div className="mt-4 border-t border-line pt-3">
        <Badge tone="ok">{t("✓ Tekshiruvdan oʻtdi")}</Badge>
      </div>
    </Card>
  );
}

/** Icon + sarlavha + matn — SaaS uslubidagi rangli ikonka-karta o'rniga oddiy qator (AuthLayout bullet uslubi bilan bir xil). */
function FeatureRow({ icon: Icon, title, text, index }: { icon: ComponentType<{ className?: string }>; title: string; text: string; index: number }) {
  return (
    <FadeIn delay={staggerDelay(index, 90)} className={cn("flex gap-4 border-line py-6", index > 0 && "border-t")}>
      <Icon className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
      <div>
        <h3 className="font-serif text-[18px] font-semibold leading-snug">{title}</h3>
        <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-muted">{text}</p>
      </div>
    </FadeIn>
  );
}

const features = (t: (k: string) => string) => [
  { icon: MessageSquareTextIcon, title: t("Qonun boʻyicha savol-javob"), text: t("Javob amaldagi qonun moddasiga tayanadi — har bir iqtibos manba bilan solishtiriladi.") },
  { icon: BriefcaseIcon, title: t("Ish hujjatlarini tahlili"), text: t("Hujjatni OCR orqali oʻqiydi, faktlarni ajratadi, ziddiyatlarni topadi va huquqiy asoslash tayyorlaydi.") },
  { icon: FileTextIcon, title: t("Hujjat konstruktori"), text: t("Shablon asosida (AI ishtirokisiz) tez va aniq hujjat — DOCX yoki PDF koʻrinishida.") },
];

const steps = (t: (k: string) => string) => [
  { title: t("Roʻyxatdan oʻting"), text: t("Telefon raqamingiz bilan bir necha soniyada hisob oching.") },
  { title: t("Savol bering yoki ish yuklang"), text: t("Qonunchilik boʻyicha savol yozing yoki ish hujjatlarini yuklang.") },
  { title: t("Asoslangan natija oling"), text: t("Iqtibosli javob, tahlil hisoboti yoki tayyor hujjatni darhol koʻring.") },
];

export function LandingPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-3.5 sm:px-8">
          <Logo />
          <nav className="hidden items-center gap-6 md:flex">
            <NavAnchor href="#imkoniyatlar">{t("Imkoniyatlar")}</NavAnchor>
            <NavAnchor href="#qanday-ishlaydi">{t("Qanday ishlaydi")}</NavAnchor>
            <NavAnchor href="#xavfsizlik">{t("Xavfsizlik")}</NavAnchor>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeSwitch compact className="hidden sm:inline-grid" />
            <LanguageSelect className="w-32" />
            <Button variant="outline" asChild><Link to="/login">{t("Kirish")}</Link></Button>
            <Button asChild className="hidden sm:inline-flex"><Link to="/register">{t("Roʻyxatdan oʻtish")}</Link></Button>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:py-24">
          <FadeIn>
            <h1 className="font-serif text-[36px] font-semibold leading-[1.15] sm:text-[46px]">
              {t("Oʻzbekiston qonunchiligi boʻyicha ishonchli raqamli yordamchi")}
            </h1>
            <p className="mt-5 max-w-lg text-[17px] leading-relaxed text-muted">
              {t("Savolingizga amaldagi qonun moddasiga asoslangan javob olasiz, ish hujjatlarini tahlil qildirasiz va hujjatlarni shablon asosida tayyorlaysiz — bitta joyda.")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" asChild><Link to="/register">{t("Roʻyxatdan oʻtish")}</Link></Button>
              <Button size="lg" variant="outline" asChild><Link to="/login">{t("Kirish")}</Link></Button>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-muted">
              <span className="flex items-center gap-1.5"><BookOpenIcon className="size-4 text-primary" /> {t("lex.uz manbali javoblar")}</span>
              <span className="flex items-center gap-1.5"><LockIcon className="size-4 text-primary" /> {t("Shifrlangan saqlash")}</span>
            </div>
          </FadeIn>
          <FadeIn delay={120} className="flex justify-center lg:justify-end">
            <PreviewCard />
          </FadeIn>
        </section>

        {/* Imkoniyatlar */}
        <section id="imkoniyatlar" className="border-t border-line px-5 py-16 sm:px-8 lg:py-20">
          <div className="mx-auto max-w-3xl">
            <FadeIn>
              <h2 className="font-serif text-[28px] font-semibold leading-tight sm:text-[32px]">{t("Nima qila olasiz")}</h2>
              <p className="mt-2 text-[15px] text-muted">{t("Bitta tizimda — savol-javobdan hujjat tayyorlashgacha.")}</p>
            </FadeIn>
            <div className="mt-8">
              {features(t).map(({ icon, title, text }, i) => (
                <FeatureRow key={title} icon={icon} title={title} text={text} index={i} />
              ))}
            </div>
          </div>
        </section>

        {/* Qanday ishlaydi */}
        <section id="qanday-ishlaydi" className="px-5 py-16 sm:px-8 lg:py-20">
          <div className="mx-auto max-w-6xl">
            <FadeIn className="max-w-xl">
              <h2 className="font-serif text-[28px] font-semibold leading-tight sm:text-[32px]">{t("Qanday ishlaydi")}</h2>
            </FadeIn>
            <div className="mt-10 grid gap-8 sm:grid-cols-3">
              {steps(t).map(({ title, text }, i) => (
                <FadeIn key={title} delay={staggerDelay(i, 110)}>
                  <span className="grid size-11 place-items-center rounded-full bg-primary font-serif text-[18px] font-semibold text-primary-foreground">
                    {i + 1}
                  </span>
                  <h3 className="mt-4 font-serif text-[19px] font-semibold leading-snug">{title}</h3>
                  <p className="mt-2 text-[14px] leading-relaxed text-muted">{text}</p>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* Xavfsizlik */}
        <section id="xavfsizlik" className="bg-[#1F3A5F] px-5 py-16 text-[#F4EFE3] sm:px-8 lg:py-20">
          <div className="mx-auto max-w-6xl">
            <FadeIn className="max-w-xl">
              <h2 className="font-serif text-[28px] font-semibold leading-tight sm:text-[32px]">{t("Maxfiylik — ustuvor")}</h2>
              <p className="mt-2 text-[15px] text-[#F4EFE3]/75">{t("Advokatlik siri va mijoz maʼlumotlari himoyalangan holda saqlanadi.")}</p>
            </FadeIn>
            <div className="mt-10 grid gap-6 sm:grid-cols-3">
              {[
                { icon: LockIcon, text: t("Fayllar va hisobotlar serverda shifrlangan holda saqlanadi") },
                { icon: ShieldCheckIcon, text: t("Shaxsiy maʼlumotlar tahlilga yuborilishidan oldin niqoblanadi") },
                { icon: CheckIcon, text: t("Har bir huquqiy iqtibos rasmiy manba bilan solishtiriladi") },
              ].map(({ icon: Icon, text }, i) => (
                <FadeIn key={text} delay={staggerDelay(i, 100)} className="flex gap-3">
                  <Icon className="mt-0.5 size-5 shrink-0 text-[#E2C77E]" aria-hidden />
                  <span className="text-[15px] leading-relaxed text-[#F4EFE3]/90">{text}</span>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* Yakuniy CTA */}
        <section className="px-5 py-16 text-center sm:px-8 lg:py-20">
          <FadeIn className="mx-auto max-w-xl">
            <h2 className="font-serif text-[26px] font-semibold leading-tight sm:text-[30px]">{t("Advokatlik ishingizni bugun osonlashtiring")}</h2>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Button size="lg" asChild><Link to="/register">{t("Roʻyxatdan oʻtish")}</Link></Button>
              <Button size="lg" variant="outline" asChild><Link to="/login">{t("Kirish")}</Link></Button>
            </div>
          </FadeIn>
        </section>
      </main>

      <footer className="border-t border-line px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <LogoMark className="size-7" />
            <span className="text-[13px] text-muted">{t("Tizim yuridik maslahat emas — advokat uchun yordamchi vosita.")}</span>
          </div>
          <div className="flex items-center gap-4 text-[13px] text-muted">
            <Link to="/login" className="hover:text-ink">{t("Kirish")}</Link>
            <Link to="/register" className="hover:text-ink">{t("Roʻyxatdan oʻtish")}</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
