# ADR-0004: PyMongo async driver instead of Motor

- **Status:** Accepted · **Date:** 2026-10-20

## Context
The synopsis specifies MongoDB with an async Python backend. Motor was the usual async driver, but MongoDB has deprecated it in favour of PyMongo's native asyncio API (`AsyncMongoClient`).

## Decision
Use `pymongo` (≥ 4.13) with `AsyncMongoClient`.

## Alternatives considered
- **Motor:** deprecated; only critical fixes.
- **An ODM (Beanie, ODMantic):** rejected. It adds abstraction and a dependency on top of Pydantic models we already have; plain repositories are easier to understand and to test.

## Consequences
- Supported long-term and fully async.
- `mongomock` does not support the async API, so repository tests run against a real MongoDB (Docker locally, a service container in CI). Unit tests for services use in-memory fake repositories.

## Update (2026-11-18)
Docker and CI service containers are not set up yet (DevOps track). Until they are, repository tests are opt-in: `pytest --db` runs them against the developer's own Atlas cluster in a throwaway `muse_test_<random>` database, and plain `pytest` (which CI runs) skips them. Moving them to a MongoDB service container in CI is part of the DevOps track.
