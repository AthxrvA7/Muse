# ADR-0011: Song moods from Last.fm listener tags, and the user's own top tracks

- **Status:** Accepted · **Date:** 2026-11-26 · **Deciders:** Atharva

## Context
Testing the deployed app with real accounts showed two problems:
1. **The same playlist every time.** Curation was fully deterministic, and Spotify's artist search returns the same top hits, so the same mood always gave the same songs.
2. **Mood barely changed the songs from favourite artists.** Muse could only estimate a song's feel from the genre search that found it (ADR-0002). Songs found by an artist search had no estimate and all scored a neutral 0.5 for mood, so Muse couldn't tell which of a favourite artist's songs fit tonight.

Spotify gives Development Mode apps no audio features, popularity or recommendations, so a per-song mood signal has to come from somewhere else.

## Decision
- **Last.fm listener tags** give each song a mood. Feeling tags ("chill", "sad", "party", 84 of them in `knowledge/mood_tags.json`) are placed on the valence-energy map; genre tags use `genre_kb.json` at half weight. Track tags first, the artist's tags as a less certain fallback. Lookups run in parallel within a 6-second budget, are cached for a day, and any failure falls back to the old estimate.
- **Last.fm similar artists** replace most "new song" discovery: artists similar to the first three favourites are searched on Spotify (taste fit 0.8, between a favourite artist and a favourite genre).
- **The user's Spotify top tracks** (last ~4 weeks and ~6 months, read with the `user-top-read` scope) become the "familiar" pool. They are read when the user curates and are never stored.
- **A familiar/new mix** (`familiarity`, 0–1, default by mode: comfort 0.7, focus/energy 0.6, discovery 0.3) decides how many songs the user already knows.
- **Freshness:** a small random nudge (≤ 0.04) lets equally good songs take turns; songs picked for the user recently (last 90 track IDs, kept 30 days) lose 0.15; "Give me another" sends the shown track IDs to be left out.

## Alternatives considered
- **Lyrics sentiment:** no lyrics API we may use for free, and lyrics are copyrighted text.
- **An LLM tagging each song:** cost, an extra key, slow, and hard to explain in a viva.
- **Saved library / recently played:** more permissions for little extra signal; top tracks already reflect what the user listens to.

## Consequences
- Mood fit is now song-level wherever Last.fm knows the song, and the explanation can say why ("listeners tag it 'chill' and 'late night'").
- A new external dependency (free Last.fm API key, `LASTFM_API_KEY`) with attribution on the results page. Without a key, Muse works as before.
- The synopsis said Muse would not use Spotify listening data. We read the user's top artists and tracks only on their action (curate or import), never store them, never analyse skips or completion, and never train on them. Recent picks are Muse's own data and are included in export and deletion.
- Results are no longer deterministic for the same input (FR6 updated); tests pin the random source where order matters.

## Addendum (26 Nov 2026): coherence and tempo
- Listeners also tag language and genre ("hindi", "bollywood"), so each song gets a language and a genre from Last.fm tags (track and artist) and its title's script. A playlist keeps one language and builds around one genre; `genre_kb.json` gives every genre a family and lists related families.
- Tempo (BPM) comes from Deezer's free public API, matched by ISRC. It is shown on each song and gives a small bonus when the pace fits the mood. No key is needed; `DEEZER_ENABLED=false` switches it off.
