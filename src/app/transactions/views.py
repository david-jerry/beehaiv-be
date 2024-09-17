#  remember to use the user dependencies to test for users that are not blocked to ensure the page shows the correct information for blocked users
from datetime import datetime, timedelta

from typing import Optional, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.models import User
from src.app.auth.services import BusinessService, UserService
from src.app.auth.utils import verify_password
from src.app.transactions.models import TransactionHistory, TransactionStatus, TransactionType

from src.app.auth.dependencies import get_current_user, RoleChecker, RefreshTokenBearer, AccessTokenBearer
from .schemas import (
    TransactionCreate,
    TransactionRead,
    DomesticTransferSchema,
    InternationalTransferSchema,
    TransactionUpdate,
    WithdrawalSchema,
)
from .services import TransactionService
from src.errors import BankAccountNotFound, InsufficientFunds, InvalidTransactionPin, TransactionNotFound, UserAlreadyExists, UserNotFound, InvalidCredentials, InvalidToken, InsufficientPermission
from src.config.settings import Config
from src.db.db import get_session
from src.celery_tasks import send_email

transaction_router = APIRouter()
transaction_service = TransactionService()
user_service = UserService()
business_service = BusinessService()

# Transaction Routers
@transaction_router.post("", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
async def create_transaction_record(
    transaction_data: TransactionCreate,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    transaction: TransactionHistory = await transaction_service.create_new_transaction(session, user, transaction_data)

    return {
        "message": "Transaction Created!",
        "transaction": transaction,
    }

@transaction_router.post("/domestic-transfer", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
async def make_domestic_transfers(
    transaction_data: DomesticTransferSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(account_number, session)

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = await transaction_service.transfer_to_domestic_account(session, user, transaction_data)

    if transaction:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return {
        "message": "Transfer Successful!",
        "transaction": transaction,
    }

@transaction_router.post("/international-transfer", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
async def make_international_transfers(
    transaction_data: DomesticTransferSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(account_number, session)

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = await transaction_service.transfer_to_international_account(session, user, transaction_data)

    if transaction:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return {
        "message": "Transfer Successful!",
        "transaction": transaction,
    }

@transaction_router.post("/withdraw", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
async def withdraw_from_balance(
    transaction_data: WithdrawalSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(account_number, session)

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = await transaction_service.withdraw_from_account(session, user, transaction_data)

    if transaction:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return {
        "message": "Withdrawal Successful!",
        "transaction": transaction,
    }

@transaction_router.patch("/{uid}", status_code=status.HTTP_200_OK, response_model=TransactionRead)
async def update_transaction(
    transaction_data: TransactionUpdate,
    account_number: str,
    uid: uuid.UUID,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    bank_account = await business_service.get_bank_by_account_number(account_number, session)

    if bank_account is None:
        raise BankAccountNotFound()

    transaction: TransactionHistory = await transaction_service.update_transaction(uid, transaction_data, session)

    if transaction.status == TransactionStatus.COMPLETED and transaction.transaction_type == TransactionType.TRANSFER:
        bank_account.balance -= transaction.amount
    elif transaction.status == TransactionStatus.FAILED and transaction.transaction_type == TransactionType.TRANSFER:
        bank_account.balance += transaction.amount
    await session.commit()
    await session.refresh(bank_account)


    return {
        "message": "Update Successful!",
        "transaction": transaction,
    }

@transaction_router.get("", status_code=status.HTTP_200_OK, response_model=List[TransactionRead])
async def all_transactions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    transactions = await transaction_service.get_all_transactions(session, user)

    return {
        "message": "Ok!",
        "transaction": transactions,
    }

@transaction_router.get("/{uid}", status_code=status.HTTP_200_OK, response_model=TransactionRead)
async def get_transaction(
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction records
    body:
        transaction_data: TransactionCreate
    """
    transaction: Optional[TransactionHistory] = await transaction_service.get_transaction_by_uid(session, user, uid)
    if transaction is None:
        raise TransactionNotFound()

    return {
        "message": "Ok!",
        "transaction": transaction,
    }

