# Muse 🎧

[![CI](https://github.com/AthxrvA7/Muse/actions/workflows/ci.yml/badge.svg)](https://github.com/AthxrvA7/Muse/actions/workflows/ci.yml)

**Mood-aware music curation on top of Spotify.**

Muse combines how you feel *right now* with the music you say you love, ranks tracks with its own explainable scoring, and saves the result as a playlist in your Spotify account.

> **Status:** 🚧 Phase 1 (backend) in progress. This is a university DevOps & SCM project (CSDV2010P). See the [roadmap](docs/ROADMAP.md).

---

## Problem statement

Music recommenders usually suggest tracks from your long-term listening habits, and generic mood playlists give everyone the same songs for "sad" or "focus". Neither answers the real question: *given what I like and how I feel right now, what should I listen to?*

Muse is an independent personalisation layer. It uses Spotify for login, catalogue search and playlist creation, and applies its own mood analysis and recommendation logic.

## Team

| Member | Role |
|---|---|
| Atharva Ingale | Backend, AI/ML, data intelligence & deployment |
| Darsh | SCM, testing, containerisation & CI/CD |
| Piyush | Frontend, UI/UX & monitoring |

## Features

| Stage | Feature | Status |
|---|---|---|
| Classics: "Know your music" | Database ✅, Spotify login, preference profile, reference tracks, Music DNA | In progress |
| Essential: "Curate for me" | Mood analysis ✅, preference + mood scoring ✅, explained playlist ✅, export to Spotify | In progress |
| Advanced: "Learn from me" | Feedback loop, session history, mood trajectory | Future |

## Try the mood engine

Start the backend (see Setup), open http://127.0.0.1:8000/docs and call **POST /api/v1/mood/analyze**:

```json
{"chips": ["anxious", "low"], "text": "exams tomorrow, need to study"}
```

```json
{"valence": 0.23, "energy": 0.5, "tempo": "medium", "mode": "focus",
 "labels": ["anxious", "low"], "confidence": 0.9, "text_analysis": "keywords", "support": null}
```

To retrain the emotion model: `cd backend`, `pip install -r requirements-train.txt`, `python -m scripts.train_mood_model`.

## Curate a playlist

With Spotify connected (next section), call **POST /api/v1/curate** in `/docs`:

```json
{
  "mood": {"chips": ["tired", "low"], "text": "long day, want something soft"},
  "taste": {"artists": ["Prateek Kuhad"], "genres": ["indie folk", "bollywood"], "languages": ["hi", "en"]},
  "size": 15
}
```

Each returned track has `score`, `mood_fit`, `taste_fit` and a `reason`, e.g. *"Picked because you like Prateek Kuhad, and its indie folk feel fits your tired and low mood."* Allowed genres and languages: **GET /api/v1/curate/options**.

## Connect Spotify (optional for tests, needed for search)

1. Create an app at https://developer.spotify.com/dashboard (Redirect URI `http://127.0.0.1:8000/api/v1/auth/callback`, API: Web API).
2. Put its credentials in `.env` (never commit this file):
   ```
   SPOTIFY_CLIENT_ID=...
   SPOTIFY_CLIENT_SECRET=...
   SPOTIFY_MARKET=IN
   ```
3. Start the backend and try **GET /api/v1/catalog/search** in `/docs`, e.g. `q=Prateek Kuhad`.

Without credentials the app still runs; Spotify endpoints answer `503`. Tests never call the real Spotify.

## Connect MongoDB (optional locally, required in production)

Muse stores users, sessions and preferences in MongoDB. Locally it's optional: without it the mood and curate endpoints still work and `/ready` reports `degraded`.

1. Create a free **M0** cluster at https://cloud.mongodb.com (AWS, Mumbai `ap-south-1`).
2. **Security → Database Access:** add a database user with an auto-generated password (letters and numbers only, so the connection string needs no escaping).
3. **Security → Network Access:** add your current IP address.
4. **Connect → Drivers:** copy the connection string, put the password in place of `<db_password>`, and add it to `.env`:
   ```
   MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
   MONGODB_DB=muse
   ```
5. Start the backend and open http://127.0.0.1:8000/ready. It should show `"database": "ok"`.

On startup Muse creates its indexes (unique IDs and auto-expiry for sessions and pending logins), so the `muse` database and its collections appear in Atlas after the first run. If your IP address changes, `/ready` shows `"database": "unavailable"` until you add the new one in Network Access.

## Log in with Spotify

Logging in lets Muse save your taste and create playlists in your Spotify account. It needs Spotify credentials, MongoDB (above) and an encryption key for stored tokens.

1. In the Spotify dashboard, open your app → **Settings** and make sure this **Redirect URI** is listed exactly: `http://127.0.0.1:8000/api/v1/auth/callback`
2. Under **User Management**, add the Spotify account(s) that will log in (Development Mode allows 5).
3. Generate an encryption key and add it to `.env`:
   ```powershell
   cd backend
   python -c "from app.core.crypto import generate_key; print(generate_key())"
   ```
   ```
   TOKEN_ENCRYPTION_KEY=<the printed key>
   ```
4. Start the backend and open **http://127.0.0.1:8000/api/v1/auth/login** in the browser (use `127.0.0.1`, not `localhost`, so the cookie matches). After approving on Spotify you land on `/docs`, logged in; try **GET /api/v1/me**.

The browser only receives a random session ID in an `HttpOnly` cookie. Spotify tokens stay on the server, encrypted. **POST /api/v1/auth/logout** ends the session immediately.

## Technology stack

Python 3.12 · FastAPI · scikit-learn · MongoDB · Spotify Web API · pytest · Docker · GitHub Actions · Render

The full design is in [Architecture](docs/ARCHITECTURE.md).

## Setup

### Prerequisites
- Git
- Python 3.12 or newer (`python --version`)
- Docker Desktop (needed from the Docker setup onwards)

### Run the backend locally (Windows PowerShell)

```powershell
git clone https://github.com/AthxrvA7/Muse.git
cd Muse
Copy-Item .env.example .env

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

On macOS or Linux, use `cp .env.example .env` and `source .venv/bin/activate` instead.

### Run the tests

```powershell
cd backend
pytest          # everything except the database tests (same as CI)
pytest --db     # also runs the repository tests against MONGODB_URI from .env
```

`pytest --db` works in a throwaway database (`muse_test_<random>`) and removes it afterwards; the real `muse` database is never touched. CI runs plain `pytest`, so it never needs the database password.

### Run the same checks as CI

```powershell
cd backend
ruff check .
ruff format --check .
pytest
```

CI runs these automatically on every push and pull request (see the **Actions** tab).

## Screenshots

*Added as features land.*

## Git workflow

We use **GitHub Flow**:

1. `main` is protected and always working.
2. Each change is made on a short-lived branch: `feature/<name>`, `fix/<name>`, `docs/<name>` or `chore/<name>`.
3. Commits follow [Conventional Commits](https://www.conventionalcommits.org/), e.g. `feat(auth): add Spotify OAuth callback`.
4. Each branch is merged through a pull request after CI passes and a teammate approves.
5. Milestones are tagged (`v0.1.0`, `v0.2.0`, …) and published as GitHub Releases.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements & risks](docs/REQUIREMENTS.md)
- [Security, privacy & wellbeing](docs/SECURITY_PRIVACY.md)
- [Architecture decisions](docs/adr/)
- [Roadmap](docs/ROADMAP.md)

## Disclaimer

Muse suggests music for how you feel. It is not a medical or mental-health tool. Muse is not affiliated with or endorsed by Spotify.

## License

[MIT](LICENSE)
