import { AnimatePresence, motion } from "framer-motion";
import { Compass, Dna, History, ListMusic, Settings } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router";

import { HealthDot } from "@/components/HealthDot";
import { Logo } from "@/components/Logo";
import { SpotifyStatus } from "@/components/SpotifyStatus";
import { Badge } from "@/components/ui/badge";
import { DEMO_MODE } from "@/lib/api/services";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const NAV = [
  { to: "/", label: "Discover", icon: Compass, end: true },
  { to: "/dna", label: "My Music DNA", icon: Dna },
  { to: "/results", label: "Playlist", icon: ListMusic, needsSession: true },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Layout() {
  const location = useLocation();
  const { session } = useApp();
  const items = NAV.filter((item) => !item.needsSession || session);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-line bg-surface/70 px-4 py-6 lg:flex">
        <div className="flex items-center gap-3 px-2">
          <Logo />
          <div>
            <div className="font-display text-2xl leading-none text-ink">Muse</div>
            <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-soft">mood-aware music</div>
          </div>
        </div>
        <nav className="mt-10 flex flex-col gap-1" aria-label="Main">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition",
                  isActive ? "text-plum" : "text-ink-soft hover:bg-lavender-faint hover:text-ink",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-2xl bg-lavender-soft"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  <Icon className="relative size-[18px]" />
                  <span className="relative">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-3">
          {DEMO_MODE && <Badge variant="amber">Demo data, no backend</Badge>}
          <SpotifyStatus />
          <div className="px-1">
            <HealthDot />
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-canvas/85 px-4 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center gap-2">
            <Logo className="size-8" />
            <span className="font-display text-xl">Muse</span>
          </div>
          <SpotifyStatus compact />
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-28 pt-6 sm:px-8 lg:pb-12 lg:pt-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="hidden px-8 pb-6 text-xs text-ink-soft lg:block">
          Muse suggests music for how you feel. It is not a health tool, and the words you type are never stored.
        </footer>

        <nav
          className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-line bg-surface/95 px-2 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-2 backdrop-blur lg:hidden"
          aria-label="Main"
        >
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1 text-[11px] font-medium",
                  isActive ? "text-plum" : "text-ink-soft",
                )
              }
            >
              <Icon className="size-5" />
              {label.replace("My ", "")}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
