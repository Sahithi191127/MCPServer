#!/usr/bin/env python3
"""Generate token.json with refresh_token for Railway GOOGLE_TOKEN_JSON."""

from __future__ import annotations

import json
import sys

from auth import TOKEN_FILE, _run_local_oauth_flow


def main() -> int:
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print(f"Removed existing {TOKEN_FILE.name}")

    print("Opening browser for Google OAuth (Docs + Gmail compose scopes)...")
    print("If no refresh_token is returned, revoke this app at:")
    print("https://myaccount.google.com/permissions then re-run this script.")
    print()

    creds = _run_local_oauth_flow()
    token_json = creds.to_json()
    TOKEN_FILE.write_text(token_json, encoding="utf-8")

    data = json.loads(token_json)
    if not data.get("refresh_token"):
        print("ERROR: token.json has no refresh_token — revoke app access and re-run.")
        return 1

    print(f"Wrote {TOKEN_FILE}")
    print("refresh_token: present")
    print()
    print("Next: copy the ENTIRE contents of token.json into Railway variable")
    print("GOOGLE_TOKEN_JSON, then redeploy MCPServer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
