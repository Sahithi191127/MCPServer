# Deployment Plan: Google MCP Server on Railway

This guide covers deploying the FastAPI Google Docs/Gmail server to [Railway](https://railway.app).

## Overview

| Item | Local dev | Railway |
|---|---|---|
| Process | `python server.py` | `uvicorn` bound to `$PORT` |
| OAuth login | Browser on your machine | **Done locally first** — token injected as a secret |
| Terminal `Approve? (y/n)` | Works in foreground terminal | **Does not work** — no interactive stdin |
| `credentials.json` / `token.json` | Files on disk | Railway **environment variables** |

Railway runs the app as a headless web service. Plan for two pre-deploy adaptations: **cloud-friendly auth** and **replacing terminal approval**.

---

## Phase 1 — Pre-deploy code changes

Complete these before pushing to Railway.

### 1.1 Use `$PORT` and a start command

Railway assigns a dynamic port. Add a **Procfile** (or set the start command in the Railway dashboard):

```
web: uvicorn server:app --host 0.0.0.0 --port $PORT
```

Alternatively, create `railway.toml`:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn server:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
```

### 1.2 Load Google credentials from environment variables

Railway’s filesystem is ephemeral. Do **not** rely on uploading `credentials.json` or `token.json` as repo files.

Update `auth.py` to:

1. Read `GOOGLE_TOKEN_JSON` (full contents of `token.json`) if set.
2. Fall back to `token.json` on disk for local dev.
3. Use `GOOGLE_CREDENTIALS_JSON` (full contents of `credentials.json`) when refreshing an expired token — only needed if the saved token includes a `refresh_token`.
4. Keep `run_local_server()` **only for local dev** when no token env var exists.

Example env-first logic:

```python
import json
import os

token_json = os.environ.get("GOOGLE_TOKEN_JSON")
if token_json:
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
elif TOKEN_FILE.exists():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
```

### 1.3 Replace terminal approval for production

`input("Approve? (y/n)")` will hang or fail on Railway.

Pick one approach:

| Option | How it works |
|---|---|
| **A. API key (recommended)** | Require `X-API-Key` header; set `API_KEY` in Railway secrets |
| **B. Env flag** | `REQUIRE_APPROVAL=false` skips the prompt in production |
| **C. Out-of-band approval** | Not suitable for Railway — requires a human at a terminal |

Recommended: **API key** plus logging every action and payload to Railway logs (audit trail without blocking).

```python
import os
from fastapi import Header, HTTPException

API_KEY = os.environ.get("API_KEY")

def verify_api_key(x_api_key: str = Header(...)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

Apply as a dependency on `/append_to_doc` and `/create_email_draft`.

---

## Phase 2 — Google Cloud preparation

### 2.1 APIs and OAuth client

1. Enable **Google Docs API** and **Gmail API** in Google Cloud Console.
2. OAuth client type can remain **Desktop app** if you only generate the token locally.
3. Add your Google account as a **test user** if the app is in *Testing* mode (OAuth consent screen).

### 2.2 Generate `token.json` locally (one time)

On your machine (not on Railway):

```powershell
cd google-mcp-server
.venv\Scripts\activate
python authenticate.py
```

Confirm `token.json` exists. Copy its **entire JSON string** — you will paste it into Railway as `GOOGLE_TOKEN_JSON`.

Also copy the full JSON from `credentials.json` for `GOOGLE_CREDENTIALS_JSON` (needed when the access token expires and must refresh).

> **Important:** Ensure the token response includes `"refresh_token"`. If it does not, delete `token.json`, revoke app access in [Google Account permissions](https://myaccount.google.com/permissions), and re-run `authenticate.py` with `prompt=consent` so Google issues a refresh token.

---

## Phase 3 — Railway project setup

### 3.1 Create the service

1. Sign in at [railway.app](https://railway.app).
2. **New Project → Deploy from GitHub repo** (recommended) or **Empty Project → Deploy from local CLI**.
3. Set the **root directory** to `google-mcp-server` if the repo contains other folders.
4. Railway detects Python via `requirements.txt` and installs dependencies automatically.

### 3.2 Environment variables

In **Project → Service → Variables**, add:

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_TOKEN_JSON` | Yes | Full JSON from local `token.json` (single line) |
| `GOOGLE_CREDENTIALS_JSON` | Yes | Full JSON from `credentials.json` (for token refresh) |
| `API_KEY` | Yes | Random secret for request authentication |
| `REQUIRE_APPROVAL` | No | Set to `false` on Railway if you keep the approval code path |

Generate a strong API key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Do **not** commit these values. Railway encrypts variables at rest.

### 3.3 Networking

1. Open **Settings → Networking → Generate Domain** to get a public URL (e.g. `https://google-mcp-server-production.up.railway.app`).
2. Use **HTTPS only** for all client calls.

---

## Phase 4 — Deploy

### Option A: GitHub (recommended)

1. Push `google-mcp-server` to a GitHub repository.
2. Connect the repo in Railway.
3. Railway builds and deploys on every push to the default branch.

### Option B: Railway CLI

```bash
npm i -g @railway/cli
railway login
cd google-mcp-server
railway init
railway up
railway variables set GOOGLE_TOKEN_JSON='...' GOOGLE_CREDENTIALS_JSON='...' API_KEY='...'
```

### Verify deployment

```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
# {"status":"ok"}

curl -X POST https://YOUR-RAILWAY-URL.up.railway.app/append_to_doc \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d "{\"doc_id\": \"YOUR_DOC_ID\", \"content\": \"\\nDeployed from Railway!\"}"
```

Check **Deployments → Logs** for errors and audit entries.

---

## Phase 5 — Security checklist

- [ ] `credentials.json`, `token.json`, and `.env` are in `.gitignore` (already configured).
- [ ] All secrets live in Railway variables, not in the repository.
- [ ] `API_KEY` is required on all mutating endpoints.
- [ ] Google OAuth app is not published publicly unless you complete Google verification.
- [ ] Railway service is not shared with untrusted collaborators without scoped access.
- [ ] Rotate `API_KEY` and re-issue `token.json` if either is exposed.

---

## Phase 6 — Operations

### Token refresh

Access tokens expire (~1 hour). With a valid `refresh_token` and `GOOGLE_CREDENTIALS_JSON` set, `google-auth` refreshes automatically.

If refresh fails (`invalid_grant`):

1. Re-run `python authenticate.py` locally.
2. Update `GOOGLE_TOKEN_JSON` in Railway variables.
3. Redeploy (or restart the service).

### Monitoring

- Use Railway **Metrics** (CPU, memory, requests).
- `/health` is the health-check endpoint for Railway and uptime monitors.
- Watch logs for Google API quota or 403 errors.

### Scaling

This workload is I/O-bound (Google API calls). A single Railway instance is sufficient for light use. Enable horizontal scaling only if request volume grows.

---

## Known limitations on Railway

| Limitation | Mitigation |
|---|---|
| No browser OAuth at runtime | Generate token locally; store in `GOOGLE_TOKEN_JSON` |
| No terminal approval | API key or `REQUIRE_APPROVAL=false` |
| Ephemeral disk | Never depend on writing `token.json` at runtime without syncing back to env vars |
| Cold starts | First request after idle may be slower; use `/health` keep-alive if needed |

---

## Suggested file additions (summary)

```
google-mcp-server/
├── Procfile              # web: uvicorn server:app --host 0.0.0.0 --port $PORT
├── railway.toml          # optional — start command + health check
├── deploymentplan.md     # this document
├── auth.py               # update — env-based credentials
└── server.py             # update — API key auth, no stdin on Railway
```

---

## Rollback plan

1. In Railway **Deployments**, select the last successful deployment → **Redeploy**.
2. If OAuth broke, restore the previous `GOOGLE_TOKEN_JSON` variable value.
3. For local-only fallback, run `python server.py` on your machine with existing `token.json`.

---

## Timeline estimate

| Step | Time |
|---|---|
| Code changes (auth + API key) | 30–60 min |
| Local OAuth + token export | 10 min |
| Railway project + variables | 15 min |
| First deploy + smoke test | 15 min |
| **Total** | **~1–2 hours** |

---

## References

- [Railway Docs — Deploy a Python app](https://docs.railway.app/guides/flask)
- [Railway — Environment variables](https://docs.railway.app/guides/variables)
- [Google OAuth 2.0 for installed apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google Docs API — batchUpdate](https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate)
- [Gmail API — drafts.create](https://developers.google.com/gmail/api/reference/rest/v1/users.drafts/create)
