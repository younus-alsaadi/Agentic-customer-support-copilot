from typing import Optional, List, Dict, Any
from datetime import date

from sqlalchemy import select
from .BaseDataModel import BaseDataModel
from .db_schemes import Contracts


class ContractsModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        return cls(db_client=db_client)

    async def create_contract(self, contract: Contracts) -> Contracts:
        # Creates a new contract row and returns it after DB refresh.
        async with self.db_client() as session:
            session.add(contract)
            await session.commit()
            await session.refresh(contract)
        return contract

    async def get_contract_by_customer_id(self, customer_id: int) -> Optional[Contracts]:
        # Fetch contract by primary key (customer_id).
        async with self.db_client() as session:
            stmt = select(Contracts).where(Contracts.customer_id == customer_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_contract_by_contract_number(self, contract_number: str) -> Optional[Contracts]:
        # Fetch contract by contract_number (unique).
        async with self.db_client() as session:
            stmt = select(Contracts).where(Contracts.contract_number == contract_number)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_contracts(
        self,
        limit: int = 50,
        offset: int = 0,
        newest_first: bool = True,
    ) -> List[Contracts]:
        # Admin/helper: list contracts ordered by created time.
        async with self.db_client() as session:
            order_col = Contracts.created_at.desc() if newest_first else Contracts.created_at.asc()
            stmt = select(Contracts).order_by(order_col).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def verify_identity(
        self,
        contract_number: str,
        postal_code: Optional[str] = None,
        birthday: Optional[date] = None,
        full_name: Optional[str] = None,
    ) -> Optional[Contracts]:
        # Identity check for auth: find contract by contract_number and verify extra fields.
        # Returns the contract if it matches, otherwise None.
        async with self.db_client() as session:
            stmt = select(Contracts).where(Contracts.contract_number == contract_number)
            result = await session.execute(stmt)
            contract = result.scalar_one_or_none()

            if contract is None:
                return None

            # Check provided factors (only compare if user provided them)
            if postal_code is not None and contract.postal_code != postal_code:
                return None
            if birthday is not None and contract.birthday != birthday:
                return None
            if full_name is not None and contract.full_name != full_name:
                return None

            return contract

    async def find_by_postal_code(
        self,
        postal_code: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Contracts]:
        # Search contracts by postal_code (index exists).
        async with self.db_client() as session:
            stmt = (
                select(Contracts)
                .where(Contracts.postal_code == postal_code)
                .order_by(Contracts.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
