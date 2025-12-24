import asyncio
import re
import logging
from typing import Optional, Literal

from src.agents.CaseOrchestratorAgent.tools.case_resolver import case_resolver
from src.models.MessagesModel import MessagesModel
from src.models.db_schemes import Messages
from src.logs.log import build_logger
from src.utils.client_deps_container import DependencyContainer

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
        case_id=case_uuid,          # FK -> cases.case_uuid
        direction=direction,
        subject=subject_raw,        # store original subject
        body=body_raw,
        from_email=from_email,
    )

    try:
        new_message = await message_model.create_message(message=msg)
    except Exception:
        log.exception("Message creation failed")
        raise

    return new_message


# test
async def main():
    container = await DependencyContainer.create()

    emails = [
        {
            "from_email": "customer@example.com",
            "subject": "Meter reading",
            "body": "Hello, my meter reading is 12345.",
        },
        {
            "from_email": "customer@example.com",
            "subject": "Re: Meter reading [CASE: 39dd8ad7-13ee-4735-ab3e-635fcd0bd39b]",
            "body": "Here is the missing info you asked for.",
        },
        {
            "from_email": "customer@example.com",
            "subject": "Re: Meter reading",
            "body": "Another follow-up without token.",
        },
        {
            "from_email": "other@example.com",
            "subject": "Tariff question",
            "body": "Can you explain the dynamic tariff?",
        },
    ]

    for i, email in enumerate(emails, start=1):
        case = await case_resolver(
            container=container,
            from_email=email["from_email"],
            subject=email["subject"],
            body=email["body"],
        )

        msg = await message_writer(
            container=container,
            case_uuid=case.case_uuid,  # IMPORTANT: use case_uuid
            direction="inbound",
            subject=email["subject"],
            body=email["body"],
            from_email=email["from_email"],
        )

        print(f"[Email {i}] case_uuid={case.case_uuid}  message_id={msg.message_id}  subject={msg.subject}")


if __name__ == "__main__":
    asyncio.run(main())