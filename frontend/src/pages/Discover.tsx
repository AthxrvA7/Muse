import { motion } from "framer-motion";
import { ArrowRight, Clock, ExternalLink, Music2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import { IntentionPicker } from "@/components/IntentionPicker";
import { MoodOrb } from "@/components/MoodOrb";
import { MoodPicker } from "@/components/MoodPicker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/services";
import { greeting, shortDate } from "@/lib/format";
import { familiarityLabel, intentionById, MODE_FAMILIARITY } from "@/lib/intentions";
import { MOOD_EMOJI } from "@/lib/moods";
import type { MoodOptions, Playlist, TasteOptions } from "@/lib/types";
import { useApp } from "@/state/AppState";

export default function Discover() {
  const navigate = useNavigate();
  const { user, draft, setDraft, recentSessions, setSession } = useApp();
  const [options, setOptions] = useState<MoodOptions | null>(null);
  const [taste, setTaste] = useState<TasteOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);

  useEffect(() => {
    api.mood.options().then(setOptions).catch((e: Error) => setError(e.message));
    api.preferences.options().then(setTaste).catch(() => setTaste(null));
  }, []);
  useEffect(() => {
    if (user) api.playlists.list().then(setPlaylists).catch(() => setPlaylists([]));
  }, [user]);

  const toggleChip = (id: string) =>
    setDraft({
      ...draft,
      chips: draft.chips.includes(id) ? draft.chips.filter((c) => c !== id) : [...draft.chips, id],
    });
  const canCurate = draft.chips.length > 0 || draft.text.trim().length > 0;
  const intention = intentionById(draft.intention);
  const familiarity = draft.familiarity ?? MODE_FAMILIARITY[intention.mode];

  return (
    <div className="space-y-10">
      <section
        className="relative overflow-hidden rounded-[2rem] border border-line bg-surface px-6 py-8 sm:px-10 sm:py-10"
        onMouseMove={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          e.currentTarget.style.setProperty("--mx", `${e.clientX - box.left}px`);
          e.currentTarget.style.setProperty("--my", `${e.clientY - box.top}px`);
        }}
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-70 transition-opacity"
          style={{ background: "radial-gradient(420px circle at var(--mx, 70%) var(--my, 30%), var(--c-accent-faint), transparent 70%)" }}
        />
        <div className="relative flex flex-col items-center gap-6 md:flex-row md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-plum">{greeting(new Date().getHours())}</p>
            <h1 className="mt-3 max-w-2xl font-display text-4xl leading-[1.02] text-ink sm:text-6xl">
              Music for the way you&apos;re{" "}
              <span className="bg-gradient-to-r from-plum via-coral to-amber bg-clip-text italic text-transparent">feeling</span>.
            </h1>
            <p className="mt-4 max-w-xl text-ink-soft sm:text-lg">
              Tell Muse what&apos;s on your mind. It mixes songs you love with ones you&apos;ll love, in your language, at your pace.
            </p>
          </div>
          <MoodOrb chips={(options?.chips ?? []).filter((c) => draft.chips.includes(c.id))} />
        </div>
      </section>

      <section aria-labelledby="mood-heading" className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="mood-heading" className="font-display text-2xl">How are you feeling?</h2>
            <p className="text-sm text-ink-soft">Pick up to {options?.max_chips ?? 5}. Change your mind any time.</p>
          </div>
          {draft.chips.length > 0 && (
            <button type="button" className="-mr-3 rounded-full px-3 py-2 text-sm text-ink-soft underline-offset-4 hover:bg-lavender-faint hover:underline" onClick={() => setDraft({ ...draft, chips: [] })}>
              Clear
            </button>
          )}
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        {options ? (
          <MoodPicker chips={options.chips} selected={draft.chips} max={options.max_chips} onToggle={toggleChip} />
        ) : (
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-5">
            {Array.from({ length: 10 }, (_, i) => <Skeleton key={i} className="h-12" />)}
          </div>
        )}
        <div className="relative">
          <Textarea
            rows={3}
            value={draft.text}
            maxLength={options?.max_text_length ?? 500}
            onChange={(e) => setDraft({ ...draft, text: e.target.value })}
            placeholder="Tell Muse what you're feeling..."
            aria-label="Describe your mood in your own words"
            className="min-h-28 rounded-3xl p-5 text-base"
          />
          <span className="pointer-events-none absolute bottom-3 right-4 text-xs text-ink-soft">
            {draft.text.length}/{options?.max_text_length ?? 500} · never stored
          </span>
        </div>
      </section>

      <section aria-labelledby="intent-heading" className="space-y-4">
        <div>
          <h2 id="intent-heading" className="font-display text-2xl">What should the music do for you?</h2>
          <p className="text-sm text-ink-soft">How you feel and what you need aren&apos;t always the same thing.</p>
        </div>
        <IntentionPicker value={draft.intention} onChange={(id) => setDraft({ ...draft, intention: id })} />
      </section>

      <Card className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <label htmlFor="size" className="text-sm font-semibold">
            Playlist length: <span className="text-plum">{draft.size} tracks</span>
          </label>
          <input
            id="size"
            type="range"
            min={10}
            max={30}
            value={draft.size}
            onChange={(e) => setDraft({ ...draft, size: Number(e.target.value) })}
            className="block w-56 accent-plum"
          />
          {user && (
            <div className="space-y-1 pt-1">
              <label htmlFor="familiarity" className="text-sm font-semibold">
                Familiar <span className="font-normal text-ink-soft">↔</span> New:{" "}
                <span className="text-plum">{familiarityLabel(familiarity)}</span>
              </label>
              <div className="flex items-center gap-2 text-xs text-ink-soft">
                <span>New</span>
                <input
                  id="familiarity"
                  type="range"
                  min={0}
                  max={100}
                  step={10}
                  value={Math.round(familiarity * 100)}
                  onChange={(e) => setDraft({ ...draft, familiarity: Number(e.target.value) / 100 })}
                  className="block w-44 accent-moss"
                  aria-valuetext={familiarityLabel(familiarity)}
                />
                <span>Familiar</span>
                {draft.familiarity !== null && (
                  <button type="button" className="ml-1 text-plum hover:underline" onClick={() => setDraft({ ...draft, familiarity: null })}>
                    Auto
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-3 pt-1">
            <label className="space-y-1 text-sm">
              <span className="block font-semibold">Language</span>
              <select
                value={draft.language}
                onChange={(e) => setDraft({ ...draft, language: e.target.value })}
                className="h-9 rounded-xl border border-line bg-surface px-3 text-sm focus:border-plum focus:outline-none"
              >
                <option value="auto">Auto: one language</option>
                <option value="mix">Mix languages</option>
                {taste && Object.entries(taste.languages).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="block font-semibold">Genre</span>
              <select
                value={draft.genre ?? ""}
                onChange={(e) => setDraft({ ...draft, genre: e.target.value || null })}
                className="h-9 max-w-56 rounded-xl border border-line bg-surface px-3 text-sm capitalize focus:border-plum focus:outline-none"
              >
                <option value="">Auto: Muse picks one</option>
                {taste?.genres.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </label>
          </div>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {draft.chips.map((c) => (
              <Badge key={c}>{MOOD_EMOJI[c]} {c}</Badge>
            ))}
            <Badge variant="sage">{intention.label}</Badge>
            <Badge variant="outline">{user ? "+ your Music DNA" : "mood only (not logged in)"}</Badge>
          </div>
        </div>
        <motion.div whileHover={canCurate ? { scale: 1.02 } : undefined}>
          <Button
            size="lg"
            disabled={!canCurate}
            onClick={() => {
              setDraft({ ...draft, exclude: [] }); // a fresh request, not "give me another"
              navigate("/curate");
            }}
            className="w-full sm:w-auto"
          >
            <Sparkles /> Curate my playlist <ArrowRight />
          </Button>
        </motion.div>
      </Card>

      {(recentSessions.length > 0 || playlists.length > 0) && (
        <section className="grid gap-6 lg:grid-cols-2">
          {recentSessions.length > 0 && (
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 font-display text-xl"><Clock className="size-4 text-plum" /> Recent sessions</h2>
              {recentSessions.slice(0, 3).map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setSession(s);
                    navigate("/results");
                  }}
                  className="flex w-full items-center justify-between rounded-2xl border border-line bg-surface px-4 py-3 text-left transition hover:border-lavender hover:shadow-soft"
                >
                  <div>
                    <div className="text-sm font-semibold capitalize">
                      {s.preview.mood.labels.join(", ") || "Your words"} · {intentionById(s.request.intention).label}
                    </div>
                    <div className="text-xs text-ink-soft">{s.preview.tracks.length} tracks · {shortDate(s.created_at)}</div>
                  </div>
                  <ArrowRight className="size-4 text-ink-soft" />
                </button>
              ))}
            </div>
          )}
          {playlists.length > 0 && (
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 font-display text-xl"><Music2 className="size-4 text-moss" /> Saved to Spotify</h2>
              {playlists.slice(0, 3).map((p) => (
                <a
                  key={p.id}
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between rounded-2xl border border-line bg-surface px-4 py-3 transition hover:border-sage hover:shadow-soft"
                >
                  <div>
                    <div className="text-sm font-semibold">{p.name}</div>
                    <div className="text-xs text-ink-soft">{p.track_count} tracks · {shortDate(p.created_at)}</div>
                  </div>
                  <ExternalLink className="size-4 text-moss" />
                </a>
              ))}
              <Link to="/history" className="-ml-3 inline-block rounded-full px-3 py-2 text-sm text-plum underline-offset-4 hover:underline">See all</Link>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
