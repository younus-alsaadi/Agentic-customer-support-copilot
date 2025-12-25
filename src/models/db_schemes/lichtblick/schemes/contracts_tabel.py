from .lichblick_base import SQLAlchemyBase
from sqlalchemy import Column, Date, DateTime, String, Integer, Identity, func, Index
from sqlalchemy.dialects.postgresql import JSONB

class Contracts(SQLAlchemyBase):
    __tablename__ = "contracts"

    customer_id = Column(Integer, Identity(start=1), primary_key=True)

    contract_number = Column(String, nullable=False, unique=True)

    full_name = Column(String, nullable=False)
    birthday = Column(Date, nullable=True)

    postal_code = Column(String, nullable=False)

    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_contracts_postal_code", "postal_code"),
        Index("ix_contracts_created_at", "created_at"),
    )
