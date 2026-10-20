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

### Changed
- Spotify connection setup shared by catalogue and curation (`services/spotify_session.py`); Spotify error mapping moved to `api/errors.py`
- `httpx2` moved to runtime dependencies: one HTTP library for the Spotify client and FastAPI's TestClient
- Lint: tests may contain fake secrets (Ruff S105/S106 allowed in `tests/` only)
- The classifier is used only when it is at least 50% confident; neutral text ("need to study") falls back to mood words instead of a guessed emotion
- Swagger's example mood request no longer pre-fills `mode`, which was overriding the detected intent
