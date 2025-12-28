from datetime import datetime
from typing import List, Dict, Any, Optional

from typing import List, Dict, Any
from uuid import UUID

from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from src.models.MessagesModel import MessagesModel
from src.models.ReviewsModel import ReviewsModel
from src.models.db_schemes import Messages

#Step — Ask customer for missing auth data (loop)

def _build_auth_request_draft(missing_fields: List[str]) -> str:
    bullets = "\n".join([f"- {f}" for f in missing_fields])
    return (
        "Hello,\n"
        "to process your request, we still need the following information to verify your identity:\n"
        f"{bullets}\n\n"
        "Please reply to this email with the missing information.\n\n"
        "Thank you and kind regards"
    )

def _build_internal_summary(missing_fields: List[str], provided_fields: Dict[str, Any]) -> str:
    provided_keys = ", ".join(sorted(provided_fields.keys())) if provided_fields else "—"
    missing = ", ".join(missing_fields) if missing_fields else "—"
    return (
        f"Auth missing. Required: {missing}. Provided: {provided_keys}. "
        "Next step: when the customer responds, run extraction again and update AuthSessions."
    )

async def create_or_update_draft(container, case_id, auth_session) -> Dict[str, Any]:

    required = auth_session.required_fields or []
    provided = auth_session.provided_fields or {}
    missing_fields = auth_session.missing_fields or []

    customer_reply = _build_auth_request_draft(missing_fields)
    internal_summary = _build_internal_summary(missing_fields, provided)

    # Upsert draft

    draft_model = await DraftsModel.create_instance(db_client=container.db_client)
    case_model = await CasesModel.create_instance(db_client=container.db_client)

    draft= await draft_model.update_case_status_by_uuid(
        case_uuid=case_id,
        payload={
            "customer_reply_draft": customer_reply,
            "internal_summary": internal_summary,
            "actions_suggested": [],
            "updated_at": datetime.utcnow(),
        }
    )

    # Update case status -> pending_review
    await case_model.update_case_status_by_uuid(
        case_id=case_id,
        new_status="pending_review",
        case_status_meta={
                "stage": "auth_request_draft",
                "missing_fields": missing_fields,
                "auth_session_id": str(auth_session.id),
        }
    )

    return {
        "missing_fields": missing_fields,
        "draft_id": str(getattr(draft, "id", "")) if draft else None,
    }


async def approve_and_send_auth_request(container,
    case_id: UUID,
    reviewer_email: str,
    support_from_email: str,
    subject: str = "Verification needed",
    review_notes: Optional[str] = None # for Backeend msg { "decision": "approved", "review_notes": "Edited for tone." }
) -> Dict[str, Any]:

    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    reviews_model = await ReviewsModel.create_instance(db_client=container.db_client)
    messages_model = await MessagesModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)


    # 1) Load the current draft
    draft = await drafts_model.get_draft_by_case_id(case_id=case_id)
    if draft is None:
        return {"ok": False, "error": "No draft found for this case."}

    body_text = draft.customer_reply_draft
    if not body_text or not body_text.strip():
        return {"ok": False, "error": "Draft is empty."}

        # 2) Create review record (approved)
    review = await reviews_model.create_review(
        payload={
            "case_id": case_id,
            "draft_id": getattr(draft, "id", None),
            "reviewer": reviewer_email,
            "decision": "approved",
            "review_notes": review_notes,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    # 3) Create outbound message
    msg = await messages_model.create_message(message=Messages(
        case_id=case_id,
        direction="outbound",
        subject="",
        body="",
        from_email="",
    ))

    # Call send_email_api(to=customer_email, subject, body)


    # 4) Update case status -> waiting_customer
    await cases_model.update_case_status_by_uuid(
        case_uuid=case_id,
        new_status="waiting_customer",
        status_meta={
            "stage": "auth_request_sent",
            "review_id": str(getattr(review, "id", "")),
            "outbound_message_id": str(getattr(msg, "message_id", "")),
            "draft_id": str(getattr(draft, "id", "")),
        },
    )

    return {
        "ok": True,
        "case_id": str(case_id),
        "review_id": str(getattr(review, "id", "")),
        "outbound_message_id": str(getattr(msg, "message_id", "")),
        "new_case_status": "waiting_customer",
    }


