"""One-time OAuth login — creates token.json after browser approval."""

from auth import TOKEN_FILE, get_credentials

if __name__ == "__main__":
    print("Starting Google OAuth login...")
    print("A browser window should open. Sign in and approve access.")
    print("If the browser does not open, copy the URL printed below into your browser.")
    print("Scopes: Google Docs (edit) + Gmail (compose drafts)\n")

    creds = get_credentials()

    print(f"\nSuccess! Saved token to: {TOKEN_FILE}")
    print("\nFor Railway, set these environment variables:")
    print("  GOOGLE_TOKEN_JSON     = contents of token.json")
    print("  GOOGLE_CREDENTIALS_JSON = contents of credentials.json")
    print("  API_KEY               = a random secret (see deploymentplan.md)")
    print("  REQUIRE_APPROVAL      = false")
    print("\nYou can now run: python server.py")
