# Google MCP Server

A Python FastAPI server that integrates with **Google Docs** and **Gmail**. It exposes tool-style HTTP endpoints with a terminal approval step before any action runs.

## Features

| Endpoint | Description |
|---|---|
| `POST /append_to_doc` | Append text to a Google Doc |
| `POST /create_email_draft` | Create a Gmail draft |
| `GET /health` | Health check |

Before each action executes, the server prints the action name and payload to the terminal and prompts:

```
Approve? (y/n)
```

The request is only processed if you type `y`.

## Prerequisites

- Python 3.10+
- A Google Cloud project with **Google Docs API** and **Gmail API** enabled
- OAuth 2.0 Desktop credentials downloaded as `credentials.json`

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select an existing one).
3. Enable these APIs:
   - [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
4. Go to **APIs & Services → Credentials**.
5. Click **Create Credentials → OAuth client ID**.
6. Choose **Desktop app** as the application type.
7. Download the JSON file and save it as `credentials.json` in this directory.

## Installation

```bash
cd google-mcp-server
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Place your downloaded `credentials.json` in the project root (same folder as `server.py`).

## First-Time Authentication

On the first API call, a browser window opens for Google OAuth login. After you approve access, a `token.json` file is created automatically. Subsequent runs reuse this token (refreshing it when expired).

**Do not commit `credentials.json` or `token.json`.** They are listed in `.gitignore`.

## Running the Server

```bash
python server.py
```

The server starts at `http://localhost:8000`.

Interactive API docs: `http://localhost:8000/docs`

## Usage Examples

### Append to a Google Doc

Find the document ID in the URL:

```
https://docs.google.com/document/d/DOCUMENT_ID/edit
```

```bash
curl -X POST http://localhost:8000/append_to_doc \
  -H "Content-Type: application/json" \
  -d "{\"doc_id\": \"YOUR_DOC_ID\", \"content\": \"\\nHello from MCP server!\"}"
```

Switch to the terminal where the server is running and type `y` when prompted.

### Create a Gmail Draft

```bash
curl -X POST http://localhost:8000/create_email_draft \
  -H "Content-Type: application/json" \
  -d "{\"to\": \"recipient@example.com\", \"subject\": \"Test Draft\", \"body\": \"Hello from the MCP server.\"}"
```

Approve with `y` in the server terminal.

## Project Structure

```
google-mcp-server/
├── server.py          # FastAPI app with tool endpoints
├── auth.py            # Google OAuth authentication
├── docs_tool.py       # Google Docs tool (append content)
├── gmail_tool.py      # Gmail tool (create draft)
├── requirements.txt   # Dependencies
├── README.md          # This file
├── credentials.json   # (not committed) OAuth client secrets
└── token.json         # (not committed) Saved access token
```

## OAuth Scopes

- `https://www.googleapis.com/auth/documents` — read and edit Google Docs
- `https://www.googleapis.com/auth/gmail.compose` — create and manage Gmail drafts

## Troubleshooting

| Issue | Fix |
|---|---|
| `credentials.json not found` | Download OAuth credentials from Google Cloud Console |
| `403 Access Not Configured` | Enable Docs and Gmail APIs in your GCP project |
| `invalid_grant` on token refresh | Delete `token.json` and re-authenticate |
| Approval prompt not visible | Run the server in a foreground terminal, not as a background service |
