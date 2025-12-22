from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime


ReviewDecision = Literal["approved", "rejected", "needs_changes"]


class Reviews(BaseModel):
    id: UUID = Field(default_factory=uuid4)

    case_id: UUID

    draft_id: UUID

    # Who reviewed it (keep simple; you can also store reviewer_id if you have users table)
    reviewer_email: Optional[EmailStr] = None
    reviewer_name: Optional[str] = Field(default=None, min_length=1)


    decision: ReviewDecision
    review_notes: Optional[str] = None

    # If the agent edited the drafts, store the final edited text
    edited_customer_reply_draft: Optional[str] = None
    edited_internal_summary: Optional[str] = None

    # Optional metadata (UI info, tool versions, etc.)
    meta: Optional[Dict[str, Any]] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            # list reviews for a case
            {"key": [("case_id", 1), ("created_at", -1)], "name": "review_case_id_created_at_desc_idx", "unique": False},

            # fetch review by draft quickly (usually 0..1 per draft)
            {"key": [("draft_id", 1)], "name": "review_draft_id_idx", "unique": False},

            # triage by decision
            {"key": [("decision", 1), ("updated_at", -1)], "name": "review_decision_updated_at_desc_idx", "unique": False},
        ]

