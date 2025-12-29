import re
import logging
from typing import Optional, Literal

from src.models.MessagesModel import MessagesModel
from src.models.db_schemes import Messages
from src.logs.log import build_logger

log = build_logger(level=logging.DEBUG)

Direction = Literal["inbound", "outbound"]

RE_PREFIX_RE = re.compile(r"^(re:|fw:|fwd:)\s*", re.IGNORECASE)

def normalize_subject_for_matching(subject: Optional[str]) -> str:
    """
    ONLY for matching / resolver logic.
    NOT store this into DB subject column.
    """
    if not subject:
        return ""
    s = subject.strip()
    s = RE_PREFIX_RE.sub("", s).strip()
    return s.lower()


async def message_writer(
    container,
    case_uuid,
    direction: Direction,
    subject: Optional[str],
    body: str,
    from_email: str,
    to_email: str,
) -> Messages:
    """
    Stores one email message (inbound/outbound) in the Messages table.
    - Stores RAW subject (not normalized).
    - body must be str.
    - direction must be inbound/outbound.
    """
    if direction not in ("inbound", "outbound"):
        raise ValueError(f"Invalid direction: {direction}")

    if body is None or not str(body).strip():
        raise ValueError("body is required and cannot be empty")

    subject_raw = subject.strip() if subject else None
    body_raw = str(body)

    message_model = await MessagesModel.create_instance(db_client=container.db_client)

    msg = Messages(
        case_id=case_uuid,
        direction=direction,
        subject=subject_raw,
        body=body_raw,
        from_email=from_email,
        to_email=to_email,
    )

    try:
        new_message = await message_model.create_message(message=msg)
    except Exception:
        log.exception("Message creation failed")
        raise

    return new_message