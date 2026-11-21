import type { Schemas } from "@mezon/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, postJson, restoreSession, tokenStore } from "./api";

type User = Schemas["User"];
type Status = "loading" | "anonymous" | "authenticated";

export interface RegisterData {
  phone_number: string;
  full_name: string;
  role: "LAWYER" | "STUDENT" | "CLIENT";
  advocate_license_no?: string;
  university?: string;
  study_level?: string;
  student_id_no?: string;
  password1: string;
  password2: string;
  consent: boolean;
}

interface AuthContextValue {
  status: Status;
  user: User | null;
  login(phone: string, password: string): Promise<User>;
  register(data: RegisterData): Promise<User>;
  logout(): Promise<void>;
  updateMe(patch: Partial<Pick<User, "full_name" | "advocate_license_no" | "university" | "study_level" | "student_id_no" | "language">>): Promise<User>;
  /** Profilni serverdan qayta o'qish (masalan, til almashgach — rol nomi yangi tilda) */
  reloadUser(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  const signedIn = useCallback((data: Schemas["TokenPair"]) => {
    tokenStore.set(data.access);
    setUser(data.user);
    setStatus("authenticated");
    // Kirish so'rovi tokensiz — server matnlari (rol nomi) cookie/brauzer tilida bo'lishi mumkin; profil tilida qayta o'qiymiz
    void api.raw("/auth/me").then(async (r) => setUser((await r.json()) as User)).catch(() => undefined);
    return data.user;
  }, []);

  const signedOut = useCallback(() => {
    tokenStore.set(null);
    setUser(null);
    setStatus("anonymous");
    queryClient.clear(); // boshqa foydalanuvchining ma'lumotlari keshda qolmasin
  }, [queryClient]);

  useEffect(() => {
    let alive = true;
    restoreSession()
      .then((me) => {
        if (!alive) return;
        setUser(me);
        setStatus(me ? "authenticated" : "anonymous");
      })
      .catch(() => alive && setStatus("anonymous"));
    const off = tokenStore.onExpired(signedOut);
    return () => {
      alive = false;
      off();
    };
  }, [signedOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login: async (phone, password) =>
        signedIn(await postJson("/auth/login", { phone_number: phone, password, cookie: true })),
      register: async (data) => signedIn(await postJson("/auth/register", { ...data, cookie: true })),
      logout: async () => {
        await postJson("/auth/logout", {}).catch(() => undefined);
        signedOut();
      },
      updateMe: async (patch) => {
        const response = await api.raw("/auth/me", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch),
        });
        const me = (await response.json()) as User;
        setUser(me);
        return me;
      },
      reloadUser: async () => {
        if (!tokenStore.get()) return;
        setUser((await (await api.raw("/auth/me")).json()) as User);
      },
    }),
    [status, user, signedIn, signedOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider ichida ishlatilsin");
  return ctx;
}
