from __future__ import annotations
from src.agents.CaseOrchestratorAgent.AgentState import AgentState, AuthSessionsState
from src.agents.CaseOrchestratorAgent.tools.mange_draft import approve_and_send_auth_request
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container





async def approve_and_send_auth_request_node(state: AgentState) -> AgentState:

    container = await get_container()

    case = state.get("Case") or {}

    human_review = state.get("human_review") or {}
    decision = human_review.get("decision") or {}

    reviewer_email = human_review.get("reviewer_email") or ""
    reviewer_name = human_review.get("reviewer_name") or ""
    review_notes = human_review.get("review_notes") or ""
    edited_customer_reply = human_review.get("edited_customer_reply") or ""

    support_from_email = human_review.get("support_from_email") or {}
    subject = human_review.get("subject") or {}

    case_id = case.get("case_uuid")
    if not case_id:
        return {"errors": state.get("errors", []) + [{"stage": "plan_actions_node", "error": "Missing case_uuid"}]}

    result = await approve_and_send_auth_request(
        container=container,
        case_uuid=case_id,
        reviewer_email=reviewer_email,
        reviewer_name=reviewer_name,
        support_from_email=support_from_email,
        subject=subject,
        review_notes=review_notes,
    )

    print("result of approve_and_send_auth_request", result)
    print("=" * 20)

    return state


