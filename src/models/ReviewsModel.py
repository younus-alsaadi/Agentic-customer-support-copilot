from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Reviews


class ReviewsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        return cls(db_client=db_client)

    async def create_review(self, review: Reviews) -> Reviews:
        # Creates a new review row and returns it after DB refresh.
        async with self.db_client() as session:
            session.add(review)
            await session.commit()
            await session.refresh(review)
        return review

    async def get_review_by_id(self, review_id: UUID) -> Optional[Reviews]:
        # Fetch a single review by its id. Returns None if not found.
        async with self.db_client() as session:
            stmt = select(Reviews).where(Reviews.id == review_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_reviews_by_case(
        self,
        case_uuid: UUID,
        limit: int = 50,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Reviews]:
        # Lists all reviews for a case (audit trail), ordered by created_at.
        async with self.db_client() as session:
            stmt = select(Reviews).where(Reviews.case_id == case_uuid)

            order_col = Reviews.created_at.desc() if newest_first else Reviews.created_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_reviews_by_decision(
        self,
        decision: str,  # "approved" | "rejected" | "needs_changes"
        limit: int = 50,
        offset: int = 0,
    ) -> List[Reviews]:
        # Triage view: list reviews by decision, newest updated first.
        async with self.db_client() as session:
            stmt = (
                select(Reviews)
                .where(Reviews.decision == decision)
                .order_by(Reviews.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_review_by_draft_id(self, draft_id: UUID) -> Optional[Reviews]:
        # Fetch a review linked to a specific draft.
        # Useful if your UI is "one review per draft".
        async with self.db_client() as session:
            stmt = select(Reviews).where(Reviews.draft_id == draft_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_review_decision(
        self,
        review_id: UUID,
        decision: str,  # "approved" | "rejected" | "needs_changes"
        review_notes: Optional[str] = None,
        edited_customer_reply_draft: Optional[str] = None,
        edited_internal_summary: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Reviews]:
        # Updates decision/notes/edits for a review row.
        async with self.db_client() as session:
            stmt = select(Reviews).where(Reviews.id == review_id)
            result = await session.execute(stmt)
            review = result.scalar_one_or_none()

            if review is None:
                return None

            review.decision = decision

            if review_notes is not None:
                review.review_notes = review_notes
            if edited_customer_reply_draft is not None:
                review.edited_customer_reply_draft = edited_customer_reply_draft
            if edited_internal_summary is not None:
                review.edited_internal_summary = edited_internal_summary
            if meta is not None:
                review.meta = meta

            await session.commit()
            await session.refresh(review)
            return review

    async def upsert_review_for_draft(
        self,
        case_uuid: UUID,
        draft_id: Optional[UUID],
        reviewer_email: Optional[str],
        reviewer_name: Optional[str],
        decision: str,
        review_notes: Optional[str] = None,
        edited_customer_reply_draft: Optional[str] = None,
        edited_internal_summary: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Reviews:
        # If you enforce "one review per draft", this will create/update that single review.
        # If draft_id is None, it will create a new review each time (audit-style).
        async with self.db_client() as session:
            review = None
            if draft_id is not None:
                stmt = select(Reviews).where(Reviews.draft_id == draft_id)
                res = await session.execute(stmt)
                review = res.scalar_one_or_none()

            if review is None:
                review = Reviews(
                    case_id=case_uuid,
                    draft_id=draft_id,
                    reviewer_email=reviewer_email,
                    reviewer_name=reviewer_name,
                    decision=decision,
                    review_notes=review_notes,
                    edited_customer_reply_draft=edited_customer_reply_draft,
                    edited_internal_summary=edited_internal_summary,
                    meta=meta,
                )
                session.add(review)
            else:
                review.reviewer_email = reviewer_email
                review.reviewer_name = reviewer_name
                review.decision = decision

                if review_notes is not None:
                    review.review_notes = review_notes
                if edited_customer_reply_draft is not None:
                    review.edited_customer_reply_draft = edited_customer_reply_draft
                if edited_internal_summary is not None:
                    review.edited_internal_summary = edited_internal_summary
                if meta is not None:
                    review.meta = meta

            await session.commit()
            await session.refresh(review)
            return review
