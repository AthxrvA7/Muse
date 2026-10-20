# Muse — Development Roadmap (Phase 1: Backend)

Each block is **one branch → one pull request**. Tick boxes as commits land, and note the GitHub PR number when merged (GitHub numbers PRs in the order they're opened, so they won't match this list's order).

**Rules:** one commit = one logical change · Conventional Commit message · CI green before merge · ≥ 1 teammate approval · merge with **"Create a merge commit"** · update docs and tests in the same PR (Definition of Done in `CONTRIBUTING.md`).

**Pacing rule:** a DevOps feature is built only after the team has studied it in class and can explain it. Items marked ⏸ wait for that.

**Owners:** 🅰 Atharva · 🅳 Darsh · 🅿 Piyush. Each person commits from their own GitHub account.

---

## Milestone 0 — Foundation ✅

### `main` — initial commit 🅰
- [x] `chore: initialize repository with README, license and git config`
- [x] *(GitHub settings)* public repo, collaborators, protect `main`

### `docs/project-design` 🅰 — merged as #1
- [x] `docs: add system architecture document`
- [x] `docs: add requirements, assumptions and risk register`
- [x] `docs: add architecture decision records`
- [x] `docs: add threat model and privacy design`
- [x] `docs: add roadmap, contributing guide, changelog and AI use log`

### `chore/repo-templates` 🅳 — merged as #3
- [x] `chore: add pull request template with definition of done`
- [x] `chore: add issue templates for bugs and features`
- [x] `chore: add security policy and editorconfig`

### `feature/backend-skeleton` 🅰 — merged as #2
- [x] `feat(backend): scaffold FastAPI application structure`
- [x] `feat(config): add validated environment settings and env example`
- [x] `test(backend): add pytest setup and app startup tests`
- [x] `refactor(api): add typed response model for service info`

### `feature/ci-pipeline` 🅳 — merged as #4
- [x] `ci: add GitHub Actions workflow for lint and tests`
- [ ] *(GitHub settings, 🅰)* require `Lint` and `Tests` checks to pass before merging

### `docs/sync-foundation` 🅰
- [ ] `docs: sync changelog, roadmap, readme and AI log after foundation`

---

## Milestone 1 — Observability & data

### `feature/health-monitoring` 🅿
- [ ] `feat(monitoring): add structured JSON logging with request IDs`
- [ ] `feat(monitoring): add log redaction for sensitive fields`
- [ ] `feat(monitoring): add health and readiness endpoints`
- [ ] `test(monitoring): add health, request ID and redaction tests`

### `feature/error-handling` 🅿
- [ ] `feat(errors): add consistent error response format`
- [ ] `feat(errors): add global exception handlers without stack traces`
- [ ] `test(errors): add error format and unhandled exception tests`

### `feature/database` 🅰 (MongoDB Atlas free cluster for development)
- [ ] `feat(db): add async MongoDB connection lifecycle`
- [ ] `feat(db): add repositories with unique and TTL indexes`
- [ ] `test(db): add repository tests`

🏷 **Tag `v0.1.0` — Foundation**

---

## Milestone 2 — Security, auth & privacy

### `feature/security-hardening` 🅰
- [ ] `feat(security): add security headers and strict CORS`
- [ ] `feat(security): add rate limiting`
- [ ] `feat(security): add origin check for state-changing requests`
- [ ] `test(security): add header, CORS, rate-limit and CSRF tests`

### `feature/spotify-auth` 🅰
- [ ] `feat(spotify): add Spotify API client with timeouts and retry handling`
- [ ] `feat(auth): add Spotify OAuth login and callback with state check`
- [ ] `feat(auth): add encrypted token storage and server-side sessions`
- [ ] `feat(auth): add token refresh, logout and me endpoint`
- [ ] `test(auth): add OAuth, session and token encryption tests`

### `feature/privacy-controls` 🅰
- [ ] `feat(privacy): add privacy notice endpoint and consent versioning`
- [ ] `feat(privacy): add personal data export endpoint`
- [ ] `feat(privacy): add account deletion across all collections`
- [ ] `feat(audit): add audit events for security-relevant actions`
- [ ] `test(privacy): add export, deletion and audit tests`

🏷 **Tag `v0.2.0` — Secure auth & data**

---

## Milestone 3 — Classics ("Know your music")

### `feature/user-preferences` 🅰
- [ ] `feat(catalog): add artist and track search endpoint`
- [ ] `feat(preferences): add preference profile endpoints`
- [ ] `feat(preferences): add Music DNA summary endpoint`
- [ ] `test(preferences): add validation, access-control and DNA tests`

🏷 **Tag `v0.3.0` — Classics**

---

## Milestone 4 — Essential ("Curate for me")

### `feature/mood-analysis` 🅰
- [ ] `feat(mood): add mood chip to valence-energy mapping`
- [ ] `feat(mood): add emotion classifier training script and model card`
- [ ] `feat(mood): add trained model with integrity check and analyze endpoint`
- [ ] `feat(mood): add wellbeing support notice`
- [ ] `test(mood): add mapping, classifier, fallback and wellbeing tests`

### `feature/recommendation` 🅰
- [ ] `feat(recommender): add genre knowledge base`
- [ ] `feat(recommender): add query planning and candidate search`
- [ ] `feat(recommender): add mood and taste scoring`
- [ ] `feat(recommender): add diversity re-ranking`
- [ ] `feat(recommender): add recommendation explanations`
- [ ] `test(recommender): add scoring, ranking, explanation and performance tests`

### `feature/playlist-export` 🅰
- [ ] `feat(playlist): add curate endpoint with session storage`
- [ ] `feat(playlist): export curated playlist to Spotify`
- [ ] `test(playlist): add end-to-end curate flow test with mocked Spotify`

🏷 **Tag `v0.4.0` — Essential backend**

---

## DevOps track (🅳 lead) — added as each topic is covered in class

| Branch | Adds | Status |
|---|---|---|
| `feature/ci-type-coverage` | mypy type check, coverage report and 80% gate | ⏸ after GitHub Actions basics |
| `feature/ci-mongodb-service` | MongoDB service container so database tests run in CI | ⏸ with `feature/database` |
| `feature/ci-dependency-audit` | pip-audit vulnerability scan | ⏸ |
| `feature/ci-security-scanning` | Dependabot + CodeQL | ⏸ |
| `feature/docker` | Dockerfile, docker-compose with MongoDB, Docker build in CI | ⏸ after Docker is covered |
| `feature/deployment` | Render deployment + deploy after CI on `main` | ⏸ after CD is covered |
| `feature/ops-runbooks` | Backup/restore + incident runbooks, restore rehearsal | ⏸ with deployment |

🏷 **Tag `v1.0.0-backend` — Deployed backend** (submission point for this semester)

---

## Later phases (not this semester)
- **Phase 2:** `feature/frontend-*` (Piyush lead): React app, consent screen, dashboard, Music DNA charts, mood input, playlist view; WCAG 2.2 AA.
- **Phase 3:** `feature/feedback-loop`, `feature/session-history`, `feature/mood-trajectory`.
