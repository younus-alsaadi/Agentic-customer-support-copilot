from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.extract_intents_entities import extract_intents_entities
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container



async def extract_intents_entities_node(state: AgentState):


    container = await get_container()

    case = state.get("Case") or {}
    msg_in = state.get("Message") or {}

    case_id = case.get("case_uuid") or msg_in.get("case_id")
    message_id = msg_in.get("message_id")
    from_email = msg_in.get("from_email")
    subject = msg_in.get("subject")
    body = msg_in.get("body")

    if not case_id:
        state.setdefault("errors", []).append({"stage": "extract_intents_entities_node", "error": "Missing case_id"})
        return state
    if not message_id:
        state.setdefault("errors", []).append({"stage": "extract_intents_entities_node", "error": "Missing message_id"})
        return state
    if not from_email or body is None:
        state.setdefault("errors", []).append(
            {"stage": "extract_intents_entities_node", "error": "Missing from_email or body"})
        return state

    llm_intents_entities_result = await extract_intents_entities(
        container=container,
        case_id=str(case_id),
        message_id=str(message_id),
        from_email=from_email,
        subject=subject,
        body=body,
    )

    if not llm_intents_entities_result:
        state.setdefault("errors", []).append(
            {"stage": "extract_intents_entities_node", "error": "LLM returned empty result"})
        return state

    state["llm_response_extractions"] = llm_intents_entities_result
    return state
