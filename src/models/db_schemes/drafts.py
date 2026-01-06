from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from uuid import UUID, uuid4
from datetime import datetime

# Store what the copilot generated before sending.

class Drafts(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    case_id: UUID

    customer_reply_draft: str = Field(..., min_length=1)  # draft email to the customer
    internal_summary: str = Field(..., min_length=1)      # summary for support agent

    draft_type: str= Literal["public_reply", "auth_request", "sensitive_reply"]

    actions_suggested: Optional[List[Dict[str, Any]]] = None  # multiple suggested actions

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            # One draft per type per case
            {"key": [("case_id", 1), ("draft_type", 1)], "name": "draft_case_id_type_uq", "unique": True},

            {"key": [("updated_at", -1)], "name": "draft_updated_at_desc_idx", "unique": False},
        ]