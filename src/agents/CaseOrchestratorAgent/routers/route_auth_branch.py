from langgraph.graph import END

from src.agents.CaseOrchestratorAgent.AgentState import AgentState



def route_auth_branch(state: AgentState) -> str:
    auth_intents = state.get("auth_intents") or []
    return "auth_session_manager_node" if auth_intents else END



def route_non_auth_branch(state: AgentState) -> str:
    non_auth_intents = state.get("non_auth_intents") or []
    return "plan_non_auth_actions_node" if non_auth_intents else END