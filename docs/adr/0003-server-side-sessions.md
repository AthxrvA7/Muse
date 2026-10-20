# ADR-0003: Server-side sessions and encrypted Spotify tokens

- **Status:** Accepted · **Date:** 2026-10-20

## Context
After OAuth, Muse holds Spotify tokens that can modify a user's account. The browser needs a way to stay logged in to Muse.

## Decision
- Spotify tokens are stored **only in the backend**, encrypted with Fernet (AES-128-CBC + HMAC) using a key from the environment, on top of Atlas disk encryption.
- The browser gets an **opaque random session ID** (`secrets.token_urlsafe(32)`) in an `httpOnly`, `Secure`, `SameSite=Lax` cookie. The database stores only its SHA-256 hash, with a 7-day idle TTL. The ID is rotated on every login.

## Alternatives considered
- **JWT in the cookie:** rejected. It cannot be revoked before expiry, so logout and account deletion would not be immediate.
- **Tokens in browser storage, or PKCE in the frontend:** rejected. It exposes Spotify tokens to XSS, and the synopsis requires tokens never reach the frontend.

## Consequences
- Logout and deletion are instant.
- One database read per request (negligible at this scale).
- Key rotation needs a key list (`MultiFernet`), as documented in SECURITY_PRIVACY §7.
