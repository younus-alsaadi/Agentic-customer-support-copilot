import operator
from typing import TypedDict, List, Dict, Any, Literal, Optional, Annotated
from uuid import UUID


class CaseState(TypedDict,total=False):
    case_id: str
    case_uuid: UUID
    case_status:str
    case_status_meta:Dict[str, Any]
    case_channel:str
    case_created_at:str
    case_updated_at:str

class Message(TypedDict, total=False):
    case_id: str
    message_id: str
    direction: str
    subject: str
    body: str
    from_email: str
    to_email: str
    received_at:str

class ExtractionsState(TypedDict, total=False):
    extraction_id:str
    case_id: str
    message_id: str
    intents: List[Dict[str, Any]]
    entities:List[Dict[str, Any]]
    confidence: float
    created_at: str

class ActionsState(TypedDict, total=False):
    action_id: str
    case_id: str
    action_type:str
    action_status: Literal["planned", "executed", "blocked", "no_need"]
    result:Optional[Dict[str, Any]]
    created_at: str
    updated_at: str

class DraftsState(TypedDict, total=False):
    draft_id: str
    case_id: str
    customer_reply_draft:str
    internal_summary:str
    actions_suggested:List[Dict[str, Any]]
    created_at: str
    updated_at: str

class HumanReviewState(TypedDict, total=False):
    decision: Literal["approved", "rejected"]
    reviewer_email:str
    reviewer_name:str
    support_from_email:str
    edited_customer_reply:str
    review_notes:str

class AuthSessionsState(TypedDict, total=False):
    id: str
    case_id: str
    required_fields:Dict[str, Any]
    provided_fields:Dict[str, Any]
    auth_status:Literal["missing", "success", "failed"]
    created_at: str
    updated_at: str


class AgentState(TypedDict):
    case_id: str
    Case: CaseState
    Message: Message
    extractions: ExtractionsState
    actions: Annotated[List[ActionsState], operator.add]
    drafts: Annotated[List[DraftsState], operator.add]
    auth_sessions: AuthSessionsState
    human_review: HumanReviewState
    auth_intents: List[Dict[str, Any]]
    non_auth_intents: List[Dict[str, Any]]
    non_auth_plan_result:Dict[str, Any]
    auth_plan_result: Dict[str, Any]
    non_auth_done: bool
    auth_done: bool
    join_ready: bool
    joined_once: bool
    errors: List[Dict[str, Any]]
    llm_response_extractions: Dict[str, Any]
