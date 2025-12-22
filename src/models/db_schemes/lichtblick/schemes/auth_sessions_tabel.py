from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, DateTime, String, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

class AuthSessions(SQLAlchemyBase):
    __tablename__ = "auth_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.case_uuid", ondelete="CASCADE"),
        nullable=False
    )

    # List of required identity fields (e.g. ["contract_number", "postal_code", "installment_amount"])
    required_fields = Column(JSONB, nullable=True)

    # Provided identity fields (store masked/hashed values only)
    provided_fields = Column(JSONB, nullable=True)

    # missing / success / failed
    auth_status = Column(String, nullable=False, server_default="missing")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    case = relationship("Cases", back_populates="auth_session")

    __table_args__ = (
        # One auth session per case
        Index("auth_case_id_uq", "case_id", unique=True),

        # Fast triage: filter by status, sort by newest updated
        Index("auth_status_updated_at_desc_idx", "auth_status", updated_at.desc()),
    )
