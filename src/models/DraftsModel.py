from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Drafts


class DraftsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        # Factory method (useful if later you add async init logic)
        return cls(db_client=db_client)

    async def create_draft(self, draft: Drafts) -> Drafts:
        # Creates a new draft row and returns it after DB refresh.
        # NOTE: Because you have UNIQUE(case_id), this will fail if a draft already exists for the case.
        async with self.db_client() as session:
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
        return draft

    async def get_draft_by_id(self, draft_id: UUID) -> Optional[Drafts]:
        # Fetch a single draft by its id. Returns None if not found.
        async with self.db_client() as session:
            stmt = select(Drafts).where(Drafts.id == draft_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_draft_by_case_uuid(self, case_uuid: UUID) -> Optional[Drafts]:
        # Fetch the current draft for a case (one-to-one).
        async with self.db_client() as session:
            stmt = select(Drafts).where(Drafts.case_id == case_uuid)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upsert_draft_for_case(
        self,
        case_id: UUID,
        customer_reply_draft: Optional[str] = None,
        internal_summary: Optional[str] = None,
        actions_suggested: Optional[List[Dict[str, Any]]] = None,
    ) -> Drafts:
        # Creates the draft for a case if it doesn't exist, otherwise updates it.
        # This is ideal for workflows where you regenerate drafts multiple times.
        async with self.db_client() as session:
            stmt = select(Drafts).where(Drafts.case_id == case_id)
            result = await session.execute(stmt)
            draft = result.scalar_one_or_none()

            if draft is None:
                # For create: customer_reply_draft and internal_summary must exist
                if not customer_reply_draft or not internal_summary:
                    raise ValueError("customer_reply_draft and internal_summary are required when creating a new draft.")

                draft = Drafts(
                    case_id=case_id,
                    customer_reply_draft=customer_reply_draft,
                    internal_summary=internal_summary,
                    actions_suggested=actions_suggested,
                )
                session.add(draft)
            else:
                # For update: patch only provided fields
                if customer_reply_draft is not None:
                    draft.customer_reply_draft = customer_reply_draft
                if internal_summary is not None:
                    draft.internal_summary = internal_summary
                if actions_suggested is not None:
                    draft.actions_suggested = actions_suggested

            await session.commit()
            await session.refresh(draft)
            return draft

    async def list_recent_drafts(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Drafts]:
        # Lists recent drafts across all cases (admin / monitoring view).
        async with self.db_client() as session:
            stmt = select(Drafts).order_by(Drafts.updated_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def delete_draft_by_case_uuid(self, case_uuid: UUID) -> bool:
        # Deletes the draft for a case (if it exists). Returns True if deleted, False otherwise.
        async with self.db_client() as session:
            stmt = select(Drafts).where(Drafts.case_id == case_uuid)
            result = await session.execute(stmt)
            draft = result.scalar_one_or_none()

            if draft is None:
                return False

            await session.delete(draft)
            await session.commit()
            return True
