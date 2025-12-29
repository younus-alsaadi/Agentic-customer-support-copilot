from src.agents.CaseOrchestratorAgent.AgentState import AgentState, Message
from src.agents.CaseOrchestratorAgent.tools.message_writer import message_writer
from src.agents.CaseOrchestratorAgent.utils.build_container import get_container
from src.models.db_schemes import Messages


def _message_orm_to_state(msg: Messages) -> Message:
    data: Message = {
        "message_id": str(msg.message_id),
        "case_uuid": str(msg.case_id),      # or rename your TypedDict to case_id
        "direction": msg.direction,
        "subject": msg.subject or "",
        "body": msg.body,
        "from_email": msg.from_email,
        "to_email": msg.to_email,
        "received_at": msg.received_at.isoformat() if msg.received_at else "",
    }
    return data

async def create_msg_node(state: AgentState) -> AgentState:
    container = await get_container()

    case = state.get("Case") or {}
    msg_in = state.get("Message") or {}


    case_id =case.get("case_uuid")
    if not case_id:
        state.setdefault("errors", []).append({"stage": "create_msg_node", "error": "Missing Case.case_id"})
        return state

    direction = msg_in.get("direction", "inbound")
    from_email = msg_in.get("from_email")
    to_email = msg_in.get("to_email")
    subject = msg_in.get("subject")
    body = msg_in.get("body")

    if not from_email or body is None:
        state.setdefault("errors", []).append({"stage": "create_msg_node", "error": "Missing from_email or body"})
        return state

    new_msg_orm = await message_writer(
        container=container,
        case_uuid=case_id,
        direction=direction,
        subject=subject,
        body=body,
        from_email=from_email,
        to_email=to_email
    )

    if not new_msg_orm:
        state.setdefault("errors", []).append({"stage": "create_msg_node", "error": "message_writer returned None"})
        return state

    state["Message"] = _message_orm_to_state(new_msg_orm)
    return state
