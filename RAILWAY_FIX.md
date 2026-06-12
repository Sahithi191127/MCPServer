# Railway Fix Guide

## Problem detected

If your URL returns `Cannot GET /` or NestJS-style errors, the domain is on the **wrong Railway service**.

Your FastAPI service URL: `https://web-production-c5ea8.up.railway.app`

| Signal | NestJS (wrong) | FastAPI (correct) |
|---|---|---|
| `GET /` | `Cannot GET /` | `{"service":"google-mcp-server",...}` |
| `GET /docs` | 404 | 200 (Swagger UI) |
| `POST /append_to_doc` | 404 | 401 without API key |

## Fix in Railway dashboard

1. Open [Railway project](https://railway.com/project/aa0258c6-cd3d-4a53-b9ec-1966b970ea8d).
2. Check how many **services** exist in the project.
3. **Delete** or **remove the public domain** from any Node/NestJS/MCP template service.
4. Select the service connected to **GitHub → Sahithi191127/MCPServer**.
5. Confirm settings:
   - **Builder:** Dockerfile (or Nixpacks)
   - **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
6. **Settings → Networking → Generate Domain** on the **Python/GitHub** service only.
7. Verify env vars on that same service:
   - `GOOGLE_TOKEN_JSON`
   - `GOOGLE_CREDENTIALS_JSON`
   - `API_KEY`
   - `REQUIRE_APPROVAL=false`
8. Redeploy.

## Verify correct deployment

```bash
curl https://YOUR-URL/
# Must include: "service": "google-mcp-server"

curl https://YOUR-URL/health
# {"status":"ok","service":"google-mcp-server","runtime":"fastapi"}

curl -X POST https://YOUR-URL/append_to_doc \
  -H "Content-Type: application/json" \
  -d '{"doc_id":"x","content":"y"}'
# Must return 401 (not 404) if API_KEY is set
```

If you still see `Cannot GET /`, the domain is still pointed at the wrong service.

## Healthcheck failure fix

If deploy fails at **Network > Healthcheck**:

1. Ensure **Builder** is **Dockerfile** (not a Node template).
2. Do **not** set a custom start command in the Railway UI — `Dockerfile` CMD handles it.
3. Set these env vars on the **same service** (missing vars cause API 500, not healthcheck fail):
   - `GOOGLE_TOKEN_JSON` — raw JSON from `token.json` (one line, no extra quotes)
   - `GOOGLE_CREDENTIALS_JSON` — raw JSON from `credentials.json`
   - `API_KEY` — from your local `.env`
   - `REQUIRE_APPROVAL=false`
4. Redeploy after saving variables.

Verify:
```bash
curl https://web-production-c5ea8.up.railway.app/health
# {"status":"ok","service":"google-mcp-server","runtime":"fastapi"}
```
