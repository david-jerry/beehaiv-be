from typing import List
import uuid
from fastapi import (
    APIRouter,
    Depends,
    status,
    BackgroundTasks,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.models import User
from src.app.auth.services import UserService
from src.app.auth.dependencies import get_current_user
from src.app.loans.schemas import LoanCreate, LoanUpdate, LoanRead
from src.app.loans.services import LoanService
from src.app.loans.models import Loan
from src.errors import LoanNotFound
from src.db.db import get_session

loan_router = APIRouter()
loan_service = LoanService()
user_service = UserService()


# Loan Routers
@loan_router.post("", status_code=status.HTTP_201_CREATED, response_model=LoanRead)
async def create_loan_record(
    loan_data: LoanCreate,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new loan record.

    This endpoint creates a new loan record in the database for the current authenticated
    user based on the provided loan data.

    Args:
    - loan_data (LoanCreate): The details of the loan to be created.
    - bg_tasks (BackgroundTasks): For any background tasks related to loan creation.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a success message and the created loan details.
    """
    loan: Loan = await loan_service.create_new_loan(session, user, loan_data)

    return {"message": "Loan Created!", "loan": loan.model_dump(mode="json", exclude_none=False, exclude_unset=False)}


@loan_router.patch("/{uid}", status_code=status.HTTP_200_OK, response_model=LoanRead)
async def update_loan_record(
    loan_data: LoanUpdate,
    uid: uuid.UUID,
    bg_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an existing loan record.

    This endpoint allows the user to update an existing loan record identified by its unique ID (uid).
    The updated loan details are saved to the database.

    Args:
    - loan_data (LoanUpdate): The updated loan details.
    - uid (uuid.UUID): The unique identifier of the loan to be updated.
    - bg_tasks (BackgroundTasks): For any background tasks related to loan updates.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a success message and the updated loan details.
    """
    loan: Loan = await loan_service.update_loan(uid, user, loan_data, session)

    return {"message": "Loan Updated!", "loan": loan.model_dump(mode="json", exclude_none=False, exclude_unset=False)}


@loan_router.get("", status_code=status.HTTP_200_OK, response_model=List[LoanRead])
async def get_all_loans(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve all loans for the authenticated user.

    This endpoint returns a list of all loan records associated with the authenticated user.

    Args:
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a list of all loan records for the user.
    """
    loans: List[Loan] = await loan_service.get_all_loans(session, user)

    return {"message": "Ok!", "loans": loans}


@loan_router.get("/user-loans", status_code=status.HTTP_200_OK, response_model=List[LoanRead])
async def get_user_loans(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve all loans for the authenticated user.

    This endpoint returns a list of all loan records associated with the authenticated user.

    Args:
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a list of all loan records for the user.
    """
    loans: List[Loan] = await loan_service.get_all_user_loans(session, user)

    return {"message": "Ok!", "loans": loans}


@loan_router.get("/{uid}", status_code=status.HTTP_200_OK, response_model=LoanRead)
async def get_loan_by_uid(
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve a specific loan record by its unique ID.

    This endpoint returns the details of a loan identified by its unique identifier (uid).
    The loan must belong to the authenticated user.

    Args:
    - uid (uuid.UUID): The unique identifier of the loan.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Raises:
    - LoanNotFound: If the loan with the specified uid does not exist for the user.

    Returns:
    - A JSON response containing the details of the requested loan.
    """
    loan = await loan_service.get_loan_by_uid(session, user, uid)
    if loan is None:
        raise LoanNotFound()

    return {"message": "Ok!", "loan": loan.model_dump(mode="json", exclude_none=False, exclude_unset=False)}


@loan_router.delete("/{uid}", status_code=status.HTTP_200_OK)
async def delete_loan_record(
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a loan record by its unique ID.

    This endpoint deletes a loan record identified by its unique identifier (uid) if the loan
    belongs to the authenticated user.

    Args:
    - uid (uuid.UUID): The unique identifier of the loan to be deleted.
    - user (User): The current authenticated user.
    - session (AsyncSession): The current database session.

    Returns:
    - A JSON response containing a success message confirming the loan has been deleted.
    """
    loan = await loan_service.get_loan_by_uid(session, user, uid)
    if loan is None:
        raise LoanNotFound()

    await loan_service.delete_loan(uid, user, session)

    return {"message": "Loan Deleted Successfully!"}
