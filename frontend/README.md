# Muse website (frontend)

**Owner:** Piyush (frontend, UI/UX, monitoring)

React 19, TypeScript, Vite, Tailwind CSS 4, shadcn-style components (Radix), Framer Motion, Lucide icons, React Router, Recharts.

The built site is served by the Muse backend at **`/app/`**, from the same server as the API. The browser talks to one origin, so the Spotify login cookie works without CORS, and the backend's Origin check and Content-Security-Policy protect it.

## The journey

**Music DNA → current mood → listening intention → Muse curation → personalised playlist**

| Page | What it does | API |
|---|---|---|
| **Discover** (`#/`) | Greeting; mood cards (up to 5); "tell Muse what you're feeling"; **listening intention**, separate from the mood; playlist length; recent sessions and saved playlists | `GET /mood/options`, `GET /playlists` |
| **Curate** (`#/curate`) | A five-step progress view that mirrors what the backend does: understand the mood, map a musical direction, match your Music DNA, find tracks, curate | `POST /curate` |
| **Playlist results** (`#/results`) | Title, artwork, mood, intention, track count and duration; every track with art, artist, album and duration; open a track to see **why Muse picked it** (mood fit, taste fit); remove tracks; regenerate; **Create in Spotify** | `POST /playlists` |
| **My Music DNA** (`#/dna`) | Taste map (your genres on the valence-energy map, with your centre); favourite artists from Spotify search (with photos); genre bubbles with search; languages; styles; reference tracks; artists to exclude | `GET/PUT /preferences`, `GET /preferences/dna`, `GET /catalog/search` |
| **History** (`#/history`) | Timeline of playlists saved to Spotify plus recent curations from this browser; filter by text, date range and mood | `GET /playlists` |
| **Settings** (`#/settings`) | Spotify connection, log out, edit taste, clear this browser's history, **download my data**, **delete my account** | `GET /me/data`, `DELETE /me`, `POST /auth/logout` |

The footer and sidebar show a live health light from `GET /ready` (monitoring).

### What we kept honest

- **Listening intentions** map onto the backend's four real modes: comfort, focus, energy and discovery. Each card says which mode it uses.
- **Like/dislike** is the Phase 3 feedback loop, so those buttons are disabled with a "coming in Phase 3" tooltip.
- **History** shows saved playlists, plus recent curations kept only in this browser (without the mood text).
- Logged out, curation still works from the mood alone. Saving, Music DNA and history ask you to connect Spotify.

## Run it

Needs **Node.js 22.6+** (the LTS from nodejs.org is fine).

```powershell
cd frontend
npm ci
npm run dev:demo     # demo mode: mock data, no backend needed -> http://localhost:5173/app/
```

**With the real backend:**

```powershell
npm run build        # creates frontend/dist
cd ../backend
$env:FRONTEND_DIST = "../frontend/dist"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000/app/**. Use `127.0.0.1`, not `localhost`, so the login cookie matches Spotify's redirect URI. Set `POST_LOGIN_REDIRECT=/app/` in `.env` so logging in lands on the website. For live reload against the real backend, keep uvicorn running and use `npm run dev`; it proxies `/api` to port 8000.

## Checks (also run in CI)

```powershell
npm run lint        # ESLint + typescript-eslint + React hooks rules
npm run typecheck   # TypeScript, strict
npm test            # unit tests for helpers and intentions (Node's built-in test runner)
npm run build       # type check + production build
```

## Structure

```
src/
  App.tsx                 routes (hash routing: /app/#/dna works on refresh)
  state/AppState.tsx      login, health, current draft and session, recent sessions
  lib/types.ts            TypeScript shapes of the API (User, Track, Mood, Playlist, ...)
  lib/api/client.ts       fetch wrapper; turns API errors into readable messages
  lib/api/services.ts     one service per backend area; swaps to mocks in demo mode
  lib/mock/               demo data and mock services (positions copied from the backend)
  lib/intentions.ts       listening intentions -> backend modes
  lib/format.ts           small pure helpers
  components/ui/          Button, Card, Badge, Input, Dialog, Tooltip, Skeleton
  components/             Layout, MoodPicker, IntentionPicker, TrackRow, SaveToSpotify,
                          DnaChart, SearchBox, TagInput, ...
  pages/                  Discover, Curate, Results, MusicDna, History, Settings
  index.css               design tokens (palette, fonts, shadows)
```

**Design tokens** (in `index.css`): background `#FAF9FC`, lavender `#C9B6F0` / `#EAE2F8`, deep purple `#6E58A8`, text `#201D27` / `#77717F`, border `#E9E4EF`, sage `#A8C9B0`, deep green `#547A60`. Purple is the brand; green means success, positive states and Spotify. Fonts: Inter (UI) and Fraunces (display), bundled with the site.
