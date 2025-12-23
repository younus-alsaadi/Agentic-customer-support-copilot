from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Actions


class ActionsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        # Factory method (useful if later you add async init logic)
        return cls(db_client=db_client)

    async def create_action(self, action: Actions) -> Actions:
        # Create a new action row (planned/executed/blocked) and return it after refresh.
        async with self.db_client() as session:
            session.add(action)
            await session.commit()
            await session.refresh(action)
        return action

    async def get_action_by_id(self, action_id: UUID) -> Optional[Actions]:
        # Fetch a single action by its id. Returns None if not found.
        async with self.db_client() as session:
            stmt = select(Actions).where(Actions.id == action_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_actions_by_case(
        self,
        case_uuid: UUID,
        limit: int = 100,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Actions]:
        # Get all actions for a case (timeline view).
        async with self.db_client() as session:
            stmt = select(Actions).where(Actions.case_id == case_uuid)

            order_col = Actions.created_at.desc() if newest_first else Actions.created_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_actions_by_status(
        self,
        action_status: str,  # "planned" | "executed" | "blocked"
        limit: int = 100,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Actions]:
        # Triage view: list all actions by status.
        async with self.db_client() as session:
            stmt = select(Actions).where(Actions.action_status == action_status)

            order_col = Actions.created_at.desc() if newest_first else Actions.created_at.asc()
            stmt = stmt.order_by(order_col).offset(offset).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_action_status(
        self,
        action_id: UUID,
        new_status: str,  # "planned" | "executed" | "blocked"
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Actions]:
        # Update action_status and optionally store result payload (success info / error details).
        async with self.db_client() as session:
            stmt = select(Actions).where(Actions.id == action_id)
            result = await session.execute(stmt)
            action = result.scalar_one_or_none()

            if action is None:
                return None

            action.action_status = new_status

            if result_payload is not None:
                action.result = result_payload

            await session.commit()
            await session.refresh(action)
            return action

    async def upsert_action_for_case(
        self,
        case_uuid: UUID,
        action_type: str,
        action_status: str = "planned",
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> Actions:
        # Creates an action if one with same (case_id + action_type) doesn't exist,
        # otherwise updates its status/result.
        #
        # NOTE: This only makes sense if you enforce uniqueness in DB:
        # UNIQUE(case_id, action_type)
        async with self.db_client() as session:
            stmt = select(Actions).where(
                Actions.case_id == case_uuid,
                Actions.action_type == action_type,
            )
            res = await session.execute(stmt)
            action = res.scalar_one_or_none()

            if action is None:
                action = Actions(
                    case_id=case_uuid,
                    action_type=action_type,
                    action_status=action_status,
                    result=result_payload,
                )
                session.add(action)
            else:
                action.action_status = action_status
                if result_payload is not None:
                    action.result = result_payload

            await session.commit()
            await session.refresh(action)
            return action
