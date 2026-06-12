"""Google OAuth 2.0 authentication for Docs and Gmail APIs."""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def _client_config_from_env() -> dict | None:
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not raw:
        return None
    return json.loads(raw)


def _enrich_token_info(token_info: dict) -> dict:
    """Merge client_id/secret from credentials env when missing from token."""
    client_config = _client_config_from_env()
    if not client_config:
        return token_info

    installed = client_config.get("installed") or client_config.get("web", {})
    enriched = dict(token_info)
    enriched.setdefault("client_id", installed.get("client_id"))
    enriched.setdefault("client_secret", installed.get("client_secret"))
    enriched.setdefault(
        "token_uri", installed.get("token_uri", "https://oauth2.googleapis.com/token")
    )
    return enriched


def _load_creds_from_env() -> Credentials | None:
    raw = os.environ.get("GOOGLE_TOKEN_JSON")
    if not raw:
        return None
    token_info = _enrich_token_info(json.loads(raw))
    return Credentials.from_authorized_user_info(token_info, SCOPES)


def _load_creds_from_file() -> Credentials | None:
    if not TOKEN_FILE.exists():
        return None
    return Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)


def _save_token(creds: Credentials) -> None:
    if os.environ.get("GOOGLE_TOKEN_JSON"):
        print(
            "Token refreshed in memory. Update GOOGLE_TOKEN_JSON in Railway to persist."
        )
        return
    TOKEN_FILE.write_text(creds.to_json())


def _run_local_oauth_flow() -> Credentials:
    client_config = _client_config_from_env()
    if client_config:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    elif CREDENTIALS_FILE.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    else:
        raise FileNotFoundError(
            "No Google credentials found. Add credentials.json or set "
            "GOOGLE_CREDENTIALS_JSON."
        )

    return flow.run_local_server(port=0, prompt="consent")


def get_credentials() -> Credentials:
    """Load saved credentials, refresh if needed, or run local OAuth flow."""
    creds = _load_creds_from_env() or _load_creds_from_file()

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.environ.get("GOOGLE_TOKEN_JSON") or os.environ.get("RAILWAY_ENVIRONMENT"):
            raise RuntimeError(
                "Google credentials are missing or invalid. Re-run authenticate.py "
                "locally and update GOOGLE_TOKEN_JSON in Railway."
            )
        else:
            creds = _run_local_oauth_flow()

        _save_token(creds)

    return creds
