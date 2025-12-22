from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

class Extractions(BaseModel):

    extractions_id: UUID = Field(default_factory=uuid4)
    extractions_case_id: UUID
    extractions_message_id: UUID

    intents: Optional[Dict[str, Any]] = None # What does the customer want?
    entities: Optional[Dict[str, Any]] = None # What important data is inside the text?

    confidence: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            # Fetch extraction by message quickly (often one per message)
            {
                "key": [("message_id", 1)],
                "name": "extraction_message_id_uq",
                "unique": True,
            },
            # List extractions for a case (latest first)
            {
                "key": [("case_id", 1), ("created_at", -1)],
                "name": "extraction_case_id_created_at_desc_idx",
                "unique": False,
            },
            # if you search by case+message together
            {
                "key": [("case_id", 1), ("message_id", 1)],
                "name": "extraction_case_id_message_id_uq",
                "unique": True,
            },
        ]
