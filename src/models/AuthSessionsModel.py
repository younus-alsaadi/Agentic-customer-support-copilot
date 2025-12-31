from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import AuthSessions


class AuthSessionsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        # Factory method (useful if later you add async init logic)
        return cls(db_client=db_client)

    async def create_auth_session(self, auth_session: AuthSessions) -> AuthSessions:
        # Creates a new auth session row and returns it after DB refresh.
        # NOTE: Because you have UNIQUE(case_id), this will fail if a session already exists for the case.
        async with self.db_client() as session:
            session.add(auth_session)
            await session.commit()
            await session.refresh(auth_session)
        return auth_session

    async def get_auth_session_by_id(self, auth_session_id: UUID) -> Optional[AuthSessions]:
        # Fetch a single auth session by its primary id.
        async with self.db_client() as session:
            stmt = select(AuthSessions).where(AuthSessions.id == auth_session_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_auth_session_by_case_id(self, case_id: UUID) -> Optional[AuthSessions]:
        # Fetch the auth session for a given case (one-to-one).
        async with self.db_client() as session:
            stmt = select(AuthSessions).where(AuthSessions.case_id == case_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upsert_auth_session_for_case(
        self,
        case_uuid: UUID,
        required_fields: Optional[List[str]] = None,
        provided_fields: Optional[Dict[str, Any]] = None,
        auth_status: Optional[str] = None,  # "missing" | "success" | "failed"
    ) -> AuthSessions:
        # Creates the auth session for a case if it doesn't exist,
        # otherwise updates it (safe for re-runs of the workflow).
        async with self.db_client() as session:
            stmt = select(AuthSessions).where(AuthSessions.case_id == case_uuid)
            result = await session.execute(stmt)
            auth = result.scalar_one_or_none()

            if auth is None:
                auth = AuthSessions(
                    case_id=case_uuid,
                    required_fields=required_fields,
                    provided_fields=provided_fields,
                    auth_status=auth_status or "missing",
                )
                session.add(auth)
            else:
                if required_fields is not None:
                    auth.required_fields = required_fields
                if provided_fields is not None:
                    auth.provided_fields = provided_fields
                if auth_status is not None:
                    auth.auth_status = auth_status

            await session.commit()
            await session.refresh(auth)
            return auth

    async def patch_provided_fields(
        self,
        case_uuid: UUID,
        new_fields: Dict[str, Any],
    ) -> Optional[AuthSessions]:
        # Merges new provided fields into existing provided_fields (does NOT overwrite the whole dict).
        # Useful when customer sends partial auth info across multiple emails.
        async with self.db_client() as session:
            stmt = select(AuthSessions).where(AuthSessions.case_id == case_uuid)
            result = await session.execute(stmt)
            auth = result.scalar_one_or_none()

            if auth is None:
                return None

            current = auth.provided_fields or {}
            current.update(new_fields)
            auth.provided_fields = current

            await session.commit()
            await session.refresh(auth)
            return auth

    async def list_auth_sessions_by_status(
        self,
        auth_status: str,  # "missing" | "success" | "failed"
        limit: int = 50,
        offset: int = 0,
    ):
        # Lists auth sessions filtered by status, newest updated first (triage view).
        async with self.db_client() as session:
            stmt = (
                select(AuthSessions)
                .where(AuthSessions.auth_status == auth_status)
                .order_by(AuthSessions.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
