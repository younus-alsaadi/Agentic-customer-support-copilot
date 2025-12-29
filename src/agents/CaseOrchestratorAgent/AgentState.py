from typing import TypedDict, List, Dict, Any
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



class AgentState(TypedDict):
    Case: CaseState
    Message: Message
    extractions: ExtractionsState
    auth_intents: List[Dict[str, Any]]
    non_auth_intents: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    llm_response_extractions: Dict[str, Any]
