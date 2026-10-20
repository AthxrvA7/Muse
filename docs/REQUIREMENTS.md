# Muse — Requirements

> **Source:** Muse synopsis (FR1–FR10, NFRs), the course guidelines (CSDV2010P), and the team's quality brief (security, privacy, wellbeing, reliability, documentation).
> **Status column:** `Planned` → `Implemented` → `Verified`. A requirement counts as *Verified* only when a test or a recorded manual check proves it. The evidence goes in the last column.

---

## 1. Course requirements (mandatory)

| ID | Requirement | Acceptance criteria | Status | Evidence |
|---|---|---|---|---|
| C1 | GitHub repository | Meaningful name; ≥ 15 commits with meaningful messages | Planned | |
| C2 | Branching | `main` + `feature/*` branches; every member merges via PR | Planned | |
| C3 | README | Title, problem, team, features, stack, setup, screenshots, git workflow | Planned | |
| C4 | Automated tests | ≥ 3 automated tests (we target ≥ 80% backend coverage) | Verified | 60 pytest tests run in CI on every push |
| C5 | CI | GitHub Actions on push showing pass/fail | Planned | |
| C6 | Deployment | A public deployment URL with documented setup | Planned | |

## 2. Functional requirements

| ID | Requirement | Acceptance criteria | Phase | Status |
|---|---|---|---|---|
| FR1 | Spotify authentication | Login redirects to Spotify; callback rejects a missing or mismatched `state` with `400`; success creates a session cookie; logout invalidates it server-side | 1 | Planned |
| FR2 | Preference input | Save/read artists, genres, languages, styles, reference tracks and exclusions; invalid or oversized input rejected with `422` | 1 | Planned |
| FR3 | Music DNA | Returns a genre spread, top artists, language mix and default mood centre, computed only from stated preferences | 1 | Planned |
| FR4 | Mood input | Accepts chips (≤ 5) and/or text (≤ 500 chars); at least one is required | 1 | Verified (`test_mood_api.py`) |
| FR5 | Mood processing | Returns valence, energy (0–1), tempo, labels, mode and confidence; chips-only input is deterministic | 1 | Verified (`test_mood_analyzer.py`, `test_mood_classifier.py`) |
| FR6 | Preference + mood scoring | Every candidate gets `mood_fit`, `taste_fit` and `score`; ranking is deterministic for the same input and candidates | 1 | Planned |
| FR7 | Playlist generation | Returns 10–30 tracks (default 15); ≤ 2 tracks per artist; excluded artists never appear | 1 | Planned |
| FR8 | Explanations | Every track has a sentence that only refers to factors that actually contributed to its score | 1 | Planned |
| FR9 | Spotify playlist creation | Export creates a playlist in the user's account containing exactly the curated tracks; the Spotify URL is returned and stored | 1 | Planned |
| FR10 | Persistence | Preferences, mood sessions and playlist records are stored in MongoDB | 1 | Planned |
| FR11 | Data access & deletion *(added)* | `GET /me/data` returns all of the user's Muse data as JSON; `DELETE /me` removes every document for that user and ends all sessions | 1 | Planned |
| FR12 | Wellbeing notice *(added)* | Text matching the crisis-phrase list returns a `support` notice with helpline information; music is still returned; the text is not stored | 1 | Verified (`test_wellbeing.py`); phrase list awaits counsellor/faculty review |
| FR13 | Feedback loop | Like/dislike per track | 3 | Deferred |
| FR14 | Session history & mood trajectory | List past sessions; chart moods over time | 3 | Deferred |

## 3. Non-functional requirements

| ID | Quality | Requirement | Acceptance criteria (how we verify) |
|---|---|---|---|
| NFR1 | Performance | Curate completes quickly | p95 ≤ 5 s for a 15-track playlist with mocked Spotify latency of 300 ms per call (timed test); Muse's own scoring ≤ 200 ms for 300 candidates |
| NFR2 | Security | Secrets never in code, logs or the frontend | Secret scanning on; log-redaction test; `.env` git-ignored |
| NFR3 | Security | Tokens encrypted at rest | Test: the stored token field is not equal to the plaintext token and decrypts correctly |
| NFR4 | Security | Protected endpoints need a valid session | Security tests: no cookie, expired session and deleted session each return `401` |
| NFR5 | Security | Abuse resistance | Rate-limit test returns `429` after the limit; security headers present on every response |
| NFR6 | Security | Supply chain | pip-audit passes in CI (no known high/critical vulnerabilities, or a documented exception); Dependabot enabled; CodeQL shows no open high alerts |
| NFR7 | Privacy | Data minimisation and retention | Mood text never written to the database or logs (test); TTL indexes exist for sessions, mood_sessions, oauth_states and audit_events (test) |
| NFR8 | Reliability | Graceful degradation | Tests for Spotify timeout → `503`, 429 → `429`, missing model → degraded mode, unknown exception → generic `500` with no stack trace |
| NFR9 | Reliability | Recoverability | Backup and restore rehearsed once against a test database; result recorded in the runbook |
| NFR10 | Maintainability | Layered and typed | Ruff and mypy pass in CI; routes never import the database or Spotify client directly (reviewed in PRs) |
| NFR11 | Portability | Runs anywhere Docker runs | `docker compose up` gives a healthy `/ready` on a clean machine |
| NFR12 | Usability / accessibility | Clear errors now; WCAG 2.2 AA in Phase 2 | Phase 1: every error has a human-readable `message`. Phase 2: axe/Lighthouse checks in CI, keyboard-only walkthrough |
| NFR13 | Compliance | Within Spotify developer policy | No Spotify content used for ML training; no listening-history metrics; only the scopes listed in ARCHITECTURE §4.2 |
| NFR14 | Observability | Traceable requests | Every log line has a request ID; `/health` and `/ready` available |

## 4. Assumptions

| ID | Assumption | If wrong… |
|---|---|---|
| A1 | Spotify's Feb-2026 developer-mode rules stay as documented (5 users, search limit 10, new playlist endpoints) | The Spotify client is updated in one place; checked again before each milestone |
| A2 | Users of the demo are the ≤ 5 accounts added to the Spotify dashboard | Others will get a Spotify error at login — documented in the README |
| A3 | Users type mood text in English | Classifier accuracy drops; chips remain reliable |
| A4 | Render and Atlas free tiers stay available | Fallback is documented local deployment (allowed by the guidelines) |
| A5 | No real personal data beyond the team's own test accounts is used during development | — |

## 5. Scoped-down or excluded requirements (and why)

The quality brief is written for a commercial product. Muse is a Semester III project with ≤ 5 test users, so these items are deliberately scaled down. Each one is a decision, not an oversight.

| Brief item | What we do instead | Why |
|---|---|---|
| "Compliance with applicable data protection laws" | We follow the principles of India's DPDP Act 2023 (notice, consent, purpose limitation, minimisation, deletion, security safeguards). We do **not** claim legal compliance. | No legal review is available. The DPDP Rules' main obligations only take effect on 13 May 2027, and Muse is not offered to the public. |
| Clinical safety / medical-data regulation | Not applicable: Muse gives no health advice or diagnosis (synopsis "Out of Scope"). We add a conservative wellbeing notice (FR12) and clear "not a medical tool" wording. | Mood-based music curation is not a health function. |
| Defined availability SLA | Best-effort availability with stated RPO 24 h / RTO 1 h | The free hosting tier sleeps; promising an SLA would be false. |
| Automated backups | Manual `mongodump` before demos and releases, plus one rehearsed restore | Atlas M0 has no self-service backups; automating dumps of user data into CI artifacts would be a privacy risk. |
| Penetration testing / enterprise DevSecOps | CodeQL, pip-audit, Dependabot, secret scanning, security unit tests, and a STRIDE threat model | The guidelines list enterprise DevSecOps platforms as out of scope; the free GitHub tools cover the main risks. |
| Formal incident response team | A one-page incident runbook (detect → contain → rotate secrets → notify team → post-mortem) | Three-person team, no public users. |
| Multi-instance scalability | A single instance; rate-limit state in memory | Five users. Moving rate limits to MongoDB or Redis is noted in ADR-0001 as the scale-out path. |
| WCAG 2.2 AA now | Applies in Phase 2 (frontend) | Phase 1 has no UI apart from the auto-generated Swagger docs. |
| Database migrations framework | Versioned documents + numbered scripts | MongoDB has no fixed schema; a framework adds nothing at this size. |

## 6. Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Owner's Spotify Premium lapses → app stops working | Low | High | Keep the subscription active through the evaluation; note in README | Atharva |
| R2 | Spotify changes the API again | Medium | High | Single Spotify client; contract tests with recorded responses; recheck before milestones | Atharva |
| R3 | Recommendations feel generic (genre-level mood only) | Medium | Medium | Good KB coverage; diversity re-ranking; explanations; stated openly as a limitation | Atharva |
| R4 | Atlas free cluster paused after 30 days of inactivity | Medium | Medium | Use the app at least monthly; backups before breaks | Atharva |
| R5 | Uneven contribution history | Medium | High (grading) | Owners commit from their own accounts; PR reviews by teammates | All |
| R6 | Secret accidentally committed | Low | High | `.gitignore`, secret scanning + push protection; rotation steps in incident runbook | Darsh |
| R7 | Wellbeing check misses or over-triggers | Medium | Medium | Conservative list, tested both ways; notice is non-blocking; documented limits | Atharva |
| R8 | AI-generated code accepted without understanding | Medium | High | AI use log; owner explains every PR in review; tests required | All |
