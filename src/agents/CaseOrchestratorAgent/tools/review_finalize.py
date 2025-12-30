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

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from src.logs.log import build_logger
from src.models.ActionsModel import ActionsModel
from src.models.CasesModel import CasesModel
from src.models.DraftsModel import DraftsModel
from src.models.MessagesModel import MessagesModel
from src.models.ReviewsModel import ReviewsModel
from src.email_servers.IMAPSMTP.imap_smtp_mcp_server import email_smtp_send
from src.models.db_schemes import Reviews, Messages

import logging


log = build_logger(level=logging.DEBUG)


ReviewDecision = Literal["approved", "rejected"]



async def finalize_case_after_review(
        container,
        case_id: UUID,
        decision: ReviewDecision,
        reviewer_name: str,
        reviewer_email: str = "system@local",
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

    draft = await drafts_model.get_draft_by_case_uuid(case_uuid=case_id)

    if draft is None:
        return {"ok": False, "error": "No draft found for this case."}


    final_reply_text = (edited_customer_reply or draft.customer_reply_draft or "").strip()
    if decision == "approved" and not final_reply_text:
        return {"ok": False, "error": "Approved but final reply text is empty."}

    print(f"final_reply_text is {final_reply_text}")
    print("=" * 20)

    # 2) Create review record

    review_omr = Reviews(
        case_id= case_id,
        draft_id=getattr(draft, "id", None),
        reviewer_email=reviewer_email,
        reviewer_name=reviewer_name,
        decision=decision,
        review_notes=review_notes,
        edited_customer_reply_draft= edited_customer_reply,
        created_at= datetime.now(timezone.utc),
        updated_at= datetime.now(timezone.utc),
    )

    review = await reviews_model.create_review(review=review_omr)

    print(f"review insert and is  {review}")
    print("=" * 20)

    if decision == "rejected":
        await cases_model.update_case_status_by_uuid(
            case_uuid=case_id,
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
            "case_uuid": str(case_id),
            "case_status": "failed",
            "review_id": str(getattr(review, "id", "")),
        }

        # 4) Approved: execute actions
        #    We will execute only actions with status "planned"
    actions = await actions_model.list_actions_by_case(case_id=case_id)

    print(f"actions got and is  {actions}")
    print("=" * 20)
    executed_action_ids: List[str] = []
    blocked_action_ids: List[str] = []

    for a in actions:
        if getattr(a, "action_status", None) != "planned":
            continue

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


    latest_inbound = await messages_model.get_latest_inbound_message(case_id=case_id)

    if latest_inbound is None:
        return {"ok": False, "error": "No inbound message found; cannot determine customer email."}

    to_email = latest_inbound.from_email  # customer email

    msg_form = Messages(
        case_id=case_id,
        direction="outbound",
        subject=subject if subject.startswith("Re:") else f"Re: {subject}",
        body=final_reply_text,
        from_email=support_from_email,
        to_email=to_email,
    )



    msg = await messages_model.create_message(message=msg_form)

    print(f"msg got and is  {msg} and to email is{msg.to_email}")
    print("=" * 20)

    # Here I would call the email API:
    res = email_smtp_send(to=to_email, subject=subject, body=final_reply_text)
    print("email send done and result:", res)
    print("=" * 20)

    # 6) Close the case
    await cases_model.update_case_status_by_uuid(
        case_uuid=case_id,
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
        "case_uuid": str(case_id),
        "case_status": "done",
        "review_id": str(getattr(review, "id", "")),
        "outbound_message_id": str(getattr(msg, "message_id", "")),
        "executed_action_ids": executed_action_ids,
        "blocked_action_ids": blocked_action_ids,
    }




