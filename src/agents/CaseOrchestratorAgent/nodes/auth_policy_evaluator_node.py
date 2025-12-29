from src.agents.CaseOrchestratorAgent.AgentState import AgentState
from src.agents.CaseOrchestratorAgent.tools.auth_policy_evaluator import separate_auth_intents




async def auth_policy_evaluator_node(state: AgentState):

    extraction =state.get("extractions") or {}
    intents = extraction.get("intents") or []

    if not isinstance(intents, list):
        state.setdefault("errors", []).append({
            "stage": "auth_policy_evaluator_node",
            "error": f"Extraction.intents must be a list, got {type(intents).__name__}"
        })
        intents = []

    intents = separate_auth_intents(intents=intents)

    state["auth_intents"] = intents["auth_intents"]
    state["non_auth_intents"] = intents["non_auth_intents"]

    return state





