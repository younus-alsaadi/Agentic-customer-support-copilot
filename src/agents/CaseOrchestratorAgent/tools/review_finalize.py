"""
Step F — Human review

DB writes
13. Reviews

Agent approves/rejects/edits

Then

If approved:

execute actions → update Actions.action_status="executed" and fill result

send final outbound email → new Messages row

Cases.case_status="done"

If rejected:

Cases.case_status="failed" (or stay in "pending_review")
"""


from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from src.logs.log import build_logger
from src.models.ActionsModel import ActionsModel
from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from src.models.MessagesModel import MessagesModel
from src.models.ReviewsModel import ReviewsModel

log = build_logger(level=None)

ReviewDecision = Literal["approved", "rejected"]

async def finalize_case_after_review(
        container,
        case_uuid: UUID,
        decision: ReviewDecision,
        reviewer_email: str = "system@local",  # temporary until build real agent/user
        support_from_email: str = "support@local",
        subject: str = "Update on your request",
        edited_customer_reply: Optional[str] = None, # text coming from the human reviewer.
        review_notes: Optional[str] = None,

)-> Dict[str, Any]:
    """
    Step F:
    - Insert a Reviews row (approved/rejected)
    - If approved:
        - execute Actions (mark executed + store result)
        - send final outbound email (Messages row)
        - set case_status="done"
    - If rejected:
        - set case_status="failed" (or keep pending_review)
    """
    reviews_model = await ReviewsModel.create_instance(db_client=container.db_client)
    drafts_model = await DraftsModel.create_instance(db_client=container.db_client)
    actions_model = await ActionsModel.create_instance(db_client=container.db_client)
    messages_model = await MessagesModel.create_instance(db_client=container.db_client)
    cases_model = await CasesModel.create_instance(db_client=container.db_client)

    draft = await drafts_model.get_draft_by_case_uuid(case_uuid=case_uuid)

    if draft is None:
        return {"ok": False, "error": "No draft found for this case."}


    final_reply_text = (edited_customer_reply or draft.customer_reply_draft or "").strip()
    if decision == "approved" and not final_reply_text:
        return {"ok": False, "error": "Approved but final reply text is empty."}

    # 2) Create review record
    review = await reviews_model.create_review(payload={
        "case_id": case_uuid,
        "draft_id": getattr(draft, "id", None),
        "reviewer": reviewer_email,
        "decision": decision,
        "review_notes": review_notes,
        "edited_customer_reply": edited_customer_reply,  # optional field if you add it
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    if decision == "rejected":
        await cases_model.update_case_status_by_uuid(
            case_uuid=case_uuid,
            new_status="failed",  # or keep "pending_review"
            status_meta={
                "stage": "review_rejected",
                "review_id": str(getattr(review, "id", "")),
                "notes": review_notes,
            },
        )
        return {
            "ok": True,
            "decision": "rejected",
            "case_uuid": str(case_uuid),
            "case_status": "failed",
            "review_id": str(getattr(review, "id", "")),
        }

        # 4) Approved: execute actions
        #    We will execute only actions with status "planned"
    actions = await actions_model.get_actions_by_case_id(case_id=case_uuid)
    executed_action_ids: List[str] = []
    blocked_action_ids: List[str] = []

    for a in actions:
        if getattr(a, "action_status", None) != "planned":
            continue

        # ---- Placeholder execution (replace later with real integrations) ----
        # For now: mark success with a dummy payload
        execution_result = {
            "success": True,
            "executed_at": datetime.utcnow().isoformat(),
            "note": "Dummy execution (replace with real action runner).",
        }

        try:
            updated = await actions_model.update_action_status(
                action_id=a.id,
                new_status="executed",
                result=execution_result,
            )
            executed_action_ids.append(str(getattr(updated, "id", a.id)))
        except Exception as e:
            # If execution fails, block it (don’t lie to customer)
            await actions_model.update_action_status(
                action_id=a.id,
                new_status="blocked",
                result={"success": False, "error": str(e)},
            )
            blocked_action_ids.append(str(a.id))

    # 5) Create outbound message (final reply)
    # NOTE: i should pass the customer "to_email" into your email API.
    # the Messages table currently doesn't store 'to_email'; i can add it to meta or case meta later.
    msg = await messages_model.create_message(payload={
        "message_case_id": case_uuid,
        "direction": "outbound",
        "subject": subject,
        "body": final_reply_text,
        "from_email": support_from_email,
        "received_at": datetime.utcnow(),
    })

    # Here i would call your email API:
    # await email_client.send(to=customer_email, subject=subject, body=final_reply_text)

    # 6) Close the case
    await cases_model.update_case_status_by_uuid(
        case_uuid=case_uuid,
        new_status="done",
        status_meta={
            "stage": "case_done",
            "review_id": str(getattr(review, "id", "")),
            "outbound_message_id": str(getattr(msg, "message_id", "")),
            "executed_action_ids": executed_action_ids,
            "blocked_action_ids": blocked_action_ids,
        },
    )

    return {
        "ok": True,
        "decision": "approved",
        "case_uuid": str(case_uuid),
        "case_status": "done",
        "review_id": str(getattr(review, "id", "")),
        "outbound_message_id": str(getattr(msg, "message_id", "")),
        "executed_action_ids": executed_action_ids,
        "blocked_action_ids": blocked_action_ids,
    }




