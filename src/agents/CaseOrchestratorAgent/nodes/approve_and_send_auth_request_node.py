from __future__ import annotations
from src.agents.CaseOrchestratorAgent.AgentState import AgentState, AuthSessionsState
from src.agents.CaseOrchestratorAgent.tools.mange_draft import approve_and_send_auth_request
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container





async def approve_and_send_auth_request_node(state: AgentState) -> AgentState:

    container = await get_container()

    case = state.get("Case") or {}


    decision = "approved"

    reviewer_email = "test@younus-alsaadi.de"
    reviewer_name ="Younus AL-Saadi"
    review_notes = ""

    support_from_email = "test@younus-alsaadi.de"
    subject = "auth_request"

    case_id = case.get("case_uuid")
    if not case_id:
        return {"errors": state.get("errors", []) + [{"stage": "plan_actions_node", "error": "Missing case_uuid"}]}



    if decision != "approved":
        return {
            "auth_request_send_result": {
                "ok": False,
                "skipped": True,
                "reason": f"decision={decision}",
                "review_notes": review_notes,
            }
        }

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

    return {"auth_request_send_result": result, "auth_done": True}


