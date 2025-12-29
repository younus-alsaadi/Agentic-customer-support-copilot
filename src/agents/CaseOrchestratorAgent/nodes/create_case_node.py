from src.agents.CaseOrchestratorAgent.AgentState import AgentState, CaseState
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container
from src.agents.CaseOrchestratorAgent.tools.case_resolver import case_resolver
from src.models.db_schemes import Cases

def _case_orm_to_state(case: Cases) -> CaseState:
    return {
        "case_id": str(case.case_id),
        "case_uuid": str(case.case_uuid),
        "case_status": case.case_status,
        "case_status_meta": case.case_status_meta or {},  # dict, not ""
        "case_channel": case.case_channel,
        "case_created_at": case.case_created_at.isoformat() if case.case_created_at else "",
        "case_updated_at": case.case_updated_at.isoformat() if case.case_updated_at else "",
    }

async def create_case_node(state: AgentState)-> AgentState:

    container = await get_container()

    msg = state.get("Message", {})
    from_email = msg.get("from_email")
    subject = msg.get("subject")
    body = msg.get("body")

    if not (from_email and not (body is None)):
        # fail fast: message missing required fields
        state["errors"] = state.get("errors", [])
        state["errors"].append({"stage": "create_case_node", "error": "Missing from_email or body"})
        # optionally set a failure status if you already have a case
        return state

    case_orm = await case_resolver(container, from_email, subject, body)

    if not case_orm:
        state["errors"] = state.get("errors", [])
        state["errors"].append({"stage": "create_case_node", "error": "case_resolver returned None"})
        return state

    case_state = _case_orm_to_state(case_orm)
    state["Case"] = case_state

    state["Message"]["case_id"] = case_state["case_uuid"]

    return state