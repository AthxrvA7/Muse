# ADR-0010: Distance on the valence-energy plane, not cosine similarity, for mood fit

- **Status:** Accepted · **Date:** 2026-10-21 · **Deciders:** Atharva

## Context
The architecture first said `mood_fit` would be the cosine similarity between a track's (valence, energy) vector and the mood's. Cosine similarity compares the *direction* of two vectors and ignores their length. On a plane where both axes run from 0 to 1, that is wrong: (0.1, 0.1) "very sad and very calm" and (0.9, 0.9) "very happy and very energetic" point in the same direction, so cosine similarity calls them a perfect match (1.0).

## Decision
`mood_fit = 1 − euclidean_distance(track, mood) / √2`, where √2 is the largest possible distance in the unit square. 1 = same spot, 0 = opposite corners. When a track's feel is only an estimate, the fit is pulled towards a neutral 0.5 in proportion to the uncertainty (genre search = certain, title words = 0.8, unknown = 0).

## Alternatives considered
- **Cosine similarity:** rejected for the reason above.
- **Gaussian (RBF) similarity, exp(−d²/2σ²):** smooth, but adds a tuning parameter (σ) we have no data to set; distance is easier to explain.
- **A learned model:** no training data that we are allowed to use (Spotify content can't be used for training).

## Consequences
- Tested: a tired mood (0.30, 0.20) rates a ghazal track > 0.8 and a metal track < 0.6.
- Scoring is plain Python geometry rather than a scikit-learn call; 300 candidates score in well under 200 ms (NFR1).
- ADR-0002 still stands; only the similarity measure changes.
