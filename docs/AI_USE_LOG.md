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
- **Changes made by us:** _(fill in after team review, e.g. adjusted owners, weights, scope)_
- **Verification:** Spotify Feb-2026 developer-mode changes checked against Spotify's official migration guide; course requirements cross-checked against the Project Guidelines; design reviewed by the team in PR #1.
- **Reflection:** _(fill in: e.g. the AI flagged that Spotify removed audio features and recommendations, which changed our recommender design to a Muse-owned genre knowledge base)_
