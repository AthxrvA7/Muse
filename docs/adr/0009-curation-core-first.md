# ADR-0009: Build the curation core before persistence and login

- **Status:** Accepted · **Date:** 2026-10-21 · **Deciders:** Atharva

## Context
The first roadmap built bottom-up: database, Spotify login, preferences, then mood and recommendations. That meant weeks of plumbing before anything visible worked, and a real risk of reaching the deadline without the core idea demonstrated. Spotify's client-credentials flow lets an app search the catalogue without a user logging in.

## Decision
Build in vertical slices, core first:
1. Mood engine (no external services).
2. Recommender: Spotify search via client credentials + Muse scoring, with preferences sent in the request (stateless).
3. User login (OAuth), MongoDB, stored preferences and Music DNA.
4. Playlist export to the user's account and privacy controls.

## Alternatives considered
- **Bottom-up (original plan):** rejected for the reason above.
- **Frontend first:** rejected; the frontend is Phase 2 and depends on a working API.

## Consequences
- A demoable "mood → explained songs" result after slice 2.
- The architecture (ARCHITECTURE.md) is unchanged; only the order differs. Slice 3 adds a stored profile in front of the same recommender.
- Client credentials only allow catalogue reads; user-specific actions (playlist creation) still need OAuth in slice 4.
