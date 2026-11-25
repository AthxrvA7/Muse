# Deployment runbook (Render + MongoDB Atlas)

Muse runs as one Render **web service** built from `main`: the build compiles the React website (`frontend/`) and installs the backend, which serves the site at `/app/` and the API at `/api/v1` ([ADR-0007](adr/0007-render-and-atlas-deployment.md)). The configuration is in [`render.yaml`](../render.yaml); secrets are entered in Render's dashboard, never committed.

| | Local | Deployed |
|---|---|---|
| URL | `http://127.0.0.1:8000` | `https://<service>.onrender.com` |
| Settings | `.env` | Render → service → **Environment** |
| Database | Atlas cluster (or none) | Atlas cluster, database `muse` |
| Spotify redirect URI | `http://127.0.0.1:8000/api/v1/auth/callback` | `https://<service>.onrender.com/api/v1/auth/callback` |

## First deployment (about 15 minutes)

1. **Atlas → Security → Network Access → Add IP Address → Allow access from anywhere (`0.0.0.0/0`).** Render's free tier has no fixed IP address, so the cluster can't allow-list it. The database still requires the user's password, which only Render and your `.env` hold.
2. **Render:** sign in at https://render.com with GitHub → **New → Blueprint** → choose the `muse` repository. Render reads `render.yaml` and asks for each secret:
   - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`: from the Spotify dashboard
   - `MONGODB_URI`: the same connection string as in `.env`
   - `TOKEN_ENCRYPTION_KEY`: a **new** key for production (`python -c "from app.core.crypto import generate_key; print(generate_key())"`), so a leaked local key can't read production tokens
   - `SPOTIFY_REDIRECT_URI`: `https://muse-api.onrender.com/api/v1/auth/callback` (if Render gives the service a different URL, update it in step 4)
3. Click **Apply**. The first build takes a few minutes. When it is live, open `https://<service>.onrender.com/ready`; it should show `"database": "ok"`.
4. **Spotify dashboard → your app → Settings → Redirect URIs:** add `https://<service>.onrender.com/api/v1/auth/callback` (keep the `127.0.0.1` one for local work). If the URL differs from what you entered in step 2, fix `SPOTIFY_REDIRECT_URI` in Render → **Environment** (Render redeploys by itself).
5. Check the deployed app: open `/app/` (the website) and click **Connect Spotify**, then curate and save a playlist. `/docs` is the API documentation.

## Every later deployment

Merging a pull request into `main` deploys it: Render rebuilds and switches over only after `/health` answers, so a broken build never replaces the running version. CI runs lint and tests on the same pull request before it can be merged.

## Rollback

Render → service → **Events** → pick the last good deploy → **Rollback**. Then fix the problem on a branch and merge as usual. A rollback does not change the database; Muse's indexes are created idempotently at startup, so older versions still start.

## Checks during a demo

- Free services **sleep after 15 minutes without traffic**; the first request then takes about a minute. Open `/health` a couple of minutes before presenting.
- `/health` = the process is running. `/ready` = it can also reach MongoDB.
- Logs: Render → service → **Logs**. Every line is JSON with a `request_id`; responses carry the same ID in `X-Request-ID`, so one request can be traced end to end. Tokens, passwords and mood text are never logged.

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `/ready` shows `"database": "unavailable"` | Atlas Network Access doesn't allow Render | Step 1 |
| Spotify says `INVALID_CLIENT: Invalid redirect URI` | Redirect URI in Render and Spotify differ | Make them identical (step 4) |
| Login works but `/me` says 401 | Opened the site on a different host than the redirect URI | Use the exact `onrender.com` URL |
| `403` mentioning **Users Management** | Spotify account not on the app's Development Mode list | Add it in the Spotify dashboard (max 5) |
| Build fails | Dependency or code error | Read the build log in **Events**; CI should have caught it on the PR |
| A secret leaked | Screenshot, commit or log | Rotate it at the source (Spotify, Atlas, new Fernet key), update Render; with a new Fernet key users log in again |
