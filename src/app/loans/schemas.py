import uuid
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

# Reuse the LoanType and LoanDuration enums from the original model
from .models import LoanType, LoanDuration, MortgageAssetRange


# Create Schema
class LoanCreate(BaseModel):
    user_id: UUID
    loan_type: str
    principal_amount: float
    interest_rate: float
    duration: int
    repayment_schedule: str

    class Config:
        schema_extra = {
            "example": {
                "user_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                "loan_type": "startup",
                "principal_amount": 50000.0,
                "interest_rate": 5.5,
                "duration": 12,
                "repayment_schedule": "monthly",
            }
        }


# Read Schema
class LoanRead(BaseModel):
    uid: UUID
    user_id: Optional[UUID]
    loan_type: LoanType
    principal_amount: float
    interest_rate: float
    duration: LoanDuration
    initial_deposit: float
    repayment_schedule: str
    total_repayment: float
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "user_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                "loan_type": "office",
                "principal_amount": 100000.0,
                "interest_rate": 4.0,
                "duration": 24,
                "initial_deposit": 10000.0,
                "repayment_schedule": "quarterly",
                "total_repayment": 104000.0,
                "created_at": "2024-09-17T10:00:00",
                "updated_at": "2024-09-17T10:00:00",
            }
        }


# Update Schema (for partial updates)
class LoanUpdate(BaseModel):
    loan_type: Optional[str]
    principal_amount: Optional[float]
    interest_rate: Optional[float]
    duration: Optional[int]
    repayment_schedule: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "loan_type": "research",
                "principal_amount": 75000.0,
                "interest_rate": 3.8,
                "duration": 48,
                "repayment_schedule": "annually",
            }
        }


# Pydantic schema for FounderMortgage
class FounderMortgageBase(BaseModel):
    company_name: str
    email: EmailStr
    phone_number: str
    range_of_total_company_assets: str
    how_you_heard_about_us: str


# Schema for creating a new FounderMortgage entry
class FounderMortgageCreate(FounderMortgageBase):
    pass


# Schema for reading a FounderMortgage entry
class FounderMortgageRead(FounderMortgageBase):
    uid: uuid.UUID 
    created_at: datetime
    updated_at: datetime


# Schema for updating a FounderMortgage entry
class FounderMortgageUpdate(BaseModel):
    company_name: Optional[str] = Field(
        None, example="Tech Ventures", description="Updated company name"
    )
    email: Optional[EmailStr] = Field(
        None, example="founder@techventures.com", description="Updated email address"
    )
    phone_number: Optional[str] = Field(
        None, example="+1234567890", description="Updated phone number"
    )
    range_of_total_company_assets: Optional[MortgageAssetRange] = Field(
        None,
        example=MortgageAssetRange.LESS_THAN_ONE_M,
        description="Updated range of total company assets",
    )
    how_you_heard_about_us: Optional[str] = Field(
        None, example="Referral", description="Updated referral information"
    )
