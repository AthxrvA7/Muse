// Demo-mode data (VITE_DEMO=true). Mood and genre positions are copied from the backend's
// mood_map.json and genre_kb.json so the demo behaves like the real thing. Tracks are made up.

import type { Genre, MoodChip, MusicPreferences, Playlist, Track, User } from "../types";

export const demoUser: User = {
  id: "demo-user",
  spotify_id: "demo",
  display_name: "Demo listener",
  created_at: "2026-11-01T10:00:00Z",
  last_login_at: "2026-11-25T18:00:00Z",
};

const chipRows: [string, number, number][] = [
  ["angry", 0.12, 0.88], ["anxious", 0.25, 0.75], ["bored", 0.35, 0.28], ["calm", 0.65, 0.2],
  ["confident", 0.78, 0.7], ["dreamy", 0.62, 0.3], ["energetic", 0.7, 0.85], ["focused", 0.55, 0.5],
  ["frustrated", 0.2, 0.75], ["grateful", 0.82, 0.4], ["happy", 0.85, 0.65], ["heartbroken", 0.1, 0.35],
  ["hyped", 0.8, 0.92], ["lonely", 0.2, 0.3], ["low", 0.22, 0.25], ["nostalgic", 0.5, 0.32],
  ["relaxed", 0.7, 0.25], ["romantic", 0.78, 0.45], ["stressed", 0.25, 0.7], ["tired", 0.4, 0.15],
];
export const demoChips: MoodChip[] = chipRows.map(([id, valence, energy]) => ({ id, valence, energy }));

const genreRows: [string, string, number, number, string[]][] = [
  ["indie folk", "indie folk", 0.5, 0.3, ["en"]], ["acoustic", "acoustic", 0.55, 0.25, ["en"]],
  ["dream pop", "dream pop", 0.55, 0.35, ["en"]], ["indie pop", "indie pop", 0.65, 0.5, ["en"]],
  ["lo-fi", "lo-fi", 0.55, 0.2, []], ["jazz", "jazz", 0.6, 0.35, []], ["soul", "soul", 0.6, 0.45, ["en"]],
  ["r&b", "R&B", 0.6, 0.5, ["en"]], ["pop", "pop", 0.75, 0.65, ["en"]], ["rock", "rock", 0.55, 0.75, ["en"]],
  ["edm", "EDM", 0.75, 0.9, []], ["ambient", "ambient", 0.5, 0.1, []], ["bollywood", "Bollywood", 0.65, 0.6, ["hi"]],
  ["hindi indie", "Hindi indie", 0.5, 0.4, ["hi"]], ["sufi", "Sufi", 0.45, 0.4, ["hi", "ur", "pa"]],
  ["ghazal", "ghazal", 0.35, 0.2, ["ur", "hi"]], ["punjabi pop", "Punjabi pop", 0.8, 0.8, ["pa"]],
  ["k-pop", "K-pop", 0.8, 0.75, ["ko"]],
];
export const demoGenrePoints = Object.fromEntries(
  genreRows.map(([id, name, valence, energy]) => [id, { id, name, valence, energy }]),
);
export const demoGenres: Genre[] = genreRows.map(([id, name, , , languages]) => ({ id, name, languages }));
export const demoLanguages: Record<string, string> = {
  en: "English", hi: "Hindi", pa: "Punjabi", ur: "Urdu", mr: "Marathi", ko: "Korean",
};

export const demoPreferences: MusicPreferences = {
  artists: ["Prateek Kuhad", "Anuv Jain", "Phoebe Bridgers"],
  genres: ["indie folk", "hindi indie", "lo-fi"],
  languages: ["hi", "en"],
  styles: ["acoustic", "soft vocals"],
  reference_tracks: [],
  exclusions: [],
  updated_at: "2026-11-24T19:30:00Z",
};

function track(id: string, name: string, artist: string, album: string, minutes: number): Track {
  return {
    id,
    name,
    artists: [{ id: `${id}-a`, name: artist }],
    album,
    release_year: 2020,
    image_url: null,
    spotify_url: "https://open.spotify.com/",
    uri: `spotify:track:${id}`,
    explicit: false,
    duration_ms: Math.round(minutes * 60000),
  };
}

// [track, genre it came from (or null for a favourite artist), favourite artist?]
export const demoTrackPool: [Track, string | null, boolean][] = [
  [track("d1", "Paper Lanterns", "Rhea Sol", "Quiet Hours", 3.6), "indie folk", false],
  [track("d2", "Window Seat Rain", "Prateek Kuhad", "Demo Sessions", 3.9), null, true],
  [track("d3", "Kites Over Bandra", "Anuv Jain", "Demo Sessions", 3.2), null, true],
  [track("d4", "Soft Static", "Mira Holt", "Low Light", 2.8), "lo-fi", false],
  [track("d5", "Shaam Ka Rang", "Ira Kapoor", "Dhoop", 4.1), "hindi indie", false],
  [track("d6", "Lullaby for Tuesdays", "Phoebe Bridgers", "Demo Sessions", 3.5), null, true],
  [track("d7", "Cedar & Smoke", "The Larches", "Northbound", 3.4), "indie folk", false],
  [track("d8", "Late Bus Home", "Kabir Sen", "City Lights", 3.7), "hindi indie", false],
  [track("d9", "Tape Hiss Dreams", "Nocturne Kid", "Bedroom Tapes", 2.5), "lo-fi", false],
  [track("d10", "Gentle Harbour", "Elin Rowe", "Tidelines", 4.0), "acoustic", false],
  [track("d11", "Neend", "Zoya Mir", "Raat", 4.4), "ghazal", false],
  [track("d12", "Blue Hour Walk", "Sam Okoro", "Evening Notes", 3.1), "jazz", false],
  [track("d13", "Sunroom", "Hollow Pines", "Greenhouse", 3.3), "dream pop", false],
  [track("d14", "Chai at 2am", "Aarav Das", "Night Shift", 2.9), "lo-fi", false],
  [track("d15", "Small Victories", "June Alder", "Daylight", 3.6), "indie pop", false],
  [track("d16", "Rooftop Static", "Neon Fern", "Pulse", 3.8), "edm", false],
  [track("d17", "Monsoon Letters", "Ira Kapoor", "Dhoop", 4.3), "hindi indie", false],
  [track("d18", "Quiet Fire", "Ana Reyes", "Embers", 3.4), "soul", false],
];

export const demoPlaylists: Playlist[] = [
  {
    id: "pl-demo-1",
    spotify_playlist_id: "demo1",
    url: "https://open.spotify.com/",
    name: "Muse: tired and low",
    track_count: 15,
    created_at: "2026-11-24T21:10:00Z",
  },
  {
    id: "pl-demo-2",
    spotify_playlist_id: "demo2",
    url: "https://open.spotify.com/",
    name: "Muse: focused",
    track_count: 12,
    created_at: "2026-11-22T10:05:00Z",
  },
];
