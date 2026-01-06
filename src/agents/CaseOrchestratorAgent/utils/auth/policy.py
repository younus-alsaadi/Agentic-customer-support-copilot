from __future__ import annotations

from typing import Any, Dict, List, Set

MAX_AUTH_ATTEMPTS = 3

DEFAULT_REQUIRED_FIELDS: List[str] = ["contract_number", "postal_code"]

REQUIRED_FIELDS_BY_INTENT: Dict[str, List[str]] = {
    "MeterReadingSubmission": ["contract_number", "postal_code"],
    "ChangeAddress": ["contract_number", "postal_code", "birthday"],
    "BankDetailsChange": ["contract_number", "postal_code", "birthday"],
}

IDENTITY_KEYS: Set[str] = {"contract_number", "postal_code", "birthday"}


def derive_required_fields(auth_intents: List[Dict[str, Any]]) -> List[str]:
    names: List[str] = [
        it.get("name") for it in auth_intents if isinstance(it, dict) and it.get("name")
    ]

    required: set[str] = set()
    for n in names:
        required.update(REQUIRED_FIELDS_BY_INTENT.get(n, []))

    if not required:
        required.update(DEFAULT_REQUIRED_FIELDS)

    # stable order helps testing + logs
    ordered = [f for f in DEFAULT_REQUIRED_FIELDS if f in required]
    for f in ["birthday"]:
        if f in required:
            ordered.append(f)
    # add any future fields
    for f in required:
        if f not in ordered:
            ordered.append(f)

    return ordered
