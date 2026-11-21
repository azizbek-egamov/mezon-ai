import { cn, LanguageSelect, Logo, PageTransition, staggerStyle, ThemeSwitch, TopLoader, useAuth } from "@mezon/web-kit";
import {
  ActivityIcon, CreditCardIcon, FileCheckIcon, LayoutDashboardIcon, LogOutIcon, MenuIcon, RadarIcon, RefreshCwIcon,
  ScrollTextIcon, TagsIcon, UsersIcon, XIcon,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";

import { useStaff } from "@/lib/admin";

function useNav() {
  const { t } = useTranslation();
  const staff = useStaff();
  const all = [
    { to: "/", label: t("Boshqaruv paneli"), icon: LayoutDashboardIcon, end: true, superadmin: true },
    { to: "/users", label: t("Foydalanuvchilar"), icon: UsersIcon, superadmin: true },
    { to: "/plans", label: t("Tariflar"), icon: TagsIcon, superadmin: true },
    { to: "/payments", label: t("Toʻlovlar"), icon: CreditCardIcon, superadmin: true },
    { to: "/costs", label: t("AI xarajatlari"), icon: ActivityIcon, superadmin: true },
    { to: "/antifraud", label: t("Shubhali faollik"), icon: RadarIcon, superadmin: true },
    { to: "/templates", label: t("Shablon moderatsiyasi"), icon: FileCheckIcon, superadmin: false },
    { to: "/sync", label: t("lex.uz sinxronizatsiyasi"), icon: RefreshCwIcon, superadmin: false },
    { to: "/audit", label: t("Amallar jurnali"), icon: ScrollTextIcon, superadmin: true },
  ];
  return all.filter((item) => !item.superadmin || staff.data?.is_superadmin);
}

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const nav = useNav();
  return (
    <nav className="flex flex-col gap-1">
      {nav.map(({ to, label, icon: Icon, end }, i) => (
        <NavLink key={to} to={to} end={end} onClick={onNavigate} style={staggerStyle(i, 40)}
          className={({ isActive }) => cn(
            "animate-in-up flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] text-muted transition-colors hover:bg-subtle hover:text-ink",
            isActive && "bg-subtle font-medium text-ink [&_svg]:text-primary",
          )}>
          <Icon className="size-[18px]" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AdminShell() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const footer = (
    <div className="mt-auto flex flex-col gap-3 border-t border-line pt-4">
      <div className="px-2">
        <div className="truncate text-sm font-medium">{user?.full_name}</div>
        <div className="truncate text-xs text-muted">{user?.role_label}</div>
      </div>
      <LanguageSelect className="w-full" />
      <div className="flex items-center justify-between gap-2">
        <ThemeSwitch compact />
        <button onClick={() => void logout()} title={t("Chiqish")} aria-label={t("Chiqish")} className="grid size-9 place-items-center rounded-lg text-muted hover:bg-red/10 hover:text-red">
          <LogOutIcon className="size-4" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[264px_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh flex-col gap-8 overflow-y-auto border-r border-line bg-surface px-4 py-6 lg:flex">
        <Logo subtitle={t("Boshqaruv paneli")} className="px-2" />
        <Nav />
        {footer}
      </aside>

      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-surface/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <button onClick={() => setOpen(true)} aria-label="Menu" className="rounded-lg p-1.5 text-muted hover:bg-subtle hover:text-ink"><MenuIcon className="size-5" /></button>
        <Logo compact />
      </header>
      {open && (
        <div className="animate-in-fade fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={() => setOpen(false)}>
          <aside className="animate-in-left flex h-full w-72 flex-col gap-6 overflow-y-auto border-r border-line bg-surface p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <Logo compact />
              <button onClick={() => setOpen(false)} aria-label="×" className="rounded p-1 text-muted"><XIcon className="size-5" /></button>
            </div>
            <Nav onNavigate={() => setOpen(false)} />
            {footer}
          </aside>
        </div>
      )}

      <TopLoader />
      <main className="min-w-0 px-5 py-10 sm:px-8 lg:px-10">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  );
}

/** Sahifa sarlavhasi (serif) + izoh + amallar */
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end gap-4">
      <div className="min-w-0 flex-1">
        <h1 className="font-serif text-[30px] font-semibold leading-tight">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-[15px] text-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}
