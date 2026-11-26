// Demo-mode versions of every service: same signatures, answers from mock data after a
// short delay. Lets the site be shown and developed without the backend.

import type { Services } from "../api/services";
import type {
  CuratedTrack,
  CurateOptions,
  CuratePreview,
  Mode,
  MoodPoint,
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
import { summarise as summariseMoods } from "../trajectory";

const wait = <T,>(value: T, ms = 350) => new Promise<T>((resolve) => setTimeout(() => resolve(value), ms));

let preferences: MusicPreferences = { ...demoPreferences };
const playlists: Playlist[] = [...demoPlaylists];
const demoRatings: Record<string, 1 | -1> = {};

// A believable fortnight of moods for the trajectory: stressed weekdays, lighter evenings.
const DEMO_MOODS: [number, number, number, string[]][] = [
  [13, 9, 0.32, ["stressed", "tired"]], [12, 22, 0.45, ["calm"]], [11, 8, 0.28, ["anxious"]],
  [10, 20, 0.55, ["relaxed"]], [9, 23, 0.25, ["low", "lonely"]], [8, 18, 0.62, ["happy"]],
  [7, 10, 0.38, ["focused"]], [6, 21, 0.58, ["nostalgic"]], [5, 9, 0.42, ["tired"]],
  [4, 19, 0.7, ["happy", "energetic"]], [3, 13, 0.66, ["confident"]], [2, 22, 0.52, ["dreamy"]],
  [1, 8, 0.6, ["focused"]], [0, 18, 0.78, ["hyped"]],
];
let demoMoodsOn = true;
let demoMoods: MoodPoint[] = DEMO_MOODS.map(([daysAgo, hour, valence, labels], i) => {
  const at = new Date();
  at.setDate(at.getDate() - daysAgo);
  at.setHours(hour, (i * 17) % 60, 0, 0);
  const energy = Math.min(0.95, Math.max(0.1, 0.3 + (i % 5) * 0.13));
  return { at: at.toISOString(), valence, energy, labels, mode: "comfort" };
});

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

function curate(mood: MoodRequest, size: number, options: CurateOptions = {}): CuratePreview {
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
      known: favourite,
      tags: [],
      bpm: point ? Math.round(70 + point.energy * 80) : null,
      tempo: point ? (point.energy < 0.35 ? "slow" : point.energy > 0.7 ? "fast" : "medium") : null,
      genre: point?.name ?? null,
      language: null,
    };
  });
  scored.sort((a, b) => b.score - a.score);
  return {
    mood: profile,
    tracks: scored.filter((t) => !options.exclude?.includes(t.track.id)).slice(0, size),
    searches: 6,
    candidates_considered: demoTrackPool.length,
    taste_source: "saved_profile",
    note: size > demoTrackPool.length ? "Demo mode has a small track pool." : null,
    familiarity: options.familiarity ?? 0.7,
    personal: true,
    mood_data: "estimated",
    similar_artists: ["Anuv Jain", "The Local Train"],
    language: options.language && options.language !== "auto" && options.language !== "mix" ? options.language : "en",
    genre: options.genre ?? "indie folk",
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
    fromSpotify: () =>
      wait(
        {
          artists: ["Arijit Singh", "Prateek Kuhad", "The Local Train", "Taylor Swift", "Anuv Jain"],
          genres: ["bollywood", "hindi indie", "pop"],
          languages: ["hi", "en"],
          source: "Your top artists on Spotify (about the last 6 months)",
          saved: false,
        },
        500,
      ),
    options: () => wait({ genres: demoGenres, languages: demoLanguages }),
  },
  mood: {
    options: () =>
      wait({ chips: demoChips, modes: ["comfort", "focus", "energy", "discovery"] as Mode[], max_chips: 5, max_text_length: 500 }),
  },
  curation: {
    curate: (mood, size, options) => wait(curate(mood, size, options), 900),
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
        cover: "none",
      };
      playlists.unshift(playlist);
      return wait(playlist, 700);
    },
  },
  moods: {
    trajectory: (days) => {
      const since = Date.now() - days * 86400000;
      const points = demoMoods.filter((p) => new Date(p.at).getTime() >= since);
      return wait({ ...summariseMoods(points, days), enabled: demoMoodsOn });
    },
    clear: () => {
      demoMoods = [];
      return wait(undefined, 200);
    },
    setEnabled: (enabled) => {
      demoMoodsOn = enabled;
      return wait(undefined, 200);
    },
  },
  feedback: {
    rate: (rating) => {
      if (rating.value === 0) delete demoRatings[rating.track_id];
      else demoRatings[rating.track_id] = rating.value;
      return wait(undefined, 200);
    },
    learned: () => {
      const values = Object.values(demoRatings);
      return wait({
        likes: values.filter((v) => v > 0).length,
        dislikes: values.filter((v) => v < 0).length,
        liked_artists: [],
        avoided_artists: [],
        ratings: { ...demoRatings },
      });
    },
    forget: () => {
      Object.keys(demoRatings).forEach((k) => delete demoRatings[k]);
      return wait(undefined, 200);
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
