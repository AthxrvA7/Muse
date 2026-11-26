# AI Use Log

Required by the Muse synopsis (§14, Responsible Use of AI). Add one entry per meaningful use of an AI tool, newest at the bottom.
Never paste secrets, tokens or real user data into an AI tool.

**Template**

```
### YYYY-MM-DD — <short title>
- **Member:** 
- **Tool:** 
- **Purpose:** (learning / design / code suggestion / debugging / tests / docs)
- **Prompt (summary):** 
- **Output used:** (which files or parts)
- **Changes made by us:** 
- **Verification:** (how we checked it: tests, review, docs consulted)
- **Reflection:** (what we learned, what was wrong or missing in the AI output)
```

---

### 2026-10-20 — Architecture and project documentation
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design, documentation
- **Prompt (summary):** Design an industry-style architecture for Muse within the course guidelines and the synopsis; check current Spotify API limits; produce the architecture, requirements, ADRs, threat model and roadmap.
- **Output used:** `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `docs/SECURITY_PRIVACY.md`, `docs/adr/*`, `docs/ROADMAP.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, the initial README.
- **Changes made by us:** Kept the repo public after first making it private (branch protection and security scanning are free only on public repos). Kept reviews required on `main` instead of letting the admin bypass them. Cut back a lot of the CI plan, because we haven't covered GitHub Actions in class yet and didn't want anything in the repo we can't explain. The roadmap now waits for each DevOps topic to be taught first.
- **Verification:** Spotify Feb-2026 developer-mode changes checked against Spotify's official migration guide; course requirements cross-checked against the Project Guidelines; design reviewed by the team in PR #1.
- **Reflection:** The biggest surprise was Spotify's API. Most tutorials still use audio features and the recommendations endpoint, but both are gone for apps like ours, so the recommender has to rely on our own genre data. Also, the first plan was more than we needed for a Semester III project. Pushing back on it (especially the CI extras) made the plan more realistic. Next time we'll ask for the smallest working version first and add to it.

### 2026-10-21 — Backend skeleton and first CI workflow
- **Member:** Atharva (skeleton), Darsh (CI)
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, learning
- **Prompt (summary):** Set up a FastAPI project structure with settings and tests; write a GitHub Actions workflow that runs lint and tests on every push.
- **Output used:** `backend/app/*`, `backend/tests/*`, `.env.example`, `.github/workflows/ci.yml`, ruff config in `backend/pyproject.toml`.
- **Changes made by us:** Ran the app and the tests on our own laptops (Windows and Mac) before committing. Fixed how the server was started (it has to be run from inside `backend/`). Added a typed response model after Swagger showed `additionalProp1` instead of the real fields. Fixed the GitHub login on the Mac so it could push workflow files.
- **Verification:** `pytest` passes locally (8 tests); the CI run on the PR shows Lint and Tests both green.
- **Reflection:** A workflow is just the same commands we run on our laptop, run on a fresh machine on every push. Pushing a workflow file needs extra GitHub permission (`workflow` scope), which we didn't know about until the push failed.

### 2026-10-21 — Mood engine (slice 1)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, design, learning
- **Prompt (summary):** Build the mood engine: chips on Russell's circumplex, an analyze endpoint, a TF-IDF + logistic regression emotion classifier with a training script, safe model loading, and a wellbeing notice.
- **Output used:** `backend/app/services/mood/*`, `backend/app/knowledge/*.json`, `backend/app/schemas/mood.py`, `backend/app/api/v1/mood.py`, `backend/scripts/train_mood_model.py`, the mood tests.
- **Changes made by us:** Trained the model on my own laptop (Claude couldn't reach Hugging Face). Results: test accuracy 0.879, macro-F1 0.838, best C = 4. Testing in Swagger showed two problems. First, neutral sentences like "exams tomorrow, need to study" got a made-up "joy" label, because the model always picks something (top probability only 0.31). We added a rule to use the model only when it's at least 50% sure and fall back to mood words otherwise. Second, Swagger pre-filled `"mode": "comfort"`, which overrode the "study" intent, so we fixed the example.
- **Verification:** 60 tests pass locally and in CI; ran real sentences through the trained model and checked the results by hand.
- **Reflection:** The model is very confident when there's a feeling word ("nervous" → fear 0.98) but unreliable on neutral text. An accuracy number alone doesn't show that; trying real inputs did. The mood positions in `mood_map.json` are our own estimates, and we say so in the file.

### 2026-10-21 — Spotify client and catalogue search (slice 2, part 1)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, learning
- **Prompt (summary):** Build the Spotify client for the client-credentials flow (token caching, retries, rate limits), catalogue search with Spotify's 10-results-per-page limit, and a search endpoint.
- **Output used:** `backend/app/clients/spotify.py`, `backend/app/services/catalog.py`, `backend/app/api/v1/catalog.py`, `backend/app/schemas/catalog.py`, Spotify settings in `config.py`, tests.
- **Changes made by us:** Created the Spotify developer app myself. I accidentally showed the client secret in a screenshot, so I rotated it in the Spotify dashboard right away and only kept the new one in `.env`.
- **Verification:** 93 tests pass with a fake Spotify (no network in CI). I then ran a real search from my laptop in Swagger and got real tracks back.
- **Reflection:** Spotify now limits search to 10 results per request, so paging matters. A leaked secret has to be rotated, not just deleted, because a screenshot can't be taken back.

### 2026-10-21 — Recommender and curate endpoint (slice 2, part 2)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design, code suggestion, testing
- **Prompt (summary):** Build the recommender: a genre knowledge base, search planning from mood + taste, parallel candidate search, mood/taste scoring, diversity re-ranking, explanations, and `POST /api/v1/curate`.
- **Output used:** `backend/app/knowledge/genre_kb.json`, `backend/app/services/recommender/*`, `backend/app/services/curate.py`, `backend/app/api/v1/curate.py`, tests.
- **Changes made by us:** The end-to-end tests caught two problems before anything shipped. First, one genre search filled the whole playlist, and my favourite artist didn't appear; we added a 40%-per-search limit. Second, duplicate results were counted twice. We also switched mood fit from cosine similarity to distance (ADR-0010). Then I ran it against real Spotify (6 searches, 83 candidates, 15 tracks), and the output showed three more problems the fake data couldn't. Arijit Singh appeared 3 times, because he's credited second on Bollywood songs, so the per-artist limit now counts every credited artist. Many tracks had identical scores, so ties are now broken by Spotify's result order. And ghazal songs were explained as "bollywood feel", so explanations now name every genre behind the estimate and keep proper names.
- **Verification:** 153 tests (unit, end-to-end with a fake catalogue, and a 300 ms-latency timing test), plus real Spotify runs from my laptop before and after the fixes.
- **Reflection:** Each kind of testing found different bugs. Unit tests passed while the playlist was bad; fake end-to-end data found the genre monopoly; only real Spotify data found the featured-artist and tie problems. Real data also showed that Spotify's `genre:` filter is loose (Shawn Mendes came back for "indie folk"), and that favourite-artist songs get a neutral mood fit because Spotify says nothing about how they sound. Both are limitations we should state in the report.

### 2026-11-18 — MongoDB connection and repositories (slice 3, `feature/database`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, testing, setup help
- **Prompt (summary):** Connect the backend to MongoDB Atlas with PyMongo's async client, add a database check to `/ready`, add repositories with unique and TTL indexes for users, sessions, OAuth states and preferences, and test them against a real database.
- **Output used:** `backend/app/db/*`, `backend/app/services/readiness.py`, MongoDB settings in `config.py`, the lifespan in `main.py`, `tests/test_database.py`, `tests/test_indexes.py`, `tests/test_repositories.py`.
- **Changes made by us:** Created the Atlas M0 cluster (Mumbai), the database user and the IP allow-list myself, and kept the connection string only in `.env`. My first attempt saved the URI with an empty password, and the app refused to start with "A password is required"; I fixed `.env` and `/ready` then showed `"database": "ok"`. While writing the settings tests we found that a validation error would have printed the whole invalid value, password included, so settings errors now hide their input and logs mask passwords inside connection strings.
- **Verification:** `pytest` (CI): 192 passed, 11 skipped. `pytest --db` on my laptop against Atlas: 203 passed, which was the first time the repository code ran against a real database. Checked `/ready` and the collections in Atlas by hand.
- **Reflection:** The repository code couldn't be run against a real database in Claude's workspace, so the `--db` run on my laptop was the real check. The database tests take about a minute because every call goes to Atlas over the internet; CI skips them so it never needs the password.

### 2026-11-25 — Security hardening (slice 3, `feature/security-hardening`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, testing
- **Prompt (summary):** Add security headers, strict CORS, per-IP rate limiting and an Origin check for state-changing requests, before Spotify login adds cookies.
- **Output used:** `backend/app/core/security.py`, middleware wiring in `main.py`, `CORS_ORIGINS` and rate-limit settings in `config.py`, `tests/test_security_headers.py`, `tests/test_rate_limit.py`, `tests/test_origin_check.py`.
- **Changes made by us:** Chose a small hand-written fixed-window limiter instead of slowapi (ARCHITECTURE §8 updated) so the whole mechanism can be explained. Kept the strict Content-Security-Policy off `/docs`, because it blocked Swagger's scripts.
- **Verification:** 217 tests pass (25 new): headers on every route, CORS preflight from allowed and other websites, 429 with `Retry-After`, a separate stricter curate budget, exempt health checks, and blocked look-alike origins.
- **Reflection:** The Origin check only matters once there is a login cookie, which is why it goes in before `feature/spotify-auth`. The limiter lives in memory, so it resets on restart and won't work across several instances; that's fine for one instance and noted as the scale-out path.

### 2026-11-25 — Spotify login and sessions (slice 3, `feature/spotify-auth`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, testing
- **Prompt (summary):** Add Spotify login with the Authorization Code flow, a state check, encrypted token storage, server-side sessions, logout and a `/me` endpoint.
- **Output used:** `backend/app/clients/spotify_user.py`, `backend/app/core/crypto.py`, `backend/app/services/auth.py`, `backend/app/api/deps.py`, `backend/app/api/v1/auth.py`, token methods in the users repository, `tests/test_auth.py`, `tests/test_spotify_user.py`, `tests/test_crypto.py`, `tests/fakes.py`.
- **Changes made by us:** Used the playlist endpoints from Spotify's February 2026 changelog (`POST /me/playlists`, `POST /playlists/{id}/items`), since older tutorials use removed ones. Made the post-login redirect accept only a path on this server, so it can't become an open redirect. Writes to Spotify are never retried, so a timeout can't create a playlist twice.
- **Verification:** 252 tests pass with a fake Spotify and in-memory storage: state reuse, expired and unknown states, cancelled login, rejected code, a Development Mode 403, cookie flags, hashed session IDs, encrypted tokens, automatic refresh and immediate logout.
- **Reflection:** The tests use fakes, so the real check is logging in with my own Spotify account on my laptop.

### 2026-11-25 — Taste profile and Music DNA (slice 3, `feature/user-preferences`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, testing
- **Prompt (summary):** Let a logged-in user save their taste, summarise it as Music DNA, and curate from the saved profile.
- **Output used:** `backend/app/schemas/preferences.py`, `backend/app/services/preferences.py`, `backend/app/api/v1/preferences.py`, the `saved_taste` dependency, curate changes, `tests/test_preferences.py`, new curate tests.
- **Changes made by us:** Music DNA uses only what the user stated (no Spotify listening history, as the synopsis requires). Its "mood centre" is the average position of the chosen genres on the same valence-energy map the recommender uses. Styles and reference tracks are stored and shown but don't affect scoring yet; we say so rather than pretend.
- **Verification:** 266 tests pass, including validation, replacing a profile, the DNA numbers worked out by hand from `genre_kb.json`, and curate choosing saved vs sent taste.
- **Reflection:** Keeping the saved-profile lookup in one dependency meant the curate logic didn't change at all; it still receives a `Taste`.

### 2026-11-25 — Saving playlists to Spotify (slice 4, `feature/playlist-export`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, testing
- **Prompt (summary):** Create the curated playlist in the logged-in user's Spotify account and keep a history of saved playlists.
- **Output used:** `backend/app/services/playlists.py`, `backend/app/api/v1/playlists.py`, `backend/app/schemas/playlists.py`, `backend/app/db/repositories/playlists.py`, `PlaylistRecord`, a `playlists` index, `tests/test_playlists.py`, a repository test.
- **Changes made by us:** We changed the plan from `POST /curate/{session_id}/export` to `POST /playlists` with the track IDs from the preview. That way curate stays stateless and we don't store mood sessions just to export them. Playlists are created private. Only the playlist's reference (ID, link, name, track count) is stored.
- **Verification:** 275 tests pass with a fake Spotify: request shapes for the two new endpoints, duplicate track IDs removed, a 403 explained, an expired login asking to log in again, and nothing recorded when Spotify refuses.
- **Reflection:** Spotify's February 2026 changes removed the playlist endpoints most tutorials use; checking the official changelog first avoided building on dead endpoints.

### 2026-11-25 — Deployment on Render (`feature/deployment`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** configuration, documentation
- **Prompt (summary):** Deploy the backend to Render with MongoDB Atlas, document setup and rollback, and bring the requirement statuses up to date.
- **Output used:** `render.yaml`, `docs/DEPLOYMENT.md`, README and REQUIREMENTS updates.
- **Changes made by us:** Used a separate encryption key for production. Kept Swagger enabled in production because it is our demo UI until the frontend exists. Allowed Atlas access from anywhere because Render's free tier has no fixed IP, relying on the database password; this is noted as a trade-off in the runbook.
- **Verification:** Checked on the live URL https://muse-api-mu05.onrender.com: `/ready` showed the database as `ok`; I logged in with Spotify, saved my taste, read the Music DNA, curated a "tired and low" playlist from the saved profile, and saved it to my Spotify as a private playlist. Render gave the service a different URL than we guessed, so the redirect URI had to be updated in Render and in the Spotify dashboard.
- **Reflection:** Behind Render's proxy the app sees Render's address and plain HTTP unless uvicorn trusts the forwarded headers. Without `--proxy-headers`, rate limiting would treat every user as one client and the Origin check would see the wrong scheme.

### 2026-11-26 — Import from Spotify (`feature/spotify-taste-import`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code generation, testing, documentation
- **Prompt (summary):** While testing the live app, the profile saved during API testing wasn't my taste and the playlists felt unfamiliar. Add a way to start the taste profile from my Spotify top artists.
- **Output used:** `user-top-read` scope, `GET /me/top/artists` in the allow-list, `services/taste_import.py`, `GET /api/v1/preferences/from-spotify`, `tests/test_taste_import.py`, docs.
- **Changes made by us:** We kept the synopsis principle that the profile is *stated* by the user: the import only pre-fills the form, nothing is saved until the user presses Save, and the top-artist list is not stored or analysed. Old logins without the new permission get a clear "log in again" answer instead of a Spotify error.
- **Verification:** 303 backend tests pass; the new tests check the genre mapping, that the endpoint makes exactly one read-only call and saves nothing, the log-in-again path, and the error paths. Checked on the live site after deployment.
- **Reflection:** The synopsis lists Spotify listening data as out of scope. We read the top-artist list only on request and only to suggest a profile, which keeps the user in control while making the first playlist feel familiar.

### 2026-11-26 — Smarter curation (`feature/smart-curation`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design discussion, code generation, testing, documentation
- **Prompt (summary):** On the live site the playlist was the same every time and mood barely changed which of my artists' songs came up. I asked for songs that fit my mood *and* that I like, including ones I already listen to, and for it to feel like a real product.
- **Output used:** Last.fm client and tag-to-mood map, top tracks as a familiar pool, similar-artist searches, familiar/new mix, recent-picks memory, random variety, "Give me another", website slider and badges, ADR-0011, tests.
- **Changes made by us:** Chose Last.fm over lyrics or an LLM (free, explainable, no copyrighted text). Kept every external call optional with a fallback, and a 6-second budget so the playlist is never held up. Kept the top tracks out of the database; only Muse's own recent picks are stored, with a 30-day expiry and included in export and deletion.
- **Verification:** 326 backend tests and 12 website tests pass; new tests cover tag moods, the time budget, the familiar/new share, similar artists, "Give me another", recent picks and failure fallbacks. Checked on the live site after deployment with my own Spotify account.
- **Reflection:** The first version worked as designed but felt repetitive in real use; testing with a real account found what unit tests couldn't. A song-level mood signal and the user's own songs mattered more than any scoring tweak.

### 2026-11-26 — Coherent playlists and tempo (`feature/coherent-playlists`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code generation, testing, documentation
- **Prompt (summary):** Playlists mixed languages and jumped between unrelated genres; I wanted one language, one consistent genre that can borrow from close ones, and each song's tempo.
- **Output used:** genre families in `genre_kb.json`, language/genre detection from tags and script, `recommender/focus.py`, Deezer BPM client, website pickers and BPM chips, tests.
- **Changes made by us:** We chose the families and related families ourselves, kept "Mix languages" as an option, and made an explicitly chosen genre count more than an automatic one.
- **Verification:** 339 backend tests and 12 website tests pass.
- **Reflection:** Language and genre come from the same listener tags as mood, so one lookup per song now does three jobs.

### 2026-11-26 — Engine fixes and redesign (`feature/engine-v3`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** debugging, code generation, UI design, testing
- **Prompt (summary):** On the live site Hindi and English were still mixed, the genre wasn't holding and the vibe was off. I also wanted dark/light themes, a collapsible menu, a better logo, warmer colours and a more playful UI.
- **Output used:** artist-level language/genre detection, title-word language hints, stricter focus rules, off-vibe penalty for known songs, a fix for Last.fm errors being cached, coverage diagnostics; theme tokens, burger drawer, logo, mood orb and micro-interactions.
- **Changes made by us:** Chose the "late-night record store" palette and the record logo; kept the user's own songs even when Muse can't tell their language or genre.
- **Verification:** 345 backend tests and 12 website tests pass; the site was clicked through in both themes and on the loading, playlist and menu screens.
- **Reflection:** The coverage numbers turned a vague "it feels wrong" into something we can check: if language is known for few songs, the cause is missing data, not scoring.

### 2026-11-26 — 30-second previews (`feature/previews`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** research, code generation, testing
- **Prompt (summary):** Add song previews without risking rate limits or timeouts.
- **Output used:** Deezer match (ID + BPM) in one lookup, a preview endpoint that mints fresh links, a site-wide player, tests.
- **Changes made by us:** Research showed Deezer preview links expire in about 15–30 minutes, so we store the Deezer track ID instead of the link and fetch a fresh link on play.
- **Verification:** 357 backend tests; a real browser played a preview through the redirect with the site's CSP on.
- **Reflection:** Checking how others hit expired preview links saved us from a bug that only shows up after the demo has been running for a while.

### 2026-11-26 — Cover art (`feature/cover-art`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** research, code generation, design, testing
- **Prompt (summary):** Give each saved playlist its own cover, without risking the playlist itself.
- **Output used:** `services/cover.py` (Pillow), `GET /api/v1/covers`, upload in the playlist service, a new allow-listed call and scope, the cover tick-box and hero image, tests.
- **Changes made by us:** Checked Spotify's current rules first (endpoint still available, `ugc-image-upload`, base64 JPEG ≤ 256 KB) and sized the image for them; made the cover optional and never able to fail a save.
- **Verification:** 365 backend tests; a browser run showed the cover on the page and in the dialog, and saving uploaded it to the new playlist.
- **Reflection:** Using the same colour rule as the mood orb makes the cover feel like part of the app rather than decoration.

### 2026-11-26 — Learn from me (`feature/learning`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design, code generation, testing
- **Prompt (summary):** Make the 👍/👎 buttons actually teach Muse, the synopsis's "Learn from me" stage.
- **Output used:** `feedback` collection and API, `services/learning.py`, liked-artist searches, reasons, the rating buttons, the "What Muse learned" card, tests.
- **Changes made by us:** Kept every nudge small and capped so ratings refine the mood and taste instead of overriding them; chose to remove 👎 songs from the current playlist straight away (with Undo); added "Forget what Muse learned".
- **Verification:** 374 backend tests; in a browser a 👍 and a 👎 were saved, the 👎 song left the playlist, and the next playlist reported "Learned from 2 ratings".
- **Reflection:** Simple, explainable rules can be described line by line in the viva, which matters more here than a model nobody can inspect.

### 2026-11-26 — Mood trajectory (`feature/mood-trajectory`)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design, code generation, testing
- **Prompt (summary):** Add the synopsis's mood trajectory: show how the user's moods change across Muse sessions.
- **Output used:** `mood_log` repository, `GET /moods/trajectory`, on/off and clear endpoints, the summary rules (`services/trajectory.py`), the History page card with the mood map and the over-time chart, tests.
- **Changes made by us:** Made it opt-in and kept for 90 days to match our own privacy design (SECURITY_PRIVACY.md); kept only the two numbers and fixed mood words, never the text; merged quick repeats so "Give me another" doesn't flood the chart; added "not a diagnosis" to the card.
- **Verification:** 384 backend tests and 17 website tests; in a browser the map, the over-time chart, pause, clear and turn on all worked in light, dark and mobile layouts.
- **Reflection:** The first version logged moods for everyone; checking it against our own privacy document caught that it should be opt-in.
