# AI Use Log

Required by the Muse synopsis (§14, Responsible Use of AI). Add one entry per meaningful use of an AI tool, newest at the bottom.
Never paste secrets, tokens or real user data into an AI tool.

**Template**

```
### YYYY-MM-DD — <short title>
- **Member:** 
- **Tool:** 
- **Purpose:** (learning / design / code suggestion / debugging / tests / docs)
- **Prompt (summary):** 
- **Output used:** (which files or parts)
- **Changes made by us:** 
- **Verification:** (how we checked it: tests, review, docs consulted)
- **Reflection:** (what we learned, what was wrong or missing in the AI output)
```

---

### 2026-10-20 — Architecture and project documentation
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** design, documentation
- **Prompt (summary):** Design an industry-style architecture for Muse within the course guidelines and the synopsis; check current Spotify API limits; produce the architecture, requirements, ADRs, threat model and roadmap.
- **Output used:** `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `docs/SECURITY_PRIVACY.md`, `docs/adr/*`, `docs/ROADMAP.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, the initial README.
- **Changes made by us:** Kept the repo public after first making it private (branch protection and security scanning are free only on public repos). Kept reviews required on `main` instead of letting the admin bypass them. Cut back a lot of the CI plan, because we haven't covered GitHub Actions in class yet and didn't want anything in the repo we can't explain. The roadmap now waits for each DevOps topic to be taught first.
- **Verification:** Spotify Feb-2026 developer-mode changes checked against Spotify's official migration guide; course requirements cross-checked against the Project Guidelines; design reviewed by the team in PR #1.
- **Reflection:** The biggest surprise was Spotify's API. Most tutorials still use audio features and the recommendations endpoint, but both are gone for apps like ours, so the recommender has to rely on our own genre data. Also, the first plan was more than we needed for a Semester III project. Pushing back on it (especially the CI extras) made the plan more realistic. Next time we'll ask for the smallest working version first and add to it.

### 2026-10-21 — Backend skeleton and first CI workflow
- **Member:** Atharva (skeleton), Darsh (CI)
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, learning
- **Prompt (summary):** Set up a FastAPI project structure with settings and tests; write a GitHub Actions workflow that runs lint and tests on every push.
- **Output used:** `backend/app/*`, `backend/tests/*`, `.env.example`, `.github/workflows/ci.yml`, ruff config in `backend/pyproject.toml`.
- **Changes made by us:** Ran the app and the tests on our own laptops (Windows and Mac) before committing. Fixed how the server was started (it has to be run from inside `backend/`). Added a typed response model after Swagger showed `additionalProp1` instead of the real fields. Fixed the GitHub login on the Mac so it could push workflow files.
- **Verification:** `pytest` passes locally (8 tests); the CI run on the PR shows Lint and Tests both green.
- **Reflection:** A workflow is just the same commands we run on our laptop, run on a fresh machine on every push. Pushing a workflow file needs extra GitHub permission (`workflow` scope), which we didn't know about until the push failed.

### 2026-10-21 — Mood engine (slice 1)
- **Member:** Atharva
- **Tool:** Claude (Anthropic)
- **Purpose:** code suggestion, design, learning
- **Prompt (summary):** Build the mood engine: chips on Russell's circumplex, an analyze endpoint, a TF-IDF + logistic regression emotion classifier with a training script, safe model loading, and a wellbeing notice.
- **Output used:** `backend/app/services/mood/*`, `backend/app/knowledge/*.json`, `backend/app/schemas/mood.py`, `backend/app/api/v1/mood.py`, `backend/scripts/train_mood_model.py`, the mood tests.
- **Changes made by us:** Trained the model on my own laptop (Claude couldn't reach Hugging Face). Results: test accuracy 0.879, macro-F1 0.838, best C = 4. Testing in Swagger showed two problems. First, neutral sentences like "exams tomorrow, need to study" got a made-up "joy" label, because the model always picks something (top probability only 0.31). We added a rule to use the model only when it's at least 50% sure and fall back to mood words otherwise. Second, Swagger pre-filled `"mode": "comfort"`, which overrode the "study" intent, so we fixed the example.
- **Verification:** 60 tests pass locally and in CI; ran real sentences through the trained model and checked the results by hand.
- **Reflection:** The model is very confident when there's a feeling word ("nervous" → fear 0.98) but unreliable on neutral text. An accuracy number alone doesn't show that; trying real inputs did. The mood positions in `mood_map.json` are our own estimates, and we say so in the file.
