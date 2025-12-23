from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Extractions


class ExtractionsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):

        return cls(db_client=db_client)

    async def create_extraction(self, extraction: Extractions) -> Extractions:
        # Creates a new extraction row and returns it after DB refresh.
        # NOTE: If you enforce "one extraction per message" (unique on message_id),
        # this will fail if an extraction already exists for that message.
        async with self.db_client() as session:
            session.add(extraction)
            await session.commit()
            await session.refresh(extraction)
        return extraction

    async def get_extraction_by_id(self, extraction_id: UUID) -> Optional[Extractions]:
        # Fetch a single extraction by extraction_id. Returns None if not found.
        async with self.db_client() as session:
            stmt = select(Extractions).where(Extractions.extraction_id == extraction_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_extraction_by_message_id(self, message_id: UUID) -> Optional[Extractions]:
        # Fetch the extraction for a specific message.
        async with self.db_client() as session:
            stmt = select(Extractions).where(Extractions.message_id == message_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_extractions_by_case(
        self,
        case_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Extractions]:
        # List all extractions for a case, usually ordered by newest created first.
        async with self.db_client() as session:
            stmt = select(Extractions).where(Extractions.case_id == case_uuid)

            order_col = Extractions.created_at.desc() if newest_first else Extractions.created_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def upsert_extraction_by_message_id(
        self,
        case_uuid: UUID,
        message_id: UUID,
        intents: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
    ) -> Extractions:
        # Creates or updates the extraction for a message (safe if you re-run extraction).
        async with self.db_client() as session:
            stmt = select(Extractions).where(Extractions.message_id == message_id)
            result = await session.execute(stmt)
            extraction = result.scalar_one_or_none()

            if extraction is None:
                extraction = Extractions(
                    case_id=case_uuid,
                    message_id=message_id,
                    intents=intents,
                    entities=entities,
                    confidence=confidence,
                )
                session.add(extraction)
            else:
                # update existing fields only if provided
                if intents is not None:
                    extraction.intents = intents
                if entities is not None:
                    extraction.entities = entities
                if confidence is not None:
                    extraction.confidence = confidence

            await session.commit()
            await session.refresh(extraction)
            return extraction
