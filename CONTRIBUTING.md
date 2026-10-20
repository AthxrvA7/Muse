# Contributing to Muse

This guide is how the three of us work. If something here stops matching reality, fix this file in a PR.

## 1. Workflow (GitHub Flow)

1. Pick a task from the [roadmap](docs/ROADMAP.md) or an issue and assign it to yourself.
2. Update `main` and create a branch:
   ```bash
   git switch main
   git pull
   git switch -c feature/<short-name>
   ```
   Prefixes: `feature/` new functionality · `fix/` bug fix · `docs/` documentation only · `chore/` tooling and config.
3. Commit small, logical steps (see §2). Push your branch: `git push -u origin <branch>`.
4. Open a pull request into `main`. Fill in the template and request a reviewer.
5. Wait for green CI **and** one approval, then merge with **"Create a merge commit"** (never squash; every commit should stay visible in history).
6. Delete the branch after merging.

Never push directly to `main`. Branch protection enforces this.

## 2. Commit messages — Conventional Commits

```
<type>(<optional scope>): <what changed, imperative, lowercase, no full stop>
```

| Type | Use for |
|---|---|
| `feat` | new behaviour |
| `fix` | bug fix |
| `test` | adding or changing tests only |
| `docs` | documentation only |
| `ci` | GitHub Actions and pipeline |
| `build` | Docker, dependencies, packaging |
| `refactor` | code change with no behaviour change |
| `chore` | repo housekeeping |

Good: `feat(auth): add Spotify OAuth callback`. Bad: `update`, `final`, `fixed stuff`, `abc`.

**Commit from your own GitHub account.** Before your first commit, set your identity and check that the email is linked to your GitHub account:
```bash
git config --global user.name "Your Name"
git config --global user.email "email-on-your-github-account"
```

## 3. Definition of Done

A PR is mergeable only when **all** of these are true:

- [ ] It meets the acceptance criteria of the requirement(s) it implements (`docs/REQUIREMENTS.md`)
- [ ] It has tests for new behaviour, including at least one failure or edge case
- [ ] CI is green (lint, type check, tests, dependency audit, Docker build)
- [ ] There are no secrets, tokens or personal data in code, tests, logs or fixtures
- [ ] Docs are updated in the same PR: README, ARCHITECTURE, an ADR if a decision was made, CHANGELOG under *Unreleased*, requirement status
- [ ] Any AI assistance is recorded in `docs/AI_USE_LOG.md`
- [ ] The author can explain every line of it in review

## 4. Reviewing

Reviewers check:
- **Correctness:** does it do what the PR claims, and are failure cases handled?
- **Layering:** routes never touch MongoDB or Spotify directly.
- **Security and privacy:** input validated, user data scoped by `user_id`, nothing sensitive logged.
- **Tests:** do they fail if the feature is broken?
- **Docs:** do they match the code?

Use "Request changes" for anything that blocks merging, and comments for suggestions. Be kind and specific.

## 5. Using AI tools

AI tools may help (see the synopsis, §14). Rules:
1. Never paste secrets, tokens or real user data into an AI tool.
2. Review, test and understand any AI output before committing it.
3. Add an entry to `docs/AI_USE_LOG.md`: prompt summary, what was used, what you changed, and a short reflection.
4. Passing tests does not prove AI-generated code is secure. Review it like any other code.

## 6. Reporting security issues

Don't open a public issue. See `SECURITY.md`.
