// Сессия пользователя: восстановление по refresh-cookie, вход, выход, синхронизация вкладок.
// Инвариант: данные в кэше запросов всегда принадлежат текущему пользователю — при любой
// смене пользователя (выход, вход, чужой токен после refresh в другой вкладке) кэш очищается.
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { onAuthEvent, broadcastAuth } from "../api/broadcast";
import { logoutRequest, refreshSession, tokenSubject } from "../api/client";
import { authApi } from "../api/endpoints";
import { session } from "../api/session";
import type { Me, TokenOut } from "../api/types";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "anonymous"; user: null }
  | { status: "authenticated"; user: Me };

type AuthContextValue = AuthState & {
  signIn: (tokens: TokenOut) => Promise<Me>;
  /** Выход на сервере; beforeClear вызывается до очистки локальной сессии (навигация). */
  signOut: (beforeClear?: () => void) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });
  const userRef = useRef<Me | null>(null);

  const becomeAnonymous = useCallback(() => {
    userRef.current = null;
    queryClient.clear();
    setState({ status: "anonymous", user: null });
  }, [queryClient]);

  const loadUser = useCallback(async () => {
    const user = await authApi.me();
    if (userRef.current?.id !== user.id) queryClient.clear();
    userRef.current = user;
    setState({ status: "authenticated", user });
    return user;
  }, [queryClient]);

  const restore = useCallback(async () => {
    const outcome = session.get() !== null ? "ok" : await refreshSession();
    if (outcome !== "ok") return becomeAnonymous();
    await loadUser().catch(becomeAnonymous);
  }, [becomeAnonymous, loadUser]);

  useEffect(() => {
    void restore();
    const unsubscribeSession = session.subscribe(() => {
      const token = session.get();
      if (token === null) {
        if (userRef.current) becomeAnonymous();
        return;
      }
      // refresh выдал токен другого пользователя (вход в другой вкладке) — перечитываем
      const current = userRef.current;
      if (current && tokenSubject(token) !== current.id) void loadUser().catch(becomeAnonymous);
    });
    const unsubscribeTabs = onAuthEvent((event) => {
      if (event === "logout") session.clear();
      else void syncWithOtherTab();
    });
    // вход в другой вкладке: cookie уже новый — берём токен по нему; смену пользователя
    // обработает подписка на session (sub токена не совпадёт с текущим пользователем)
    async function syncWithOtherTab() {
      const outcome = await refreshSession();
      if (outcome === "invalid") becomeAnonymous();
      else if (outcome === "ok" && !userRef.current) await loadUser().catch(becomeAnonymous);
    }
    return () => {
      unsubscribeSession();
      unsubscribeTabs();
    };
  }, [becomeAnonymous, loadUser, restore]);

  const signIn = useCallback(
    async (tokens: TokenOut) => {
      userRef.current = null;
      queryClient.clear();
      session.set(tokens.access_token);
      const user = await loadUser();
      broadcastAuth("login");
      return user;
    },
    [loadUser, queryClient],
  );

  const signOut = useCallback(async (beforeClear?: () => void) => {
    await logoutRequest();
    beforeClear?.();
    broadcastAuth("logout");
    session.clear();
  }, []);

  const value = useMemo(() => ({ ...state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth вне AuthProvider");
  return ctx;
}
