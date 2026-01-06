from typing import List, Dict, Any

DRAFT_TYPE_AUTH = "auth_request"

_FIELD_LABELS = {
    "contract_number": "your contract number",
    "postal_code": "your postal code",
    "birthday": "your date of birth",
    "full_name": "your full name",
    "address": "your address",
}

def pretty_field(f: str) -> str:
    return _FIELD_LABELS.get(f, f)

def build_auth_request_draft(case_id: str, missing_fields: List[str]) -> str:
    bullets = "\n".join([f"- {pretty_field(f)}" for f in missing_fields])
    return (
        "Moin,\n\n"
        f"Your case ID: {case_id}\n\n"
        "To process your request, we still need the following information to verify your identity:\n"
        f"{bullets}\n\n"
        "Please reply to this email. Also, always include your case ID in your reply or keep it in the email subject.\n\n"
        "Thank you and kind regards"
    )

def build_internal_summary(required_fields: List[str], missing_fields: List[str], provided_fields: Dict[str, Any]) -> str:
    required = ", ".join(required_fields) if required_fields else "—"
    missing = ", ".join(missing_fields) if missing_fields else "—"
    provided_keys = ", ".join(sorted(provided_fields.keys())) if provided_fields else "—"
    return (
        f"Auth request draft created.\n"
        f"Required: {required}\n"
        f"Missing: {missing}\n"
        f"Provided (keys): {provided_keys}\n"
        "Next step: when the customer responds, run extraction again and update AuthSessions."
    )

def compute_missing_fields(required_fields: List[str], provided_fields: Dict[str, Any]) -> List[str]:
    # provided_fields may store values like {"contract_number": {"hash": "...", "masked": "****"}}
    missing = []
    for f in required_fields:
        if f not in provided_fields or provided_fields.get(f) in (None, "", {}, "null"):
            missing.append(f)
    return missing
