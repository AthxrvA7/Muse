# Changelog

All notable changes to Muse are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- System architecture document (`docs/ARCHITECTURE.md`)
- Requirements with acceptance criteria, assumptions, scoped-down items and risk register (`docs/REQUIREMENTS.md`)
- Architecture decision records ADR-0001 to ADR-0008 (`docs/adr/`)
- Threat model, OWASP Top 10 (2025) mapping, privacy design and wellbeing safeguard (`docs/SECURITY_PRIVACY.md`)
- Development roadmap, contributing guide and AI use log
- Initial repository files: README, MIT license, `.gitignore`, `.gitattributes`
- Pull request template, issue forms, security policy and editorconfig
- FastAPI application skeleton with layered package structure
- Environment-based settings validated at startup (`.env.example`)
- Typed service-info endpoint and 8 automated tests (pytest)
- CI pipeline (GitHub Actions): Ruff lint and format check, and pytest, on every push and pull request
- Mood engine: `POST /api/v1/mood/analyze` turns mood chips and/or free text into valence, energy, tempo and a playlist mode (comfort, focus, energy, discovery)
- Mood vocabulary of 20 chips on Russell's circumplex, plus emotion points and intent words (`app/knowledge/mood_map.json`)
- Emotion classifier (TF-IDF + logistic regression on dair-ai/emotion): test accuracy 0.879, macro-F1 0.838; training script and model card
- Model integrity check: the model loads only if its SHA-256 and scikit-learn version match its card; otherwise keyword fallback
- Wellbeing notice with the Tele-MANAS helpline when text suggests crisis; the text is never stored or logged
- ADR-0009: build the curation core before persistence and login

- Spotify client (client-credentials flow): cached app token with automatic refresh; one retry on 401, 429 (waits up to 5 s for `Retry-After`), 5xx and timeouts
- Catalogue search with paging (Spotify's 10-per-request limit) and a query builder that strips quotes and control characters from user input
- `GET /api/v1/catalog/search?q=&type=track|artist&limit=`: answers 503 if Spotify isn't configured or is down, and 429 with `Retry-After` if rate-limited
- Spotify settings (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_MARKET`): optional, so the app and CI run without them; the secret is a `SecretStr` and is never printed

- Genre knowledge base: 60 genres on the valence-energy plane with languages and Spotify search terms (`app/knowledge/genre_kb.json`)
- Recommender: plans searches from mood + taste (favourite artists, closest favourite genres, language genres, discovery genres), runs them in parallel with keyword fallback and partial-failure tolerance
- Scoring: mood fit from distance on the valence-energy plane, taste fit from why a track was found, weights per mode
- Diversity re-ranking (≤ 2 per artist, ≤ 40% per search, song versions de-duplicated) and one-sentence explanations
- `POST /api/v1/curate` (stateless playlist preview) and `GET /api/v1/curate/options`
- ADR-0010: distance, not cosine similarity, for mood fit

- Structured JSON logs with request IDs and redaction, `GET /health` (liveness) and `GET /ready` (readiness)
- MongoDB connection (PyMongo async) opened at startup and closed at shutdown; settings `MONGODB_URI` (secret) and `MONGODB_DB`; required when `APP_ENV=production`
- `/ready` checks the database: `ready` (MongoDB answers), `degraded` (no database configured, e.g. local or CI), `not_ready` with HTTP 503 (configured but not answering)
- Document models and repositories for `users`, `sessions`, `oauth_states` and `preferences`, with unique indexes and TTL indexes (sessions after 7 idle days, pending logins after 10 minutes), created at startup
- Repository tests against a real MongoDB, run with `pytest --db` in a throwaway database
- `GET /api/v1/auth/login`, `GET /api/v1/auth/callback`, `POST /api/v1/auth/logout`, `GET /api/v1/me`
- Taste profile: `GET`/`PUT /api/v1/preferences` (artists, genres, languages, styles, reference tracks, exclusions), validated against the genre knowledge base
- Music DNA: `GET /api/v1/preferences/dna` with top artists, genres and languages, and the average feel of the user's genres on the valence-energy map
- `POST /api/v1/playlists` creates a private playlist with the curated tracks in the user's Spotify account (Spotify's February 2026 endpoints `POST /me/playlists` and `POST /playlists/{id}/items`) and records it; `GET /api/v1/playlists` lists them
- `POST /api/v1/curate` without `taste` uses the logged-in user's saved profile; the response's `taste_source` says which was used

### Fixed
- The Swagger example for `POST /api/v1/playlists` used real track IDs, which added two unrelated songs when run as-is; it now asks for IDs from `/curate`
- A database outage during a request (e.g. Atlas blocking a new IP address) now returns a clear `503` instead of a generic 500 error page

### Fixed (found in the first run against real Spotify)
- The 2-per-artist limit now counts every credited artist; Arijit Singh appeared 3 times because he was credited second
- Tracks with equal scores are now ordered by Spotify's own result order instead of by track ID
- Explanations name every genre that shaped a track's estimated feel, don't repeat a genre already named, and keep proper names ("Bollywood", "R&B")

### Deployment
- Render Blueprint (`render.yaml`): one web service built from `main`, health-checked on `/health`, behind Render's HTTPS proxy (`--proxy-headers`); secrets entered in Render, never committed
- Deployment runbook (`docs/DEPLOYMENT.md`): first deployment, rollback, demo checks, troubleshooting

### Privacy
- `GET /api/v1/me/data` downloads everything Muse holds about you as JSON (account, taste profile, playlists it created; never tokens), and lists what is never stored
- `DELETE /api/v1/me` deletes your account, taste profile, playlist records and every login session, and logs you out

### Website support
- `GET /api/v1/mood/options`: mood chips with their valence and energy, and the modes, for clients
- The built website is served at `/app/` by the backend (`FRONTEND_DIST`), with its own Content-Security-Policy

### Cover art
- Every saved playlist can get a 640x640 cover painted from the mood (Pillow, no AI or stock images): colour from positivity, waves from energy, the playlist's headline and mood words, the Muse mark and a little grain
- The same cover is shown on the playlist page (`GET /api/v1/covers`) and offered as a tick-box when saving
- Uploaded with `PUT /playlists/{id}/images`, only to the playlist Muse has just created; new scope `ugc-image-upload`. Accounts that logged in before get their playlist saved without the cover and a "log in again" note; a failed upload never fails the playlist
- The JPEG is kept under 190 KB so the base64 upload stays below Spotify's 256 KB limit

### 30-second previews
- Every song with a match on Deezer gets a play button on its artwork: one player for the whole site, with a progress bar and an equaliser that moves at the song's tempo
- `GET /api/v1/previews/{deezer_id}` redirects to a fresh signed clip on Deezer's CDN. Deezer's links expire within about 15 minutes, so Muse never stores them: it asks for a new one on play and reuses it at most 10 minutes (and never past a minute before its expiry). The Deezer ID comes from the same lookup as the tempo, so playlists cost no extra calls
- Only `https://*.dzcdn.net` links are handed out, and the website's CSP allows audio only from there

### Gentler on Spotify
- Search results are cached for 6 hours, so repeating a mood or taste costs no Spotify calls
- When Spotify asks Muse to wait longer than 5 seconds, Muse stops calling it until the wait is over (calling during a block only lengthens it) and says how long to wait
- If some searches are rate-limited, the playlist is built from the ones that worked
- Fewer searches per playlist (3 similar artists, 1 discovery genre, 2 extra language genres, 3 at a time)

### Strict language
- A playlist now holds only songs Muse knows are in its language (plus instrumental genres); songs of unknown language are never used. If there are too few, Muse first searches more genres in that language, and otherwise returns a shorter playlist with a note instead of mixing
- Render deploys on every commit to main (`autoDeployTrigger: commit`); pull requests already pass CI before they are merged

### Engine fixes and a new look
- Language and genre now come mainly from each artist's Last.fm tags (one lookup per artist), plus title words ("Tum Hi Ho" is Hindi) and the title's script; an artist's known language and genre fill their other songs
- Stricter focus: songs in other languages or unrelated genres are left out unless there aren't enough; a single language in your taste is used automatically
- Songs you know but whose listener-tagged feel doesn't fit the mood drop back
- Last.fm rate-limit and key errors are no longer cached as "no tags"; fewer, better-ordered lookups
- "Under the hood" on the playlist page shows how many songs had a known feel, language, genre and tempo
- New look: dark and light themes with a toggle, burger menu, record-and-pulse logo, warm tangerine/mint palette, draggable mood orb, beating BPM dots, equaliser hover, turntable loading screen, confetti on save

### Coherent playlists
- One language per playlist: chosen automatically from your songs and taste, or picked on Discover ("Mix languages" turns it off). Each song's language comes from Last.fm tags and the title's script
- One genre per playlist, with close genres allowed: every genre now has a family in `genre_kb.json`, and families list related ones; unrelated genres are left out while there are enough songs. Pick a genre on Discover or let Muse choose
- Tempo: BPM for each song from Deezer's free public API (matched by ISRC), shown next to the song; songs whose pace fits the mood rank a little higher

### Smarter curation (ADR-0011)
- Songs you already play: your Spotify top tracks (last ~4 weeks and ~6 months) are mixed in, marked "You know this"
- Song moods from Last.fm listener tags ("chill", "sad", "party"), so Muse knows which of your songs fit tonight; explanations quote the tags
- New songs from artists similar to your favourites (Last.fm), instead of mostly genre searches
- `familiarity` (0–1) and a Familiar ↔ New slider on the website; defaults by mode
- Never the same playlist twice: a small random nudge, recent picks are less likely (`recent_picks`, 30 days), and "Give me another" leaves out the songs on screen
- `LASTFM_API_KEY` setting (optional); `GET /me/top/tracks` added to the read-only allow-list

### Import from Spotify
- `GET /api/v1/preferences/from-spotify` suggests a taste profile from your Spotify top artists (about the last 6 months): artists, plus the genres and languages Muse knows among their Spotify genres. Nothing is saved: the website puts it in the Music DNA form for you to edit and save
- New read-only scope `user-top-read`, and `GET /me/top/artists` added to the user-token allow-list. Accounts that logged in before are asked to log in again (`relogin_needed`) instead of calling Spotify

### Docker and CI
- Multi-stage `Dockerfile`: Node builds the website, a slim Python image serves it with the API as a non-root user, with a `/health` healthcheck
- `docker-compose.yml`: Muse plus MongoDB 7, one command (`docker compose up --build`); the database is not exposed outside Docker
- CI: website job (ESLint, type check, unit tests, build); Docker job builds the image, starts the compose stack and smoke-tests it
- CI: 90% backend coverage gate; database tests run against a temporary MongoDB service container
- CI: `pip-audit` and `npm audit` dependency checks; Dependabot for pip, npm, Actions and Docker

### Security
- Hard allow-list for calls made with a user's Spotify token: only reading the profile (and, later, the top-artist list), creating a new playlist, and adding tracks to a playlist Muse just created. Deleting, editing, reordering or reading existing playlists is refused before any request is sent
- Spotify login (Authorization Code flow): single-use `state` checked on the callback and expired after 10 minutes; minimal scopes (`playlist-modify-private`, `playlist-modify-public`, `user-read-private`)
- Server-side sessions: the browser holds only a random ID in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` in production); Muse stores its SHA-256 hash; a new ID on every login; logout is immediate
- Spotify tokens encrypted at rest with Fernet (`TOKEN_ENCRYPTION_KEY`), refreshed automatically before they expire, never logged or sent to the browser
- Security headers on every response (nosniff, frame denial, no referrer, a nothing-allowed CSP on API responses, `no-store` on `/api/*`, HSTS in production)
- CORS limited to the origins in `CORS_ORIGINS` (empty by default; `*` rejected at startup)
- Per-IP rate limiting in one-minute windows: 120/min default, 10/min on `/curate` and `/auth/*`, `/health` and `/ready` exempt; `429` with `Retry-After`
- Origin check: POST/PUT/PATCH/DELETE from other websites are refused with `403` (CSRF defence)
- Settings validation errors no longer echo the invalid value, which could have printed a password or secret at startup
- Logs mask the password inside connection strings (`mongodb+srv://user:[REDACTED]@…`)

### Changed
- Spotify connection setup shared by catalogue and curation (`services/spotify_session.py`); Spotify error mapping moved to `api/errors.py`
- `httpx2` moved to runtime dependencies: one HTTP library for the Spotify client and FastAPI's TestClient
- Lint: tests may contain fake secrets (Ruff S105/S106 allowed in `tests/` only)
- The classifier is used only when it is at least 50% confident; neutral text ("need to study") falls back to mood words instead of a guessed emotion
- Swagger's example mood request no longer pre-fills `mode`, which was overriding the detected intent
