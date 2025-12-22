from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, DateTime, ForeignKey, Index, func, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

class Extractions(SQLAlchemyBase):
    __tablename__ = "extractions"

    extraction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=False)

    intents = Column(JSONB, nullable=True)   # list/dict of detected intents
    entities = Column(JSONB, nullable=True)  # extracted fields

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    case = relationship("Cases", back_populates="extractions")
    message = relationship("Messages", back_populates="extractions")

    __table_args__ = (
        # Fetch extraction by message quickly (often one per message)
        Index("extraction_message_id_uq", "message_id", unique=True),

        # List extractions for a case (latest first)
        Index("extraction_case_id_created_at_desc_idx", "case_id", created_at.desc()),

        # If you search by case+message together
        Index("extraction_case_id_message_id_uq", "case_id", "message_id", unique=True),
    )
