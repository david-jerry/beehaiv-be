from typing import Optional
import uuid

from sqlmodel import select
from src.app.auth.models import User, UserRole
from src.app.transactions.models import (
    TransactionHistory,
    TransactionStatus,
    TransactionType,
)
from src.app.transactions.schemas import (
    DomesticTransferSchema,
    InternationalTransferSchema,
    TransactionCreate,
    TransactionUpdate,
    WithdrawalSchema,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from src.errors import (
    InsufficientPermission,
    TransactionNotFound,
)


class TransactionService:
    async def get_all_transactions(
        self,
        session: AsyncSession,
        user: User,
    ):
        statement = (
            select(TransactionHistory).where(TransactionHistory.domain == user.domain)
            if user.role == UserRole.MANAGER
            else select(TransactionHistory)
        )
        result = await session.exec(statement)
        return result

    async def get_transaction_by_uid(
        self,
        session: AsyncSession,
        user: User,
        uid: uuid.UUID,
    ):
        statement = (
            select(TransactionHistory)
            .where(TransactionHistory.user_id == user.uid)
            .where(TransactionHistory.uid == uid)
            if user.role not in (UserRole.MANAGER, UserRole.ADMIN)
            else select(TransactionHistory).where(TransactionHistory.uid == uid)
        )
        result = await session.exec(statement)
        transaction = result.first()
        return transaction

    async def create_new_transaction(
        self, session: AsyncSession, user: User, transfer_data: TransactionCreate
    ):
        if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
            raise InsufficientPermission()

        transfer_data_dict = transfer_data.model_dump()
        transaction = TransactionHistory(**transfer_data_dict)
        transaction.domain = user.domain
        transaction.user = user
        transaction.user_id = user.uid
        transaction.transaction_type = TransactionType.TRANSFER
        transaction.status = TransactionStatus.COMPLETED
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        return transaction

    async def transfer_to_domestic_account(
        self, session: AsyncSession, user: User, transfer_data: DomesticTransferSchema
    ) -> TransactionHistory:
        transfer_data_dict = transfer_data.model_dump()

        # Create a new user with the given data
        new_transaction = TransactionHistory(**transfer_data_dict)
        new_transaction.transaction_type = TransactionType.TRANSFER
        new_transaction.domain = user.domain
        new_transaction.user = user
        new_transaction.user_id = user.uid

        # Logic for domestic transfer goes here
        new_transaction.status = TransactionStatus.COMPLETED

        # Add and commit the new user to the session
        session.add(new_transaction)
        await session.commit()
        await session.refresh(new_transaction)

        return new_transaction

    async def transfer_to_international_account(
        self,
        session: AsyncSession,
        user: User,
        transfer_data: InternationalTransferSchema,
    ) -> TransactionHistory:
        transfer_data_dict = transfer_data.model_dump()

        # Create a new user with the given data
        new_transaction = TransactionHistory(**transfer_data_dict)
        new_transaction.transaction_type = TransactionType.TRANSFER
        new_transaction.domain = user.domain
        new_transaction.user = user
        new_transaction.user_id = user.uid

        # Logic for domestic transfer goes here
        new_transaction.status = TransactionStatus.PENDING

        # Add and commit the new user to the session
        session.add(new_transaction)
        await session.commit()
        await session.refresh(new_transaction)

        return new_transaction

    async def withdraw_from_account(
        self, session: AsyncSession, user: User, transfer_data: WithdrawalSchema
    ) -> TransactionHistory:
        transfer_data_dict = transfer_data.model_dump()

        # Create a new user with the given data
        new_transaction = TransactionHistory(**transfer_data_dict)
        new_transaction.transaction_type = TransactionType.WITHDRAWAL
        new_transaction.domain = user.domain
        new_transaction.user = user
        new_transaction.user_id = user.uid

        # Logic for domestic transfer goes here
        new_transaction.status = TransactionStatus.COMPLETED

        # Add and commit the new user to the session
        session.add(new_transaction)
        await session.commit()
        await session.refresh(new_transaction)

        return new_transaction

    async def update_transaction(
        self,
        uid: uuid.UUID,
        user: User,
        trans_data: TransactionUpdate,
        session: AsyncSession,
    ):
        if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
            raise InsufficientPermission()

        trans_data_dict = trans_data.model_dump()

        transaction: Optional[TransactionHistory] = await self.get_transaction_by_uid(
            session, user, uid
        )

        if transaction is None:
            raise TransactionNotFound()

        for k, v in trans_data_dict.items():
            setattr(transaction, k, v)

        await session.commit()
        await session.refresh(transaction)

        return transaction
