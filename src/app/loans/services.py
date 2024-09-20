from typing import Optional
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.models import User, UserRole
from src.app.loans.models import Loan
from src.app.loans.schemas import LoanCreate, LoanUpdate
from src.errors import LoanNotFound, InsufficientPermission

from .models import LoanType, LoanDuration


class LoanService:
    async def get_all_user_loans(
        self,
        session: AsyncSession,
        user: User,
    ):
        statement = select(Loan).where(Loan.user_id == user.uid)

        result = await session.exec(statement)

        return result.all()
<<<<<<< HEAD

=======
    
>>>>>>> 2d8a31fafe3901bb51df271543a68d3c59da2542
    async def get_all_loans(
        self,
        session: AsyncSession,
        user: User,
    ):
        if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
            raise InsufficientPermission()

        statement = (
            select(Loan).where(Loan.user_id == user.uid)
            if user.role != UserRole.ADMIN
            else select(Loan)
        )
        result = await session.exec(statement)

        return result.all()

    async def get_loan_by_uid(
        self,
        session: AsyncSession,
        user: User,
        uid: uuid.UUID,
    ):
        statement = (
            select(Loan).where(Loan.user_id == user.uid).where(Loan.uid == uid)
            if user.role != UserRole.ADMIN
            else select(Loan).where(Loan.uid == uid)
        )
        result = await session.exec(statement)
        loan = result.first()
        if not loan:
            raise LoanNotFound()
        return loan

    async def create_new_loan(
        self, session: AsyncSession, user: User, loan_data: LoanCreate
    ):
        # Get the LoanType and LoanDuration from the body and validate
        loan_type = LoanType.from_str(loan_data.loan_type)
        loan_duration = LoanDuration.from_int(loan_data.duration)

        loan_data_dict = loan_data.model_dump()

        # Update the dict with validated enum values
        loan_data_dict["loan_type"] = loan_type
        loan_data_dict["duration"] = loan_duration

        loan = Loan(**loan_data_dict)
        loan.user_id = user.uid

        session.add(loan)
        await session.commit()
        await session.refresh(loan)

        return loan

    async def update_loan(
        self,
        uid: uuid.UUID,
        user: User,
        loan_data: LoanUpdate,
        session: AsyncSession,
    ):
        loan: Optional[Loan] = await self.get_loan_by_uid(session, user, uid)

        if loan is None:
            raise LoanNotFound()

        # Get the LoanType and LoanDuration from the body and validate
        loan_type = LoanType.from_str(loan_data.loan_type)
        loan_duration = LoanDuration.from_int(loan_data.duration)

        loan_data_dict = loan_data.model_dump()

        # Update the dict with validated enum values
        loan_data_dict["loan_type"] = loan_type
        loan_data_dict["duration"] = loan_duration

        for k, v in loan_data_dict.items():
            setattr(loan, k, v)

        await session.commit()
        await session.refresh(loan)
        return loan

    async def delete_loan(
        self,
        uid: uuid.UUID,
        user: User,
        session: AsyncSession,
    ):
        loan: Optional[Loan] = await self.get_loan_by_uid(session, user, uid)

        if loan is None:
            raise LoanNotFound()

        await session.delete(loan)
        await session.commit()

        return {"message": "Loan deleted successfully."}
