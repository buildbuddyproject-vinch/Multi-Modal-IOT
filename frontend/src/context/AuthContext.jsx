// Replaces dashboard/auth.py's Flask-session-cookie approach. Auth state
// lives in a JS variable (React state) backed by localStorage for persistence
// across refreshes -- reading it is synchronous and client-side only, so
// there's no server round-trip involved in deciding what to render. This is
// the core reason the login-page-behind-authenticated-sidebar glitch from the
// Dash version can't happen here: no race between a server-set session cookie
// and a separate client-side router is possible when both live in the same
// JS memory space.
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import * as api from "../api/client";

const STORAGE_KEY = "sepsis_icu_auth";
const AuthContext = createContext(null);

function readStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(readStoredAuth);

  const login = useCallback(async (username, password) => {
    const data = await api.login(username, password); // { access_token, username, role }
    const next = { token: data.access_token, username: data.username, role: data.role };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setAuth(next);
    return next;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }, []);

  const value = useMemo(
    () => ({
      token: auth?.token ?? null,
      username: auth?.username ?? null,
      role: auth?.role ?? null,
      isAuthenticated: Boolean(auth?.token),
      isAdmin: auth?.role === "admin",
      login,
      logout,
    }),
    [auth, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
