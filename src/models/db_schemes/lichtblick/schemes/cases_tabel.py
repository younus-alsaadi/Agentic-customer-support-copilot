from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from sqlalchemy.orm import relationship


class Cases(SQLAlchemyBase):
    __tablename__ = 'cases'

    case_id = Column(Integer, primary_key=True, autoincrement=True)
    case_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)


    case_status = Column(String, nullable=False, server_default="new")
    case_status_meta = Column(JSONB, nullable=True)  # optional extra details

    case_channel = Column(String, nullable=False, server_default="Email")

    case_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    case_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),nullable=False)

    actions = relationship("Actions", back_populates="case", cascade="all, delete-orphan")
    messages = relationship("Messages", back_populates="case", cascade="all, delete-orphan")
    extractions = relationship("Extractions", back_populates="case", cascade="all, delete-orphan")
    reviews = relationship("Reviews", back_populates="case", cascade="all, delete-orphan")

    auth_session = relationship("AuthSessions", back_populates="case", uselist=False, cascade="all, delete-orphan")

    drafts = relationship("Drafts", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("cases_status_idx", "case_status"),
        Index("cases_updated_at_desc_idx", case_updated_at.desc()),
        Index("cases_channel_updated_at_desc_idx", "case_channel", case_updated_at.desc()),
    )