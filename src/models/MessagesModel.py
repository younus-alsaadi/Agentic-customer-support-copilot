from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, desc
from .BaseDataModel import BaseDataModel
from .db_schemes import Messages


class MessagesModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        # Factory method (useful if later you add async init logic)
        return cls(db_client=db_client)

    async def create_message(self, message: Messages) -> Messages:
        # Creates a new message row (inbound/outbound) and returns it after DB refresh.
        async with self.db_client() as session:
            session.add(message)
            await session.commit()
            await session.refresh(message)
        return message

    async def get_message_by_id(self, message_id: UUID) -> Optional[Messages]:
        # Fetch a single message by message_id. Returns None if not found.
        async with self.db_client() as session:
            stmt = select(Messages).where(Messages.message_id == message_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_latest_inbound_message(self, case_id):
        async with self.db_client() as session:  # session is AsyncSession
            stmt = (
                select(Messages)
                .where(
                    Messages.case_id == case_id,
                    Messages.direction == "inbound",
                )
                .order_by(desc(Messages.received_at))
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalars().first()
    async def list_messages_by_case(
        self,
        case_uuid: UUID,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Messages]:
        # Returns messages for one case, optionally filtered by direction (inbound/outbound).
        # Useful to "bring all his messages" for a case thread.
        async with self.db_client() as session:
            stmt = select(Messages).where(Messages.case_id == case_uuid)

            if direction:
                stmt = stmt.where(Messages.direction == direction)

            order_col = Messages.received_at.desc() if newest_first else Messages.received_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_messages_by_sender(
        self,
        from_email: str,
        limit: int = 100,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Messages]:
        # Returns messages by sender email across all cases (useful for search / triage).
        async with self.db_client() as session:
            stmt = select(Messages).where(Messages.from_email == from_email)

            order_col = Messages.received_at.desc() if newest_first else Messages.received_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()
