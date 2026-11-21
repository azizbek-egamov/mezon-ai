import { Button, Card, RouteError, safeNext, Spinner, useAuth } from "@mezon/web-kit";
import { ShieldAlertIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router";

import { AdminShell } from "@/components/AdminShell";
import { useStaff } from "@/lib/admin";
import { AntiFraudPage } from "@/pages/AntiFraudPage";
import { AuditPage } from "@/pages/AuditPage";
import { CostsPage } from "@/pages/CostsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { PaymentsPage } from "@/pages/PaymentsPage";
import { PlansPage } from "@/pages/PlansPage";
import { SyncPage } from "@/pages/SyncPage";
import { TemplateEditPage, TemplatesPage } from "@/pages/TemplatesPage";
import { UserDetailPage, UsersPage } from "@/pages/UsersPage";

function FullScreenSpinner() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <Spinner className="size-6" />
    </div>
  );
}

function NoAccess() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  return (
    <div className="grid min-h-dvh place-items-center px-4">
      <Card accent="red" className="max-w-md p-6 text-center">
        <ShieldAlertIcon className="mx-auto size-8 text-red" />
        <h1 className="mt-3 text-lg font-semibold">{t("Admin panelga ruxsat yoʻq")}</h1>
        <p className="mt-1 text-sm text-muted">{t("Faqat yurist-moderator yoki superadmin uchun")}</p>
        <p className="mt-2 tabular-nums text-xs text-muted">{user?.phone_number} · {user?.role_label}</p>
        <Button variant="outline" className="mt-5" onClick={() => void logout()}>{t("Chiqish")}</Button>
      </Card>
    </div>
  );
}

/** Kirgan va xodim (MODERATOR / SUPERADMIN) bo'lishi shart */
function RequireStaff() {
  const { status } = useAuth();
  const location = useLocation();
  const staff = useStaff(status === "authenticated");
  if (status === "loading" || (status === "authenticated" && staff.isLoading)) return <FullScreenSpinner />;
  if (status === "anonymous") return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (!staff.data?.is_staff_role) return <NoAccess />;
  return <Outlet />;
}

/** Faqat superadmin sahifalari; moderator — shablonlarga */
function RequireSuperAdmin() {
  const staff = useStaff();
  return staff.data?.is_superadmin ? <Outlet /> : <Navigate to="/templates" replace />;
}

function GuestOnly() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullScreenSpinner />;
  // kirgach — so'ralgan sahifaga (?next=)
  return status === "authenticated" ? <Navigate to={safeNext(new URLSearchParams(location.search).get("next"))} replace /> : <Outlet />;
}

export const router = createBrowserRouter([
  { element: <GuestOnly />, errorElement: <RouteError />, children: [{ path: "/login", element: <LoginPage /> }] },
  {
    element: <RequireStaff />,
    errorElement: <RouteError />,
    children: [
      {
        element: <AdminShell />,
        children: [
          { path: "/templates", element: <TemplatesPage /> },
          { path: "/templates/:id", element: <TemplateEditPage /> },
          { path: "/sync", element: <SyncPage /> },
          {
            element: <RequireSuperAdmin />,
            children: [
              { path: "/", element: <DashboardPage /> },
              { path: "/users", element: <UsersPage /> },
              { path: "/users/:id", element: <UserDetailPage /> },
              { path: "/plans", element: <PlansPage /> },
              { path: "/payments", element: <PaymentsPage /> },
              { path: "/costs", element: <CostsPage /> },
              { path: "/antifraud", element: <AntiFraudPage /> },
              { path: "/audit", element: <AuditPage /> },
            ],
          },
          { path: "*", element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
// Production da admin panel veb-sayt bilan bitta domenda, /panel/ ostida (mezon_backend/config/urls.py)
], { basename: import.meta.env.PROD ? "/panel" : undefined });
