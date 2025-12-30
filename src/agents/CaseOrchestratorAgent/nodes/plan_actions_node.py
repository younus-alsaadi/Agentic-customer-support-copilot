from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.plan_actions import plan_actions_and_create_final_draft
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container

from src.agents.CaseOrchestratorAgent.AgentState import DraftsState, ActionsState
from src.models.db_schemes import Drafts as DraftORM, Actions as ActionORM


def _draft_orm_to_state(draft: DraftORM) -> DraftsState:
    data: DraftsState = {
        "draft_id": str(getattr(draft, "id", "")),      # or draft.draft_id if your column name is draft_id
        "case_id": str(draft.case_id),
        "customer_reply_draft": draft.customer_reply_draft,
        "internal_summary": draft.internal_summary,
        "actions_suggested": draft.actions_suggested or [],
        "created_at": draft.created_at.isoformat() if getattr(draft, "created_at", None) else "",
        "updated_at": draft.updated_at.isoformat() if getattr(draft, "updated_at", None) else "",
    }
    return data


def _action_orm_to_state(action: ActionORM) -> ActionsState:
    data: ActionsState = {
        "action_id": str(getattr(action, "id", "")),     # or action.action_id if your column name is action_id
        "case_id": str(action.case_id),
        "action_type": action.action_type,
        "action_status": action.action_status,
        "result": action.result if getattr(action, "result", None) is not None else None,
        "created_at": action.created_at.isoformat() if getattr(action, "created_at", None) else "",
    }
    return data


async def plan_actions_node(state: AgentState)->AgentState:

    container = await get_container()

    case = state.get("Case") or {}
    extraction = state.get("extractions") or {}

    case_id = case.get("case_uuid")
    if not case_id:
        return {"errors": state.get("errors", []) + [{"stage": "plan_actions_node", "error": "Missing case_uuid"}]}

    intents = extraction.get("intents") or []
    entities = extraction.get("entities") or {}
    topic_keywords = entities.get("topic_keywords")



    result = await plan_actions_and_create_final_draft(
        container=container,
        case_id=case_id,
        intents=intents,
        entities=entities,
        topic_keywords=topic_keywords,
        auth_status="no_need"
    )

    state["actions"] = [_action_orm_to_state(a) for a in result["actions_suggested"]]
    state["drafts"] = _draft_orm_to_state(result["draft"])

    # Return updates to state
    return state



