import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router";

import { RouteError, Spinner, useAuth, safeNext } from "@mezon/web-kit";

import { AppShell } from "@/components/layout/AppShell";
import { BillingPage } from "@/pages/BillingPage";
import { CasesPage } from "@/pages/cases/CasesPage";
import { ChatPage } from "@/pages/chat/ChatPage";
import { LandingPage } from "@/pages/LandingPage";
import { LoginPage, RegisterPage } from "@/pages/auth/AuthPages";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { StudentPage } from "@/pages/student/StudentPage";
import { TemplateFillPage } from "@/pages/templates/TemplateFillPage";
import { TemplatesPage } from "@/pages/templates/TemplatesPage";

function FullScreenSpinner() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <Spinner className="size-6" />
    </div>
  );
}

/** "/" — kirmagan foydalanuvchi uchun ommaviy bosh sahifa; kirgan foydalanuvchi uchun /chat ga yoʻnaltirish */
function HomeRoute() {
  const { status } = useAuth();
  if (status === "loading") return <FullScreenSpinner />;
  if (status === "authenticated") return <Navigate to="/chat" replace />;
  return <LandingPage />;
}

/** Faqat kirganlar uchun; kirmagan — /login?next=... */
function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullScreenSpinner />;
  if (status === "anonymous") {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }
  return <Outlet />;
}

/** Kirgan foydalanuvchi login/register ga kirmaydi */
function GuestOnly() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullScreenSpinner />;
  // kirgach — so'ralgan sahifaga (?next=), login sahifasi o'zi yo'naltirib ulgurmaydi
  if (status === "authenticated") return <Navigate to={safeNext(new URLSearchParams(location.search).get("next"), "/chat")} replace />;
  return <Outlet />;
}

export const router = createBrowserRouter([
  { path: "/", element: <HomeRoute />, errorElement: <RouteError /> },
  {
    element: <GuestOnly />,
    errorElement: <RouteError />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    errorElement: <RouteError />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/chat", element: <ChatPage /> },
          { path: "/cases", element: <CasesPage /> },
          // pdf.js (~1 MB) faqat ish sahifasi ochilganda yuklanadi
          { path: "/cases/:id", lazy: async () => ({ Component: (await import("@/pages/cases/CaseDetailPage")).CaseDetailPage }) },
          { path: "/templates", element: <TemplatesPage /> },
          { path: "/templates/:id", element: <TemplateFillPage /> },
          { path: "/laws", lazy: async () => ({ Component: (await import("@/pages/laws/LawsPage")).LawsPage }) },
          { path: "/student", element: <StudentPage /> },
          { path: "/billing", element: <BillingPage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
