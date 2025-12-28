from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP  # :contentReference[oaicite:5]{index=5}

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

mcp = FastMCP("Gmail")

def _service(credentials_path: str = "credentials.json", token_path: str = "token.json"):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

@mcp.tool()
def gmail_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search messages using Gmail search syntax."""
    svc = _service()
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return resp.get("messages", [])

@mcp.tool()
def gmail_get(message_id: str, format: str = "full") -> Dict[str, Any]:
    """Get one message (format: full|metadata|raw|minimal)."""
    svc = _service()
    return svc.users().messages().get(userId="me", id=message_id, format=format).execute()

@mcp.tool()
def gmail_mark_read(message_id: str) -> Dict[str, Any]:
    """Remove UNREAD label."""
    svc = _service()
    return svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()

@mcp.tool()
def gmail_send(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send email via Gmail API (raw must be base64url)."""
    svc = _service()

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    # Gmail expects base64url in "raw" :contentReference[oaicite:6]{index=6}
    return svc.users().messages().send(userId="me", body={"raw": raw}).execute()



if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
