from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.helpers.config import get_settings
from src.models.AuthSessionsModel import AuthSessionsModel
from src.models.CasesModel import CasesModel
from src.models.ContractsModel import ContractsModel
from src.utils.pii_safe import hash_field, mask_value

MAX_AUTH_ATTEMPTS = 3  # tune


def _is_empty(v: Any) -> bool:
    return v is None or v == "" or v == {} or v == "null"


def _safe_str(v: Any) -> Optional[str]:
    if _is_empty(v):
        return None
    return str(v).strip() or None


def _safe_hash(v: Optional[str], salt: str) -> Optional[str]:
    if not v:
        return None
    return hash_field(v, salt=salt)


def _safe_masked(val: Optional[str]) -> str:
    if not val:
        return "<missing>"
    return mask_value(val)

DEFAULT_REQUIRED_FIELDS = ["contract_number", "postal_code"]

REQUIRED_FIELDS_BY_INTENT = {
    "MeterReadingSubmission": ["contract_number", "postal_code"],
    "ChangeAddress": ["contract_number", "postal_code", "birthday"],
    "BankDetailsChange": ["contract_number", "postal_code", "birthday"],
}

def derive_required_fields(auth_intents: List[Dict[str, Any]]) -> List[str]:
    names = []
    for it in auth_intents:
        if isinstance(it, dict) and it.get("name"):
            names.append(it["name"])

    out = set()
    for n in names:
        out.update(REQUIRED_FIELDS_BY_INTENT.get(n, []))

    if not out:
        out.update(DEFAULT_REQUIRED_FIELDS)

    return list(out)


async def auth_session_manager(
    container,
    case_uuid: UUID,
    entities: Dict[str, Any],
    auth_intents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Auth gate for sensitive intents with debug prints.
    """
    settings = get_settings()
    salt = settings.PII_HASH_SALT

    auth_model = await AuthSessionsModel.create_instance(db_client=container.db_client)
    case_model = await CasesModel.create_instance(db_client=container.db_client)
    contracts_model = await ContractsModel.create_instance(db_client=container.db_client)

    print("\n" + "=" * 80)
    print("[AUTH] START")
    print("[AUTH] case_uuid:", case_uuid)
    print("[AUTH] entities (raw):", entities)
    print("=" * 20)

    # Load case + meta
    case = await case_model.get_case_by_uuid(case_uuid)
    meta = case.case_status_meta or {}
    attempts = int(meta.get("auth_attempts", 0))

    print("[AUTH][DB] case_status:", getattr(case, "case_status", None))
    print("[AUTH][DB] case_status_meta:", meta)
    print("[AUTH][DB] attempts:", attempts)
    print("=" * 20)

    # Load existing auth session ONCE
    existing = await auth_model.get_auth_session_by_case_id(case_uuid)

    if existing:
        print("[AUTH][DB] existing auth_session id:", getattr(existing, "id", None))
        print("[AUTH][DB] existing auth_status:", getattr(existing, "auth_status", None))
        print("[AUTH][DB] existing required_fields:", getattr(existing, "required_fields", None))
        print("[AUTH][DB] existing provided_fields:", getattr(existing, "provided_fields", None))
    else:
        print("[AUTH][DB] no existing auth_session for this case.")
    print("=" * 20)

    required_fields: List[str] = []

    if existing and getattr(existing, "required_fields", None):
        required_fields = list(existing.required_fields or [])
        print("[AUTH] required_fields loaded from AuthSessions:", required_fields)
    else:
        rf = meta.get("auth_required_fields")
        if isinstance(rf, list) and rf:
            required_fields = rf
            print("[AUTH] required_fields loaded from Cases.meta:", required_fields)
        else:
            required_fields = derive_required_fields(auth_intents)
            print("[AUTH] required_fields derived from auth_intents:", required_fields)

    print("[AUTH] required_fields final:", required_fields)
    print("=" * 20)

    # IMPORTANT: in this node, empty required_fields is an error, not "success"
    if not required_fields:
        return {
            "auth_status": "failed",
            "missing_fields": [],
            "attempts": attempts,
            "error_type": "policy_error",
            "provided_fields": (existing.provided_fields if existing and existing.provided_fields else {}),
            "auth_session_id": str(getattr(existing, "id", "")) if existing else None,
        }

    # Only store/consider identity fields (whitelist)
    IDENTITY_KEYS = {"contract_number", "postal_code", "birthday"}
    print("[AUTH] IDENTITY_KEYS whitelist:", IDENTITY_KEYS)
    print("=" * 20)

    # Build accumulated identity input:
    accumulated: Dict[str, Any] = {}
    if existing and existing.provided_fields:
        accumulated.update(existing.provided_fields)
        print("[AUTH] accumulated starts from existing.provided_fields")
        print("=" * 20)

    for k in IDENTITY_KEYS:
        if k in entities and not _is_empty(entities.get(k)):
            accumulated[k] = entities.get(k)
            print(f"[AUTH] accumulated updated from entities: {k} = {_safe_masked(_safe_str(entities.get(k)))}")
            print("=" * 20)

    print("[AUTH] accumulated identity input (raw mix):", accumulated)
    print("=" * 20)

    # Compute missing based on accumulated
    missing_fields: List[str] = []
    for f in required_fields:
        if _is_empty(accumulated.get(f)):
            missing_fields.append(f)

    print("[AUTH] missing_fields (based on accumulated):", missing_fields)
    print("=" * 20)

    auth_status: str = "missing"
    error_type: str = "none"
    verified_contract = None

    if missing_fields:
        auth_status = "missing"
        error_type = "missing"
        print("[AUTH] Not enough info -> cannot verify. Need:", missing_fields)
        print("=" * 20)
    else:
        print("[AUTH] Have all required fields -> verifying against Contracts...")
        print("=" * 20)

        contract_number = _safe_str(accumulated.get("contract_number"))
        postal_code = _safe_str(accumulated.get("postal_code")) if "postal_code" in required_fields else None
        birthday = _safe_str(accumulated.get("birthday")) if "birthday" in required_fields else None

        print("[AUTH] verify input (masked):")
        print("       contract_number:", _safe_masked(contract_number))
        print("       postal_code:", _safe_masked(postal_code))
        print("       birthday:", _safe_masked(birthday))
        print("=" * 20)

        contract_hash = _safe_hash(contract_number, salt)
        postal_hash = _safe_hash(postal_code, salt)
        birthday_hash = _safe_hash(birthday, salt) if "birthday" in required_fields else None

        print("[AUTH] verify input (hash present?):")
        print("       contract_hash:", "<yes>" if contract_hash else "<no>")
        print("       postal_hash:", "<yes>" if postal_hash else "<no>")
        print("       birthday_hash:", "<yes>" if birthday_hash else "<no>")
        print("=" * 20)

        verified_contract = await contracts_model.verify_identity(
            contract_number=contract_hash,
            postal_code=postal_hash,
            birthday=birthday_hash,  # Contracts must store same hashed form
        )

        if verified_contract:
            auth_status = "success"
            error_type = "none"
            print("[AUTH] ✅ Verification SUCCESS. verified_customer_id:", getattr(verified_contract, "customer_id", None))
            print("=" * 20)
        else:
            attempts += 1
            error_type = "mismatch"
            auth_status = "failed" if attempts >= MAX_AUTH_ATTEMPTS else "missing"
            print(f"[AUTH] ❌ Verification FAILED. attempts={attempts}, auth_status={auth_status}")
            print("=" * 20)

    # Store safe fields in AuthSessions: only identity info, hashed + masked
    safe_provided: Dict[str, Any] = {}

    cn = _safe_str(accumulated.get("contract_number"))
    if cn:
        safe_provided["contract_number"] = {"hash": _safe_hash(cn, salt), "masked": mask_value(cn)}

    pc = _safe_str(accumulated.get("postal_code"))
    if pc:
        safe_provided["postal_code"] = {"hash": _safe_hash(pc, salt), "masked": mask_value(pc)}

    bd = _safe_str(accumulated.get("birthday"))
    if bd:
        safe_provided["birthday"] = {"hash": _safe_hash(bd, salt), "masked": mask_value(bd)}

    print("[AUTH] safe_provided to store:", safe_provided)
    print("=" * 20)

    # Merge with existing safe fields (so we keep previously stored hashes)
    merged_fields: Dict[str, Any] = {}
    if existing and existing.provided_fields:
        merged_fields.update(existing.provided_fields)
        print("[AUTH] merged_fields starts from existing.provided_fields")
    merged_fields.update(safe_provided)

    if verified_contract:
        merged_fields["verified_customer_id"] = getattr(verified_contract, "customer_id", None)

    print("[AUTH] merged_fields final (stored in AuthSessions):", merged_fields)
    print("=" * 20)

    auth_row = await auth_model.upsert_auth_session_for_case(
        case_uuid=case_uuid,
        required_fields=required_fields,
        provided_fields=merged_fields,
        auth_status=auth_status,
    )
    print("[AUTH][DB] upsert_auth_session_for_case -> auth_session_id:", getattr(auth_row, "id", None))
    print("=" * 20)

    # Update case status + meta
    new_meta = dict(meta)
    new_meta["auth_required_fields"] = required_fields
    new_meta["auth_missing_fields"] = missing_fields
    new_meta["auth_attempts"] = attempts
    new_meta["auth_status"] = auth_status
    new_meta["auth_error_type"] = error_type
    new_meta["auth_session_id"] = str(getattr(auth_row, "id", ""))

    if auth_status == "missing":
        new_case_status = "waiting_auth"
        new_meta["auth_hint"] = (
            "Provided details do not match our records."
            if error_type == "mismatch"
            else "Missing required verification fields."
        )
    elif auth_status == "failed":
        new_case_status = "failed"
        new_meta["escalation"] = "manual_support_required"
    else:
        new_case_status = "new" if getattr(case, "case_status", None) == "waiting_auth" else getattr(case, "case_status", "new")

    await case_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status=new_case_status,
        status_meta=new_meta,
    )

    print("[AUTH][DB] case updated -> new_case_status:", new_case_status)
    print("[AUTH][DB] case_status_meta:", new_meta)
    print("[AUTH] auth_session_manager END")
    print("=" * 20 + "\n")

    return {
        "auth_status": auth_status,
        "auth_session": auth_row,
        "attempts": attempts,
        "error_type": error_type,
        "provided_fields": merged_fields,
        "auth_session_id": str(getattr(auth_row, "id", "")),
    }
