from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from src.app.transactions.models import TransactionStatus, TransactionType


# Base schema with common attributes
class TransactionBase(BaseModel):
    amount: float


# Schema for creating a new transaction
class TransactionCreate(TransactionBase):
    pass


# Schema for reading transaction data
class TransactionRead(TransactionBase):
    uid: UUID
    domain: str
    transaction_type: TransactionType
    status: TransactionStatus
    user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class TransactionUpdate(BaseModel):
    status: TransactionStatus


class DomesticTransferSchema(TransactionBase):
    recipient_account_number: str
    recipient_bank_name: str


class InternationalTransferSchema(TransactionBase):
    recipient_account_number: str
    recipient_bank_name: str
    sort_code: str
    routing_number: str


class WithdrawalSchema(TransactionBase):
    pass
