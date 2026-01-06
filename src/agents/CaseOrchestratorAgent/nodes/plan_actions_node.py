from typing import List, Dict, Any

from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.plan_actions import plan_actions_and_create_final_draft
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container

from src.agents.CaseOrchestratorAgent.AgentState import DraftsState, ActionsState
from src.models.db_schemes import Drafts as DraftORM, Actions as ActionORM


def _draft_dict_to_state(d: Dict[str, Any]) -> DraftsState:
    return {
        "draft_id": str(d.get("id") or d.get("draft_id") or ""),
        "case_id": str(d.get("case_id") or ""),
        "customer_reply_draft": d.get("customer_reply_draft") or "",
        "internal_summary": d.get("internal_summary") or "",
        "actions_suggested": d.get("actions_suggested") or [],
        "created_at": d.get("created_at") or "",
        "updated_at": d.get("updated_at") or "",
    }

def _action_dict_to_state(a: Dict[str, Any]) -> ActionsState:
    # your action dict keys depend on action_to_dict() you return from the tool
    return {
        "action_id": str(a.get("id") or a.get("action_id") or ""),
        "case_id": str(a.get("case_id") or ""),
        "action_type": a.get("action_type"),
        # some code uses "status" not "action_status" — handle both safely
        "action_status": a.get("action_status") or a.get("status"),
        "result": a.get("result"),
        "created_at": a.get("created_at") or "",
    }


async def plan_non_auth_actions_node(state: AgentState) -> AgentState:
    container = await get_container()

    case = state.get("Case") or {}
    extraction = state.get("extractions") or {}

    case_id = case.get("case_uuid")
    if not case_id:
        state.setdefault("errors", []).append({"stage": "plan_non_auth_actions_node", "error": "Missing case_uuid"})
        return state

    entities = extraction.get("entities") or {}
    topic_keywords = entities.get("topic_keywords")

    non_auth_intents = state.get("non_auth_intents") or []
    if not non_auth_intents:
        state["non_auth_plan_actions"] = {"actions_suggested": [], "draft": None}
        return state

    print("non auth actions start plan")
    print("="*20)
    result = await plan_actions_and_create_final_draft(
        container=container,
        case_id=case_id,
        intents=non_auth_intents,
        entities=entities,
        topic_keywords=topic_keywords,
        auth_status="no_need",
    )

    print("%" * 20)
    print(f" Imported : plan (NON) auth actions node is done ")
    print("%" * 20)


    return {"non_auth_plan_actions": result, "non_auth_done": True,}



async def plan_auth_actions_node(state: AgentState) -> AgentState:
    container = await get_container()

    case = state.get("Case") or {}
    extraction = state.get("extractions") or {}

    case_id = case.get("case_uuid")
    if not case_id:
        state.setdefault("errors", []).append({"stage": "plan_auth_actions_node", "error": "Missing case_uuid"})
        return state

    auth_sessions = state.get("auth_sessions") or {}
    if auth_sessions.get("auth_status") != "success":
        state["auth_plan_actions"] = {"actions_suggested": [], "draft": None}
        return state

    entities = extraction.get("entities") or {}
    topic_keywords = entities.get("topic_keywords")

    auth_intents = state.get("auth_intents") or []
    if not auth_intents:
        state["auth_plan_actions"] = {"actions_suggested": [], "draft": None}
        return state


    print("Auth actions start plan")
    print("="*20)
    result = await plan_actions_and_create_final_draft(
        container=container,
        case_id=case_id,
        intents=auth_intents,
        entities=entities,
        topic_keywords=topic_keywords,
        auth_status="success",
    )

    print("%" * 20)
    print(f" Imported : plan auth actions node is done ")
    print("%"*20)

    return {"auth_plan_result": result, "auth_done": True,}



def join_plans_node(state):
    auth_done = bool(state.get("auth_done"))
    non_auth_done = bool(state.get("non_auth_done"))

    print("[JOIN] auth_done:", auth_done, "non_auth_done:", non_auth_done)

    if not (auth_done and non_auth_done):
        return {"join_ready": False}

    if state.get("joined_once"):
        return {"join_ready": False}

    return {"joined_once": True, "join_ready": True}




