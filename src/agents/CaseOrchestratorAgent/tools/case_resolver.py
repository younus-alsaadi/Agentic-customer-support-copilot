import re
from typing import Optional
from src.models.CasesModel import CasesModel
from src.models.db_schemes import Cases
import logging
from src.logs.log import build_logger
import asyncio

from src.utils.client_deps_container import DependencyContainer

log = build_logger(level=logging.DEBUG)

CASE_TOKEN_RE = re.compile(r"\[CASE:\s*([0-9a-fA-F-]{36})\]")

def _extract_case_uuid(subject: str | None, body: str | None) -> Optional[str]:
    text = f"{subject or ''}\n{body or ''}"
    m = CASE_TOKEN_RE.search(text)
    return m.group(1) if m else None


def _normalize_subject(subject: str | None) -> str:
    if not subject:
        return ""
    s = subject.strip()
    # remove common reply prefixes
    s = re.sub(r"^(re:|fw:|fwd:)\s*", "", s, flags=re.IGNORECASE).strip()
    return s.lower()

async def case_resolver(container,from_email, subject, body):
    """
    Resolve a case for a new inbound email:
    1) If email contains [CASE: uuid] token -> load that case.
    2) Else find latest open case for sender (and optionally similar subject).
    3) Else create a new case.
    """

    case_model = await CasesModel.create_instance(db_client=container.db_client)

    # 1) Strong link: CASE token
    case_uuid = _extract_case_uuid(subject, body)
    if case_uuid:
        case = await case_model.get_case_by_uuid(case_uuid=case_uuid)
        if case:
            return case
        log.warning(f"CASE token found but case not in DB: {case_uuid}")

    # 2) Heuristic link: open case by sender (+ subject similarity)
    normalized_subject = _normalize_subject(subject)

    # case = await case_model.find_open_case_by_sender(
    #     from_email=from_email,
    #     normalized_subject=normalized_subject,  # optional filter
    #     lookback_days=14,
    # )
    # if case:
    #     return case

    # 3) Create new case

    case_resource = Cases(
        case_status="new",
        case_status_meta={
            "customer_email": from_email,
            "subject_norm": normalized_subject,
            "auth_attempts":0
        },
        case_channel="Email",

    )
    new_case = await case_model.create_case(
        case= case_resource
    )

    if not new_case:
        log.error("Case creation failed")
        return None

    return new_case
