# ADR-0007: Render + MongoDB Atlas for the demo deployment

- **Status:** Accepted · **Date:** 2026-10-20

## Context
The guidelines require a deployment (Render, Netlify, Vercel, GitHub Pages or documented local deployment). Spotify requires HTTPS redirect URIs, except for loopback. The backend runs in Docker and needs MongoDB.

## Decision
Deploy the backend Docker image to a **Render** free web service, and use a **MongoDB Atlas M0** free cluster in the nearest region (Mumbai if available). Deploy only from `main` after CI passes, via a Render deploy hook stored as a GitHub secret. Documented local deployment (`docker compose up`) is the fallback.

## Alternatives considered
- **Vercel / Netlify:** built for frontends and serverless; a poor fit for a long-running FastAPI + ML process. Possible for the Phase 2 frontend.
- **AWS / Azure VMs:** cost, card verification and complexity; "AWS production infrastructure" is out of scope per the guidelines.
- **Railway / Fly.io:** comparable, but Render is on the guideline list.

## Consequences
- Free public HTTPS URL; the Docker image is the same one CI builds.
- Cold starts (~30–60 s after idle). Before a demo, call `/health` first.
- Atlas M0: no self-service backups, and the cluster pauses after 30 days of inactivity. Mitigated by the backup runbook (risk R4).
