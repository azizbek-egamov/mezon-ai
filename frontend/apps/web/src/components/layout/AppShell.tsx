import { BookOpenIcon, BriefcaseIcon, CreditCardIcon, FileTextIcon, GraduationCapIcon, LogOutIcon, MessageSquareTextIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { cn, LanguageSelect, Logo, PageTransition, Progress, staggerStyle, ThemeSwitch, TopLoader, useAuth } from "@mezon/web-kit";

import { useUsage } from "@/lib/queries";

function useNav() {
  const { t } = useTranslation();
  return [
    { to: "/chat", label: t("Savol-javob"), icon: MessageSquareTextIcon, end: true },
    { to: "/cases", label: t("Ish tahlili"), icon: BriefcaseIcon },
    { to: "/templates", label: t("Hujjatlar"), icon: FileTextIcon },
    { to: "/laws", label: t("Qonunlar"), icon: BookOpenIcon },
    { to: "/student", label: t("Akademiya (Talabalar)"), icon: GraduationCapIcon },
    { to: "/billing", label: t("Tarif"), icon: CreditCardIcon },
  ];
}

function initials(name?: string | null) {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "") || "M";
}

export function Avatar({ name, className }: { name?: string | null; className?: string }) {
  return (
    <span className={cn("grid size-9 shrink-0 place-items-center rounded-full bg-primary/10 text-[13px] font-semibold text-primary", className)}>
      {initials(name)}
    </span>
  );
}

/** Yon paneldagi tarif: nomi va birinchi limit (masalan, "Ish tahlili — 4 / 10") */
function PlanMini() {
  const { t } = useTranslation();
  const { data } = useUsage();
  if (!data) return null;
  const row = data.usage[0];
  return (
    <Link to="/billing" className="block rounded-lg px-3 py-3 hover:bg-subtle">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="truncate font-medium text-ink">{data.plan_name}</span>
        {data.unlimited && <span className="text-xs text-green">{t("Cheklovsiz")}</span>}
      </div>
      {row && (
        <>
          <div className="mt-1.5 flex justify-between gap-2 text-xs text-muted">
            <span className="truncate">{row.label}</span>
            <span className="tabular-nums">
              {row.used} / {row.limit}
            </span>
          </div>
          <Progress className="mt-1.5 h-1.5" value={(row.used / Math.max(row.limit, 1)) * 100} tone={row.used >= row.limit ? "red" : "blue"} />
        </>
      )}
    </Link>
  );
}

export function AppShell() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const nav = useNav();

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[264px_minmax(0,1fr)]">
      {/* Desktop: yon panel */}
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface px-4 py-6 lg:flex">
        <Logo to="/chat" className="px-2" />
        <nav className="mt-8 flex flex-col gap-1">
          {nav.map(({ to, label, icon: Icon, end }, i) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              style={staggerStyle(i, 40)}
              className={({ isActive }) =>
                cn(
                  "animate-in-up flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] text-muted transition-colors hover:bg-subtle hover:text-ink",
                  isActive && "bg-subtle font-medium text-ink [&_svg]:text-primary",
                )
              }
            >
              <Icon className="size-[18px]" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-3">
          <PlanMini />
          <div className="border-t border-line pt-4">
            <Link to="/profile" className="flex items-center gap-3 rounded-lg p-2 hover:bg-subtle">
              <Avatar name={user?.full_name} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink">{user?.full_name}</span>
                <span className="block truncate text-xs text-muted">{user?.role_label}</span>
              </span>
            </Link>
          </div>
          <LanguageSelect className="w-full" />
          <div className="flex items-center justify-between gap-2">
            <ThemeSwitch compact />
            <button
              onClick={() => void logout()}
              title={t("Chiqish")}
              aria-label={t("Chiqish")}
              className="grid size-9 place-items-center rounded-lg text-muted hover:bg-red/10 hover:text-red"
            >
              <LogOutIcon className="size-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobil: yuqori panel */}
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-surface/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <Logo to="/chat" compact />
        <Link to="/profile" aria-label={t("Profil")} className="ml-auto">
          <Avatar name={user?.full_name} className="size-8" />
        </Link>
      </header>

      <TopLoader />
      <main className="min-w-0 pb-24 lg:pb-0">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>

      {/* Mobil: pastki navigatsiya */}
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-6 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn("flex flex-col items-center gap-1 py-2.5 text-xs text-muted", isActive && "font-medium text-primary")
            }
          >
            <Icon className="size-5" />
            <span className="max-w-full truncate px-1">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
