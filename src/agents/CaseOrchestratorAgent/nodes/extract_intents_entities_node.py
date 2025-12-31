from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.extract_intents_entities import extract_intents_entities
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container


def _normalize_case_uuid(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s or s.lower() in {"none", "null", "n/a"}:
        return None

    return s


async def extract_intents_entities_node(state: AgentState):


    container = await get_container()

    case = state.get("Case") or {}
    msg_in = state.get("Message") or {}

    from_email = msg_in.get("from_email")
    subject = msg_in.get("subject")
    body = msg_in.get("body")

    if not from_email or body is None:
        state.setdefault("errors", []).append(
            {"stage": "extract_intents_entities_node", "error": "Missing from_email or body"})
        return state

    llm_intents_entities_result = await extract_intents_entities(
        container=container,
        from_email=from_email,
        subject=subject,
        body=body,
    )

    if not llm_intents_entities_result:
        state.setdefault("errors", []).append(
            {"stage": "extract_intents_entities_node", "error": "LLM returned empty result"})
        return state

    state["llm_response_extractions"] = llm_intents_entities_result
    state["case_id"]= _normalize_case_uuid(llm_intents_entities_result["case_id"])

    return state
