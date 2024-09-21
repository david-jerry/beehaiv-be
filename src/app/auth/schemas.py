from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime
from typing import Optional, List, Annotated
from enum import Enum
import uuid

from src.app.transactions.schemas import TransactionRead


# Enum for user roles
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"

    @classmethod
    def from_str(cls, role_str: str) -> "UserRole":
        try:
            return cls(role_str)
        except ValueError:
            raise ValueError(f"'{role_str}' is not a valid UserRole")


# Base schema for User
class UserBase(BaseModel):
    first_name: Optional[
        Annotated[str, constr(max_length=50)]
    ]  # First name with max length constraint
    last_name: Optional[
        Annotated[str, constr(max_length=50)]
    ]  # Last name with max length constraint
    phone_number: Optional[
        Annotated[str, constr(min_length=10, max_length=14)]
    ]  # Phone number with length constraints
    email: Optional[EmailStr]  # Email with validation
    domain: Optional[Annotated[str, constr(min_length=10, max_length=255)]]
    country: Optional[
        Annotated[str, constr(max_length=50)]
    ]  # Country with max length constraint
    role: Optional[UserRole] = UserRole.USER  # Default role set to 'USER'


# Schema for creating a new user
class UserCreate(BaseModel):
    email: EmailStr  # Email with validation
    password: str = Field(min_length=8)


# Schema for updating an existing user
class UserUpdate(UserBase):
    password: Optional[Annotated[str, constr(min_length=8)]] = (
        None  # Optional password update
    )
    transfer_pin: Optional[Annotated[str, constr(min_length=4, max_length=6)]] = (
        None  # Optional transfer pin update
    )


# Schema for reading a user's data
class UserRead(UserBase):
    uid: uuid.UUID  # Unique identifier for the user
    image: Optional[str]
    is_blocked: bool
    joined: datetime  # Timestamp when the user joined
    updated_at: datetime  # Timestamp for the last update

    verified_emails: List["VerifiedEmailRead"] = (
        []
    )  # List of verified emails related to the user
    business_profiles: List["BusinessProfileRead"] = (
        []
    )  # List of business profiles related to the user
    transactions: List["TransactionRead"] = []

    class Config:
        from_attributes = True  # Enable ORM mode for SQLModel compatibility


class UserLoginModel(BaseModel):
    email: EmailStr  # Email with validation
    password: str = Field(min_length=8)


class LoginResponseModel(BaseModel):
    access_token: str
    refresh_token: str
    user: UserRead


class UserPinModel(BaseModel):
    transfer_pin: str = Field(min_length=4, max_length=4)


class EmailModel(BaseModel):
    addresses: List[str]


class PasswordResetRequestModel(BaseModel):
    email: str


class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str


class VerifiedEmailBase(BaseModel):
    email: EmailStr


class VerifiedEmailCreate(VerifiedEmailBase):
    pass


class VerifiedEmailRead(VerifiedEmailBase):
    uid: uuid.UUID
    verified_at: datetime
    user_id: uuid.UUID

    class Config:
        from_attributes = True


# class BusinessProfileBase(BaseModel):
#     business_id: str
#     business_name: str
#     address: str
#     apartment: str
#     city: str
#     state: str
#     country: str
#     zip: str
#     phone_number: str
#     email: Optional[EmailStr] = None
#     website: Optional[str] = None
#     registration_number: Optional[str] = None
#     tax_id: Optional[str] = None
#     business_type: Optional[str] = None
#     industry: Optional[str] = None
#     founding_date: Optional[datetime] = None
#     number_of_employees: Optional[int] = None
#     annual_revenue: Optional[float] = None
#     description: Optional[str] = None


# class BusinessProfileCreate(BusinessProfileBase):
#     pass


# class BusinessProfileUpdate(BaseModel):
#     website: Optional[str] = None
#     registration_number: Optional[str] = None
#     tax_id: Optional[str] = None
#     business_type: Optional[str] = None
#     industry: Optional[str] = None
#     founding_date: Optional[datetime] = None
#     number_of_employees: Optional[int] = None
#     annual_revenue: Optional[float] = None
#     description: Optional[str] = None


# class BusinessProfileRead(BusinessProfileBase):
#     uid: uuid.UUID
#     created_at: datetime
#     updated_at: datetime

#     # relationships
#     user_id: uuid.UUID
#     bank_account: Optional["BankAccountRead"]

#     class Config:
#         from_attributes = True

class BusinessProfileBase(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[str] = None
    apartment: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    company_industry: Optional[str] = None
    asset_source_description: Optional[str] = None
    deposit_size: Optional[str] = None
    founding_date: Optional[datetime] = None
    number_of_employees: Optional[int] = None
    annual_revenue: Optional[float] = None
    description: Optional[str] = None


class BusinessProfileCreate(BusinessProfileBase):
    pass


class BusinessProfileUpdate(BaseModel):
    website: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    company_industry: Optional[str] = None
    asset_source_description: Optional[str] = None
    deposit_size: Optional[str] = None
    founding_date: Optional[datetime] = None
    number_of_employees: Optional[int] = None
    annual_revenue: Optional[float] = None
    description: Optional[str] = None


class BusinessProfileRead(BusinessProfileBase):
    uid: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # relationships
    user_id: uuid.UUID
    bank_account: Optional["BankAccountRead"]

    class Config:
        from_attributes = True


class CardCreate(BaseModel):
    card_number: str = Field(max_length=16)
    expiration_date: datetime
    cvv: str = Field(max_length=3)


class CardRead(BaseModel):
    uid: uuid.UUID
    card_number: str
    card_name: str
    expiration_date: datetime
    cvv: str = Field(max_length=3)
    business_id: uuid.UUID
    bank_id: uuid.UUID

    class Config:
        from_attributes = True


class BankAccountCreate(BaseModel):
    account_number: str = Field(max_length=20)
    account_type: str = Field(max_length=50, default="checking")
    bank_name: str = Field(max_length=100)
    sort_code: str = Field(max_length=10)
    routing_number: str = Field(max_length=9)


class BankAccountUpdate(BaseModel):
    balance: float


class BankAccountRead(BaseModel):
    uid: uuid.UUID
    account_number: str
    account_type: str
    bank_name: str
    sort_code: str
    routing_number: str
    balance: float
    business_id: uuid.UUID
    user_id: uuid.UUID

    card: Optional[CardRead] = None

    class Config:
        from_attributes = True
