from .lichblick_base import SQLAlchemyBase

import uuid
from sqlalchemy import Column, String, DateTime, func, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship


class Actions(SQLAlchemyBase):
    __tablename__ = "actions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.case_uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action_type = Column(String, nullable=False)

    action_status = Column(String, nullable=False, default="planned", index=True)


    result = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


    case = relationship("Cases", back_populates="actions")


    __table_args__ = (
        # latest actions per case (timeline)
        Index("action_case_id_created_at_desc_idx", "case_id", created_at.desc()),

        # triage by status
        Index("action_status_created_at_desc_idx", "action_status", created_at.desc()),
    )
