from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, DateTime, String, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Messages(SQLAlchemyBase):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=False)


    direction = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(String, nullable=False)
    from_email = Column(String, nullable=False)
    to_email = Column(String, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Cases", back_populates="messages")

    extractions = relationship("Extractions", back_populates="message", cascade="all, delete-orphan")


    __table_args__ = (
        # 1) WHERE case_id = ...
        Index("msg_case_id_idx", "case_id"),

        # 2) WHERE case_id=... ORDER BY received_at DESC
        Index("msg_case_id_received_at_desc_idx", "case_id", received_at.desc()),

        # 3) WHERE case_id=... AND direction='inbound' ORDER BY received_at DESC
        Index("msg_case_id_direction_received_at_desc_idx", "case_id", "direction", received_at.desc()),
    )
