"""FastAPI server exposing Google Docs and Gmail tools."""

import os
import sys

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

from docs_tool import append_to_doc
from gmail_tool import create_email_draft

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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
