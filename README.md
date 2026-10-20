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
| Classics: "Know your music" | Preference profile, reference tracks, Music DNA | Planned |
| Essential: "Curate for me" | Mood analysis ✅, preference + mood scoring, explained playlist, export to Spotify | In progress |
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
pytest
```

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
