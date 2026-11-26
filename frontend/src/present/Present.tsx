import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/services";
import type { RoomSummary } from "@/lib/types";
import { useApp } from "@/state/AppState";

import { CREAM, INK, type Point, roomPersonality } from "./parts";
import { SLIDES, type DeckContext, type Room } from "./slides";

const W = 1600;
const H = 900;
const FAKE_CHIPS = [["happy"], ["tired", "low"], ["stressed", "anxious"], ["calm"], ["hyped", "energetic"], ["focused"], ["nostalgic", "dreamy"], ["bored"], ["confident", "happy"], ["relaxed"]];
const FAKE_POINTS: Record<string, [number, number]> = {
  happy: [0.85, 0.65], tired: [0.35, 0.15], low: [0.2, 0.25], stressed: [0.2, 0.75], anxious: [0.25, 0.7], calm: [0.7, 0.2],
  hyped: [0.85, 0.9], energetic: [0.75, 0.85], focused: [0.6, 0.55], nostalgic: [0.5, 0.3], dreamy: [0.6, 0.3], bored: [0.35, 0.2],
  confident: [0.8, 0.7], relaxed: [0.75, 0.2],
};

/** Rehearsal votes, made on this laptop only (never sent to the server). */
function fakeVotes(n: number): Point[] {
  return Array.from({ length: n }, (_, i) => {
    const labels = FAKE_CHIPS[(i * 7) % FAKE_CHIPS.length];
    const pts = labels.map((l) => FAKE_POINTS[l]);
    const v = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const e = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    return { valence: v, energy: e, labels };
  });
}

function merge(summary: RoomSummary | null, fake: Point[]): Room | null {
  if (!summary) return null;
  if (!fake.length) return { ...summary, rehearsal: false };
  const points = [...summary.points, ...fake];
  const counts = new Map<string, number>();
  points.forEach((p) => p.labels.forEach((l) => counts.set(l, (counts.get(l) ?? 0) + 1)));
  const average = {
    valence: points.reduce((s, p) => s + p.valence, 0) / points.length,
    energy: points.reduce((s, p) => s + p.energy, 0) / points.length,
  };
  return {
    ...summary,
    voters: points.length,
    points,
    average,
    chips: [...counts.entries()].map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count),
    personality: roomPersonality(points),
    rehearsal: true,
  };
}

/** The live room: opened once per browser tab, polled every 2 seconds. */
function useRoom(loggedIn: boolean) {
  const [code, setCode] = useState<string | null>(() => sessionStorage.getItem("muse.room"));
  const [summary, setSummary] = useState<RoomSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fake, setFake] = useState<Point[]>([]);

  const open = useCallback(
    () =>
      api.rooms
        .create()
        .then(({ code: fresh }) => {
          sessionStorage.setItem("muse.room", fresh);
          setSummary(null);
          setCode(fresh);
          setError(null);
        })
        .catch((e: unknown) => {
          setError(e instanceof ApiError && e.status === 401 ? "Log in to Muse on this laptop to open a room." : (e as Error).message);
        }),
    [],
  );

  useEffect(() => {
    if (code || !loggedIn) return;
    api.rooms
      .create()
      .then(({ code: fresh }) => {
        sessionStorage.setItem("muse.room", fresh);
        setCode(fresh);
        setError(null);
      })
      .catch((e: unknown) => {
        setError(e instanceof ApiError && e.status === 401 ? "Log in to Muse on this laptop to open a room." : (e as Error).message);
      });
  }, [code, loggedIn]);

  useEffect(() => {
    if (!code) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let wait = 2000;
      try {
        const next = await api.rooms.get(code);
        if (live) {
          setSummary(next);
          setError(null);
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 404 && live) {
          sessionStorage.removeItem("muse.room"); // the server restarted: open a new room
          setCode(null);
          return;
        }
        wait = 5000; // busy network: back off, keep the last picture on screen
      }
      if (live) timer = setTimeout(poll, wait);
    };
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [code]);

  const room = useMemo(() => merge(summary, fake), [summary, fake]);
  const rehearse = useCallback(() => setFake((f) => (f.length ? [] : fakeVotes(18))), []);
  return { code, room, error, open, rehearse, setSummary };
}

function useFit() {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const fit = () => setScale(Math.min(window.innerWidth / W, window.innerHeight / H));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);
  return scale;
}

/** The interactive deck: a live room, live demos, arrow keys to move. Served at /app/#/present. */
export default function Present() {
  const { user } = useApp();
  const { code, room, error, open, rehearse, setSummary } = useRoom(!!user);
  const [index, setIndex] = useState(() => Math.min(Number(sessionStorage.getItem("muse.slide") ?? 0) || 0, SLIDES.length - 1));
  const [step, setStep] = useState(0);
  const [notes, setNotes] = useState(false);
  const [help, setHelp] = useState(false);
  const scale = useFit();
  const stage = useRef<HTMLDivElement>(null);
  const slide = SLIDES[index];

  useEffect(() => {
    sessionStorage.setItem("muse.slide", String(index));
    document.title = `Muse · ${slide.title}`;
  }, [index, slide.title]);

  const go = useCallback((to: number, toStep = 0) => {
    const target = Math.max(0, Math.min(SLIDES.length - 1, to));
    setIndex(target);
    setStep(toStep === -1 ? SLIDES[target].steps : toStep);
  }, []);
  const next = useCallback(() => (step < slide.steps ? setStep(step + 1) : index < SLIDES.length - 1 && go(index + 1)), [step, slide.steps, index, go]);
  const prev = useCallback(() => (step > 0 ? setStep(step - 1) : index > 0 && go(index - 1, -1)), [step, index, go]);

  const lock = useCallback(async () => {
    if (!code || !room) return;
    try {
      await api.rooms.lock(code, !room.locked);
      setSummary((s) => (s ? { ...s, locked: !room.locked } : s));
    } catch {
      /* the next poll shows the real state */
    }
  }, [code, room, setSummary]);
  const reset = useCallback(async () => {
    if (code && window.confirm("Clear every vote in this room?")) await api.rooms.reset(code).catch(() => undefined);
  }, [code]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest("input, textarea, select, [contenteditable=true]")) return; // typing in a demo
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const key = event.key.toLowerCase();
      if ((key === " " || key === "enter") && target.closest("button, a")) return; // pressing a demo button
      if (["arrowright", "pagedown", " ", "enter"].includes(key)) next();
      else if (["arrowleft", "pageup", "backspace"].includes(key)) prev();
      else if (key === "home") go(0);
      else if (key === "end") go(SLIDES.length - 1);
      else if (key === "n") setNotes((v) => !v);
      else if (key === "f") void (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen());
      else if (key === "r") rehearse();
      else if (key === "l") void lock();
      else if (key === "x") void reset();
      else if (key === "?") setHelp((v) => !v);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, go, rehearse, lock, reset]);

  const joinUrl = code ? `${window.location.origin}${window.location.pathname}#/join/${code}` : `${window.location.origin}${window.location.pathname}#/join`;
  const shortJoin = `${window.location.host}/app/#/join`;
  const context: DeckContext = { step, room, code, joinUrl, shortJoin, roomError: error, openRoom: open, loggedIn: !!user, next };

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ background: INK }}>
      <div
        ref={stage}
        className="absolute left-1/2 top-1/2 overflow-hidden"
        style={{ width: W, height: H, transform: `translate(-50%, -50%) scale(${scale})`, transformOrigin: "center" }}
      >
        <AnimatePresence mode="wait">
          <motion.section
            key={slide.id}
            initial={{ opacity: 0, scale: 0.98, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 1.02, y: -20 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="absolute inset-0"
            style={{ background: slide.bg, color: slide.fg }}
          >
            {slide.render(context)}
          </motion.section>
        </AnimatePresence>

        {/* Persistent join chip, so latecomers can still get in */}
        {index > 0 && code && (
          <div className="absolute right-6 top-6 z-20 flex items-center gap-3 rounded-full px-5 py-2 text-lg font-bold shadow-xl" style={{ background: CREAM, color: INK }}>
            <span className="size-3 animate-pulse rounded-full" style={{ background: room?.locked ? "#999" : "#13875A" }} />
            {room?.locked ? "Room locked" : <>Join: {shortJoin} · <span className="tracking-[0.2em]">{code}</span></>}
            <span className="opacity-60">· {room?.voters ?? 0} in{room?.rehearsal ? " (rehearsal)" : ""}</span>
          </div>
        )}

        {/* Progress */}
        <div className="absolute inset-x-0 bottom-0 z-20 flex h-2">
          {SLIDES.map((s, i) => (
            <button key={s.id} type="button" title={s.title} onClick={() => go(i)} className="h-full flex-1 transition-opacity" style={{ background: i <= index ? "#FFC93C" : "rgba(255,244,230,0.18)", opacity: i === index ? 1 : 0.75 }} />
          ))}
        </div>
      </div>

      {notes && (
        <div className="fixed inset-x-4 bottom-4 z-30 max-h-[40vh] overflow-auto rounded-2xl p-5 text-lg leading-relaxed shadow-2xl" style={{ background: CREAM, color: INK }}>
          <div className="mb-2 text-sm font-bold uppercase tracking-widest opacity-60">
            Notes · {index + 1}/{SLIDES.length} · {slide.title} {slide.steps ? `· step ${step}/${slide.steps}` : ""}
          </div>
          {slide.notes}
        </div>
      )}
      {help && (
        <div className="fixed left-4 top-4 z-30 rounded-2xl p-5 text-base shadow-2xl" style={{ background: CREAM, color: INK }}>
          <div className="mb-2 font-bold">Keys</div>
          <div>→ / Space: next · ←: back · F: fullscreen · N: notes</div>
          <div>L: lock / unlock room · X: clear votes · R: rehearsal votes (this laptop only)</div>
        </div>
      )}
    </div>
  );
}
