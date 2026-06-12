"""Gmail tool — create email drafts."""

import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from auth import get_credentials


def create_email_draft(to: str, subject: str, body: str) -> dict:
    """Create a Gmail draft with the given recipient, subject, and body."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )

    return draft
