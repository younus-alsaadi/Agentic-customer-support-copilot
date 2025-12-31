from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.email_servers.IMAPSMTP.imap_smtp_mcp_server import email_smtp_send
from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from src.models.MessagesModel import MessagesModel
from src.models.ReviewsModel import ReviewsModel

from src.models.db_schemes import Messages, Reviews as ReviewsORM


DRAFT_TYPE_AUTH = "auth_request"


_FIELD_LABELS = {
    "contract_number": "your contract number",
    "postal_code": "your postal code",
    "birthday": "your date of birth",
    "full_name": "your full name",
    "address": "your address",
}

def _pretty_field(f: str) -> str:
    return _FIELD_LABELS.get(f, f)

def _build_auth_request_draft(case_id: str, missing_fields: List[str]) -> str:
    bullets = "\n".join([f"- {_pretty_field(f)}" for f in missing_fields])
    return (
        "Hello,\n\n"
        f"Your case ID: {case_id}\n\n"
        "To process your request, we still need the following information to verify your identity:\n"
        f"{bullets}\n\n"
        "Please reply to this email. Also, always include your case ID in your reply or keep it in the email subject.\n\n"
        "Thank you and kind regards"
    )

def _build_internal_summary(required_fields: List[str], missing_fields: List[str], provided_fields: Dict[str, Any]) -> str:
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

def _compute_missing_fields(required_fields: List[str], provided_fields: Dict[str, Any]) -> List[str]:
    # provided_fields may store values like {"contract_number": {"hash": "...", "masked": "****"}}
    missing = []
    for f in required_fields:
        if f not in provided_fields or provided_fields.get(f) in (None, "", {}, "null"):
            missing.append(f)
    return missing


# -------------------------
# Step D — Create/Update Draft + set case to pending_review
# -------------------------

async def create_or_update_auth_request_draft(
    container,
    case_uuid: UUID,
    auth_session_id,
    required_fields,
    provided_fields,
) -> Dict[str, Any]:

    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)

    missing_fields = _compute_missing_fields(required_fields, provided_fields)

    print(f"auth_session_id is {auth_session_id}")
    print(f"required_fields is {required_fields}")
    print(f"provided_fields is {provided_fields}")
    print(f"missing_fields is {missing_fields}")

    if not missing_fields:
        return {"ok": False, "error": "No missing fields. Auth request draft not needed."}

    customer_reply = _build_auth_request_draft(case_id=case_uuid, missing_fields=missing_fields)
    internal_summary = _build_internal_summary(required_fields, missing_fields, provided_fields)

    draft = await drafts_model.upsert_draft_for_case_and_type(
        case_id=case_uuid,
        draft_type=DRAFT_TYPE_AUTH,
        customer_reply_draft=customer_reply,
        internal_summary=internal_summary,
        actions_suggested=[],
    )

    case = await cases_model.get_case_by_uuid(case_uuid)
    meta = dict(case.case_status_meta or {})

    meta.update({
        "stage": "auth_request_draft",
        "missing_fields": missing_fields,
        "required_fields": required_fields,
        "auth_session_id": str(auth_session_id),
        "draft_type": DRAFT_TYPE_AUTH,
        "draft_id": str(getattr(draft, "id", "")) if draft else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    await cases_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status="pending_review",
        status_meta=meta,
    )

    return {
        "ok": True,
        "case_uuid": str(case_uuid),
        "draft_id": str(getattr(draft, "id", "")) if draft else None,
        "missing_fields": missing_fields,
        "new_case_status": "pending_review",
    }

# -------------------------
# Step D — Review approve + send auth request email + set waiting_customer
# -------------------------
async def approve_and_send_auth_request(
    container,
    case_uuid: UUID,
    reviewer_email: str,
    reviewer_name: str,
    support_from_email: str,
    subject: str = "Verification needed",
    review_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Writes:
      - Reviews (approved)
      - Messages (outbound auth request)
      - Cases -> waiting_customer
    Sends:
      - SMTP email to customer (to_email derived from latest inbound message)
    """
    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    reviews_model = await ReviewsModel.create_instance(db_client=container.db_client)
    messages_model = await MessagesModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)


    draft = await drafts_model.get_draft_by_case_and_type(case_id=case_uuid, draft_type=DRAFT_TYPE_AUTH)


    if draft is None:
        return {"ok": False, "error": f"No draft found for this case (type={DRAFT_TYPE_AUTH})."}

    body_text = (getattr(draft, "customer_reply_draft", "") or "").strip()
    if not body_text:
        return {"ok": False, "error": "Draft is empty."}

    # 2) Derive customer to_email from latest inbound message
    latest_inbound = await messages_model.get_latest_inbound_message(case_id=case_uuid)
    if latest_inbound is None:
        return {"ok": False, "error": "No inbound message found; cannot determine customer email."}

    to_email = getattr(latest_inbound, "from_email", None)
    if not to_email:
        return {"ok": False, "error": "Inbound message missing from_email; cannot determine customer email."}

    now_utc = datetime.now(timezone.utc)

    review_obj = ReviewsORM(
        case_id=case_uuid,
        draft_id=getattr(draft, "id", None),
        reviewer_email=reviewer_email,  # must be str
        reviewer_name=reviewer_name,  # must be str (don’t pass {})

        decision="approved",
        review_notes=review_notes,

        edited_customer_reply_draft=None,
        edited_internal_summary=None,

        created_at=now_utc,
        updated_at=now_utc,
    )

    # 3) Create review record (approved)
    review = await reviews_model.create_review(review_obj)

    # 4) Create outbound message row (auth request email)
    msg_obj = Messages(
        case_id=case_uuid,     # adjust if your column name differs
        direction="outbound",
        subject=subject,
        body=body_text,
        from_email=support_from_email,
        to_email=to_email,
        received_at=now_utc,
    )
    msg = await messages_model.create_message(message=msg_obj)


    # 5) Send email via SMTP
    # If your email_smtp_send supports from_email, pass it. Otherwise keep minimal.
    try:
        final_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        res = email_smtp_send(to=to_email, subject=final_subject, body=body_text)
        print("email send done and result:", res)
    except Exception as e:
        # If sending fails, do NOT claim waiting_customer
        # Keep case in pending_review (or mark failed) depending on your policy
        case = await cases_model.get_case_by_uuid(case_uuid)
        meta = dict((case.case_status_meta or {}))
        meta.update({"stage": "auth_request_send_failed", "error": str(e)})

        await cases_model.update_case_status_by_uuid(
            case_uuid=case_uuid,
            new_status="pending_review",
            status_meta=meta,
        )
        return {"ok": False, "error": f"SMTP send failed: {e}"}

    # 6) Update case status -> waiting_customer
    case = await cases_model.get_case_by_uuid(case_uuid)
    meta = dict((case.case_status_meta or {}))
    meta.update({
        "stage": "auth_request_sent",
        "review_id": str(getattr(review, "id", "")),
        "outbound_message_id": str(getattr(msg, "message_id", "")),
        "draft_id": str(getattr(draft, "id", "")),
        "draft_type": DRAFT_TYPE_AUTH,
        "to_email": to_email,
    })

    await cases_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status="waiting_customer",
        status_meta=meta,
    )

    return {
        "ok": True,
        "case_uuid": str(case_uuid),
        "review_id": str(getattr(review, "id", "")),
        "outbound_message_id": str(getattr(msg, "message_id", "")),
        "new_case_status": "waiting_customer",
        "to_email": to_email,
    }
