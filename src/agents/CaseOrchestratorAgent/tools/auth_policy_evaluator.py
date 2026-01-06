
import logging

from src.logs.log import build_logger
log = build_logger(level=logging.DEBUG)
from typing import Dict, Any, List, Tuple

SENSITIVE_INTENTS = {
    "MeterReadingSubmission",
    "MeterReadingCorrection",
    "PersonalDataChange",
    "ContractIssue",
}

# DEFAULT_REQUIRED_FIELDS = ["contract_number", "postal_code"]

def separate_auth_intents(
    intents: List[Dict[str, Any]] | None
) -> dict:

    auth_intents: List[Dict[str, Any]] = []
    non_auth_intents: List[Dict[str, Any]] = []

    for intent in intents or []:
        if not isinstance(intent, dict):
            continue

        name = (intent.get("name") or "Other").strip()
        model_requires_auth = bool(intent.get("requires_auth", False))
        rule_requires_auth = name in SENSITIVE_INTENTS

        final_requires_auth = model_requires_auth or rule_requires_auth

        item = {
            "name": name,
            "confidence": intent.get("confidence"),
            "requires_auth": final_requires_auth,
            "reason": intent.get("reason"),
        }

        if final_requires_auth:
            auth_intents.append(item)
        else:
            non_auth_intents.append(item)

    return {
        "auth_intents": auth_intents,
        "non_auth_intents": non_auth_intents,
    }
