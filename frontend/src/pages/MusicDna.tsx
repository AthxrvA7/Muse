import { motion } from "framer-motion";
import { Disc3, CloudDownload, Loader2, Mic2, Save, Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { DnaChart } from "@/components/DnaChart";
import { LoginPrompt } from "@/components/LoginPrompt";
import { SearchBox } from "@/components/SearchBox";
import { TagInput } from "@/components/TagInput";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/services";
import type { Artist, MusicDNA, MusicPreferences, TasteOptions, Track } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const LIMITS = { artists: 10, genres: 10, languages: 5, styles: 10, reference_tracks: 10, exclusions: 20 };

function initials(name: string) {
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

export default function MusicDna() {
  const { user } = useApp();
  const [prefs, setPrefs] = useState<MusicPreferences | null>(null);
  const [options, setOptions] = useState<TasteOptions | null>(null);
  const [dna, setDna] = useState<MusicDNA | null>(null);
  const [artistImages, setArtistImages] = useState<Record<string, string | null | undefined>>({});
  const [trackNames, setTrackNames] = useState<Record<string, string>>({});
  const [genreQuery, setGenreQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.preferences.get(), api.preferences.options(), api.preferences.dna()])
      .then(([p, o, d]) => {
        setPrefs(p);
        setOptions(o);
        setDna(d);
      })
      .catch((e: Error) => setError(e.message));
  }, [user]);

  const update = (change: Partial<MusicPreferences>) => {
    setPrefs((p) => (p ? { ...p, ...change } : p));
    setDirty(true);
  };
  const toggle = (field: "genres" | "languages", value: string) => {
    if (!prefs) return;
    const list = prefs[field];
    if (list.includes(value)) update({ [field]: list.filter((v) => v !== value) });
    else if (list.length < LIMITS[field]) update({ [field]: [...list, value] });
    else toast.message(`Up to ${LIMITS[field]} ${field}`);
  };

  const searchArtists = useCallback((q: string) => api.catalog.artists(q), []);
  const searchTracks = useCallback((q: string) => api.catalog.tracks(q), []);

  const genres = useMemo(() => {
    if (!options || !prefs) return [];
    const q = genreQuery.trim().toLowerCase();
    return [...options.genres]
      .filter((g) => !q || g.name.toLowerCase().includes(q))
      .sort((a, b) => Number(prefs.genres.includes(b.id)) - Number(prefs.genres.includes(a.id)));
  }, [options, prefs, genreQuery]);

  // Fills the form from Spotify top artists. Nothing is saved until the user presses Save.
  async function importFromSpotify() {
    if (!prefs) return;
    setImporting(true);
    try {
      const s = await api.preferences.fromSpotify();
      if (!s.artists.length) {
        toast.message("Spotify has no top artists for you yet", { description: "Listen a bit more, or add artists yourself." });
        return;
      }
      update({
        artists: s.artists.slice(0, LIMITS.artists),
        ...(s.genres.length ? { genres: s.genres.slice(0, LIMITS.genres) } : {}),
        ...(s.languages.length ? { languages: s.languages.slice(0, LIMITS.languages) } : {}),
      });
      toast.success(`Imported ${s.artists.length} artists from Spotify`, {
        description: "Check them, change anything you like, then press Save my taste.",
      });
    } catch (e) {
      if (e instanceof ApiError && e.code === "relogin_needed") {
        toast.message("One more permission needed", {
          description: "Log in with Spotify again to let Muse read your top artists.",
          action: { label: "Log in again", onClick: () => window.location.assign(api.auth.loginUrl) },
        });
      } else {
        toast.error("Couldn't import from Spotify", { description: (e as Error).message });
      }
    } finally {
      setImporting(false);
    }
  }

  async function save() {
    if (!prefs) return;
    setSaving(true);
    try {
      const { updated_at: _ignored, ...body } = prefs;
      void _ignored;
      const saved = await api.preferences.save(body);
      setPrefs(saved);
      setDna(await api.preferences.dna());
      setDirty(false);
      toast.success("Music DNA saved", { description: "Curate for me will use it from now on." });
    } catch (e) {
      toast.error("Couldn't save", { description: (e as Error).message });
    } finally {
      setSaving(false);
    }
  }

  if (user === null) return <LoginPrompt title="Your Music DNA lives with your Spotify login" />;

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-4xl sm:text-5xl">Your Music DNA</h1>
          <p className="mt-2 text-ink-soft">Your taste, the way you describe it. Start from your Spotify top artists, then make it yours.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="lg" variant="outline" onClick={importFromSpotify} disabled={!prefs || importing}>
            {importing ? <Loader2 className="animate-spin" /> : <CloudDownload />} Import from Spotify
          </Button>
          <Button size="lg" onClick={save} disabled={!prefs || saving || !dirty}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />} {dirty ? "Save my taste" : "Saved"}
          </Button>
        </div>
      </header>
      {error && <p className="rounded-2xl bg-danger-soft p-4 text-sm text-danger">{error}</p>}

      <Card className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <CardTitle>Taste map</CardTitle>
          <CardDescription>Each genre sits on the same mood map Muse uses to match music to how you feel. The green dot is your centre.</CardDescription>
          {dna ? (dna.genres.length ? <DnaChart dna={dna} /> : <p className="mt-10 text-center text-sm text-ink-soft">Add genres to see your map.</p>) : <Skeleton className="mt-4 h-72" />}
        </div>
        <div className="space-y-4">
          {dna ? (
            <>
              <p className="font-display text-xl leading-snug">{dna.summary}</p>
              {dna.mood_centre && (
                <div className="rounded-2xl bg-sage-soft p-4 text-sm text-moss">
                  On average your genres feel <strong>{dna.mood_centre.label}</strong>.
                </div>
              )}
              <div className="flex flex-wrap gap-1.5">
                {dna.languages.map((l) => <Badge key={l.code} variant="sage">{l.name}</Badge>)}
                {dna.styles.map((s) => <Badge key={s} variant="outline">{s}</Badge>)}
              </div>
              <p className="text-xs text-ink-soft">Saved changes update this summary.</p>
            </>
          ) : (
            <Skeleton className="h-40" />
          )}
        </div>
      </Card>

      {!prefs || !options ? (
        <div className="grid gap-4 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-48" />)}</div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="space-y-4 md:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2"><Mic2 className="size-4 text-plum" /> Favourite artists</CardTitle>
                <CardDescription>Search Spotify and add up to {LIMITS.artists}.</CardDescription>
              </div>
              <Badge variant="outline">{prefs.artists.length}/{LIMITS.artists}</Badge>
            </div>
            {prefs.artists.length < LIMITS.artists && (
              <SearchBox<Artist>
                label="Search artists"
                placeholder="Search artists on Spotify…"
                search={searchArtists}
                itemKey={(a) => a.id}
                onPick={(a) => {
                  if (!prefs.artists.some((x) => x.toLowerCase() === a.name.toLowerCase())) update({ artists: [...prefs.artists, a.name] });
                  setArtistImages((m) => ({ ...m, [a.name]: a.image_url }));
                }}
                render={(a) => (
                  <>
                    {a.image_url ? <img src={a.image_url} alt="" className="size-10 rounded-full object-cover" /> : <span className="grid size-10 place-items-center rounded-full bg-lavender-soft text-xs font-semibold text-plum">{initials(a.name)}</span>}
                    <span className="text-sm font-medium">{a.name}</span>
                  </>
                )}
              />
            )}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {prefs.artists.map((name) => (
                <motion.div layout key={name} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="group relative flex flex-col items-center gap-2 rounded-2xl border border-line bg-lavender-faint/40 p-4 text-center">
                  {artistImages[name] ? <img src={artistImages[name] ?? ""} alt="" className="size-16 rounded-full object-cover shadow-soft" /> : <span className="grid size-16 place-items-center rounded-full bg-gradient-to-br from-lavender to-sage text-lg font-semibold text-white">{initials(name)}</span>}
                  <span className="text-sm font-medium">{name}</span>
                  <button type="button" onClick={() => update({ artists: prefs.artists.filter((a) => a !== name) })} className="absolute right-2 top-2 rounded-full bg-surface p-1 text-ink-soft opacity-0 shadow-soft transition group-hover:opacity-100 focus:opacity-100" aria-label={`Remove ${name}`}>
                    <X className="size-3.5" />
                  </button>
                </motion.div>
              ))}
            </div>
          </Card>

          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <CardTitle>Genres</CardTitle>
              <Badge variant="outline">{prefs.genres.length}/{LIMITS.genres}</Badge>
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-ink-soft" />
              <Input value={genreQuery} onChange={(e) => setGenreQuery(e.target.value)} placeholder="Search genres…" className="pl-10" aria-label="Search genres" />
            </div>
            <div className="flex max-h-64 flex-wrap gap-2 overflow-y-auto pr-1">
              {genres.map((g) => {
                const on = prefs.genres.includes(g.id);
                return (
                  <motion.button layout key={g.id} type="button" whileTap={{ scale: 0.95 }} onClick={() => toggle("genres", g.id)} aria-pressed={on}
                    className={cn("rounded-full border px-3.5 py-1.5 text-sm transition", on ? "border-plum bg-plum text-on-accent shadow-soft" : "border-line bg-surface hover:border-lavender hover:bg-lavender-faint")}>
                    {g.name}
                  </motion.button>
                );
              })}
            </div>
          </Card>

          <Card className="space-y-4">
            <CardTitle>Languages</CardTitle>
            <div className="flex flex-wrap gap-2">
              {Object.entries(options.languages).map(([code, name]) => {
                const on = prefs.languages.includes(code);
                return (
                  <button key={code} type="button" onClick={() => toggle("languages", code)} aria-pressed={on}
                    className={cn("rounded-full border px-3.5 py-1.5 text-sm transition", on ? "border-moss bg-sage-soft font-medium text-moss" : "border-line bg-surface hover:border-sage")}>
                    {name}
                  </button>
                );
              })}
            </div>
            <div className="space-y-2 pt-2">
              <CardTitle className="text-base">Styles you like</CardTitle>
              <TagInput label="Add a style" values={prefs.styles} max={LIMITS.styles} placeholder="acoustic, soft vocals… press Enter" onChange={(styles) => update({ styles })} />
            </div>
          </Card>

          <Card className="space-y-4">
            <div>
              <CardTitle className="flex items-center gap-2"><Disc3 className="size-4 text-plum" /> Reference tracks</CardTitle>
              <CardDescription>Songs that sum up your taste.</CardDescription>
            </div>
            {prefs.reference_tracks.length < LIMITS.reference_tracks && (
              <SearchBox<Track>
                label="Search tracks"
                placeholder="Search a song…"
                search={searchTracks}
                itemKey={(t) => t.id}
                onPick={(t) => {
                  if (!prefs.reference_tracks.includes(t.id)) update({ reference_tracks: [...prefs.reference_tracks, t.id] });
                  setTrackNames((m) => ({ ...m, [t.id]: `${t.name} · ${t.artists[0]?.name ?? ""}` }));
                }}
                render={(t) => (
                  <>
                    {t.image_url ? <img src={t.image_url} alt="" className="size-10 rounded-lg object-cover" /> : <span className="size-10 rounded-lg bg-gradient-to-br from-lavender to-sage" />}
                    <span className="min-w-0 text-sm"><span className="block truncate font-medium">{t.name}</span><span className="block truncate text-xs text-ink-soft">{t.artists.map((a) => a.name).join(", ")}</span></span>
                  </>
                )}
              />
            )}
            <ul className="space-y-1.5">
              {prefs.reference_tracks.map((id) => (
                <li key={id} className="flex items-center justify-between rounded-xl bg-lavender-faint px-3 py-2 text-sm">
                  <span className="truncate">{trackNames[id] ?? `Spotify track ${id.slice(0, 6)}…`}</span>
                  <button type="button" onClick={() => update({ reference_tracks: prefs.reference_tracks.filter((x) => x !== id) })} className="rounded-full p-1 text-ink-soft hover:text-danger" aria-label="Remove track"><X className="size-3.5" /></button>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="space-y-4">
            <div>
              <CardTitle>Never play</CardTitle>
              <CardDescription>Artists Muse should always leave out.</CardDescription>
            </div>
            <TagInput label="Add an artist to exclude" values={prefs.exclusions} max={LIMITS.exclusions} placeholder="Artist name… press Enter" onChange={(exclusions) => update({ exclusions })} />
          </Card>
        </div>
      )}
    </div>
  );
}
