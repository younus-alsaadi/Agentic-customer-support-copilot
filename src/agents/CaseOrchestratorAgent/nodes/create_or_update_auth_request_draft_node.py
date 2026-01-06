from __future__ import annotations
from src.agents.CaseOrchestratorAgent.AgentState import AgentState, AuthSessionsState
from src.agents.CaseOrchestratorAgent.tools.mange_draft import create_or_update_auth_request_draft
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container
from src.models.db_schemes import AuthSessions as AuthSessionsORM


def _auth_sessions_orm_to_state(row: AuthSessionsORM) -> AuthSessionsState:
    return {
        "id": str(getattr(row, "id", "")),
        "case_id": str(getattr(row, "case_id", "")),
        "required_fields": getattr(row, "required_fields", None),
        "provided_fields": getattr(row, "provided_fields", None),
        "auth_status": getattr(row, "auth_status", "missing"),
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


async def create_or_update_auth_request_draft_node(state: AgentState) -> AgentState:
    container = await get_container()

    case = state.get("Case") or {}
    case_uuid = case.get("case_uuid")
    if not case_uuid:
        # mark error and stop cleanly
        state["errors"] = (state.get("errors") or []) + ["Missing case_uuid in state['Case']"]
        case["case_status"] = "failed"
        return state

    # one-to-one state key
    auth_session = state.get("auth_sessions")
    required_fields=auth_session.get("required_fields")
    provided_fields = auth_session.get("provided_fields")
    auth_session_id = auth_session.get("id")

    print("check auth_session in create_or_update_auth_request_draft_node", auth_session)
    print("="*20)

    result = await create_or_update_auth_request_draft(
        container=container,
        case_uuid=case_uuid,
        auth_session_id=auth_session_id,
        required_fields= required_fields,
        provided_fields= provided_fields
    )

    print("result of create_or_update_auth_request_draft", result)
    print("=" * 20)

    return {"auth_request_draft_result": result}


