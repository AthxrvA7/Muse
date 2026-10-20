# Architecture Decision Records

An ADR records one significant decision: the context, what we chose, what we rejected, and the consequences. ADRs are never edited after acceptance. To change a decision, write a new ADR that **supersedes** the old one.

Format: [Michael Nygard's template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). File name: `NNNN-short-title.md`.

| # | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with layered architecture | Accepted | 2026-10-20 |
| [0002](0002-genre-knowledge-base.md) | Muse-owned genre knowledge base instead of Spotify audio features | Accepted | 2026-10-20 |
| [0003](0003-server-side-sessions.md) | Server-side sessions and encrypted Spotify tokens | Accepted | 2026-10-20 |
| [0004](0004-pymongo-async-driver.md) | PyMongo async driver instead of Motor | Accepted | 2026-10-20 |
| [0005](0005-lightweight-mood-classifier.md) | TF-IDF + logistic regression mood classifier | Accepted | 2026-10-20 |
| [0006](0006-store-derived-mood-not-raw-text.md) | Store derived mood, never raw mood text | Accepted | 2026-10-20 |
| [0007](0007-render-and-atlas-deployment.md) | Render + MongoDB Atlas for the demo deployment | Accepted | 2026-10-20 |
| [0008](0008-github-flow-public-repo.md) | GitHub Flow, Conventional Commits and a public repository | Accepted | 2026-10-20 |
| [0009](0009-curation-core-first.md) | Build the curation core before persistence and login | Accepted | 2026-10-21 |
