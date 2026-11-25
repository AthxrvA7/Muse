import { motion } from "framer-motion";
import { ArrowRight, ExternalLink, History as HistoryIcon, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { EmptyState } from "@/components/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/services";
import { shortDate } from "@/lib/format";
import { intentionById } from "@/lib/intentions";
import { MOOD_EMOJI } from "@/lib/moods";
import type { Playlist } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const RANGES = [
  { id: "all", label: "All time", days: Infinity },
  { id: "7", label: "Last 7 days", days: 7 },
  { id: "30", label: "Last 30 days", days: 30 },
];

type Entry =
  | { kind: "session"; date: string; key: string; session: ReturnType<typeof useApp>["recentSessions"][number] }
  | { kind: "playlist"; date: string; key: string; playlist: Playlist };

export default function History() {
  const navigate = useNavigate();
  const { user, recentSessions, setSession } = useApp();
  const [playlists, setPlaylists] = useState<Playlist[] | null>(null);
  const [query, setQuery] = useState("");
  const [range, setRange] = useState("all");
  const [mood, setMood] = useState<string | null>(null);
  const [now] = useState(() => Date.now());

  useEffect(() => {
    if (user) api.playlists.list().then(setPlaylists).catch(() => setPlaylists([]));
  }, [user]);

  const moods = useMemo(() => [...new Set(recentSessions.flatMap((s) => s.preview.mood.labels))], [recentSessions]);

  const entries = useMemo(() => {
    const days = RANGES.find((r) => r.id === range)?.days ?? Infinity;
    const since = now - days * 86400000;
    const q = query.trim().toLowerCase();
    const all: Entry[] = [
      ...recentSessions.map((s) => ({ kind: "session" as const, date: s.created_at, key: s.id, session: s })),
      ...(playlists ?? []).map((p) => ({ kind: "playlist" as const, date: p.created_at, key: p.id, playlist: p })),
    ];
    return all
      .filter((e) => new Date(e.date).getTime() >= since)
      .filter((e) => (mood ? e.kind === "session" && e.session.preview.mood.labels.includes(mood) : true))
      .filter((e) => {
        if (!q) return true;
        const text = e.kind === "playlist" ? e.playlist.name : `${e.session.preview.mood.labels.join(" ")} ${intentionById(e.session.request.intention).label}`;
        return text.toLowerCase().includes(q);
      })
      .sort((a, b) => b.date.localeCompare(a.date));
  }, [recentSessions, playlists, query, range, mood, now]);

  const loading = user && playlists === null;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl sm:text-5xl">History</h1>
        <p className="mt-2 text-ink-soft">
          Playlists you saved to Spotify, and recent curations from this browser. Mood text is never kept.
        </p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-ink-soft" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by playlist or mood…" className="pl-10" aria-label="Search history" />
        </div>
        <div className="flex gap-1.5">
          {RANGES.map((r) => (
            <button key={r.id} type="button" onClick={() => setRange(r.id)} aria-pressed={range === r.id}
              className={cn("rounded-full px-3.5 py-2 text-sm transition", range === r.id ? "bg-plum text-white" : "bg-surface text-ink-soft ring-1 ring-line hover:bg-lavender-faint")}>
              {r.label}
            </button>
          ))}
        </div>
      </div>
      {moods.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {moods.map((m) => (
            <button key={m} type="button" onClick={() => setMood(mood === m ? null : m)} aria-pressed={mood === m}
              className={cn("rounded-full px-3 py-1 text-xs capitalize transition", mood === m ? "bg-lavender text-plum" : "bg-lavender-faint text-ink-soft hover:text-ink")}>
              {MOOD_EMOJI[m]} {m}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}</div>
      ) : entries.length === 0 ? (
        <EmptyState icon={HistoryIcon} title="Nothing here yet">
          Curate a playlist from how you feel, and your sessions and saved playlists will gather here.
        </EmptyState>
      ) : (
        <ol className="relative space-y-3 border-l border-line pl-6">
          {entries.map((e, i) => (
            <motion.li key={e.key} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i * 0.04, 0.3) }} className="relative">
              <span className={cn("absolute -left-[1.94rem] top-5 size-3 rounded-full ring-4 ring-canvas", e.kind === "playlist" ? "bg-moss" : "bg-plum-muted")} />
              {e.kind === "playlist" ? (
                <a href={e.playlist.url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-surface p-4 transition hover:border-sage hover:shadow-soft">
                  <div>
                    <div className="flex items-center gap-2"><span className="font-semibold">{e.playlist.name}</span><Badge variant="sage">Saved to Spotify</Badge></div>
                    <div className="mt-1 text-sm text-ink-soft">{e.playlist.track_count} tracks · {shortDate(e.date)}</div>
                  </div>
                  <ExternalLink className="size-4 shrink-0 text-moss" />
                </a>
              ) : (
                <button type="button" onClick={() => { setSession(e.session); navigate("/results"); }} className="flex w-full items-center justify-between gap-4 rounded-2xl border border-line bg-surface p-4 text-left transition hover:border-lavender hover:shadow-soft">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold capitalize">{e.session.preview.mood.labels.join(", ") || "Your words"}</span>
                      <Badge>{intentionById(e.session.request.intention).label}</Badge>
                    </div>
                    <div className="mt-1 text-sm text-ink-soft">
                      {e.session.preview.tracks.length} tracks · top pick “{e.session.preview.tracks[0]?.track.name}” · {shortDate(e.date)}
                    </div>
                  </div>
                  <ArrowRight className="size-4 shrink-0 text-plum" />
                </button>
              )}
            </motion.li>
          ))}
        </ol>
      )}
    </div>
  );
}
