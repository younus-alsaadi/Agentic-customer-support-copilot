from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, DateTime, String, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

class Drafts(SQLAlchemyBase):
    __tablename__ = "drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=False)

    customer_reply_draft = Column(String, nullable=False)   # draft email to customer
    internal_summary = Column(String, nullable=False)       # summary for support agent

    actions_suggested = Column(JSONB, nullable=True)        # list of suggested actions (JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    case = relationship("Cases", back_populates="draft")
    reviews = relationship("Reviews", back_populates="draft")


    __table_args__ = (
        # Usually one "current" draft per case
        Index("draft_case_id_uq", "case_id", unique=True),

        # Listing recent drafts quickly
        Index("draft_updated_at_desc_idx", updated_at.desc()),
    )
