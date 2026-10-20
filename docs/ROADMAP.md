# Muse — Development Roadmap (Phase 1: Backend)

Each block is **one branch → one pull request**. Tick boxes as commits land.

**Rules:** one commit = one logical change · Conventional Commit message · CI green before merge · ≥ 1 teammate approval · merge with **"Create a merge commit"** (not squash, so each commit stays visible) · update docs and tests in the same PR (see the Definition of Done in `CONTRIBUTING.md`).

**Owners:** 🅰 Atharva · 🅳 Darsh · 🅿 Piyush. Each person commits **from their own GitHub account**.

---

## Milestone 0 — Foundation

### `main` — initial commit (the only direct commit to main) 🅰
- [ ] `chore: initialize repository with README, license and git config`
- [ ] *(GitHub settings, no commit)* make the repo public, add collaborators, protect `main`, enable Dependabot alerts + secret scanning

### PR #1 `docs/project-design` 🅰
- [ ] `docs: add system architecture document`
- [ ] `docs: add requirements, assumptions and risk register`
- [ ] `docs: add architecture decision records`
- [ ] `docs: add threat model and privacy design`
- [ ] `docs: add roadmap, contributing guide, changelog and AI use log`

### PR #2 `chore/repo-templates` 🅳
- [ ] `chore: add pull request template with definition of done`
- [ ] `chore: add issue templates for bugs and features`
- [ ] `chore: add security policy and editorconfig`

### PR #3 `feature/backend-skeleton` 🅰
- [ ] `feat(backend): scaffold FastAPI application structure`
- [ ] `feat(config): add validated environment settings and env example`
- [ ] `test(backend): add pytest setup and app startup test`

### PR #4 `feature/ci-pipeline` 🅳
- [ ] `ci: add GitHub Actions workflow for lint and tests`
- [ ] `ci: add mypy type check and coverage report`
- [ ] `ci: add pip-audit dependency scan`
- [ ] `ci: add Dependabot and CodeQL configuration`
- [ ] *(GitHub settings)* mark CI checks as required on `main`

### PR #5 `feature/health-monitoring` 🅿
- [ ] `feat(monitoring): add structured JSON logging with request IDs`
- [ ] `feat(monitoring): add log redaction for sensitive fields`
- [ ] `feat(monitoring): add health and readiness endpoints`
- [ ] `test(monitoring): add health, request ID and redaction tests`

### PR #6 `feature/error-handling` 🅿
- [ ] `feat(errors): add consistent error response format`
- [ ] `feat(errors): add global exception handlers without stack traces`
- [ ] `test(errors): add error format and unhandled exception tests`

### PR #7 `feature/docker` 🅳
- [ ] `build: add backend Dockerfile with non-root user and healthcheck`
- [ ] `build: add docker-compose with MongoDB for local development`
- [ ] `ci: build Docker image in pipeline`

🏷 **Tag `v0.1.0` — Foundation** (CI, Docker, health checks, error handling)

---

## Milestone 1 — Security, auth & data

### PR #8 `feature/database` 🅰 + 🅳
- [ ] 🅰 `feat(db): add async MongoDB connection lifecycle`
- [ ] 🅰 `feat(db): add repositories with unique and TTL indexes`
- [ ] 🅳 `ci: add MongoDB service container for integration tests`
- [ ] 🅰 `test(db): add repository and index integration tests`

### PR #9 `feature/security-hardening` 🅰
- [ ] `feat(security): add security headers and strict CORS`
- [ ] `feat(security): add rate limiting`
- [ ] `feat(security): add origin check for state-changing requests`
- [ ] `test(security): add header, CORS, rate-limit and CSRF tests`

### PR #10 `feature/spotify-auth` 🅰
- [ ] `feat(spotify): add Spotify API client with timeouts and retry handling`
- [ ] `feat(auth): add Spotify OAuth login and callback with state check`
- [ ] `feat(auth): add encrypted token storage and server-side sessions`
- [ ] `feat(auth): add token refresh, logout and me endpoint`
- [ ] `test(auth): add OAuth, session and token encryption tests`

### PR #11 `feature/privacy-controls` 🅰
- [ ] `feat(privacy): add privacy notice endpoint and consent versioning`
- [ ] `feat(privacy): add personal data export endpoint`
- [ ] `feat(privacy): add account deletion across all collections`
- [ ] `feat(audit): add audit events for security-relevant actions`
- [ ] `test(privacy): add export, deletion and audit tests`

🏷 **Tag `v0.2.0` — Secure auth & data**

---

## Milestone 2 — Classics ("Know your music")

### PR #12 `feature/user-preferences` 🅰
- [ ] `feat(catalog): add artist and track search endpoint`
- [ ] `feat(preferences): add preference profile endpoints`
- [ ] `feat(preferences): add Music DNA summary endpoint`
- [ ] `test(preferences): add validation, access-control and DNA tests`

🏷 **Tag `v0.3.0` — Classics**

---

## Milestone 3 — Essential ("Curate for me")

### PR #13 `feature/mood-analysis` 🅰
- [ ] `feat(mood): add mood chip to valence-energy mapping`
- [ ] `feat(mood): add emotion classifier training script and model card`
- [ ] `feat(mood): add trained model with integrity check and analyze endpoint`
- [ ] `feat(mood): add wellbeing support notice`
- [ ] `test(mood): add mapping, classifier, fallback and wellbeing tests`

### PR #14 `feature/recommendation` 🅰
- [ ] `feat(recommender): add genre knowledge base`
- [ ] `feat(recommender): add query planning and candidate search`
- [ ] `feat(recommender): add mood and taste scoring`
- [ ] `feat(recommender): add diversity re-ranking`
- [ ] `feat(recommender): add recommendation explanations`
- [ ] `test(recommender): add scoring, ranking, explanation and performance tests`

### PR #15 `feature/playlist-export` 🅰
- [ ] `feat(playlist): add curate endpoint with session storage`
- [ ] `feat(playlist): export curated playlist to Spotify`
- [ ] `test(playlist): add end-to-end curate flow test with mocked Spotify`

🏷 **Tag `v0.4.0` — Essential backend**

---

## Milestone 4 — Deployment & operations

### PR #16 `feature/deployment` 🅰 + 🅳
- [ ] 🅰 `build: add Render deployment configuration`
- [ ] 🅳 `ci: deploy to Render after successful build on main`
- [ ] 🅰 `docs: add deployment and rollback runbooks`

### PR #17 `feature/ops-runbooks` 🅳 + 🅰
- [ ] 🅰 `feat(ops): add database backup and restore scripts`
- [ ] 🅳 `docs: add backup-restore and incident response runbooks`
- [ ] 🅳 `docs: record backup restore rehearsal result`

### PR #18 `docs/final-backend` 🅿 + 🅰
- [ ] 🅿 `docs: add API usage guide and screenshots`
- [ ] 🅰 `docs: complete README and sync architecture with implementation`
- [ ] 🅰 `docs: update requirements status and evidence`

🏷 **Tag `v1.0.0-backend` — Deployed backend** (submission point for this semester)

---

**Total planned: ~70 commits across 18 PRs + 1 initial commit** (guideline minimum: 15 commits, 2 branches, 3 tests).

## Later phases (not this semester)
- **Phase 2:** `feature/frontend-*` (Piyush lead): React app, consent screen, dashboard, Music DNA charts, mood input, playlist view; WCAG 2.2 AA with axe checks in CI.
- **Phase 3:** `feature/feedback-loop`, `feature/session-history`, `feature/mood-trajectory`.
