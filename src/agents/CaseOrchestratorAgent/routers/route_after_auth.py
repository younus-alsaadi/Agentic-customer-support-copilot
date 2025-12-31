from src.agents.CaseOrchestratorAgent.AgentState import AgentState


def route_after_auth(state: AgentState) -> str:
    auth = state.get("auth_sessions") or {}
    auth_status = (auth.get("auth_status") or "").lower().strip()

    # handle typos like "suscess"
    if auth_status in {"success", "suscess"}:
        return "plan_actions_node"

    # missing / failed -> ask for auth data
    return "create_or_update_auth_request_draft_node"
