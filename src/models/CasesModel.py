from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Cases


class CasesModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        # Factory method to create the model instance (useful if you later add async init logic).
        return cls(db_client=db_client)

    async def create_case(self, case: Cases) -> Cases:
        # Creates a new case row in the database, commits it, and returns the saved case
        # (including DB-generated fields like timestamps / ids after refresh).
        async with self.db_client() as session:
            session.add(case)
            await session.commit()
            await session.refresh(case)
        return case

    async def get_case_by_uuid(self, case_uuid: UUID) -> Optional[Cases]:
        # Fetches a single case by its public UUID.
        # Returns None if no case exists with that UUID.
        async with self.db_client() as session:
            stmt = select(Cases).where(Cases.case_uuid == case_uuid)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_cases_by_status(
        self,
        case_status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Cases]:
        # Returns cases filtered by status (e.g., "pending_review") ordered by most recently updated.
        # Supports pagination via limit/offset.
        async with self.db_client() as session:
            stmt = (
                select(Cases)
                .where(Cases.case_status == case_status)
                .order_by(Cases.case_updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_cases_by_channel(
        self,
        case_channel: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Cases]:
        # Returns cases filtered by channel (e.g., "Email") ordered by most recently updated.
        # Supports pagination via limit/offset.
        async with self.db_client() as session:
            stmt = (
                select(Cases)
                .where(Cases.case_channel == case_channel)
                .order_by(Cases.case_updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_case_status_by_uuid(
        self,
        case_uuid: UUID,
        new_status: str,
        status_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Cases]:
        # Updates a case's status (and optionally status metadata) using its UUID.
        # Returns the updated case, or None if the case UUID does not exist.
        # NOTE: status_meta overwrites the existing meta only if provided.
        async with self.db_client() as session:
            stmt = select(Cases).where(Cases.case_uuid == case_uuid)
            result = await session.execute(stmt)
            case = result.scalar_one_or_none()

            if case is None:
                return None

            case.case_status = new_status

            if status_meta is not None:
                case.case_status_meta = status_meta

            await session.commit()
            await session.refresh(case)
            return case
