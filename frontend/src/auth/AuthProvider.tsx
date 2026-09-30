// Сессия пользователя: восстановление по refresh-cookie при загрузке, вход, выход.
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { logoutRequest, refreshSession } from "../api/client";
import { authApi } from "../api/endpoints";
import { session } from "../api/session";
import type { Me, TokenOut } from "../api/types";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "anonymous"; user: null }
  | { status: "authenticated"; user: Me };

type AuthContextValue = AuthState & {
  signIn: (tokens: TokenOut) => Promise<Me>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  const loadUser = useCallback(async () => {
    const user = await authApi.me();
    setState({ status: "authenticated", user });
    return user;
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      const restored = session.get() !== null || (await refreshSession());
      if (!active) return;
      if (!restored) return setState({ status: "anonymous", user: null });
      await loadUser().catch(() => active && setState({ status: "anonymous", user: null }));
    })();
    // refresh не удался посреди работы -> на экран входа
    const unsubscribe = session.subscribe(() => {
      if (session.get() === null) setState({ status: "anonymous", user: null });
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [loadUser]);

  const signIn = useCallback(
    async (tokens: TokenOut) => {
      session.set(tokens.access_token);
      return loadUser();
    },
    [loadUser],
  );

  const signOut = useCallback(async () => {
    await logoutRequest();
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(() => ({ ...state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth вне AuthProvider");
  return ctx;
}
