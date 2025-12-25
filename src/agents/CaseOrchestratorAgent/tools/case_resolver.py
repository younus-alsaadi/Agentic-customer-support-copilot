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

    # 1) First email -> creates new case
    case1 = await case_resolver(container, emails[0]["from_email"], emails[0]["subject"], emails[0]["body"])
    print("Email 1 -> case_uuid:", case1.case_uuid)

    # 2) Second email -> same case via token
    emails[1]["subject"] = emails[1]["subject"].format(CASE_UUID=str(case1.case_uuid))
    case2 = await case_resolver(container, emails[1]["from_email"], emails[1]["subject"], emails[1]["body"])
    print("Email 2 -> case_uuid:", case2.case_uuid, "(should be same as email 1)")

    # 3) Third email -> same case via heuristic (same sender + open case + same normalized subject)
    case3 = await case_resolver(container, emails[2]["from_email"], emails[2]["subject"], emails[2]["body"])
    print("Email 3 -> case_uuid:", case3.case_uuid, "(should be same as email 1)")

    # 4) Fourth email -> new sender -> new case
    case4 = await case_resolver(container, emails[3]["from_email"], emails[3]["subject"], emails[3]["body"])
    print("Email 4 -> case_uuid:", case4.case_uuid, "(should be different)")



if __name__ == "__main__":
    asyncio.run(main())