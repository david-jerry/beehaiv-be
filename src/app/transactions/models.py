import uuid
from sqlalchemy import Column
from sqlmodel import Relationship, SQLModel, Field
import sqlalchemy.dialects.postgresql as pg
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from src.app.auth.models import User


# Enum for transaction type
class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"

    @classmethod
    def from_str(cls, role_str: str) -> "TransactionType":
        try:
            return cls(role_str)
        except ValueError:
            raise ValueError(f"'{role_str}' is not a valid TransactionType")


# Enum for transaction status
class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def from_str(cls, role_str: str) -> "TransactionStatus":
        try:
            return cls(role_str)
        except ValueError:
            raise ValueError(f"'{role_str}' is not a valid TransactionStatus")


# TransactionHistory model
class TransactionHistory(SQLModel, table=True):
    __tablename__ = "transactions"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional["User"] = Relationship(back_populates="transaction")

    domain: str

    amount: float
    transaction_type: TransactionType
    status: TransactionStatus = TransactionStatus.PENDING  # Default status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )
