import { ApiError, type Schemas } from "@mezon/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, logoutRemote, onSessionExpired, postJson, refreshSession, saveTokens } from "./api";

type User = Schemas["User"];
/** offline — server javob bermadi (kabel/tarmoq); sessiya saqlanadi, "Qayta urinish" bilan davom etadi */
type Status = "loading" | "anonymous" | "authenticated" | "offline";

export interface RegisterData {
  phone_number: string;
  full_name: string;
  role: "LAWYER" | "CLIENT";
  advocate_license_no: string;
  password1: string;
  password2: string;
  consent: boolean;
}

interface AuthValue {
  status: Status;
  user: User | null;
  login(phone: string, password: string): Promise<void>;
  register(data: RegisterData): Promise<void>;
  logout(): Promise<void>;
  reloadUser(): Promise<void>;
  /** offline holatdan: sessiyani qayta tiklashga urinish */
  retry(): Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

async function fetchMe(): Promise<User> {
  return (await (await api.raw("/auth/me")).json()) as User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  const signedOut = useCallback(() => {
    setUser(null);
    setStatus("anonymous");
    queryClient.clear();
  }, [queryClient]);

  const restore = useCallback(async () => {
    setStatus("loading");
    try {
      const token = await refreshSession();
      const me = token ? await fetchMe() : null;
      setUser(me);
      setStatus(me ? "authenticated" : "anonymous");
    } catch (error) {
      // 4xx — sessiya yaroqsiz (kirish kerak); tarmoq xatosi yoki 5xx — server vaqtincha yo'q
      setStatus(error instanceof ApiError && error.status < 500 ? "anonymous" : "offline");
    }
  }, []);

  useEffect(() => {
    void restore();
    return onSessionExpired(signedOut);
  }, [restore, signedOut]);

  const signedIn = useCallback(async (data: Schemas["TokenPair"]) => {
    await saveTokens(data);
    setUser(data.user);
    setStatus("authenticated");
    fetchMe().then(setUser).catch(() => undefined); // server matnlari profil tilida
  }, []);

  const value = useMemo<AuthValue>(() => ({
    status,
    user,
    login: async (phone, password) => signedIn(await postJson("/auth/login", { phone_number: phone, password })),
    register: async (data) => signedIn(await postJson("/auth/register", data)),
    logout: async () => {
      await logoutRemote();
      signedOut();
    },
    reloadUser: async () => {
      setUser(await fetchMe());
    },
    retry: restore,
  }), [status, user, signedIn, signedOut, restore]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider ichida");
  return ctx;
}

