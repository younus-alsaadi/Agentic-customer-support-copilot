from typing import cast, Dict, Any
from src.agents.CaseOrchestratorAgent.AgentState import AgentState, ExtractionsState
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container
from src.agents.CaseOrchestratorAgent.tools.extract_intents_entities import save_extraction
from src.models.db_schemes import Extractions



def _extraction_orm_to_state(msg: "Extractions") -> "ExtractionsState":
    data: ExtractionsState = {
        "extraction_id": str(msg.extraction_id),
        "case_id": str(msg.case_id),
        "message_id": str(msg.message_id),

        "intents": cast(Dict[str, Any], msg.intents) if msg.intents is not None else {},
        "entities": cast(Dict[str, Any], msg.entities) if msg.entities is not None else {},

        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }
    if msg.confidence is not None:
        data["confidence"] = float(msg.confidence)

    return data

async def save_extraction_node(state: AgentState):
    container = await get_container()

    msg=state.get("Message")
    message_id=msg.get("message_id")
    case_id=state.get("case_id")

    llm_result = state.get("llm_response_extractions") or {}
    if not isinstance(llm_result, dict) or not llm_result:
        state.setdefault("errors", []).append({"stage": "save_extraction_node", "error": "No llm_result in state"})
        return state


    extraction = await save_extraction(
        container = container,
        message_id=message_id,
        case_id=case_id,
        llm_result = llm_result,
    )
    print("=" * 20)
    print(f"intents is {extraction.intents}")
    print(f"entities is {extraction.entities}")
    print("="*20)

    if not extraction:
        state.setdefault("errors", []).append(
            {"stage": "save_extraction_node", "error": "save_extraction returned None"})
        return state

    return {"extractions":_extraction_orm_to_state(extraction)}
