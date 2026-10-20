# ADR-0008: GitHub Flow, Conventional Commits and a public repository

- **Status:** Accepted · **Date:** 2026-10-20

## Context
The course grades Git usage: ≥ 15 meaningful commits, feature branches, PRs per member and CI. We want branch protection and free security scanning.

## Decision
- **GitHub Flow:** `main` is protected and always deployable; short-lived `feature/`, `fix/`, `docs/`, `chore/` branches; every change goes through a PR with ≥ 1 teammate approval and green CI; squash is **not** used, so individual commits stay visible in history.
- **Conventional Commits** (`feat(scope): ...`, `fix:`, `test:`, `ci:`, `docs:`, `build:`, `chore:`).
- **Semantic version tags** at milestones, with GitHub Releases and `CHANGELOG.md`.
- **Public repository.** Branch protection, CodeQL and secret-scanning push protection are free on public repos (they need a paid plan on private personal repos). No secrets ever live in the repo.

## Alternatives considered
- **Git Flow (develop/release/hotfix branches):** too heavy for a three-person, one-semester project.
- **Private repo:** needs GitHub Pro (available free through the Student Developer Pack) for branch protection; still loses free CodeQL. Acceptable fallback if the faculty requires privacy.

## Consequences
- The commit graph clearly shows branches, PRs and authors for evaluation.
- Code is publicly visible, so secrets hygiene is mandatory (already required).
