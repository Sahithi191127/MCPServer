# Railway Fix Guide

## Railway dashboard checklist

1. **Service:** `web` connected to GitHub repo `Sahithi191127/MCPServer`
2. **Settings → Build → Builder:** `Nixpacks` (NOT Dockerfile)
3. **Settings → Deploy → Custom Start Command:** leave **empty** (uses `railway.toml`)
4. **Variables** (each as separate variable — do NOT upload `.env` as one file):

| Variable | Value |
|---|---|
| `GOOGLE_TOKEN_JSON` | Full contents of `token.json` |
| `GOOGLE_CREDENTIALS_JSON` | Full contents of `credentials.json` |
| `API_KEY` | Random secret from local `.env` (**not** Groq API key) |
| `REQUIRE_APPROVAL` | `false` |

5. **Redeploy** the latest commit from Deployments tab.

## Verify deployment

```bash
curl https://web-production-c5ea8.up.railway.app/health
```

Success looks like:

```json
{
  "status": "ok",
  "service": "google-mcp-server",
  "runtime": "fastapi",
  "config": {
    "has_google_token": true,
    "has_google_credentials": true,
    "has_api_key": true,
    "require_approval": false
  }
}
```

If `has_google_token` or `has_google_credentials` is `false`, fix Railway variables.

## Test API

```bash
curl -X POST https://web-production-c5ea8.up.railway.app/create_email_draft \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_FROM_ENV" \
  -d '{"to":"you@example.com","subject":"Test","body":"Hello"}'
```

## If deploy keeps failing

- Remove any **Dockerfile** builder override in Railway UI
- Delete failed deployments and redeploy commit `e9eec64` pattern: Nixpacks + Procfile only
- Check **Build Logs** for Python install errors
