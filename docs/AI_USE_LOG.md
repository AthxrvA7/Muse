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
