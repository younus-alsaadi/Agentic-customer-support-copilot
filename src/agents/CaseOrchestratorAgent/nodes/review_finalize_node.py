from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.review_finalize import finalize_case_after_review
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container


import asyncio
from typing import Any, Dict


async def _ainput(prompt: str) -> str:
    # async-safe input (so your async graph doesn't block the event loop badly)
    return await asyncio.to_thread(input, prompt)


async def human_review_node(state: AgentState) -> AgentState:
    human_review: Dict[str, Any] = state.get("human_review") or {}

    # If already provided (tests / UI), do not ask again
    required_keys = [
        "decision",
        "reviewer_email",
        "support_from_email",
        "subject",
        "edited_customer_reply",
        "review_notes",
    ]
    if all(k in human_review for k in required_keys):
        return state

    # Defaults (safe fallbacks)
    msg = state.get("Message") or {}
    default_subject = msg.get("subject") or "Re: Your request"
    default_support_from = msg.get("to_email") or "younis.eng.software@gmail.com"

    # Ask human
    decision = (await _ainput("Decision [approved/rejected/needs_changes] (default=approved): ")).strip() or "approved"
    reviewer_email = (await _ainput("Reviewer email: ")).strip() or "alsaadi.younus@gmail.com"
    reviewer_name = (await _ainput("Reviewer name: ")).strip() or "Younus AL-Saadi"
    support_from_email = (await _ainput(f"Support from email (default={default_support_from}): ")).strip() or default_support_from
    subject = (await _ainput(f"Subject (default={default_subject}): ")).strip() or default_subject

    edited_customer_reply = (await _ainput(
        "Edited customer reply (leave empty = keep generated draft): "
    )).strip()

    review_notes = (await _ainput("Review notes (optional): ")).strip()

    # Store in state (this is what you asked for)
    state["human_review"] = {
        "decision": decision,
        "reviewer_email": reviewer_email,
        "reviewer_name": reviewer_name,
        "support_from_email": support_from_email,
        "subject": subject,
        "edited_customer_reply": edited_customer_reply,
        "review_notes": review_notes,
    }

    print("="*20)
    print("state of human_review is :", state["human_review"])
    print("="*20)

    return state


async def review_finalize_node(state:AgentState)->AgentState:

    container = await get_container()

    case = state.get("Case") or {}

    human_review = state.get("human_review") or {}
    decision= human_review.get("decision") or {}


    reviewer_email = human_review.get("reviewer_email") or ""
    reviewer_name = human_review.get("reviewer_name") or ""
    review_notes = human_review.get("review_notes") or ""
    edited_customer_reply = human_review.get("edited_customer_reply") or ""

    support_from_email = human_review.get("support_from_email") or {}
    subject = human_review.get("subject") or {}

    case_id = case.get("case_uuid")
    if not case_id:
        return {"errors": state.get("errors", []) + [{"stage": "plan_actions_node", "error": "Missing case_uuid"}]}

    final_result = await finalize_case_after_review(
        container=container,
        case_id=case_id,
        decision=decision,
        reviewer_email=reviewer_email,
        reviewer_name = reviewer_name,
        support_from_email=support_from_email,
        subject=subject,
        edited_customer_reply=edited_customer_reply,
        review_notes=review_notes,


    )

    print("final result:", final_result)
    print("=" * 20)

    return state







