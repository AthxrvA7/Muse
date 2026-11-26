import { AnimatePresence, motion } from "framer-motion";
import { Compass, Disc3, Dna, History, ListMusic, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import { HealthDot } from "@/components/HealthDot";
import { Logo } from "@/components/Logo";
import { NowPlaying } from "@/components/NowPlaying";
import { SpotifyStatus } from "@/components/SpotifyStatus";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Badge } from "@/components/ui/badge";
import { DEMO_MODE } from "@/lib/api/services";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const NAV = [
  { to: "/", label: "Discover", hint: "Tell Muse how you feel", icon: Compass, end: true },
  { to: "/dna", label: "My Music DNA", hint: "Your taste, your way", icon: Dna },
  { to: "/results", label: "Playlist", hint: "Your latest mix", icon: ListMusic, needsSession: true },
  { to: "/history", label: "History", hint: "Past moods and mixes", icon: History },
  { to: "/rewind", label: "Rewind", hint: "Your month, wrapped", icon: Disc3 },
  { to: "/settings", label: "Settings", hint: "Account and privacy", icon: Settings },
];

/** Three lines that fold into an X. */
function Burger({ open }: { open: boolean }) {
  const line = "absolute left-0 h-0.5 w-5 rounded-full bg-current";
  return (
    <span className="relative block h-4 w-5">
      <motion.span className={line} animate={open ? { top: 7, rotate: 45 } : { top: 0, rotate: 0 }} />
      <motion.span className={line} style={{ top: 7 }} animate={{ opacity: open ? 0 : 1, scaleX: open ? 0.2 : 1 }} />
      <motion.span className={line} animate={open ? { top: 7, rotate: -45 } : { top: 14, rotate: 0 }} />
    </span>
  );
}

export function Layout() {
  const location = useLocation();
  const { session } = useApp();
  const [open, setOpen] = useState(false);
  const items = NAV.filter((item) => !item.needsSession || session);

  // A new page starts at the top (the router keeps the old scroll position otherwise)
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="grain min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line/70 bg-canvas/75 pt-[env(safe-area-inset-top)] backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <motion.button
            type="button"
            onClick={() => setOpen((o) => !o)}
            whileTap={{ scale: 0.88 }}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="grid size-10 place-items-center rounded-full text-ink transition hover:bg-lavender-faint"
          >
            <Burger open={open} />
          </motion.button>
          <Link to="/" className="group flex items-center gap-2.5" onClick={() => setOpen(false)}>
            <Logo className="size-9" />
            <span className="font-display text-2xl leading-none tracking-tight text-ink">Muse</span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            {DEMO_MODE && <Badge variant="amber" className="hidden sm:inline-flex">Demo data</Badge>}
            <ThemeToggle />
            <div className="hidden sm:block">
              <SpotifyStatus compact />
            </div>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              key="shade"
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
            />
            <motion.aside
              key="drawer"
              className="fixed inset-y-0 left-0 z-50 flex w-[19rem] max-w-[85vw] flex-col border-r border-line bg-surface px-4 py-5 shadow-lift"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 36 }}
              aria-label="Menu"
            >
              <div className="flex items-center gap-3 px-2">
                <Logo className="size-11" spinning />
                <div>
                  <div className="font-display text-2xl leading-none">Muse</div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.16em] text-ink-soft">music for how you feel</div>
                </div>
              </div>
              <nav className="mt-8 flex flex-col gap-1" aria-label="Main">
                {items.map(({ to, label, hint, icon: Icon, end }, i) => (
                  <motion.div
                    key={to}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 + i * 0.04 }}
                  >
                    <NavLink
                      to={to}
                      end={end}
                      onClick={() => setOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          "group flex items-center gap-3 rounded-2xl px-3 py-3 transition",
                          isActive ? "bg-lavender-soft text-plum" : "text-ink hover:bg-lavender-faint",
                        )
                      }
                    >
                      <span className="grid size-9 place-items-center rounded-xl bg-canvas transition group-hover:-rotate-6 group-hover:scale-110">
                        <Icon className="size-[18px]" />
                      </span>
                      <span>
                        <span className="block text-sm font-semibold">{label}</span>
                        <span className="block text-xs text-ink-soft">{hint}</span>
                      </span>
                    </NavLink>
                  </motion.div>
                ))}
              </nav>
              <div className="mt-auto space-y-3">
                {DEMO_MODE && <Badge variant="amber">Demo data, no backend</Badge>}
                <SpotifyStatus />
                <div className="px-1">
                  <HealthDot />
                </div>
                <p className="px-1 text-[11px] leading-relaxed text-ink-soft">
                  Muse suggests music for how you feel. It is not a health tool, and the words you type are never stored.
                </p>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* pb-28 leaves room for the mini player */}
      <main className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 sm:px-6 lg:pt-10">
        {/* Pages only fade in (no exit animation): with exit animations, leaving a page whose
            exit never finished left the next page stuck invisible. No blur and no lasting
            transform either, so pages aren't separate layers and position: fixed works. */}
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0, transitionEnd: { transform: "none" } }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <Outlet />
        </motion.div>
      </main>
      <NowPlaying />
    </div>
  );
}
