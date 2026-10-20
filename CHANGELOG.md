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

### Changed
- The classifier is used only when it is at least 50% confident; neutral text ("need to study") falls back to mood words instead of a guessed emotion
- Swagger's example mood request no longer pre-fills `mode`, which was overriding the detected intent
