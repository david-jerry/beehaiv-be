from typing import Optional, List
import uuid
from fastapi import (
    APIRouter,
    Depends,
    status,
    BackgroundTasks,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.models import User
from src.app.auth.services import BusinessService, UserService
from src.app.auth.utils import verify_password
from src.app.transactions.models import (
    TransactionHistory,
    TransactionStatus,
    TransactionType,
)

from src.app.auth.dependencies import (
    get_current_user,
)
from .schemas import (
    DomesticTransferSchema,
    InternationalTransferSchema,
    TransactionCreate,
    TransactionRead,
    TransactionSummary,
    TransactionUpdate,
    WithdrawalSchema,
)
from .services import TransactionService
from src.errors import (
    BankAccountNotFound,
    InsufficientFunds,
    InvalidTransactionPin,
    TransactionNotFound,
)
from src.db.db import get_session

transaction_router = APIRouter()
transaction_service = TransactionService()
user_service = UserService()
business_service = BusinessService()


# Transaction Routers
@transaction_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=TransactionRead
)
async def create_transaction_record(
    transaction_data: TransactionCreate,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new transaction record.

    This endpoint creates a new transaction record in the database based on the
    provided `transaction_data`. The authenticated user is required, and the
    transaction will be associated with that user.

    Args:
    - transaction_data (TransactionCreate): The details of the transaction to be created.
    - bg_tasks (BackgroundTasks): For any background tasks related to transaction processing.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a success message and the details of the created transaction.
    """
    transaction: TransactionHistory = await transaction_service.create_new_transaction(
        session, user, transaction_data
    )

    return transaction


@transaction_router.post(
    "/domestic-transfer",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionRead,
)
async def make_domestic_transfers(
    transaction_data: DomesticTransferSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Make a domestic transfer between accounts.

    This endpoint facilitates transferring funds domestically to another bank account.
    The user's transfer PIN is required for security validation. If the bank account
    is found and has sufficient funds, the transfer will be processed, and the balance
    will be updated accordingly.

    Args:
    - transaction_data (DomesticTransferSchema): The details of the domestic transfer.
    - transfer_pin (str): The user's transfer PIN to authorize the transaction.
    - account_number (str): The account number to transfer to.
    - bg_tasks (BackgroundTasks): For any background tasks related to transfer processing.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - InvalidTransactionPin: If the provided transfer PIN is incorrect.
    - BankAccountNotFound: If the recipient bank account is not found.
    - InsufficientFunds: If the user's account does not have enough balance for the transfer.

    Returns:
    - A JSON response containing a success message and the details of the completed transfer.
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(
        account_number, session
    )

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = (
        await transaction_service.transfer_to_domestic_account(
            session, user, transaction_data
        )
    )

    if transaction is not None:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return transaction


@transaction_router.post(
    "/international-transfer",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionRead,
)
async def make_international_transfers(
    transaction_data: InternationalTransferSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Make an international transfer between accounts.

    This endpoint facilitates transferring funds internationally to another bank account.
    The user's transfer PIN is required for security validation. The recipient bank account
    must exist and have enough funds for the transfer.

    Args:
    - transaction_data (InternationalTransferSchema): The details of the international transfer.
    - transfer_pin (str): The user's transfer PIN to authorize the transaction.
    - account_number (str): The account number to transfer to.
    - bg_tasks (BackgroundTasks): For any background tasks related to transfer processing.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - InvalidTransactionPin: If the provided transfer PIN is incorrect.
    - BankAccountNotFound: If the recipient bank account is not found.
    - InsufficientFunds: If the user's account does not have enough balance for the transfer.

    Returns:
    - A JSON response containing a success message and the details of the completed transfer.
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(
        account_number, session
    )

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = (
        await transaction_service.transfer_to_international_account(
            session, user, transaction_data
        )
    )

    if transaction is not None:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return transaction


@transaction_router.post(
    "/withdraw", status_code=status.HTTP_201_CREATED, response_model=TransactionRead
)
async def withdraw_from_balance(
    transaction_data: WithdrawalSchema,
    transfer_pin: str,
    account_number: str,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Withdraw funds from the user's bank account.

    This endpoint allows the user to withdraw funds from their bank account.
    The user's transfer PIN is required to authorize the withdrawal. The withdrawal
    will only be processed if the user has sufficient funds.

    Args:
    - transaction_data (WithdrawalSchema): The details of the withdrawal transaction.
    - transfer_pin (str): The user's transfer PIN to authorize the transaction.
    - account_number (str): The account number to withdraw from.
    - bg_tasks (BackgroundTasks): For any background tasks related to withdrawal processing.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - InvalidTransactionPin: If the provided transfer PIN is incorrect.
    - BankAccountNotFound: If the account is not found.
    - InsufficientFunds: If the account does not have enough balance for the withdrawal.

    Returns:
    - A JSON response containing a success message and the details of the completed withdrawal.
    """
    can_transfer = verify_password(transfer_pin, user.transfer_pin_hash)
    if not can_transfer:
        raise InvalidTransactionPin()

    bank_account = await business_service.get_bank_by_account_number(
        account_number, session
    )

    if bank_account is None:
        raise BankAccountNotFound()

    if bank_account.balance < transaction_data.amount:
        raise InsufficientFunds()

    transaction: TransactionHistory = await transaction_service.withdraw_from_account(
        session, user, transaction_data
    )

    if transaction is not None:
        bank_account.balance -= transaction_data.amount
        await session.commit()
        await session.refresh(bank_account)

    return transaction


@transaction_router.patch(
    "/{uid}", status_code=status.HTTP_200_OK, response_model=TransactionRead
)
async def update_transaction(
    transaction_data: TransactionUpdate,
    account_number: str,
    uid: uuid.UUID,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an existing transaction.

    This endpoint allows the user to update an existing transaction record.
    The transaction must belong to the authenticated user. Updates are reflected in
    the database, and the account balance is adjusted based on the transaction status.

    Args:
    - transaction_data (TransactionUpdate): The updated transaction details.
    - account_number (str): The account number associated with the transaction.
    - uid (uuid.UUID): The unique identifier of the transaction to be updated.
    - bg_tasks (BackgroundTasks): For any background tasks related to transaction processing.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - BankAccountNotFound: If the bank account is not found.

    Returns:
    - A JSON response containing a success message and the updated transaction details.
    """
    bank_account = await business_service.get_bank_by_account_number(
        account_number, session
    )

    if bank_account is None:
        raise BankAccountNotFound()

    transaction: TransactionHistory = await transaction_service.update_transaction(
        uid, user, transaction_data, session
    )

    if (
        transaction.status == TransactionStatus.COMPLETED
        and transaction.transaction_type == TransactionType.TRANSFER
    ):
        bank_account.balance -= transaction.amount
    elif (
        transaction.status == TransactionStatus.FAILED
        and transaction.transaction_type == TransactionType.TRANSFER
    ):
        bank_account.balance += transaction.amount
    await session.commit()
    await session.refresh(bank_account)

    return transaction


@transaction_router.get(
    "", status_code=status.HTTP_200_OK, response_model=List[TransactionRead]
)
async def all_transactions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve all transactions for the authenticated user.

    This endpoint returns a list of all transactions associated with the authenticated user.

    Args:
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a list of all transactions for the user.
    """
    transactions = await transaction_service.get_all_transactions(session, user)

    return transactions


@transaction_router.get("/summary", status_code=status.HTTP_200_OK)
async def get_transaction_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """
    Retrieve a summary of transactions for the authenticated user, grouped by day.

    This endpoint provides a breakdown of transactions for the current user,
    grouping them by day and calculating the total debits (outgoing transactions)
    and total deposits (incoming transactions) for each day.

    Args:
        user (User): The currently authenticated user, obtained via dependency injection.
        session (AsyncSession): The database session used to interact with the database, injected via dependency.

    Returns:
        TransactionSummary: A list of daily transaction summaries, where each summary contains:
            - date (datetime): The day the transactions occurred.
            - total_debits (float): The total debit amount (outgoing transactions) for that day.
            - total_deposits (float): The total deposit amount (incoming transactions) for that day.

    Response:
        200 OK: The transaction summary is successfully returned.
        401 Unauthorized: The user is not authenticated.
        500 Internal Server Error: An error occurred while processing the request.

    Example:
        GET /transactions/summary

        Response:
        [
            {
                "date": "2024-09-19",
                "total_debits": 500.00,
                "total_deposits": 1200.00
            },
            {
                "date": "2024-09-18",
                "total_debits": 200.00,
                "total_deposits": 600.00
            }
        ]
    """
    response = await transaction_service.get_transaction_summary(user, session)
    return response


@transaction_router.get(
    "/{uid}", status_code=status.HTTP_200_OK, response_model=TransactionRead
)
async def get_transaction(
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve details of a specific transaction.

    This endpoint returns the details of a transaction identified by its unique
    identifier `uid`. The transaction must belong to the authenticated user.

    Args:
    - uid (uuid.UUID): The unique identifier of the transaction.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - TransactionNotFound: If the transaction does not exist for the authenticated user.

    Returns:
    - A JSON response containing the details of the requested transaction.
    """
    transaction: Optional[TransactionHistory] = (
        await transaction_service.get_transaction_by_uid(session, user, uid)
    )
    if transaction is None:
        raise TransactionNotFound()

    return transaction
