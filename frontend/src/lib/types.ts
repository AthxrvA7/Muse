// Shapes of the Muse API (FastAPI backend). Kept in one place so the UI, the real
// services and the demo-mode mocks all agree.

export type Mode = "comfort" | "focus" | "energy" | "discovery";
export type Tempo = "slow" | "medium" | "fast";

export interface User {
  id: string;
  spotify_id: string;
  display_name: string | null;
  created_at: string;
  last_login_at: string;
}

export interface Artist {
  id: string;
  name: string;
  image_url?: string | null;
}

export interface Track {
  id: string;
  name: string;
  artists: Artist[];
  album: string;
  release_year?: number | null;
  image_url: string | null;
  spotify_url: string;
  uri: string;
  explicit: boolean;
  duration_ms: number;
}

export interface Genre {
  id: string;
  name: string;
  languages: string[];
}

export interface TasteOptions {
  genres: Genre[];
  languages: Record<string, string>;
}

export interface MoodChip {
  id: string;
  valence: number;
  energy: number;
}

export interface MoodOptions {
  chips: MoodChip[];
  modes: Mode[];
  max_chips: number;
  max_text_length: number;
}

export interface MoodRequest {
  chips: string[];
  text?: string;
  mode?: Mode;
}

export interface SupportNotice {
  message: string;
  resources: { name: string; phone: string; availability?: string }[];
}

/** How Muse read the mood: a point on the valence-energy map plus context. */
export interface MoodProfile {
  valence: number;
  energy: number;
  tempo: Tempo;
  mode: Mode;
  labels: string[];
  confidence: number;
  text_analysis: "classifier" | "keywords" | null;
  support?: SupportNotice | null;
}

/** One recommended track and why it was picked (the recommendation explanation). */
export interface CuratedTrack {
  track: Track;
  score: number;
  mood_fit: number;
  taste_fit: number;
  reason: string;
  known?: boolean; // the listener already plays it, or it's by a favourite artist
  tags?: string[]; // Last.fm listener tags about its feel
  bpm?: number | null; // tempo in beats per minute (Deezer)
  tempo?: Tempo | null;
  genre?: string | null; // the song's genre name, when known
  preview_id?: number | null; // Deezer ID: play at /api/v1/previews/{id}
  language?: string | null; // ISO code, when known
}

export interface CuratePreview {
  mood: MoodProfile;
  tracks: CuratedTrack[];
  searches: number;
  candidates_considered: number;
  taste_source: "request" | "saved_profile" | "none";
  note: string | null;
  familiarity?: number; // share of known songs aimed for
  personal?: boolean; // the listener's Spotify top tracks were used
  mood_data?: "lastfm" | "estimated";
  similar_artists?: string[];
  language?: string | null; // the playlist's language (null: mixed or unknown)
  genre?: string | null; // genre id the playlist is built around
  coverage?: {
    candidates: number;
    with_mood: number;
    with_language: number;
    with_genre: number;
    with_tempo: number;
  };
}

/** Extra knobs for one curation. */
export interface CurateOptions {
  familiarity?: number | null; // null/undefined: the mode's default
  exclude?: string[]; // track IDs to leave out (Give me another)
  language?: string; // "auto" | "mix" | a language code
  genre?: string | null; // genre id to build around; null: Muse chooses
}

export interface MusicPreferences {
  artists: string[];
  genres: string[];
  languages: string[];
  styles: string[];
  reference_tracks: string[];
  exclusions: string[];
  updated_at?: string | null;
}

/** A taste profile suggested from the user's Spotify top artists. Not saved until the user saves it. */
export interface SpotifyTasteSuggestion {
  artists: string[];
  genres: string[];
  languages: string[];
  source: string;
  saved: boolean;
}

export interface MusicDNA {
  summary: string;
  top_artists: string[];
  genres: { id: string; name: string; valence: number; energy: number }[];
  languages: { code: string; name: string }[];
  styles: string[];
  mood_centre: { valence: number; energy: number; label: string } | null;
  reference_track_count: number;
  exclusion_count: number;
}

/** A playlist Muse created in the user's Spotify account. */
export interface Playlist {
  id: string;
  spotify_playlist_id: string;
  url: string;
  name: string;
  track_count: number;
  created_at: string;
}

/** One "curate for me" run, kept in this browser so Results and Discover can show it. */
export interface MuseSession {
  id: string;
  created_at: string;
  request: {
    chips: string[];
    text: string;
    intention: string;
    size: number;
    familiarity?: number | null;
    exclude?: string[];
    language?: string;
    genre?: string | null;
  };
  preview: CuratePreview;
}

export type ReadyStatus = "ready" | "degraded" | "not_ready";
