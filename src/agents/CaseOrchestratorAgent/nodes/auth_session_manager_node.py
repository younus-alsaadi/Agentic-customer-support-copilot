from __future__ import annotations
from src.agents.CaseOrchestratorAgent.AgentState import AgentState, AuthSessionsState
from src.agents.CaseOrchestratorAgent.tools.auth_session_manager import auth_session_manager
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container
from src.models.db_schemes import AuthSessions as AuthSessionsORM


def _auth_sessions_orm_to_state(row: AuthSessionsState) -> AuthSessionsState:
    data: AuthSessionsState = {
        "id": str(getattr(row, "id", "")),
        "case_id": str(getattr(row, "case_id", "")),
        "required_fields": getattr(row, "required_fields", None),
        "provided_fields": getattr(row, "provided_fields", None),
        "auth_status": getattr(row, "auth_status", "missing"),
        "created_at": getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
        "updated_at": getattr(row, "updated_at", None).isoformat() if getattr(row, "updated_at", None) else None,
    }
    return data



async def auth_session_manager_node(state: AgentState) -> AgentState:
    container = await get_container()

    # --- read case_uuid from state ---
    case = state.get("Case") or {}
    case_uuid = case.get("case_uuid")  # fallback if you used different key

    if not case_uuid:
        state["errors"] = state.get("errors", [])
        state["errors"].append({"stage": "auth_session_manager", "error": "Missing case_uuid in state['Case']."})
        return state


    # --- entities from latest extraction ---
    extraction = state.get("extractions")
    entities = extraction.get("entities")

    auth_intents = state.get("auth_intents")



    result = await auth_session_manager(
        container=container,
        case_uuid=case_uuid,
        auth_intents=auth_intents,
        entities=entities,
    )

    # Save result summary to state
    print( f"Result auth_sessions from auth_session_manager_node is {result}")
    print("="*20)

    update={"auth_sessions": _auth_sessions_orm_to_state(result["auth_session"])}


    print(f"state Result for auth_sessions is update")
    print("="*20)
    return update
