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

    intents_split = separate_auth_intents(intents=intents)

    update = {
        "auth_intents": intents_split["auth_intents"],
        "non_auth_intents": intents_split["non_auth_intents"],
    }

    if not update["auth_intents"]:
        update["auth_done"] = True  # set on update, not state

    print("state (auth_intents):", update["auth_intents"])
    print("state (non_auth_intents):", update["non_auth_intents"])

    return update





