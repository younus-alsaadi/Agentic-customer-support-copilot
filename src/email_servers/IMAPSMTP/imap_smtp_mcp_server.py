from __future__ import annotations
import ssl
import imaplib
import smtplib
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from src.helpers.config import get_settings

from langsmith import trace
from typing import Optional, Dict, Any



mcp = FastMCP("IMAP_SMTP_Mail")


def _parse_bool(x, default: bool = False) -> bool:
    if x is None:
        return default
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

def _cfg() -> Dict[str, Any]:

    env_settings = get_settings()

    print(env_settings.EMAIL_PASS)

    return {
        "user": env_settings.EMAIL_USER,
        "password": env_settings.EMAIL_PASS,
        "imap_host": env_settings.IMAP_HOST,
        "imap_port": env_settings.IMAP_PORT,
        "smtp_host": env_settings.SMTP_HOST,
        "smtp_port": env_settings.SMTP_PORT,
        "smtp_starttls":  _parse_bool(env_settings.SMTP_STARTTLS, default=False),
        "smtp_ssl": _parse_bool(env_settings.SMTP_SSL, default=False),
    }

def _imap_login() -> imaplib.IMAP4_SSL:
    cfg = _cfg()
    if not cfg["imap_host"]:
        raise RuntimeError("IMAP_HOST is not set")
    imap = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
    imap.login(cfg["user"], cfg["password"])
    return imap

def _smtp_login() -> smtplib.SMTP:
    cfg = _cfg()
    if not cfg["smtp_host"]:
        raise RuntimeError("SMTP_HOST is not set")

    if cfg["smtp_ssl"]:
        smtp = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], context=ssl.create_default_context())
    else:
        smtp = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
        smtp.ehlo()
        if cfg["smtp_starttls"]:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()

    smtp.login(cfg["user"], cfg["password"])
    return smtp

def _decode_header_value(v: Optional[str]) -> str:
    return v or ""

def _parse_email(raw_bytes: bytes) -> Dict[str, Any]:
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    def get_text_body(m) -> str:
        if m.is_multipart():
            for part in m.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", "")).lower()
                if ctype == "text/plain" and "attachment" not in disp:
                    return part.get_content()
            # fallback: try html
            for part in m.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", "")).lower()
                if ctype == "text/html" and "attachment" not in disp:
                    return part.get_content()
            return ""
        return m.get_content()

    return {
        "subject": _decode_header_value(msg.get("Subject")),
        "from": _decode_header_value(msg.get("From")),
        "to": _decode_header_value(msg.get("To")),
        "date": _decode_header_value(msg.get("Date")),
        "message_id": _decode_header_value(msg.get("Message-ID")),
        "body": get_text_body(msg),
    }

mcp.tool()
def email_imap_search(mailbox: str = "INBOX", criteria: str = "UNSEEN", limit: int = 10) -> List[str]:
    """
    Search IMAP mailbox. Returns message UIDs (strings).
    criteria examples: 'UNSEEN', 'ALL', 'FROM "foo@bar.com"', 'SUBJECT "invoice"'
    """
    imap = _imap_login()
    try:
        imap.select(mailbox)
        # Use UID search so ids stay stable
        typ, data = imap.uid("search", None, criteria)
        if typ != "OK":
            raise RuntimeError(f"IMAP search failed: {typ} {data}")

        uids = data[0].decode().split() if data and data[0] else []
        # newest last usually; take last N
        return uids[-limit:]
    finally:
        try:
            imap.logout()
        except Exception:
            pass

mcp.tool()
def email_imap_get(uid: str, mailbox: str = "INBOX") -> Dict[str, Any]:
    """Fetch one email by UID and return headers + body text."""
    with trace(
        name="email_imap_get",
        run_type="tool",
        tags=["tool:mcp", "channel:email", "protocol:imap"],
        metadata={"mailbox": mailbox, "mcp_server": "IMAP_SMTP_Mail"},
    ) as run:
        imap = _imap_login()
        try:
            imap.select(mailbox)
            typ, data = imap.uid("fetch", uid, "(RFC822)")
            if typ != "OK" or not data or not data[0]:
                raise RuntimeError(f"IMAP fetch failed: {typ} {data}")
            raw = data[0][1]
            out = {"uid": uid, **_parse_email(raw)}
            run.end(outputs={"result": out})
            return out
        finally:
            try:
                imap.logout()
            except Exception:
                pass

mcp.tool()
def email_imap_mark_seen(uid: str, mailbox: str = "INBOX") -> Dict[str, Any]:
    """Mark message as seen/read."""

    imap = _imap_login()
    try:
        imap.select(mailbox)
        typ, data = imap.uid("store", uid, "+FLAGS", r"(\Seen)")
        if typ != "OK":
            raise RuntimeError(f"IMAP store failed: {typ} {data}")
        return {"uid": uid, "status": "seen"}
    finally:
        try:
            imap.logout()
        except Exception:
            pass




@mcp.tool()
def email_smtp_send(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email via SMTP (LangSmith traced MCP tool)."""

    with trace(
        name="mcp.email_smtp_send",
        run_type="tool",
        tags=[
            "tool:mcp",
            "protocol:smtp",
            "channel:email",
        ],
        metadata={
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "mcp_server": "IMAP_SMTP_Mail",
        },
    ) as run:

        cfg = _cfg()

        msg = EmailMessage()
        msg["From"] = cfg["user"]
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        msg.set_content(body)

        recipients = [to]
        if cc:
            recipients += [x.strip() for x in cc.split(",") if x.strip()]
        if bcc:
            recipients += [x.strip() for x in bcc.split(",") if x.strip()]

        smtp = _smtp_login()
        try:
            smtp.send_message(
                msg,
                from_addr=cfg["user"],
                to_addrs=recipients,
            )

            result = {
                "status": "sent",
                "to": recipients,
            }

            # this makes outputs visible in LangSmith UI
            run.end(outputs=result)
            return result

        except Exception as e:
            # errors show clearly in LangSmith
            run.end(error=str(e))
            raise

        finally:
            try:
                smtp.quit()
            except Exception:
                pass




if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
