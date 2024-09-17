from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from src.app.auth.models import User
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

    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 100.0,
                "transaction_type": "transfer",
                "recipient_account_number": "9876543210",
                "recipient_bank_name": "Local Bank",
            }
        }

class InternationalTransferSchema(TransactionBase):
    recipient_account_number: str
    recipient_bank_name: str
    sort_code: str
    routing_number: str

    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 200.0,
                "transaction_type": "transfer",
                "recipient_account_number": "9876543210",
                "recipient_bank_name": "International Bank",
                "sort_code": "123456",
                "routing_number": "987654321"
            }
        }

class WithdrawalSchema(TransactionBase):
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 50.0,
                "transaction_type": "withdrawal",
            }
        }
