# ADR-0006: Store derived mood, never raw mood text

- **Status:** Accepted · **Date:** 2026-10-20

## Context
Free-text mood can contain sensitive personal content. Session history (Phase 3) needs mood over time, but not the user's words.

## Decision
Free text is processed in memory and discarded. Only chips and the derived `MoodProfile` (numbers + labels) are stored, with a 90-day TTL. Mood text is excluded from logs by the redaction filter. The wellbeing check records only `support_shown: true/false`.

## Alternatives considered
- **Store the text for model improvement:** rejected. It violates purpose limitation and would need explicit opt-in consent plus a secure storage design.
- **Store the text encrypted:** rejected. It still collects more than needed.

## Consequences
- Lower privacy risk and a simpler deletion story.
- We cannot retrain the model on real user text (accepted).
- A user's history shows "Calm, slightly low (valence 0.42)", not what they typed.
