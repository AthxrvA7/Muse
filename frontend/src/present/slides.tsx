/* eslint-disable react-refresh/only-export-components -- the deck is data plus small demos */
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Play, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { type CSSProperties, type ReactNode, useEffect, useMemo, useState } from "react";

import { Logo } from "@/components/Logo";
import { TrackRow } from "@/components/TrackRow";
import { api } from "@/lib/api/services";
import { coverUrl } from "@/lib/cover";
import { MOOD_EMOJI } from "@/lib/moods";
import { stripLayout } from "@/lib/rewind";
import type { CuratePreview, MoodProfile, RoomSummary } from "@/lib/types";

import { ChipBars, CREAM, INK, Kicker, PALETTE as C, Qr, RoomMap } from "./parts";

export type Room = RoomSummary & { rehearsal: boolean };

export interface DeckContext {
  step: number;
  room: Room | null;
  code: string | null;
  joinUrl: string;
  shortJoin: string;
  roomError: string | null;
  openRoom: () => void;
  loggedIn: boolean;
  next: () => void;
}

export interface Slide {
  id: string;
  title: string;
  bg: string;
  fg: string;
  steps: number; // extra reveals before moving to the next slide
  notes: ReactNode;
  render: (ctx: DeckContext) => ReactNode;
}

const Reveal = ({ show, children, delay = 0 }: { show: boolean; children: ReactNode; delay?: number }) => (
  <AnimatePresence>
    {show && (
      <motion.div initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0 }} transition={{ type: "spring", stiffness: 220, damping: 22, delay }}>
        {children}
      </motion.div>
    )}
  </AnimatePresence>
);

const Title = ({ children, size = 96, color }: { children: ReactNode; size?: number; color?: string }) => (
  <h1 className="font-display font-black leading-[0.98]" style={{ fontSize: size, color }}>{children}</h1>
);

const Box = ({ children, className = "", style }: { children: ReactNode; className?: string; style?: CSSProperties }) => (
  <div className={`rounded-[2rem] p-8 ${className}`} style={style}>{children}</div>
);

const Mono = ({ children }: { children: ReactNode }) => <code className="rounded-lg bg-black/25 px-2 py-0.5 font-mono text-[0.85em]">{children}</code>;

// ---------------------------------------------------------------- live demos

function CurateDemo({ room }: { room: Room | null }) {
  const chips = useMemo(() => (room?.chips.length ? room.chips.slice(0, 3).map((c) => c.label) : ["happy"]), [room]);
  const [result, setResult] = useState<CuratePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.curation.curate({ chips }, 10));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid h-full grid-cols-[520px_1fr] gap-10">
      <div className="flex flex-col justify-center">
        <Kicker bg={C.lime} fg={INK}>Live demo</Kicker>
        <Title size={84}>Muse, play the room.</Title>
        <p className="mt-6 text-3xl opacity-85">The room said:</p>
        <div className="mt-4 flex flex-wrap gap-3">
          {chips.map((c) => (
            <span key={c} className="rounded-full px-5 py-2 text-3xl font-bold capitalize" style={{ background: CREAM, color: INK }}>{MOOD_EMOJI[c]} {c}</span>
          ))}
        </div>
        <button type="button" onClick={run} disabled={busy} className="mt-10 inline-flex w-fit items-center gap-3 rounded-full px-9 py-5 text-3xl font-black shadow-2xl transition hover:scale-105 disabled:opacity-70" style={{ background: C.sun, color: INK }}>
          {busy ? <Loader2 className="size-8 animate-spin" /> : <Sparkles className="size-8" />} {result ? "Curate again" : "Curate for this room"}
        </button>
        {error && <p className="mt-4 text-xl">{error}</p>}
        {result && (
          <p className="mt-6 text-xl opacity-80">
            {result.candidates_considered} songs considered · {result.searches} searches · mood {Math.round(result.mood.valence * 100)}% positive, {Math.round(result.mood.energy * 100)}% energy
          </p>
        )}
      </div>
      <div className="flex items-center">
        {result ? (
          <div className="max-h-[760px] w-full overflow-auto rounded-[2rem] p-4" style={{ background: CREAM, color: INK }}>
            <ol className="space-y-2">
              {result.tracks.slice(0, 8).map((item, i) => (
                <TrackRow key={item.track.id} item={item} index={i} onRemove={() => undefined} />
              ))}
            </ol>
          </div>
        ) : (
          <div className="grid h-[600px] w-full place-items-center rounded-[2rem] border-4 border-dashed text-3xl opacity-60" style={{ borderColor: CREAM }}>
            {busy ? "Reading the room…" : "Press the button. Tap any cover to hear 30 seconds."}
          </div>
        )}
      </div>
    </div>
  );
}

// Checked against the real model: each one is read by the classifier, not the keyword fallback
const PRESETS = ["I got the job, so happy", "I am scared about my results", "I feel lonely and miss my family", "bored in class, nothing to do"];

function AnalyzeDemo() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<MoodProfile | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(value: string) {
    if (!value.trim()) return;
    setText(value);
    setBusy(true);
    try {
      setResult(await api.mood.analyze({ chips: [], text: value }));
    } catch {
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid h-full grid-cols-[1fr_600px] gap-12">
      <div className="flex flex-col justify-center">
        <Kicker bg={C.pink} fg={INK}>Try it · NLP</Kicker>
        <Title size={80}>Say how you feel. In your own words.</Title>
        <form className="mt-8 flex gap-3" onSubmit={(e) => { e.preventDefault(); void run(text); }}>
          <input value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="Someone shout a feeling…"
            className="flex-1 rounded-2xl px-6 py-5 text-3xl outline-none ring-4 ring-transparent focus:ring-[#FFC93C]" style={{ background: CREAM, color: INK }} />
          <button type="submit" className="rounded-2xl px-8 text-3xl font-black" style={{ background: C.sun, color: INK }}>{busy ? <Loader2 className="size-8 animate-spin" /> : "Read"}</button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button key={p} type="button" onClick={() => run(p)} className="rounded-full px-4 py-2 text-lg font-semibold ring-2" style={{ borderColor: CREAM }}>“{p}”</button>
          ))}
        </div>
        <div className="mt-8 grid grid-cols-3 gap-4 text-xl">
          <div className="rounded-2xl bg-black/20 p-4"><div className="text-4xl font-black">0.879</div>accuracy</div>
          <div className="rounded-2xl bg-black/20 p-4"><div className="text-4xl font-black">0.838</div>macro-F1</div>
          <div className="rounded-2xl bg-black/20 p-4"><div className="text-4xl font-black">16k</div>training sentences</div>
        </div>
        <p className="mt-4 text-xl opacity-80">TF-IDF + logistic regression (scikit-learn) on <Mono>dair-ai/emotion</Mono>, loaded only if its SHA-256 matches its model card.</p>
      </div>
      <div className="flex flex-col items-center justify-center gap-6">
        <RoomMap points={result ? [{ valence: result.valence, energy: result.energy, labels: result.labels }] : []} average={null} size={520} />
        <AnimatePresence mode="wait">
          {result && (
            <motion.div key={text} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full space-y-2 text-2xl">
              <div className="flex flex-wrap gap-2">
                {result.labels.map((l) => <span key={l} className="rounded-full px-4 py-1 font-bold capitalize" style={{ background: CREAM, color: INK }}>{l}</span>)}
              </div>
              <div>positivity <b>{Math.round(result.valence * 100)}%</b> · energy <b>{Math.round(result.energy * 100)}%</b> · tempo <b>{result.tempo}</b> · mode <b>{result.mode}</b></div>
              <div className="opacity-75">
                read by: {result.text_analysis} · confidence {Math.round(result.confidence * 100)}%
                {result.text_analysis === "keywords" && " · the model wasn't sure, so it didn't guess"}
              </div>
              {result.support && <div className="rounded-xl bg-black/25 p-3 text-xl">💛 {result.support.message}</div>}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

const PIPELINE = [
  { k: "Plan", d: "Turns mood + taste into Spotify searches: favourite artists, similar artists (Last.fm), genres near the mood on the map.", n: "planner.py" },
  { k: "Gather", d: "Runs the searches in parallel, cached for 6 hours, backs off when Spotify says 429.", n: "candidates.py" },
  { k: "Profile", d: "Each song gets a mood, genre and language from Last.fm listener tags (\"chill\", \"sad\", \"hindi\") plus the script of its title.", n: "tags.py" },
  { k: "Score", d: "Mood fit = 1 − distance on the valence-energy map; taste fit = favourite artist, similar artist, genre. Weighted by mode.", n: "scoring.py · ADR-0010" },
  { k: "Learn", d: "Your 👍/👎: liked songs +0.1 (more in a similar mood), 👎 never returns, artists ±, genres ±. Every nudge is capped.", n: "learning.py" },
  { k: "Lock", d: "One language and one anchor genre per playlist, so English and Hindi never get randomly mixed.", n: "focus.py" },
  { k: "Tempo", d: "Real BPM from Deezer (matched by ISRC); a bonus when the pace fits the mood.", n: "deezer.py" },
  { k: "Mix", d: "Familiar vs new: a slider decides how many songs you already play; each part is diversified by artist.", n: "ranking.py" },
  { k: "Explain", d: "Every song gets a reason that names only the factors that really scored it.", n: "explain.py" },
];

function PipelineDemo({ step }: { step: number }) {
  const [open, setOpen] = useState(0);
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker bg={C.lime} fg={INK}>Under the hood · recommender</Kicker>
      <Title size={76}>Nine steps from a feeling to a playlist.</Title>
      <div className="mt-10 flex items-center gap-2">
        {PIPELINE.map((p, i) => (
          <motion.button key={p.k} type="button" onClick={() => setOpen(i)} initial={{ opacity: 0, y: 20 }} animate={{ opacity: i <= step * 3 + 2 ? 1 : 0.15, y: 0 }} transition={{ delay: i * 0.05 }}
            className="flex-1 rounded-2xl px-2 py-6 text-center text-2xl font-black transition hover:-translate-y-1" style={{ background: open === i ? C.sun : "rgba(255,244,230,0.12)", color: open === i ? INK : CREAM }}>
            <div className="text-lg opacity-70">{i + 1}</div>{p.k}
          </motion.button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={open} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-8 rounded-[2rem] p-8 text-3xl leading-snug" style={{ background: CREAM, color: INK }}>
          <b>{PIPELINE[open].k}.</b> {PIPELINE[open].d} <span className="ml-2 font-mono text-xl opacity-60">{PIPELINE[open].n}</span>
        </motion.div>
      </AnimatePresence>
      <p className="mt-6 text-2xl opacity-80">No Spotify audio features, no Spotify recommendations API, no model trained on Spotify content: all ours.</p>
    </div>
  );
}

function CoverLab() {
  const [v, setV] = useState(0.7);
  const [e, setE] = useState(0.4);
  const [title, setTitle] = useState("Our class, right now");
  const [src, setSrc] = useState(() => coverUrl({ valence: 0.7, energy: 0.4, title: "Our class, right now", words: ["live", "demo"] }));
  useEffect(() => {
    const t = setTimeout(() => setSrc(coverUrl({ valence: v, energy: e, title: title.trim() || "Muse", words: ["live", "demo"] })), 350);
    return () => clearTimeout(t);
  }, [v, e, title]);
  return (
    <div className="grid h-full grid-cols-[1fr_620px] items-center gap-12">
      <div>
        <Kicker bg={C.sun} fg={INK}>Play with it</Kicker>
        <Title size={84}>Every playlist gets its own cover.</Title>
        <p className="mt-5 text-3xl opacity-85">Painted from the mood with Pillow. No AI images, no stock photos. Colour follows positivity, waves follow energy.</p>
        <div className="mt-10 space-y-8 text-2xl font-bold">
          <label className="block">Positivity {Math.round(v * 100)}%<input type="range" min={0} max={1} step={0.05} value={v} onChange={(ev) => setV(Number(ev.target.value))} className="mt-3 block w-full accent-[#FFC93C]" /></label>
          <label className="block">Energy {Math.round(e * 100)}%<input type="range" min={0} max={1} step={0.05} value={e} onChange={(ev) => setE(Number(ev.target.value))} className="mt-3 block w-full accent-[#FF4FA3]" /></label>
          <label className="block">Title<input value={title} maxLength={60} onChange={(ev) => setTitle(ev.target.value)} className="mt-3 block w-full rounded-2xl px-5 py-3 text-2xl" style={{ background: CREAM, color: INK }} /></label>
        </div>
      </div>
      <motion.img key={src} src={src} alt="Cover art painted from the mood" initial={{ opacity: 0.4, rotate: -2, scale: 0.97 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} className="w-[600px] rounded-[2rem] shadow-2xl" />
    </div>
  );
}

type SimSong = { id: string; title: string; artist: string; base: number };
const SIM: SimSong[] = [
  { id: "a", title: "cold/mess", artist: "Prateek Kuhad", base: 0.62 },
  { id: "b", title: "Night Changes", artist: "One Direction", base: 0.6 },
  { id: "c", title: "Baarishein", artist: "Anuv Jain", base: 0.58 },
  { id: "d", title: "kasoor", artist: "Prateek Kuhad", base: 0.55 },
  { id: "e", title: "Heat Waves", artist: "Glass Animals", base: 0.53 },
];

function LearnSim() {
  const [rated, setRated] = useState<Record<string, 1 | -1>>({});
  const scores = SIM.filter((s) => rated[s.id] !== -1).map((s) => {
    const likesForArtist = SIM.filter((o) => o.artist === s.artist && rated[o.id] === 1).length;
    const lift = (rated[s.id] === 1 ? 0.16 : 0) + Math.min(0.12, 0.04 * likesForArtist);
    return { ...s, score: s.base + lift, lift };
  }).sort((a, b) => b.score - a.score);
  return (
    <div className="grid h-full grid-cols-[1fr_760px] items-center gap-12">
      <div>
        <Kicker bg={CREAM} fg={INK}>Learn from me</Kicker>
        <Title size={84}>Tap 👍 or 👎. Watch the next mix change.</Title>
        <ul className="mt-8 space-y-3 text-2xl opacity-90">
          <li>👍 a song: <b>+0.10</b>, plus <b>+0.06</b> when you're in a similar mood again</li>
          <li>👍 an artist's songs: <b>+0.04</b> each, capped at <b>+0.12</b></li>
          <li>👎 a song: gone, and it never comes back</li>
        </ul>
        <p className="mt-6 text-xl opacity-70">Same numbers as <Mono>services/learning.py</Mono>. Small and capped, so your mood still leads.</p>
        <button type="button" onClick={() => setRated({})} className="mt-6 text-xl underline opacity-80">Reset</button>
      </div>
      <ul className="space-y-3">
        <AnimatePresence>
          {scores.map((s) => (
            <motion.li key={s.id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, x: 80 }} transition={{ type: "spring", stiffness: 300, damping: 28 }}
              className="flex items-center gap-4 rounded-2xl p-4" style={{ background: CREAM, color: INK }}>
              <div className="flex-1">
                <div className="text-2xl font-bold">{s.title}</div>
                <div className="text-lg opacity-60">{s.artist}</div>
                <div className="mt-2 h-3 rounded-full bg-black/10"><motion.div className="h-3 rounded-full" style={{ background: s.lift ? C.green : C.tangerine }} animate={{ width: `${Math.min(100, s.score * 100)}%` }} /></div>
              </div>
              <div className="w-16 text-right font-mono text-2xl">{s.score.toFixed(2)}</div>
              <button type="button" aria-label="Thumbs up" onClick={() => setRated((r) => ({ ...r, [s.id]: 1 }))} className="grid size-14 place-items-center rounded-full" style={{ background: rated[s.id] === 1 ? C.green : "rgba(0,0,0,0.08)", color: rated[s.id] === 1 ? CREAM : INK }}><ThumbsUp /></button>
              <button type="button" aria-label="Thumbs down" onClick={() => setRated((r) => ({ ...r, [s.id]: -1 }))} className="grid size-14 place-items-center rounded-full bg-black/10"><ThumbsDown /></button>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </div>
  );
}

function RewindDemo({ loggedIn, room }: { loggedIn: boolean; room: Room | null }) {
  const [preview, setPreview] = useState<{ url: string; pages: number; w: number; h: number } | null>(null);
  useEffect(() => {
    let live = true;
    let url: string | null = null;
    (async () => {
      try {
        let blob: Blob;
        let pages = 10;
        if (loggedIn) {
          const result = await api.rewind.get({ days: 30, moods: true, taste: true, learned: true, playlists: true }, "preview");
          blob = result.blob;
          pages = result.pages;
        } else {
          blob = await (await fetch(`${import.meta.env.BASE_URL}demo-rewind.jpg`)).blob();
        }
        url = URL.createObjectURL(blob);
        const image = new Image();
        image.src = url;
        await image.decode();
        if (live) setPreview({ url, pages, w: image.naturalWidth, h: image.naturalHeight });
      } catch {
        /* the slide still works without the strip */
      }
    })();
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [loggedIn]);
  const shown = 430;
  const layout = preview ? stripLayout(preview.w, preview.h, preview.pages, shown) : null;
  return (
    <div className="flex h-full flex-col justify-center">
      <div className="flex items-end justify-between">
        <div>
          <Kicker bg={C.sun} fg={INK}>New · Muse Rewind</Kicker>
          <Title size={74}>Your month, wrapped.<br />In a PDF.</Title>
        </div>
        {room?.personality && (
          <div className="rounded-[2rem] px-8 py-5 text-right" style={{ background: C.lime, color: INK }}>
            <div className="text-xl font-extrabold uppercase tracking-widest">This room is</div>
            <div className="font-display text-5xl font-black">{room.personality.name}</div>
          </div>
        )}
      </div>
      <div className="mt-8 flex gap-5 overflow-hidden">
        {preview && layout
          ? Array.from({ length: Math.min(preview.pages, 6) }, (_, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 40, rotate: i % 2 ? 3 : -3 }} animate={{ opacity: 1, y: 0, rotate: i % 2 ? 1.5 : -1.5 }} whileHover={{ y: -14, rotate: 0, scale: 1.04 }} transition={{ delay: i * 0.08, type: "spring" }}
                className="relative shrink-0 overflow-hidden rounded-2xl shadow-2xl" style={{ width: layout.width, height: shown }}>
                <img src={preview.url} alt="" className="absolute left-0 top-0 max-w-none" style={{ height: shown, width: layout.stripWidth, transform: `translateX(-${layout.offset(i)}px)` }} />
              </motion.div>
            ))
          : <div className="h-[430px] w-full animate-pulse rounded-2xl bg-white/10" />}
      </div>
      <p className="mt-6 text-2xl opacity-85">Mood of the month · Muse personality · mood journey · golden hour · top artists · taste × mood match · what Muse learned. Made on request, never stored.</p>
    </div>
  );
}

const ARCH = [
  { k: "React 19 + Vite", d: "Tailwind 4, framer-motion, hash routing; built to static files and served by FastAPI at /app.", c: C.pink },
  { k: "FastAPI", d: "Modular monolith: auth, preferences, mood, curate, playlists, feedback, moods, rewind, rooms. Async all the way.", c: C.sun },
  { k: "MongoDB Atlas", d: "Users (encrypted tokens), taste, playlists, ratings, opt-in mood log. TTL indexes expire old data.", c: C.green },
  { k: "scikit-learn", d: "Emotion classifier, hash-checked before loading. Keyword fallback if the model is missing.", c: C.cobalt },
  { k: "Spotify Web API", d: "OAuth login, catalogue search, create playlist, upload cover. Hard allow-list: Muse can never touch your existing playlists.", c: C.lime },
  { k: "Last.fm + Deezer", d: "Listener tags for song moods; BPM and 30-second previews.", c: C.tangerine },
];

const SECURITY = ["OAuth state check", "Fernet-encrypted tokens", "hashed session IDs", "CSP + security headers", "Origin check (CSRF)", "per-IP rate limits", "no mood text stored", "export + delete my data"];

function ArchSlide() {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker bg={C.cobalt} fg={CREAM}>Architecture</Kicker>
      <Title size={76}>One app, six moving parts.</Title>
      <div className="mt-10 grid grid-cols-3 gap-5">
        {ARCH.map((a, i) => (
          <motion.button key={a.k} type="button" onMouseEnter={() => setOpen(i)} onFocus={() => setOpen(i)} onClick={() => setOpen(i)} whileHover={{ y: -6 }}
            className="rounded-[1.6rem] p-6 text-left" style={{ background: open === i ? a.c : "rgba(255,244,230,0.1)", color: open === i && a.c !== C.cobalt && a.c !== C.green ? INK : CREAM }}>
            <div className="font-display text-4xl font-black">{a.k}</div>
            <div className="mt-2 text-xl opacity-90">{a.d}</div>
          </motion.button>
        ))}
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        {SECURITY.map((s, i) => (
          <motion.span key={s} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 + i * 0.05 }} className="rounded-full px-4 py-2 text-xl font-bold" style={{ background: CREAM, color: INK }}>🔒 {s}</motion.span>
        ))}
      </div>
    </div>
  );
}

const STAGES = [
  { k: "feature branch", d: "feature/rooms" },
  { k: "pull request", d: "template, linked issue" },
  { k: "Lint", d: "ruff + eslint" },
  { k: "Tests", d: "400+ pytest · 90%+ coverage · real MongoDB" },
  { k: "Website", d: "typecheck · unit tests · build" },
  { k: "Docker", d: "compose up + health check" },
  { k: "Audit", d: "npm + pip vulnerabilities" },
  { k: "merge", d: "squash into main" },
  { k: "Render", d: "auto-deploy on commit" },
  { k: "live", d: "you're using it right now" },
];

function DevOpsSlide() {
  const [lit, setLit] = useState(-1);
  useEffect(() => {
    if (lit < 0 || lit >= STAGES.length - 1) return;
    const t = setTimeout(() => setLit(lit + 1), 450);
    return () => clearTimeout(t);
  }, [lit]);
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker bg={C.sun} fg={INK}>DevOps · SCM</Kicker>
      <div className="flex items-end justify-between">
        <Title size={76}>Every change goes through the pipe.</Title>
        <button type="button" onClick={() => setLit(0)} className="mb-2 inline-flex shrink-0 items-center gap-3 whitespace-nowrap rounded-full px-8 py-4 text-2xl font-black" style={{ background: C.sun, color: INK }}><Play /> Run the pipeline</button>
      </div>
      <div className="mt-12 grid grid-cols-5 gap-4">
        {STAGES.map((s, i) => (
          <motion.div key={s.k} animate={{ background: i <= lit ? (i === STAGES.length - 1 ? C.lime : C.green) : "rgba(255,244,230,0.08)", scale: i === lit ? 1.06 : 1 }} transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="rounded-2xl p-5" style={{ color: i <= lit && i === STAGES.length - 1 ? INK : CREAM }}>
            <div className="text-2xl font-black">{i <= lit ? "✓ " : ""}{s.k}</div>
            <div className="mt-1 text-lg opacity-85">{s.d}</div>
          </motion.div>
        ))}
      </div>
      <div className="mt-12 grid grid-cols-4 gap-5 text-center">
        {[["150+", "commits"], ["30+", "reviewed pull requests"], ["11", "architecture decision records"], ["5", "CI jobs on every PR"]].map(([n, l]) => (
          <div key={l} className="rounded-2xl p-5" style={{ background: CREAM, color: INK }}>
            <div className="font-display text-6xl font-black">{n}</div>
            <div className="text-xl">{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- the deck

export const SLIDES: Slide[] = [
  {
    id: "title",
    title: "Muse",
    bg: `linear-gradient(130deg, ${C.violet} 0%, #6b2580 50%, ${C.pink} 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>Open with energy: “Before we start, take out your phones. Scan this, tap how you feel right now. No login, no names.” Wait until ~half the room has joined (counter on the right). Press → when ready.</>,
    render: ({ code, joinUrl, shortJoin, room, roomError, openRoom, loggedIn }) => (
      <div className="grid h-full grid-cols-[1fr_520px] items-center gap-12 p-24">
        <div>
          <div className="flex items-center gap-5"><Logo className="size-24" /><span className="font-display text-6xl">Muse</span></div>
          <Title size={128} color={C.sun}>Music for how you feel.</Title>
          <p className="mt-8 text-4xl opacity-90">From what you love, for this exact moment.</p>
          <p className="mt-14 text-2xl opacity-75">Atharva Ingale · Darsh · Piyush — DevOps &amp; SCM project</p>
        </div>
        <div className="rounded-[2.4rem] p-8 text-center shadow-2xl" style={{ background: CREAM, color: INK }}>
          <div className="text-2xl font-extrabold uppercase tracking-[0.2em]">Scan · tap your mood</div>
          <div className="mt-5 flex justify-center">{code ? <Qr url={joinUrl} size={380} /> : <div className="grid size-[380px] place-items-center text-2xl">{roomError ?? (loggedIn ? "Opening a room…" : "Log in on this laptop to open a room")}</div>}</div>
          <div className="mt-5 text-xl opacity-70">{shortJoin}</div>
          <div className="font-display text-7xl font-black tracking-[0.25em]">{code ?? "····"}</div>
          <motion.div key={room?.voters ?? 0} initial={{ scale: 1.4 }} animate={{ scale: 1 }} className="mt-3 text-3xl font-bold">{room?.voters ?? 0} joined</motion.div>
          {roomError && <button type="button" onClick={openRoom} className="mt-3 text-xl underline">Try again</button>}
        </div>
      </div>
    ),
  },
  {
    id: "room",
    title: "The room right now",
    bg: C.violet,
    fg: CREAM,
    steps: 0,
    notes: <>Live. Read the map out loud: “Most of you are… tired. Of course, it's a 9 am lecture.” Point at the dashed ring: that's the room's average. Keep scanning open for latecomers. Press L to lock the room when everyone's in (stops fake voters). R toggles rehearsal votes (only on this laptop).</>,
    render: ({ room }) => (
      <div className="grid h-full grid-cols-[660px_1fr] items-center gap-14 p-20">
        <RoomMap points={room?.points ?? []} average={room?.average ?? null} size={660} />
        <div>
          <Kicker bg={C.sun} fg={INK}>Live from your phones</Kicker>
          <Title size={88}>How's the room feeling?</Title>
          <div className="mt-3 text-3xl opacity-80">{room?.voters ?? 0} moods · every dot is one of you</div>
          <div className="mt-10"><ChipBars chips={room?.chips ?? []} /></div>
        </div>
      </div>
    ),
  },
  {
    id: "problem",
    title: "The problem",
    bg: C.pink,
    fg: INK,
    steps: 3,
    notes: <>Ask: “Raise your hand if you've skipped five songs looking for the right vibe.” Then reveal the three cards (→ each). Point: Spotify knows what you liked over months; mood playlists are the same for everyone; Muse is your taste × this moment.</>,
    render: ({ step }) => (
      <div className="flex h-full flex-col justify-center p-24">
        <Title size={104}>Spotify knows what you like.</Title>
        <Title size={104} color={CREAM}>Not how you feel right now.</Title>
        <div className="mt-14 grid grid-cols-3 gap-6">
          <Reveal show={step >= 1}><Box style={{ background: INK, color: CREAM }}><div className="text-5xl">📈</div><div className="mt-3 text-3xl font-black">Your algorithm</div><p className="mt-2 text-2xl opacity-85">Built from months of listening. Great at “more of the same”.</p></Box></Reveal>
          <Reveal show={step >= 2}><Box style={{ background: CREAM, color: INK }}><div className="text-5xl">🗂️</div><div className="mt-3 text-3xl font-black">Mood playlists</div><p className="mt-2 text-2xl opacity-85">One “Sad Hours” for everyone. Not your artists, not your language.</p></Box></Reveal>
          <Reveal show={step >= 3}><Box style={{ background: C.sun, color: INK }}><div className="text-5xl">✨</div><div className="mt-3 text-3xl font-black">Muse</div><p className="mt-2 text-2xl opacity-85">Your taste × this moment. Explained, song by song.</p></Box></Reveal>
        </div>
      </div>
    ),
  },
  {
    id: "stages",
    title: "Meet Muse",
    bg: C.cream,
    fg: INK,
    steps: 2,
    notes: <>The three stages from our synopsis. Classics: Muse learns your taste (Music DNA, import from Spotify). Essential: mood → playlist, saved to your Spotify. Advanced: it learns from 👍/👎 and tracks your mood over time. Then: “Let's see it with your moods.”</>,
    render: ({ step }) => (
      <div className="flex h-full flex-col justify-center p-24">
        <Kicker>Three stages</Kicker>
        <Title size={92}>Know me → Curate for me → Learn from me</Title>
        <div className="mt-12 grid grid-cols-3 gap-6">
          {[
            { k: "Classics", t: "Know your music", c: C.cobalt, f: CREAM, items: ["Music DNA", "Import from Spotify", "Favourite artists, genres, languages"] },
            { k: "Essential", t: "Curate for me", c: C.tangerine, f: CREAM, items: ["Chips or your own words", "Explained playlist", "Saved to your Spotify + cover art"] },
            { k: "Advanced", t: "Learn from me", c: C.green, f: CREAM, items: ["👍/👎 shape the next mix", "Mood trajectory", "Muse Rewind PDF"] },
          ].map((s, i) => (
            <Reveal key={s.k} show={step >= i}>
              <Box style={{ background: s.c, color: s.f }} className="h-full">
                <div className="text-2xl font-extrabold uppercase tracking-widest opacity-80">{s.k}</div>
                <div className="font-display text-5xl font-black">{s.t}</div>
                <ul className="mt-5 space-y-2 text-2xl">{s.items.map((it) => <li key={it}>• {it}</li>)}</ul>
              </Box>
            </Reveal>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: "curate",
    title: "Live: play the room",
    bg: `linear-gradient(140deg, ${C.tangerine} 0%, #b8321c 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>Press “Curate for this room”. It uses the room's top 3 moods and your saved taste. Click a cover to play 30 seconds. Read one reason aloud (“Picked because…”). Point at the BPM and the familiar ✓ badges. If Spotify is slow, keep talking: it has a 5-second budget.</>,
    render: ({ room }) => <div className="h-full p-20"><CurateDemo room={room} /></div>,
  },
  {
    id: "nlp",
    title: "How Muse reads a feeling",
    bg: C.violet,
    fg: CREAM,
    steps: 0,
    notes: <>Ask the audience for a sentence and type it (or tap a preset). Full sentences with feeling words work best (“I am so stressed about exams”). Show where it lands on the map and the labels. If it says “keywords · the model wasn't sure”: that's by design, the classifier abstains below its confidence threshold instead of guessing (great geeky point). Text is analysed in memory and never stored; a wellbeing message appears if it suggests distress (Tele-MANAS).</>,
    render: () => <div className="h-full p-20"><AnalyzeDemo /></div>,
  },
  {
    id: "pipeline",
    title: "The recommender",
    bg: INK,
    fg: CREAM,
    steps: 2,
    notes: <>Click through the nine steps; → reveals them in three groups. Key geeky points: distance on the valence-energy map (ADR-0010), Last.fm tags because Spotify removed audio features in 2026, one language per playlist, Deezer BPM by ISRC, explanations only name factors that really scored.</>,
    render: ({ step }) => <div className="h-full p-20"><PipelineDemo step={step} /></div>,
  },
  {
    id: "cover",
    title: "Cover art lab",
    bg: `linear-gradient(140deg, ${C.cobalt} 0%, #1b2a9e 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>Drag the sliders and let someone suggest a title. Each change paints a new 640×640 JPEG on the server (under 190 KB, Spotify's limit is 256 KB) and it's uploaded to the playlist Muse creates. Only to that playlist: a hard allow-list means Muse can't touch anything else.</>,
    render: () => <div className="h-full p-20"><CoverLab /></div>,
  },
  {
    id: "learn",
    title: "It learns from you",
    bg: C.green,
    fg: CREAM,
    steps: 0,
    notes: <>Tap 👍 on a Prateek Kuhad song: both his songs rise (artist lift). 👎 something: it disappears. This simulation uses the same constants as the backend. Also mention the mood trajectory on the History page: opt-in, 90 days, numbers and mood words only.</>,
    render: () => <div className="h-full p-20"><LearnSim /></div>,
  },
  {
    id: "rewind",
    title: "Muse Rewind",
    bg: `linear-gradient(130deg, ${C.violet} 0%, ${C.pink} 70%, ${C.tangerine} 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>This is your real Rewind if you're logged in (otherwise a sample). Read the room's personality on the right. Mention: painted with Pillow in our own fonts, every line comes from explainable rules, made on request, nothing stored.</>,
    render: ({ loggedIn, room }) => <div className="h-full p-20"><RewindDemo loggedIn={loggedIn} room={room} /></div>,
  },
  {
    id: "arch",
    title: "Architecture & security",
    bg: INK,
    fg: CREAM,
    steps: 0,
    notes: <>Hover each box. Key line: “Muse can only create playlists and add covers to the ones it made — there's a hard allow-list in code, so it can never delete or edit your playlists.” Security chips: tokens encrypted with Fernet, sessions hashed, CSP, origin check, rate limits, data export/delete.</>,
    render: () => <div className="h-full p-20"><ArchSlide /></div>,
  },
  {
    id: "devops",
    title: "DevOps pipeline",
    bg: `linear-gradient(140deg, #0d4d35 0%, ${C.green} 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>Press “Run the pipeline”. Feature branch → PR → five CI jobs on GitHub Actions (lint, tests with real MongoDB, website, Docker compose smoke test, dependency audit) → merge → Render auto-deploys on commit. Darsh can take questions on the pipeline. Then: “Ma'am, the repository is open here” (switch to GitHub).</>,
    render: () => <div className="h-full p-20"><DevOpsSlide /></div>,
  },
  {
    id: "honest",
    title: "Honest limits",
    bg: C.sun,
    fg: INK,
    steps: 0,
    notes: <>Be upfront: Spotify's 2026 Development Mode allows 5 users and removed audio features and recommendations, so we built our own signals. Responsible by design: mood text never stored, opt-in history, not a diagnosis, wellbeing helpline, AI-use log in the repo.</>,
    render: () => (
      <div className="grid h-full grid-cols-2 items-center gap-12 p-24">
        <div>
          <Kicker>Honest limits</Kicker>
          <Title size={84}>What Spotify doesn't let us do, and what we built instead.</Title>
        </div>
        <div className="space-y-4 text-3xl">
          {[
            ["5 users max", "Spotify Development Mode (Feb 2026): you're voting without logging in for exactly this reason."],
            ["No audio features", "So: Last.fm listener tags + Deezer BPM."],
            ["No recommendations API", "So: our own planner, scorer and explanations."],
            ["Feelings are personal", "Mood text never stored · opt-in history · not a diagnosis · helpline notice."],
          ].map(([k, d]) => (
            <Box key={k} className="!p-6" style={{ background: INK, color: CREAM }}><b>{k}.</b> <span className="opacity-85">{d}</span></Box>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: "finale",
    title: "Thank you",
    bg: `linear-gradient(130deg, ${C.violet} 0%, #6b2580 50%, ${C.pink} 100%)`,
    fg: CREAM,
    steps: 0,
    notes: <>Read the room's personality with drama. Thank ma'am and the class. “The code, the CI runs and every PR are on GitHub. Questions?” Darsh answers SCM/CI, Piyush answers the website, you take the rest.</>,
    render: ({ room }) => (
      <div className="grid h-full grid-cols-[1fr_440px] items-center gap-12 p-24">
        <div>
          <Kicker bg={C.sun} fg={INK}>Today, this room was</Kicker>
          <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 120, damping: 12 }}>
            <Title size={108} color={C.lime}>{room?.personality?.name ?? "Unreadable. Mysterious."}</Title>
          </motion.div>
          <p className="mt-6 text-4xl opacity-90">{room?.personality?.line ?? "Nobody voted. Respect."}</p>
          <p className="mt-6 text-3xl opacity-80">{room?.voters ?? 0} moods · mostly {room?.chips[0] ? `${MOOD_EMOJI[room.chips[0].label] ?? ""} ${room.chips[0].label}` : "—"}</p>
          <div className="mt-8"><Title size={84}>Thank you. Questions?</Title></div>
        </div>
        <div className="rounded-[2.4rem] p-8 text-center" style={{ background: CREAM, color: INK }}>
          <div className="text-2xl font-extrabold uppercase tracking-[0.2em]">Code on GitHub</div>
          <div className="mt-4 flex justify-center"><Qr url="https://github.com/AthxrvA7/Muse" size={340} /></div>
          <div className="mt-4 text-2xl font-bold">github.com/AthxrvA7/Muse</div>
        </div>
      </div>
    ),
  },
];
