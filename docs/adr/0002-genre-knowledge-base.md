# ADR-0002: Muse-owned genre knowledge base instead of Spotify audio features

- **Status:** Accepted · **Date:** 2026-10-20

## Context
Muse must judge how well a track fits a mood. Spotify's Audio Features, Audio Analysis, Recommendations and Related Artists endpoints are unavailable to apps like ours (deprecated in November 2024). Since February 2026, development-mode apps have also lost artist top tracks and popularity, and search is capped at 10 results per request. Artist `genres` are often empty. Spotify's terms also forbid training ML models on Spotify content.

## Decision
Maintain `knowledge/genre_kb.json`, a hand-curated, versioned table of ~60–80 genres and styles, each with a valence, energy, tempo tendency and language links. A track inherits the profile of the genre query that surfaced it, combined with signals from the user's stated preferences. Scoring uses cosine similarity (scikit-learn) between the track vector and the mood target vector.

## Alternatives considered
- **Spotify audio features:** unavailable.
- **A public Kaggle dataset of Spotify audio features:** rejected. It is derived from Spotify content (a terms risk) and it goes stale.
- **Last.fm track tags for mood:** possible future enhancement (track-level signal). Deferred because it adds a second external API and key.
- **Analysing audio previews:** rejected. Previews are largely unavailable, and this is heavy and terms-sensitive.

## Consequences
- Fully compliant and explainable.
- Mood fit works at the **genre/artist level, not the per-song level**. This is stated as a known limitation in the README and report.
- The KB is application-owned data that we can test, review in PRs and version.
