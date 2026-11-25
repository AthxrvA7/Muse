import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/services";
import type { MuseSession, ReadyStatus, User } from "@/lib/types";

/** What the listener has chosen on Discover, waiting to be curated. */
export interface CurationDraft {
  chips: string[];
  text: string;
  intention: string;
  size: number;
  familiarity: number | null; // null: the mode's default
  exclude: string[]; // tracks to leave out next time (Give me another)
}

interface AppState {
  user: User | null | undefined; // undefined while checking
  loginAvailable: boolean;
  ready: ReadyStatus | "checking";
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
  draft: CurationDraft;
  setDraft: (draft: CurationDraft) => void;
  session: MuseSession | null;
  setSession: (session: MuseSession | null) => void;
  recentSessions: MuseSession[];
}

const AppContext = createContext<AppState | null>(null);

const SESSION_KEY = "muse.session";
const RECENT_KEY = "muse.recent";
const EMPTY_DRAFT: CurationDraft = { chips: [], text: "", intention: "match", size: 15, familiarity: null, exclude: [] };

// Browser storage is a convenience only: it can be unavailable, so every access is guarded.
function load<T>(storage: () => Storage, key: string, fallback: T): T {
  try {
    const raw = storage().getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function save(storage: () => Storage, key: string, value: unknown) {
  try {
    storage().setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: keep working in memory */
  }
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [loginAvailable, setLoginAvailable] = useState(true);
  const [ready, setReady] = useState<ReadyStatus | "checking">("checking");
  const [draft, setDraft] = useState<CurationDraft>(EMPTY_DRAFT);
  const [session, setSessionState] = useState<MuseSession | null>(() => load(() => sessionStorage, SESSION_KEY, null));
  // The text typed about a mood is never kept: recent sessions store only chips and results
  const [recentSessions, setRecent] = useState<MuseSession[]>(() => load(() => localStorage, RECENT_KEY, []));

  const refreshUser = useCallback(async () => {
    try {
      setUser(await api.auth.me());
    } catch (error) {
      setUser(null);
      setLoginAvailable(!(error instanceof ApiError) || error.status !== 503);
    }
  }, []);

  useEffect(() => {
    api.auth
      .me()
      .then(setUser)
      .catch((error: unknown) => {
        setUser(null);
        setLoginAvailable(!(error instanceof ApiError) || error.status !== 503);
      });
    let cancelled = false;
    const check = () => api.health.ready().then((status) => !cancelled && setReady(status));
    check();
    const timer = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const setSession = useCallback((next: MuseSession | null) => {
    setSessionState(next);
    save(() => sessionStorage, SESSION_KEY, next);
    if (next) {
      setRecent((current) => {
        const stripped = { ...next, request: { ...next.request, text: "", exclude: [] } };
        const updated = [stripped, ...current.filter((s) => s.id !== next.id)].slice(0, 6);
        save(() => localStorage, RECENT_KEY, updated);
        return updated;
      });
    }
  }, []);

  const logout = useCallback(async () => {
    await api.auth.logout().catch(() => undefined);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loginAvailable, ready, refreshUser, logout, draft, setDraft, session, setSession, recentSessions }),
    [user, loginAvailable, ready, refreshUser, logout, draft, session, setSession, recentSessions],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useApp(): AppState {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppStateProvider");
  return context;
}
