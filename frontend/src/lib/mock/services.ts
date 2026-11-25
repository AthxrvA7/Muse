// Demo-mode versions of every service: same signatures, answers from mock data after a
// short delay. Lets the site be shown and developed without the backend.

import type { Services } from "../api/services";
import type {
  CuratedTrack,
  CuratePreview,
  Mode,
  MoodProfile,
  MoodRequest,
  MusicPreferences,
  Playlist,
} from "../types";
import {
  demoChips,
  demoGenrePoints,
  demoGenres,
  demoLanguages,
  demoPlaylists,
  demoPreferences,
  demoTrackPool,
  demoUser,
} from "./data";

const wait = <T,>(value: T, ms = 350) => new Promise<T>((resolve) => setTimeout(() => resolve(value), ms));

let preferences: MusicPreferences = { ...demoPreferences };
const playlists: Playlist[] = [...demoPlaylists];

function readMood(mood: MoodRequest): MoodProfile {
  const picked = demoChips.filter((chip) => mood.chips.includes(chip.id));
  const points = picked.length ? picked : [{ id: "neutral", valence: 0.5, energy: 0.5 }];
  let valence = points.reduce((sum, p) => sum + p.valence, 0) / points.length;
  let energy = points.reduce((sum, p) => sum + p.energy, 0) / points.length;
  const mode: Mode = mood.mode ?? "comfort";
  if (mode === "focus") energy = Math.min(0.55, Math.max(0.3, energy));
  if (mode === "energy") energy = Math.max(0.75, energy);
  valence = Math.round(valence * 100) / 100;
  energy = Math.round(energy * 100) / 100;
  return {
    valence,
    energy,
    tempo: energy < 0.35 ? "slow" : energy < 0.65 ? "medium" : "fast",
    mode,
    labels: picked.map((chip) => chip.id),
    confidence: picked.length ? 0.9 : 0.2,
    text_analysis: mood.text ? "keywords" : null,
    support: null,
  };
}

function curate(mood: MoodRequest, size: number): CuratePreview {
  const profile = readMood(mood);
  const feel = profile.labels.join(" and ") || "current";
  const weights = { comfort: [0.45, 0.55], focus: [0.55, 0.45], energy: [0.6, 0.4], discovery: [0.65, 0.35] };
  const [wMood, wTaste] = weights[profile.mode];
  const scored: CuratedTrack[] = demoTrackPool.map(([track, genre, favourite]) => {
    const point = genre ? demoGenrePoints[genre] : null;
    const distance = point ? Math.hypot(point.valence - profile.valence, point.energy - profile.energy) : null;
    const moodFit = distance === null ? 0.5 : 1 - distance / Math.SQRT2;
    const tasteFit = favourite ? 1 : genre && preferences.genres.includes(genre) ? 0.75 : 0.25;
    const reason = favourite
      ? `Picked because it's by ${track.artists[0].name}, one of your favourite artists.`
      : genre && preferences.genres.includes(genre)
        ? `Picked because it's ${demoGenrePoints[genre].name}, one of your genres${moodFit >= 0.75 ? `, and its feel fits your ${feel} mood` : ""}.`
        : `Picked because its ${point?.name ?? "overall"} feel fits your ${feel} mood.`;
    return {
      track,
      score: Math.round((wMood * moodFit + wTaste * tasteFit) * 1000) / 1000,
      mood_fit: Math.round(moodFit * 1000) / 1000,
      taste_fit: tasteFit,
      reason,
    };
  });
  scored.sort((a, b) => b.score - a.score);
  return {
    mood: profile,
    tracks: scored.slice(0, size),
    searches: 6,
    candidates_considered: demoTrackPool.length,
    taste_source: "saved_profile",
    note: size > demoTrackPool.length ? "Demo mode has a small track pool." : null,
  };
}

export const mockServices: Services = {
  auth: {
    loginUrl: "#/",
    me: () => wait(demoUser, 150),
    logout: () => wait(undefined),
  },
  preferences: {
    get: () => wait(preferences),
    save: (body) => {
      preferences = { ...body, updated_at: new Date().toISOString() };
      return wait(preferences);
    },
    dna: () => {
      const genres = preferences.genres.filter((g) => demoGenrePoints[g]).map((g) => demoGenrePoints[g]);
      const valence = genres.reduce((s, g) => s + g.valence, 0) / (genres.length || 1);
      const energy = genres.reduce((s, g) => s + g.energy, 0) / (genres.length || 1);
      const label = `${energy >= 0.5 ? "energetic" : "calm"} and ${valence >= 0.5 ? "warm" : "melancholic"}`;
      return wait({
        summary: `Your stated taste: ${preferences.artists.length} favourite artist(s), ${genres.length} genre(s), ${preferences.languages.length} language(s).${genres.length ? ` On average your genres feel ${label}.` : ""}`,
        top_artists: preferences.artists.slice(0, 5),
        genres,
        languages: preferences.languages.map((code) => ({ code, name: demoLanguages[code] ?? code })),
        styles: preferences.styles,
        mood_centre: genres.length ? { valence, energy, label } : null,
        reference_track_count: preferences.reference_tracks.length,
        exclusion_count: preferences.exclusions.length,
      });
    },
    options: () => wait({ genres: demoGenres, languages: demoLanguages }),
  },
  mood: {
    options: () =>
      wait({ chips: demoChips, modes: ["comfort", "focus", "energy", "discovery"] as Mode[], max_chips: 5, max_text_length: 500 }),
  },
  curation: {
    curate: (mood, size) => wait(curate(mood, size), 900),
  },
  catalog: {
    artists: (q) =>
      wait(
        ["Prateek Kuhad", "Anuv Jain", "Arijit Singh", "Phoebe Bridgers", "Lana Del Rey", "Ritviz"]
          .filter((name) => name.toLowerCase().includes(q.toLowerCase()))
          .map((name, i) => ({ id: `artist-${i}`, name, image_url: null })),
      ),
    tracks: (q) =>
      wait(demoTrackPool.map(([t]) => t).filter((t) => t.name.toLowerCase().includes(q.toLowerCase())).slice(0, 6)),
  },
  playlists: {
    list: () => wait([...playlists]),
    create: (name, trackIds) => {
      const playlist: Playlist = {
        id: `pl-demo-${playlists.length + 1}`,
        spotify_playlist_id: "demo",
        url: "https://open.spotify.com/",
        name,
        track_count: trackIds.length,
        created_at: new Date().toISOString(),
      };
      playlists.unshift(playlist);
      return wait(playlist, 700);
    },
  },
  privacy: {
    exportUrl: "#/settings",
    deleteAccount: () => wait(undefined),
  },
  health: {
    ready: () => wait("ready" as const, 100),
  },
};
