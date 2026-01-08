import re
from src.models.CasesModel import CasesModel
from src.models.db_schemes import Cases
import logging
from src.logs.log import build_logger
from src.utils.client_deps_container import DependencyContainer

log = build_logger(level=logging.DEBUG)

def _normalize_subject(subject: str | None) -> str:
    if not subject:
        return ""
    s = subject.strip()
    # remove common reply prefixes
    s = re.sub(r"^(re:|fw:|fwd:)\s*", "", s, flags=re.IGNORECASE).strip()
    return s.lower()

async def case_resolver(container:DependencyContainer,available_case_uuid:str,from_email:str, subject:str):
    """
    Resolve a case for a new inbound email:
    1) If email contains [CASE: uuid] token -> load that case.
    2) Else find latest open case for sender (and optionally similar subject).
    3) Else create a new case.
    """

    case_model = await CasesModel.create_instance(db_client=container.db_client)

    print(f"available_case_uuid is {available_case_uuid}")

    if available_case_uuid:
        print(f"look for case uuid in Db {available_case_uuid}")
        case = await case_model.get_case_by_uuid(case_uuid=available_case_uuid)
        if case:
            return case
        print(f"CASE token found but case not in DB: {available_case_uuid}")

    # 2) Heuristic link: open case by sender (+ subject similarity)
    normalized_subject = _normalize_subject(subject)

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
