# ADR-0001: Modular monolith with layered architecture

- **Status:** Accepted · **Date:** 2026-10-20 · **Deciders:** Atharva, Darsh, Piyush

## Context
Muse has distinct concerns (auth, preferences, mood, recommendation, Spotify, persistence) but ≤ 5 users and a three-person team. The course guidelines explicitly rule out microservices for Semester III.

## Decision
One FastAPI service, split into layers: **routes → services → clients/repositories**. Routes contain no business logic. Only `clients/spotify.py` talks to Spotify; only `db/` repositories talk to MongoDB. Dependencies are injected through FastAPI's `Depends`, so tests can swap in fakes.

## Alternatives considered
- **Microservices** (separate auth, recommender and mood services): rejected. Operational cost with no benefit at this scale, and out of scope per the guidelines.
- **Flat single-file app**: rejected. It cannot be tested or reviewed in parts and would not show separation of concerns.

## Consequences
- Easy to run, test and deploy as one container.
- Module boundaries let us extract a service later if it is ever needed.
- Scale-out path: run multiple instances behind a load balancer. This would require moving rate-limit state from memory to MongoDB or Redis.
