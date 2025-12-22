from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal, List
from uuid import UUID, uuid4
from datetime import datetime

class AuthSessions(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    case_id: UUID

    required_fields: Optional[List[str]] = None # what you need to verify identity


    # postal_code + contract_number store as hash (Privacy note (PII))
    provided_fields: Optional[Dict[str, Any]] = None # what the customer already provided.

    auth_status: Literal["missing", "success", "failed"] = "missing"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            # One auth session per case (recommended)
            {
                "key": [("case_id", 1)],
                "name": "auth_case_id_uq",
                "unique": True,
            },
            # Find cases by auth_status quickly
            {
                "key": [("auth_status", 1), ("updated_at", -1)],
                "name": "auth_status_updated_at_desc_idx",
                "unique": False,
            },
        ]




