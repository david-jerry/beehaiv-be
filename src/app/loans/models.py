import uuid
from sqlalchemy import Column
from sqlmodel import Relationship, SQLModel, Field
import sqlalchemy.dialects.postgresql as pg
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from src.app.auth.models import User


# Enum for loan duration in months
class LoanDuration(int, Enum):
    THREE_MONTHS = 3
    SIX_MONTHS = 6
    TWELVE_MONTHS = 12
    TWENTY_FOUR_MONTHS = 24
    FORTY_EIGHT_MONTHS = 48
    SIXTY_MONTHS = 60  # 5 years
    ONE_HUNDRED_TWENTY_MONTHS = 120  # 10 years

    @classmethod
    def from_int(cls, duration: int) -> "LoanDuration":
        try:
            return cls(duration)
        except ValueError:
            raise ValueError(f"'{duration}' is not a valid LoanDuration")


# Enum for loan types
class LoanType(str, Enum):
    STARTUP = "startup"
    OFFICE = "office"
    RESEARCH = "research"

    @classmethod
    def from_str(cls, loan_type_str: str) -> "LoanType":
        try:
            return cls(loan_type_str)
        except ValueError:
            raise ValueError(f"'{loan_type_str}' is not a valid LoanType")


# Loan model
class Loan(SQLModel, table=True):
    __tablename__ = "loans"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional["User"] = Relationship(back_populates="loans")

    loan_type: LoanType
    principal_amount: float
    interest_rate: float
    duration: LoanDuration
    initial_deposit: float  # Calculated initial deposit
    repayment_schedule: str  # Description or format of the repayment schedule

    # This is a computed field based on principal_amount, interest_rate, and duration
    total_repayment: float = Field(default=0.0, nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )

    def calculate_total_repayment(self):
        # Simple interest calculation for the total repayment
        # Total Repayment = Principal + (Principal * Interest Rate * Duration in Years)
        duration_in_years = self.duration / 12
        interest = (
            self.principal_amount * (self.interest_rate / 100) * duration_in_years
        )
        self.total_repayment = self.principal_amount + interest

    def calculate_initial_deposit(self):
        # Assuming an initial deposit is a percentage of the principal amount
        # For example, 10% of the principal amount
        self.initial_deposit = self.principal_amount * 0.10


class MortgageAssetRange(str, Enum):
    LESS_THAN_ONE_M = "Less than $1M"
    ONE_TO_FIVE_M = "$1 - 5M"
    FIVE_TO_TEN_M = "$5 - 10M"
    TEN_M_PLUS = "$10M +"

    @classmethod
    def from_int(cls, assets: str) -> "LoanDuration":
        try:
            return cls(assets)
        except ValueError:
            raise ValueError(f"'{assets}' is not a valid MortgageAssetRange")


class FounderMortgage(SQLModel, table=True):
    __tablename__ = "founders_mortgages"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    company_name: str
    email: str
    phone_number: str
    range_of_total_company_assets: MortgageAssetRange
    how_you_heard_about_us: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )
