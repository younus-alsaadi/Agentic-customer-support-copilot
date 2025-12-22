from .lichblick_base import SQLAlchemyBase

from sqlalchemy import Column, String, DateTime, func, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
import uuid


class Reviews(SQLAlchemyBase):
    __tablename__ = "reviews"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    case_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.case_uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    draft_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewer_email = Column(String, nullable=True)
    reviewer_name = Column(String, nullable=True)

    # approved | rejected | needs_changes
    decision = Column(String, nullable=False, index=True)

    review_notes = Column(String, nullable=True)

    edited_customer_reply_draft = Column(String, nullable=True)
    edited_internal_summary = Column(String, nullable=True)

    meta = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


    case = relationship("Cases", back_populates="reviews")
    draft = relationship("Drafts", back_populates="reviews")

    __table_args__ = (
        # list reviews for a case (latest first)
        Index("review_case_id_created_at_desc_idx", "case_id", created_at.desc()),

        # triage by decision
        Index("review_decision_updated_at_desc_idx", "decision", updated_at.desc()),
    )
