from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from uuid import UUID, uuid4
from datetime import datetime

class Messages(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    message_case_id: UUID

    direction: str = Field(..., min_length=1)
    subject: Optional[str] = None

    body: str = Literal["inbound", "outbound"]
    from_email: EmailStr

    received_at: datetime = Field(default_factory=datetime.utcnow)


    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [("case_id", 1)],
                "name": "msg_case_id_idx",
                "unique": False,
            },
            {
                "key": [("case_id", 1), ("received_at", -1)],
                "name": "msg_case_id_received_at_desc_idx",
                "unique": False,
            },
            {
                "key": [("case_id", 1), ("direction", 1), ("received_at", -1)],
                "name": "msg_case_id_direction_received_at_desc_idx",
                "unique": False,
            },
        ]
