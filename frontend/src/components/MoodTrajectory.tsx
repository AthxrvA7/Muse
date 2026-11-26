import { AnimatePresence, motion } from "framer-motion";
import { ChartSpline, Loader2, Map as MapIcon, Pause, Play, RotateCcw, Trash2, Waypoints } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import { MOOD_EMOJI } from "@/lib/moods";
import { dayPartInsight, moodHue, quadrant, summarise } from "@/lib/trajectory";
import type { MoodPoint, MoodTrajectory as Trajectory } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const RANGES = [7, 30, 90];
const SIZE = 340;
const PAD = 26;

const BRIGHTNESS: Record<string, string> = { lighter: "↗ Getting lighter", heavier: "↘ Heavier lately", steady: "→ Holding steady" };
const ENERGY: Record<string, string> = { "more energetic": "⚡ More energy lately", calmer: "🌙 Winding down", steady: "" };

const colour = (p: { valence: number }, alpha = 1) => `hsl(${moodHue(p.valence)} 70% 58% / ${alpha})`;
const when = (at: string) =>
  new Date(at).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const words = (p: MoodPoint) => p.labels.slice(0, 3).map((l) => `${MOOD_EMOJI[l] ?? ""} ${l}`.trim()).join(" · ") || "your words";

/** Moods over time on the History page: one point per playlist curated. Never the text. */
export function MoodTrajectory() {
  const { user, recentSessions } = useApp();
  const [days, setDays] = useState(30);
  const [view, setView] = useState<"map" | "time">("map");
  const [remote, setRemote] = useState<{ days: number; data: Trajectory } | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const [replay, setReplay] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [now] = useState(() => Date.now());

  useEffect(() => {
    if (!user) return;
    let live = true;
    api.moods
      .trajectory(days)
      .then((data) => live && setRemote({ days, data }))
      .catch(() => live && setRemote({ days, data: summarise([], days) }));
    return () => {
      live = false;
    };
  }, [user, days]);

  const local = useMemo(() => {
    if (user) return null;
    const since = now - days * 86400000;
    const points: MoodPoint[] = recentSessions
      .filter((s) => new Date(s.created_at).getTime() >= since)
      .map((s) => ({ at: s.created_at, valence: s.preview.mood.valence, energy: s.preview.mood.energy, labels: s.preview.mood.labels, mode: s.preview.mood.mode }));
    return summarise(points, days);
  }, [user, recentSessions, days, now]);

  const data = user ? (remote?.days === days ? remote.data : null) : local;
  const points = useMemo(() => data?.points ?? [], [data]);
  const insight = useMemo(() => dayPartInsight(points), [points]);
  const shown = active !== null && points[active] ? points[active] : points[points.length - 1];

  async function setEnabled(enabled: boolean) {
    setSwitching(true);
    try {
      await api.moods.setEnabled(enabled);
      setRemote((current) => (current ? { ...current, data: { ...current.data, enabled } } : current));
      toast.success(enabled ? "Mood trajectory is on" : "Mood trajectory paused", {
        description: enabled ? "Each playlist you curate adds a point." : "New playlists won't add points. What's here stays until you clear it.",
      });
    } catch (e) {
      toast.error("Couldn't change that", { description: (e as Error).message });
    } finally {
      setSwitching(false);
    }
  }

  async function clear() {
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 4000);
      return;
    }
    setClearing(true);
    try {
      await api.moods.clear();
      setRemote((current) => ({ days, data: { ...summarise([], days), enabled: current?.data.enabled } }));
      setActive(null);
      toast.success("Mood history cleared", { description: "The trajectory starts again from your next playlist." });
    } catch (e) {
      toast.error("Couldn't clear your mood history", { description: (e as Error).message });
    } finally {
      setClearing(false);
      setConfirming(false);
    }
  }

  return (
    <Card className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2"><Waypoints className="size-4 text-plum" /> Mood trajectory</CardTitle>
          <CardDescription>
            Where your moods sat each time you curated. Only the mood’s position and mood words are kept, never what you typed.
            {!user && " From this browser — log in to keep it across devices."}
          </CardDescription>
        </div>
        <div className="flex gap-1.5">
          {RANGES.map((d) => (
            <button key={d} type="button" onClick={() => { setDays(d); setActive(null); }} aria-pressed={days === d}
              className={cn("rounded-full px-3 py-1.5 text-xs font-medium transition", days === d ? "bg-plum text-on-accent" : "bg-lavender-faint text-ink-soft hover:text-ink")}>
              {d} days
            </button>
          ))}
        </div>
      </div>

      {!data ? (
        <div className="flex h-40 items-center justify-center"><Loader2 className="size-5 animate-spin text-ink-soft" /></div>
      ) : user && data.enabled === false && points.length === 0 ? (
        <div className="flex flex-col items-start gap-3 rounded-2xl bg-lavender-faint p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-soft">
            Turn it on and each playlist you curate adds a point: where the mood sat and its mood words. Kept 90 days, never your text. Pause or clear it any time.
          </p>
          <Button size="sm" onClick={() => setEnabled(true)} disabled={switching} className="shrink-0">
            {switching ? <Loader2 className="animate-spin" /> : <Play />} Turn on
          </Button>
        </div>
      ) : points.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line p-6 text-center text-sm text-ink-soft">
          No moods in the last {days} days yet. Curate a playlist and your first point lands here.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-1.5 text-xs">
            <Chip>{points.length} mood{points.length === 1 ? "" : "s"} in {days} days</Chip>
            {data.top_labels[0] && <Chip>Mostly {MOOD_EMOJI[data.top_labels[0].label]} {data.top_labels[0].label}</Chip>}
            {data.brightness && <Chip tone={data.brightness === "lighter" ? "good" : undefined}>{BRIGHTNESS[data.brightness]}</Chip>}
            {data.energy && ENERGY[data.energy] && <Chip>{ENERGY[data.energy]}</Chip>}
            {insight && <Chip>🕰️ {insight}</Chip>}
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="inline-flex rounded-full bg-lavender-faint p-1 text-xs">
              {([["map", "Mood map", MapIcon], ["time", "Over time", ChartSpline]] as const).map(([id, label, Icon]) => (
                <button key={id} type="button" onClick={() => setView(id)} aria-pressed={view === id}
                  className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-medium transition", view === id ? "bg-surface text-ink shadow-soft" : "text-ink-soft hover:text-ink")}>
                  <Icon className="size-3.5" /> {label}
                </button>
              ))}
            </div>
            {view === "map" && points.length > 1 && (
              <button type="button" onClick={() => setReplay((r) => r + 1)} className="inline-flex items-center gap-1 text-xs text-ink-soft transition hover:text-plum">
                <RotateCcw className="size-3.5" /> Replay
              </button>
            )}
          </div>

          <AnimatePresence mode="wait">
            {view === "map" ? (
              <motion.div key="map" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="grid gap-5 md:grid-cols-[minmax(0,360px)_1fr] md:items-center">
                <div className="space-y-2">
                  <MoodMap points={points} average={data.average} active={active} onActive={setActive} replay={replay} />
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-soft">
                    <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-plum" /> latest (pulsing)</span>
                    <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full border border-dashed border-ink-soft" /> your usual mood</span>
                    <span>faded = older · colour = mood, as on covers</span>
                  </div>
                </div>
                {shown && <Detail point={shown} latest={shown === points[points.length - 1]} />}
              </motion.div>
            ) : (
              <motion.div key="time" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                <OverTime points={points} />
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4">
            <p className="text-xs text-ink-soft">
              A picture of the moods you chose, not a diagnosis.{user && data.enabled === false && " Paused: new playlists aren't added."}
            </p>
            {user && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setEnabled(data.enabled === false)} disabled={switching}>
                  {switching ? <Loader2 className="animate-spin" /> : data.enabled === false ? <Play /> : <Pause />} {data.enabled === false ? "Resume" : "Pause"}
                </Button>
                <Button variant="outline" size="sm" onClick={clear} disabled={clearing} className={cn(confirming && "border-danger text-danger")}>
                  {clearing ? <Loader2 className="animate-spin" /> : <Trash2 />} {confirming ? "Tap again to clear" : "Clear mood history"}
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </Card>
  );
}

function Chip({ children, tone }: { children: ReactNode; tone?: "good" }) {
  return (
    <motion.span initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} whileHover={{ y: -2 }}
      className={cn("rounded-full px-3 py-1 font-medium", tone === "good" ? "bg-sage-soft text-moss" : "bg-lavender-faint text-ink")}>
      {children}
    </motion.span>
  );
}

function Detail({ point, latest }: { point: MoodPoint; latest: boolean }) {
  return (
    <motion.div key={point.at} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="space-y-3 rounded-2xl p-5" style={{ background: colour(point, 0.14) }}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-soft">{latest ? "Most recent" : when(point.at)}</p>
      <p className="font-display text-2xl capitalize">{words(point)}</p>
      <p className="text-sm text-ink-soft">
        {latest ? `${when(point.at)} · ` : ""}{quadrant(point.valence, point.energy)} · {point.mode} mix
      </p>
      <div className="space-y-2 text-xs">
        <Bar label="Positivity" value={point.valence} fill={colour(point)} />
        <Bar label="Energy" value={point.energy} fill="var(--c-sky)" />
      </div>
      <p className="text-xs text-ink-soft">Tap or hover a point on the map to look back.</p>
    </motion.div>
  );
}

function Bar({ label, value, fill }: { label: string; value: number; fill: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 text-ink-soft">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface/70">
        <motion.div className="h-full rounded-full" style={{ background: fill }} initial={{ width: 0 }} animate={{ width: `${Math.round(value * 100)}%` }} transition={{ type: "spring", stiffness: 120, damping: 18 }} />
      </div>
      <span className="w-9 text-right tabular-nums">{Math.round(value * 100)}%</span>
    </div>
  );
}

const toX = (v: number) => PAD + v * (SIZE - 2 * PAD);
const toY = (e: number) => PAD + (1 - e) * (SIZE - 2 * PAD);

function MoodMap({ points, average, active, onActive, replay }: {
  points: MoodPoint[];
  average: Trajectory["average"];
  active: number | null;
  onActive: (i: number | null) => void;
  replay: number;
}) {
  const path = points.map((p, i) => `${i ? "L" : "M"}${toX(p.valence).toFixed(1)},${toY(p.energy).toFixed(1)}`).join(" ");
  const last = points.length - 1;
  const mid = SIZE / 2;
  const corners = [
    { x: PAD + 6, y: PAD + 14, text: "tense & wired", anchor: "start" },
    { x: SIZE - PAD - 6, y: PAD + 14, text: "bright & lively", anchor: "end" },
    { x: PAD + 6, y: SIZE - PAD - 8, text: "low & slow", anchor: "start" },
    { x: SIZE - PAD - 6, y: SIZE - PAD - 8, text: "calm & content", anchor: "end" },
  ] as const;
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[360px] touch-none select-none" role="img" aria-label={`Mood map with ${points.length} moods, oldest to newest`} onMouseLeave={() => onActive(null)}>
      <defs>
        <linearGradient id="moodmap-bg" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="hsl(230 70% 60% / 0.12)" />
          <stop offset="100%" stopColor="hsl(30 80% 60% / 0.14)" />
        </linearGradient>
      </defs>
      <rect x={PAD} y={PAD} width={SIZE - 2 * PAD} height={SIZE - 2 * PAD} rx={18} fill="url(#moodmap-bg)" stroke="var(--c-line)" />
      <line x1={mid} y1={PAD} x2={mid} y2={SIZE - PAD} stroke="var(--c-line)" strokeDasharray="3 5" />
      <line x1={PAD} y1={mid} x2={SIZE - PAD} y2={mid} stroke="var(--c-line)" strokeDasharray="3 5" />
      {corners.map((c) => (
        <text key={c.text} x={c.x} y={c.y} textAnchor={c.anchor} fontSize={9.5} fill="var(--c-ink-soft)" opacity={0.85}>{c.text}</text>
      ))}
      <text x={mid} y={SIZE - 6} textAnchor="middle" fontSize={9.5} fill="var(--c-ink-soft)">positivity →</text>
      <text x={8} y={mid} textAnchor="middle" fontSize={9.5} fill="var(--c-ink-soft)" transform={`rotate(-90 8 ${mid})`}>energy →</text>

      {average && (
        <g>
          <title>Your usual mood (the average)</title>
          <circle cx={toX(average.valence)} cy={toY(average.energy)} r={14} fill="none" stroke="var(--c-ink-soft)" strokeDasharray="2 3" opacity={0.7} />
        </g>
      )}

      {points.length > 1 && (
        <motion.path key={`path-${replay}`} d={path} fill="none" stroke="var(--c-accent)" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" opacity={0.45}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: Math.min(0.25 * points.length, 2.4), ease: "easeInOut" }} />
      )}

      {points.map((p, i) => {
        const age = last ? i / last : 1;
        const isActive = active === i;
        return (
          <motion.g key={`${p.at}-${replay}`} initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: Math.min(0.25 * i, 2.4), type: "spring", stiffness: 260, damping: 16 }}>
            {i === last && (
              <motion.circle cx={toX(p.valence)} cy={toY(p.energy)} fill="none" stroke={colour(p)} strokeWidth={2}
                initial={{ r: 7, opacity: 0.7 }} animate={{ r: 17, opacity: 0 }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }} />
            )}
            <circle
              cx={toX(p.valence)} cy={toY(p.energy)} r={isActive ? 9 : i === last ? 7.5 : 4.5 + age * 2}
              fill={colour(p, 0.35 + age * 0.65)} stroke={isActive || i === last ? "var(--c-surface)" : "none"} strokeWidth={2}
              tabIndex={0} role="button" aria-label={`${when(p.at)}: ${p.labels.join(", ") || "your words"}`}
              className="cursor-pointer outline-none transition-[r] duration-200"
              onMouseEnter={() => onActive(i)} onFocus={() => onActive(i)} onClick={() => onActive(isActive ? null : i)}
            />
          </motion.g>
        );
      })}
    </svg>
  );
}

type Row = { t: number; valence: number; energy: number; point: MoodPoint };

function TimeTip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  if (!active || !payload?.length) return null;
  const { point } = payload[0].payload;
  return (
    <div className="rounded-xl bg-ink px-3 py-2 text-xs text-canvas shadow-lift">
      <div className="font-semibold capitalize">{words(point)}</div>
      <div>{when(point.at)}</div>
      <div>positivity {Math.round(point.valence * 100)}% · energy {Math.round(point.energy * 100)}%</div>
    </div>
  );
}

function OverTime({ points }: { points: MoodPoint[] }) {
  const rows: Row[] = points.map((p) => ({ t: new Date(p.at).getTime(), valence: p.valence, energy: p.energy, point: p }));
  return (
    <div className="h-64 w-full" role="img" aria-label="Positivity and energy of your moods over time">
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 10, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="var(--c-line)" strokeDasharray="4 4" vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(t: number) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
            tick={{ fill: "var(--c-ink-soft)", fontSize: 11 }} minTickGap={28} />
          <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={(v: number) => (v === 0 ? "low" : v === 1 ? "high" : "mid")} tick={{ fill: "var(--c-ink-soft)", fontSize: 11 }} />
          <Tooltip content={<TimeTip />} cursor={{ stroke: "var(--c-line)" }} />
          <Line type="monotone" dataKey="valence" name="Positivity" stroke="var(--c-accent)" strokeWidth={2.5} dot={{ r: 3.5, fill: "var(--c-accent)" }} activeDot={{ r: 6 }} animationDuration={900} />
          <Line type="monotone" dataKey="energy" name="Energy" stroke="var(--c-sky)" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3, fill: "var(--c-sky)" }} activeDot={{ r: 5 }} animationDuration={1100} />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex justify-center gap-4 text-xs text-ink-soft">
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-plum" /> Positivity</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-sky" /> Energy</span>
      </div>
    </div>
  );
}
