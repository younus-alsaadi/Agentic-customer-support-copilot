from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from uuid import UUID, uuid4
from datetime import datetime


class Actions(BaseModel):

    id: UUID = Field(default_factory=uuid4)
    case_id: UUID

    action_type: str = Field(default_factory=str) # What kind of action this is (e.g. "submit_meter_reading", "update_address")
    action_status: Literal["planned", "executed", "blocked"] = "planned"  #Current state of the action in the workflow:

    result: Optional[Dict[str, Any]] = None  # Output of the action (success payload, confirmation id, or error details)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            # fetch all actions for a case
            {
                "key": [("case_id", 1)],
                "name": "action_case_id_idx",
                "unique": False
            },

            # Setch latest actions for a case (timeline view)
            {
                "key": [("case_id", 1), ("created_at", -1)],
                "name": "action_case_id_created_at_desc_idx",
                "unique": False
            },

            #triage by status (e.g. show all blocked actions)
            {
                "key": [("action_status", 1), ("created_at", -1)],
                "name": "action_status_created_at_desc_idx",
                "unique": False
            },
        ]
