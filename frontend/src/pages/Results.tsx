import { AnimatePresence } from "framer-motion";
import { Clock, Gauge, HeartHandshake, ListMusic, LogIn, RefreshCw, Shuffle, Undo2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router";

import { Artwork } from "@/components/Artwork";
import { SaveToSpotify } from "@/components/SaveToSpotify";
import { TrackRow } from "@/components/TrackRow";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import { percent, playlistName, playlistTitle, totalDuration } from "@/lib/format";
import { intentionById, MODE_LABEL } from "@/lib/intentions";
import { MOOD_EMOJI } from "@/lib/moods";
import { useApp } from "@/state/AppState";

const SOURCE = {
  saved_profile: "Your Music DNA",
  request: "The taste you sent",
  none: "Mood only",
};

export default function Results() {
  const navigate = useNavigate();
  const { session, user, setDraft } = useApp();
  const [removed, setRemoved] = useState<Set<string>>(new Set());

  const tracks = useMemo(
    () => (session ? session.preview.tracks.filter((t) => !removed.has(t.track.id)) : []),
    [session, removed],
  );
  if (!session) return <Navigate to="/" replace />;

  const { preview, request } = session;
  const { mood } = preview;
  const intention = intentionById(request.intention);

  function regenerate() {
    setDraft({ chips: request.chips, text: request.text, intention: request.intention, size: request.size });
    navigate("/curate");
  }

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-6 sm:flex-row sm:items-end">
        <Artwork tracks={preview.tracks} className="aspect-square w-44 shrink-0 sm:w-52" />
        <div className="min-w-0 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-plum">Your Muse playlist</p>
          <h1 className="font-display text-3xl leading-tight sm:text-5xl">{playlistTitle(mood.valence, mood.energy)}</h1>
          <p className="text-ink-soft">Curated around your mood, your taste, and what you need right now.</p>
          <div className="flex flex-wrap gap-1.5">
            {mood.labels.map((label) => (
              <Badge key={label} className="capitalize">{MOOD_EMOJI[label] ?? "🎵"} {label}</Badge>
            ))}
            <Badge variant="sage"><HeartHandshake /> {intention.label}</Badge>
            <Badge variant="outline"><ListMusic /> {tracks.length} tracks</Badge>
            <Badge variant="outline"><Clock /> {totalDuration(tracks.map((t) => t.track.duration_ms))}</Badge>
          </div>
        </div>
      </section>

      {mood.support && (
        <Card className="border-amber-300 bg-amber-soft">
          <p className="font-medium text-ink">{mood.support.message}</p>
          <ul className="mt-2 space-y-1 text-sm text-ink">
            {mood.support.resources.map((r) => (
              <li key={r.name}><strong>{r.name}</strong>: {r.phone}{r.availability ? ` (${r.availability})` : ""}</li>
            ))}
          </ul>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {user ? (
          <SaveToSpotify defaultName={playlistName(mood.labels, mood.mode)} trackIds={tracks.map((t) => t.track.id)} />
        ) : (
          <Button asChild variant="spotify" size="lg">
            <a href={api.auth.loginUrl}><LogIn /> Connect Spotify to save</a>
          </Button>
        )}
        <Button variant="outline" onClick={regenerate}><RefreshCw /> Regenerate</Button>
        <Button
          variant="outline"
          onClick={() => {
            setDraft({ ...request, intention: "escape" });
            navigate("/curate");
          }}
        >
          <Shuffle /> More like this, but new
        </Button>
        <Button variant="ghost" onClick={() => navigate("/")}><Undo2 /> Change mood</Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_260px]">
        <Card className="p-2 sm:p-3">
          {preview.note && <p className="m-3 rounded-2xl bg-amber-soft px-4 py-3 text-sm text-amber">{preview.note}</p>}
          {removed.size > 0 && (
            <div className="m-2 flex items-center justify-between rounded-2xl bg-lavender-faint px-4 py-2 text-sm">
              <span>{removed.size} removed</span>
              <button type="button" className="font-medium text-plum hover:underline" onClick={() => setRemoved(new Set())}>Undo</button>
            </div>
          )}
          <ol className="space-y-1">
            <AnimatePresence initial={false}>
              {tracks.map((item, i) => (
                <TrackRow
                  key={item.track.id}
                  item={item}
                  index={i}
                  onRemove={() => setRemoved((r) => new Set(r).add(item.track.id))}
                />
              ))}
            </AnimatePresence>
          </ol>
        </Card>

        <aside className="space-y-4">
          <Card className="space-y-4 p-5">
            <h2 className="flex items-center gap-2 font-semibold"><Gauge className="size-4 text-plum" /> What Muse heard</h2>
            {[
              ["Positivity", mood.valence],
              ["Energy", mood.energy],
            ].map(([label, value]) => (
              <div key={label as string} className="space-y-1">
                <div className="flex justify-between text-xs text-ink-soft"><span>{label}</span><span>{percent(value as number)}</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-lavender-faint">
                  <div className="h-full rounded-full bg-gradient-to-r from-plum-muted to-plum" style={{ width: percent(value as number) }} />
                </div>
              </div>
            ))}
            <dl className="grid grid-cols-2 gap-y-2 text-xs">
              <dt className="text-ink-soft">Mode</dt><dd className="text-right font-medium">{MODE_LABEL[mood.mode]}</dd>
              <dt className="text-ink-soft">Tempo</dt><dd className="text-right font-medium capitalize">{mood.tempo}</dd>
              <dt className="text-ink-soft">Confidence</dt><dd className="text-right font-medium">{percent(mood.confidence)}</dd>
              <dt className="text-ink-soft">Taste used</dt><dd className="text-right font-medium">{SOURCE[preview.taste_source]}</dd>
              <dt className="text-ink-soft">Searched</dt><dd className="text-right font-medium">{preview.candidates_considered} songs</dd>
            </dl>
          </Card>
          <p className="px-2 text-xs leading-relaxed text-ink-soft">
            Each track is scored on how well its feel matches your mood and how close it is to the taste you described. Open a track to see why it was picked.
          </p>
        </aside>
      </div>
    </div>
  );
}
