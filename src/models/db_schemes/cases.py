from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from uuid import UUID, uuid4
from datetime import datetime



CaseStatus = Literal[
    "new",
    "waiting_auth",
    "waiting_customer",
    "pending_review",
    "approved",
    "done",
    "failed",
]

class Cases(BaseModel):
    case_id: UUID = Field(default_factory=uuid4)

    case_status: CaseStatus = "new"
    case_status_meta: Optional[Dict[str, Any]] = None

    case_channel: str = "Email"

    case_created_at: datetime = Field(default_factory=datetime.utcnow)
    case_updated_at: datetime = Field(default_factory=datetime.utcnow)


    class Config:
        # allow reading from SQLAlchemy objects
        from_attributes = True  # pydantic v2

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [("case_id", 1)],
                "name": "case_project_id_idx",
                "unique": False,
            },
            {
                "key": [("case_id", 1), ("status", 1)],
                "name": "case_project_id_status_idx",
                "unique": False,
            },
            {
                "key": [("case_id", 1), ("updated_at", -1)],
                "name": "case_project_id_updated_at_desc_idx",
                "unique": False,
            },
        ]

