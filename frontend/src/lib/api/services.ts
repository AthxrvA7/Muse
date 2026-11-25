// One service per backend area. Components call these, never fetch() directly.
// In demo mode (`npm run dev:demo`, or VITE_DEMO=true) the same functions answer from mock data.

import { mockServices } from "../mock/services";
import type {
  Artist,
  CuratePreview,
  MoodOptions,
  MoodRequest,
  MusicDNA,
  MusicPreferences,
  Playlist,
  ReadyStatus,
  SpotifyTasteSuggestion,
  TasteOptions,
  Track,
  User,
} from "../types";
import { request } from "./client";

export const DEMO_MODE = import.meta.env.MODE === "demo" || import.meta.env.VITE_DEMO === "true";

const realServices = {
  auth: {
    loginUrl: "/api/v1/auth/login",
    me: () => request<User>("/api/v1/me"),
    logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  },
  preferences: {
    get: () => request<MusicPreferences>("/api/v1/preferences"),
    save: (body: Omit<MusicPreferences, "updated_at">) =>
      request<MusicPreferences>("/api/v1/preferences", { method: "PUT", body }),
    dna: () => request<MusicDNA>("/api/v1/preferences/dna"),
    fromSpotify: () => request<SpotifyTasteSuggestion>("/api/v1/preferences/from-spotify"),
    options: () => request<TasteOptions>("/api/v1/curate/options"),
  },
  mood: {
    options: () => request<MoodOptions>("/api/v1/mood/options"),
  },
  curation: {
    curate: (mood: MoodRequest, size: number) =>
      request<CuratePreview>("/api/v1/curate", { method: "POST", body: { mood, size } }),
  },
  catalog: {
    artists: (q: string) =>
      request<Artist[]>(`/api/v1/catalog/search?type=artist&limit=6&q=${encodeURIComponent(q)}`),
    tracks: (q: string) =>
      request<Track[]>(`/api/v1/catalog/search?type=track&limit=6&q=${encodeURIComponent(q)}`),
  },
  playlists: {
    list: () => request<Playlist[]>("/api/v1/playlists"),
    create: (name: string, trackIds: string[]) =>
      request<Playlist>("/api/v1/playlists", { method: "POST", body: { name, track_ids: trackIds } }),
  },
  privacy: {
    exportUrl: "/api/v1/me/data",
    deleteAccount: () => request<void>("/api/v1/me", { method: "DELETE" }),
  },
  health: {
    ready: async (): Promise<ReadyStatus> => {
      try {
        return (await request<{ status: ReadyStatus }>("/ready")).status;
      } catch {
        return "not_ready";
      }
    },
  },
};

export type Services = typeof realServices;
export const api: Services = DEMO_MODE ? mockServices : realServices;
