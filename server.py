"""FastAPI server exposing Google Docs and Gmail tools."""

import config  # noqa: F401 — load .env before reading os.environ
import json
import os
import sys

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from docs_tool import append_to_doc
from gmail_tool import create_email_draft
from groq_tool import chat, run_assistant

app = FastAPI(title="Google MCP Server", version="1.0.0")

API_KEY = os.environ.get("API_KEY")
REQUIRE_APPROVAL = os.environ.get("REQUIRE_APPROVAL", "true").lower() == "true"


class AppendToDocRequest(BaseModel):
    doc_id: str
    content: str


class CreateEmailDraftRequest(BaseModel):
    to: str
    subject: str
    body: str


class ChatRequest(BaseModel):
    message: str
    model: str | None = None


class AssistantRequest(BaseModel):
    message: str
    model: str | None = None


def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """Require API key when API_KEY env var is set (Railway production)."""
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def authorize_action(action_name: str, payload: dict) -> None:
    """Log the action; prompt in local dev or skip when API_KEY + REQUIRE_APPROVAL=false."""
    print(f"\n--- Action: {action_name} ---")
    print(f"Payload: {payload}")

    if API_KEY and not REQUIRE_APPROVAL:
        return

    if not REQUIRE_APPROVAL:
        return

    if not sys.stdin.isatty():
        raise HTTPException(
            status_code=403,
            detail=(
                "Terminal approval is unavailable in this environment. "
                "Set REQUIRE_APPROVAL=false and provide a valid X-API-Key header."
            ),
        )

    response = input("Approve? (y/n): ").strip().lower()
    if response != "y":
        raise HTTPException(status_code=403, detail="Action not approved by user")


@app.post("/append_to_doc")
def append_to_doc_endpoint(
    request: AppendToDocRequest,
    _: None = Depends(verify_api_key),
):
    authorize_action("append_to_doc", request.model_dump())

    try:
        result = append_to_doc(request.doc_id, request.content)
        return {"status": "success", "result": result}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})


@app.post("/create_email_draft")
def create_email_draft_endpoint(
    request: CreateEmailDraftRequest,
    _: None = Depends(verify_api_key),
):
    authorize_action("create_email_draft", request.model_dump())

    try:
        result = create_email_draft(request.to, request.subject, request.body)
        return {"status": "success", "result": result}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})


@app.post("/chat")
def chat_endpoint(
    request: ChatRequest,
    _: None = Depends(verify_api_key),
):
    try:
        reply = chat(request.message, model=request.model or "llama-3.3-70b-versatile")
        return {"status": "success", "reply": reply}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})


@app.post("/assistant")
def assistant_endpoint(
    request: AssistantRequest,
    _: None = Depends(verify_api_key),
):
    authorize_action("assistant", request.model_dump())

    try:
        result = run_assistant(
            request.message, model=request.model or "llama-3.3-70b-versatile"
        )
        return {"status": "success", **result}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})


@app.get("/")
def root():
    return {
        "service": "google-mcp-server",
        "runtime": "fastapi",
        "docs": "/docs",
        "endpoints": [
            "/append_to_doc",
            "/create_email_draft",
            "/chat",
            "/assistant",
            "/health",
        ],
    }


@app.get("/health")
def health():
    has_refresh_token = False
    google_token_usable = False
    google_token_error: str | None = None

    raw_token = os.environ.get("GOOGLE_TOKEN_JSON", "").strip()
    if raw_token:
        try:
            token_data = json.loads(raw_token)
            if isinstance(token_data, str):
                token_data = json.loads(token_data)
            if isinstance(token_data, dict):
                has_refresh_token = bool(token_data.get("refresh_token"))
        except json.JSONDecodeError:
            google_token_error = "GOOGLE_TOKEN_JSON is not valid JSON"

    if not google_token_error:
        try:
            from auth import get_credentials

            creds = get_credentials()
            google_token_usable = bool(creds.valid)
        except Exception as exc:
            google_token_error = str(exc)

    return {
        "status": "ok",
        "service": "google-mcp-server",
        "runtime": "fastapi",
        "config": {
            "has_google_token": bool(raw_token),
            "has_google_credentials": bool(os.environ.get("GOOGLE_CREDENTIALS_JSON")),
            "has_refresh_token": has_refresh_token,
            "google_token_usable": google_token_usable,
            "google_token_error": google_token_error,
            "has_api_key": bool(API_KEY),
            "has_groq_api_key": bool(os.environ.get("GROQ_API_KEY")),
            "require_approval": REQUIRE_APPROVAL,
        },
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
