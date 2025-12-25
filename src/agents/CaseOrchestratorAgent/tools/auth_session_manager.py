import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from src.helpers.config import get_settings
from src.models.AuthSessionsModel import AuthSessionsModel
from src.models.CasesModel import CasesModel
from src.models.ContractsModel import ContractsModel
from src.utils.pii_safe import hash_field, mask_value

MAX_AUTH_ATTEMPTS = 3  # tune

#Step C — Decide if authentication is needed



async def auth_session_manager(
    container,
    case_uuid: UUID,
    required_fields: List[str],
    entities: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Returns:
      {
        "auth_status": "missing"|"success"|"failed",
        "missing_fields": [...],
        "attempts": int,
        "error_type": "none"|"missing"|"mismatch",
        "provided_fields": {...},   # masked/hashed storage
      }
    """

    auth_model = await AuthSessionsModel.create_instance(db_client=container.db_client)
    case_model = await CasesModel.create_instance(db_client=container.db_client)
    contracts_model = await ContractsModel.create_instance(db_client=container.db_client)

    # -----------------------------
    # STEP A) Decide what we need
    # -----------------------------
    # required_fields comes from auth_policy_evaluator(intents)
    # Example: ["contract_number","postal_code"] for sensitive requests
    print("\n[STEP A] required_fields:", required_fields)

    # -----------------------------------------
    # STEP B) Read what customer provided (LLM)
    # -----------------------------------------
    print("[STEP B] provided_raw (from entities):", entities)

    # --------------------------
    # Load case + attempts (DB)
    # --------------------------
    case = await case_model.get_case_by_uuid(case_uuid)
    meta = case.case_status_meta or {}
    attempts = int(meta.get("auth_attempts", 0))
    print("[DB] current attempts:", attempts)

    # -------------------------------------------------
    # STEP C) Check missing fields (based on required)
    # -------------------------------------------------
    missing_fields: List[str] = []
    for f in required_fields:
        if entities.get(f) in (None, "", {}, "null"):
            missing_fields.append(f)

    print("[STEP C] missing_fields:", missing_fields)

    # default
    auth_status = "success" if not required_fields else "missing"
    error_type = "none"

    if required_fields and missing_fields:
        # Not enough info -> ask customer
        auth_status = "missing"
        error_type = "missing"
        print("[STEP C] Result: MISSING info -> ask customer for:", missing_fields)

    # ---------------------------------------------------------
    # STEP D) Verify against Contracts table (correct vs wrong)
    # ---------------------------------------------------------
    # Only possible if nothing missing (for required fields)
    verified_contract = None
    if required_fields and not missing_fields:
        contract_number = str(entities.get("contract_number"))
        postal_code = str(entities.get("postal_code")) if "postal_code" in required_fields else None

        print("[STEP D] verifying with Contracts table...")
        verified_contract = await contracts_model.verify_identity(
            contract_number=contract_number,
            postal_code=postal_code,
            # later you can include:
            # birthday=provided_raw.get("birthday"),
            # full_name=provided_raw.get("full_name"),
        )

        if verified_contract:
            auth_status = "success"
            error_type = "none"
            print("[STEP D] Result: CORRECT info -> auth success")
        else:
            # Wrong data -> count attempt
            attempts += 1
            error_type = "mismatch"
            auth_status = "failed" if attempts >= MAX_AUTH_ATTEMPTS else "missing"
            print(f"[STEP D] Result: WRONG info -> attempts={attempts} -> auth_status={auth_status}")

    # ---------------------------------------------------------
    # STEP E) Store masked/hashed values in AuthSessions (DB)
    # ---------------------------------------------------------
    # We store safe values, never raw.
    salt_hash = get_settings().PII_HASH_SALT
    stored_fields: Dict[str, Any] = {}

    for k, v in entities.items():
        if k in ("contract_number", "postal_code"):
            stored_fields[k] = {
                "hash": hash_field(str(v), salt=salt_hash),
                "masked": mask_value(str(v)),
            }
        else:
            stored_fields[k] = v

    # Merge with previous auth session provided_fields (so partial info accumulates)
    existing = await auth_model.get_auth_session_by_case_uuid(case_uuid)
    merged_fields: Dict[str, Any] = {}
    if existing and existing.provided_fields:
        merged_fields.update(existing.provided_fields)
    merged_fields.update(stored_fields)

    # Optionally store which contract matched (not PII)
    if verified_contract:
        merged_fields["verified_customer_id"] = verified_contract.customer_id

    print("[STEP E] stored_fields (safe):", stored_fields)

    auth_row = await auth_model.upsert_auth_session_for_case(
        case_uuid=case_uuid,
        required_fields=required_fields,
        provided_fields=merged_fields,
        auth_status=auth_status,
    )

    # ---------------------------------------------------------
    # STEP F) Update Cases status/meta for next workflow step
    # ---------------------------------------------------------
    new_meta = dict(meta)
    new_meta["auth_required_fields"] = required_fields
    new_meta["auth_missing_fields"] = missing_fields
    new_meta["auth_attempts"] = attempts
    new_meta["auth_status"] = auth_status
    new_meta["auth_error_type"] = error_type

    if auth_status == "missing":
        new_case_status = "waiting_auth"
        # helpful hint for your draft tool
        if error_type == "mismatch":
            new_meta["auth_hint"] = "Provided details do not match our records."
        else:
            new_meta["auth_hint"] = "Missing required verification fields."

    elif auth_status == "failed":
        new_case_status = "failed"
        new_meta["escalation"] = "manual_support_required"

    else:
        # success -> you can move to next node (actions/drafting)
        # keep current unless you prefer to set a special status
        new_case_status = case.case_status if case.case_status not in ("new", "waiting_auth") else "new"

    await case_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status=new_case_status,
        status_meta=new_meta,
    )

    print("[STEP F] case_status set to:", new_case_status)
    print("[STEP F] case_status_meta:", new_meta)

    return {
        "auth_status": auth_status,
        "missing_fields": missing_fields,
        "attempts": attempts,
        "error_type": error_type,
        "provided_fields": merged_fields,
        "auth_session_id": str(auth_row.id),
    }