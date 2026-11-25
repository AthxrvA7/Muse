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
- A database outage during a request (e.g. Atlas blocking a new IP address) now returns a clear `503` instead of a generic 500 error page

### Fixed (found in the first run against real Spotify)
- The 2-per-artist limit now counts every credited artist; Arijit Singh appeared 3 times because he was credited second
- Tracks with equal scores are now ordered by Spotify's own result order instead of by track ID
- Explanations name every genre that shaped a track's estimated feel, don't repeat a genre already named, and keep proper names ("Bollywood", "R&B")

### Deployment
- Render Blueprint (`render.yaml`): one web service built from `main`, health-checked on `/health`, behind Render's HTTPS proxy (`--proxy-headers`); secrets entered in Render, never committed
- Deployment runbook (`docs/DEPLOYMENT.md`): first deployment, rollback, demo checks, troubleshooting

### Security
- Hard allow-list for calls made with a user's Spotify token: only reading the profile, creating a new playlist, and adding tracks to a playlist Muse just created. Deleting, editing, reordering or reading existing playlists is refused before any request is sent
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
