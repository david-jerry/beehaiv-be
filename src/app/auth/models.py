from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
import sqlalchemy.dialects.postgresql as pg
import uuid
from typing import List, Optional

from src.app.transactions.models import TransactionHistory
from src.app.loans.models import Loan


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


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str] = Field(nullable=True, max_length=16, unique=True)
    email: str = Field(nullable=False, unique=True, index=True, max_length=255)
    image: Optional[str] = Field(default=None)
    domain: str = Field(nullable=False, unique=False, index=True, max_length=255)
    ip_address: Optional[str]
    address: Optional[str] = Field(nullable=True, max_length=255)  # Business address
    apartment: Optional[str] = Field(nullable=True, max_length=255)  # Business address
    city: Optional[str] = Field(nullable=True, max_length=255)
    state: Optional[str] = Field(nullable=True, max_length=255)
    country: Optional[str] = Field(nullable=True, max_length=255)
    zip: Optional[str] = Field(nullable=True, max_length=7)
    password_hash: str = Field(nullable=False)  # Store hashed passwords
    transfer_pin_hash: Optional[str] = Field(
        default="0000"
    )  # Store hashed transfer pins
    role: UserRole = Field(default=UserRole.USER)  # Default role as 'user'
    joined: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )
    is_blocked: bool = Field(default=False)

    # Relationships
    verified_emails: List["VerifiedEmail"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    business_profiles: List["BusinessProfile"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    bank_accounts: List["BankAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    transactions: List["TransactionHistory"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    loans: List["Loan"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class VerifiedEmail(SQLModel, table=True):
    __tablename__ = "verified_emails"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    email: str = Field(nullable=False, unique=True, index=True, max_length=100)
    verified_at: datetime = Field(default_factory=datetime.utcnow)

    # Foreign Key to User
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="verified_emails")

    def __repr__(self) -> str:
        return f"<VerifiedEmail {self.email}>"


class BusinessProfile(SQLModel, table=True):
    __tablename__ = "business_profiles"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    business_id: Optional[str] = Field(
        nullable=True, unique=True, index=True, max_length=50
    )  # Unique business identifier
    business_name: Optional[str] = Field(nullable=True, unique=True, max_length=255)
    deposit_size: Optional[str] = Field(nullable=True, max_length=255)
    website: Optional[str] = Field(default=None, unique=True, max_length=255)  # Business website URL
    registration_number: Optional[str] = Field(
        default=None, max_length=100
    )  # Business registration number
    tax_id: Optional[str] = Field(default=None, unique=True, max_length=100)  # Tax ID or VAT number
    business_type: Optional[str] = Field(
        default=None, max_length=50
    )  # Type of business (e.g., LLC, Corporation)
    company_industry: Optional[str] = Field(
        default=None, max_length=255
    )  # Industry or sector in which the business operates
    asset_source_description: Optional[str] = Field(
        default=None, max_length=255
    )  # Industry or sector in which the business operates
    deposit_size: Optional[str] = Field(
        default=None, max_length=255
    )  # Industry or sector in which the business operates
    founding_date: Optional[datetime] = Field(
        default=None
    )  # Date when the business was founded
    number_of_employees: Optional[int] = Field(default=None)  # Number of employees
    annual_revenue: Optional[float] = Field(
        default=None
    )  # Annual revenue in USD or other currency
    description: Optional[str] = Field(
        default=None, max_length=255
    )  # Brief description of the business
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.now),
    )

    # Foreign Key to User
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="business_profiles")

    # Relationship to BankAccount
    bank_account: Optional["BankAccount"] = Relationship(
        back_populates="business_profile"
    )

    def __repr__(self) -> str:
        return f"<BusinessProfile {self.business_name} - {self.business_id}>"


class BankAccount(SQLModel, table=True):
    __tablename__ = "bank_accounts"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    account_number: Optional[str] = Field(nullable=True, unique=True, max_length=20)
    account_type: Optional[str] = Field(
        nullable=True, max_length=50, default="checking"
    )  # E.g., "checking", "savings"
    balance: float = Field(default=0.0)  # Initial balance
    bank_name: Optional[str] = Field(nullable=True, max_length=255)
    sort_code: Optional[str] = Field(nullable=True, max_length=10)
    routing_number: Optional[str] = Field(
        nullable=True, max_length=9
    )  # US-based routing number (9 digits)

    # Foreign Key to BusinessProfile
    business_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="business_profiles.uid"
    )
    business_profile: Optional[BusinessProfile] = Relationship(
        back_populates="bank_account"
    )
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="bank_accounts")

    card: Optional["Card"] = Relationship(back_populates="bank_account", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})

    def __repr__(self) -> str:
        return f"<BankAccount {self.account_number}>"


class Card(SQLModel, table=True):
    __tablename__ = "cards"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    card_number: str = Field(nullable=False, unique=True, max_length=16)
    card_name: str = Field(nullable=False, unique=False, max_length=255)
    expiration_date: datetime = Field(nullable=False)
    cvv: str = Field(nullable=False, max_length=3)
    issued_at: datetime = Field(default_factory=datetime.utcnow)

    pin: str = Field(nullable=False, max_length=4)

    bank_id: uuid.UUID = Field(default=None, foreign_key="bank_accounts.uid")
    bank_account: Optional[BankAccount] = Relationship(back_populates="card")

    def __repr__(self) -> str:
        return f"<Card {self.card_number}>"
