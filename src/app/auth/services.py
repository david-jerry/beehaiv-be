import random
import uuid

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.auth.mails import send_card_pin, send_new_bank_account_details
from src.db.cloudinary import upload_image
from src.db.redis import store_allowed_ip
from src.errors import BankAccountNotFound, InsufficientPermission
from src.utils.logger import LOGGER

from .models import BankAccount, Card, User, BusinessProfile, UserRole, VerifiedEmail

from .schemas import (
    UserCreate,
    BusinessProfileCreate,
    BusinessProfileUpdate,
)

from .utils import generate_passwd_hash, send_verification_code


class UserService:
    async def get_all_users(self, user: User, domain: str, session: AsyncSession):
        if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
            raise InsufficientPermission()

        statement = (
            select(User)
            .where(User.domain == domain)
            .options(
                selectinload(User.verified_emails),
                selectinload(User.business_profiles),
                # selectinload(User.bank_accounts),
                selectinload(User.transactions),
                selectinload(User.loans),
            )
            if user.role == UserRole.MANAGER
            else select(User).options(
                selectinload(User.verified_emails),
                selectinload(User.business_profiles),
                # selectinload(User.bank_accounts),
                selectinload(User.transactions),
                selectinload(User.loans),
            )
        )

        result = await session.exec(statement)

        return result.all()

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = (
            select(User)
            .where(User.email == email)
            .options(
                selectinload(User.verified_emails),
                selectinload(User.business_profiles),
                # selectinload(User.bank_accounts),
                selectinload(User.transactions),
                selectinload(User.loans),
            )
        )

        result = await session.exec(statement)

        user = result.first()

        return user

    async def get_user_by_uid(self, uid: UUID, session: AsyncSession):
        statement = (
            select(User)
            .where(User.uid == uid)
            .options(
                selectinload(User.verified_emails),
                selectinload(User.business_profiles),
                # selectinload(User.bank_accounts),
                selectinload(User.transactions),
                selectinload(User.loans),
            )
        )

        result = await session.exec(statement)

        user = result.first()

        return user

    async def user_exists(self, email, session: AsyncSession):
        user = await self.get_user_by_email(email, session)

        return True if user is not None else False

    async def create_user(
        self,
        user_data: UserCreate,
        ip_address: str,
        role: Optional[str],
        domain: str,
        session: AsyncSession,
    ):
        # Convert the user_data to a dictionary
        user_data_dict = user_data.model_dump()

        # Convert role string to UserRole enum
        role_str = (
            role if role is not None else "user"
        )  # Default to "user" if no role is provided
        LOGGER.debug(f"Registration Role: {role_str}")
        role_enum = UserRole.from_str(
            role_str
        )  # Convert to upper case to match the enum values

        # Create a new user with the given data
        new_user = User(**user_data_dict)
        new_user.domain = domain
        new_user.ip_address = ip_address
        new_user.password_hash = generate_passwd_hash(user_data_dict["password"])
        new_user.role = role_enum  # Set the role using the UserRole enum
        new_user.transfer_pin_hash = generate_passwd_hash(
            str(1234)
        )

        # Add and commit the new user to the session
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        # Send verification email after the user is created
        # Use the user's domain for sending the verification email
        code = await send_verification_code(new_user, new_user.domain)

        return code, new_user

    async def save_verified_email(
        self, user: User, email_data: str, session: AsyncSession
    ):
        new_email = VerifiedEmail(email=email_data)
        new_email.user_id = user.uid
        new_email.user = user

        session.add(new_email)
        await session.commit()

        user.verified_emails.append(new_email)
        await session.commit()
        await session.refresh(user)
        return user

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        if user_data.get("transfer_pin"):
            user.transfer_pin_hash = generate_passwd_hash(user_data["transfer_pin"])
        elif user_data.get("password"):
            user.password_hash = generate_passwd_hash(user_data["password"])
        else:
            for k, v in user_data.items():
                setattr(user, k, v)

        await session.commit()
        await session.refresh(user)
        return user

    async def update_image(self, user: User, image: UploadFile, session: AsyncSession):

        user.image = await upload_image(image)

        await session.commit()
        await session.refresh(user)

        return user

    async def block_user(self, user: User, status: bool, session: AsyncSession):

        if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
            raise HTTPException(
                status_code=403,
                detail="You do not have adequate permission to perform this actions.",
            )

        user.is_blocked = status

        await session.commit()
        await session.refresh(user)

        return user

    async def add_allowed_ip(self, user: User, ip_address: str):
        await store_allowed_ip(user.uid, ip_address)
        return user


class BusinessService:
    async def create_business(
        self, user: User, business_data: BusinessProfileCreate, session: AsyncSession
    ):
        business_data_dict = business_data.model_dump()

        new_business = BusinessProfile(**business_data_dict, user_id=user.uid)
        session.add(new_business)
        await session.commit()
        await session.refresh(new_business)

        # Create and link a Card
        card = await self.create_card(new_business, session)
        new_business.card = card

        # Create and link a BankAccount
        bank_account = await self.create_bank_account(new_business, session)
        new_business.bank_account = bank_account

        # Create and link a user
        new_business.user = user
        new_business.user_id = user.uid

        await session.commit()
        await session.refresh(new_business)

        user.business_profiles.append(new_business)
        # user.bank_account = bank_account

        await session.commit()
        await session.refresh(user)

        return new_business

    async def create_card(
        self, business_profile: BusinessProfile, session: AsyncSession
    ) -> Card:
        card_number = self.generate_debit_card_number()
        expiration_date = datetime.utcnow() + timedelta(
            days=365 * 3
        )  # 3 years validity
        cvv = f"{random.randint(100, 999)}"  # Random CVV
        pin = f"{random.randint(1000, 9999)}"

        card = Card(
            card_number=card_number,
            expiration_date=expiration_date,
            card_name=f"{business_profile.user.first_name} {business_profile.user.last_name}",
            cvv=cvv,
            pin=pin,
            business_id=business_profile.uid,
            business_profile=business_profile,
            bank_id=business_profile.bank_account.uid,
            bank_account=business_profile.bank_account,
        )

        session.add(card)
        await session.commit()
        await session.refresh(card)

        await send_card_pin(card=card, user=business_profile.user)

        return card

    async def create_bank_account(
        self, business_profile: BusinessProfile, session: AsyncSession
    ) -> BankAccount:
        account_number = self.generate_bank_account_number()
        account_type = "checking"  # Default to checking account
        user = business_profile.user

        bank_account = BankAccount(
            account_number=account_number,
            account_type=account_type,
            balance=0.0,
            business_id=business_profile.uid,
            business_profile=business_profile,
            user=user,
            user_id=user.uid,
            routing_number="026009593",
            sort_code="165050",
        )

        session.add(bank_account)
        await session.commit()
        await session.refresh(bank_account)

        await send_new_bank_account_details(
            bank=bank_account, user=business_profile.user
        )

        return bank_account

    async def get_business_by_id(self, business_id: str, session: AsyncSession):
        selection = (
            select(BusinessProfile)
            .where(BusinessProfile.business_id == business_id)
            .options(
                selectinload(BusinessProfile.bank_account),
                selectinload(BusinessProfile.card),
            )
        )
        result = await session.exec(selection)
        return result.first()

    async def get_bank_by_account_number(
        self, account_number: str, session: AsyncSession
    ):
        selection = (
            select(BankAccount)
            .where(BankAccount.account_number == account_number)
            .options(
                selectinload(BankAccount.business_profile),
                selectinload(BankAccount.card),
            )
        )
        result = await session.exec(selection)
        return result.first()

    async def get_card_by_uid(self, card_id: uuid.UUID, session: AsyncSession):
        selection = (
            select(Card)
            .where(Card.uid == card_id)
            .options(
                selectinload(Card.business_profile),
                selectinload(Card.bank_account),
            )
        )
        result = await session.exec(selection)
        return result.first()

    async def update_business(
        self,
        business: BusinessProfile,
        business_data: BusinessProfileUpdate,
        session: AsyncSession,
    ):
        business_data_dict = business_data.model_dump()

        for k, v in business_data_dict.items():
            setattr(business, k, v)

        await session.commit()
        await session.refresh(business)

        return business

    async def delete_business(self, business: BusinessProfile, session: AsyncSession):
        await session.delete(business)
        await session.commit()

    async def update_card_expiry(self, card: Card, session: AsyncSession):
        # Extend the card expiration date by 3 years
        card.expiration_date = datetime.utcnow() + timedelta(days=365 * 3)
        await session.commit()
        await session.refresh(card)
        return card

    async def delete_card(self, card: Card, session: AsyncSession):
        await session.delete(card)
        await session.commit()

    async def delete_bank_account(
        self, bank_account: BankAccount, session: AsyncSession
    ):
        await session.delete(bank_account)
        await session.commit()

    async def get_user_account_balance(
        self, session: AsyncSession, user: User, account_number: str
    ) -> float:
        selection = (
            select(BankAccount)
            .where(BankAccount.account_number == account_number)
            .where(BankAccount.user_id == user.uid)
        )
        result = await session.exec(selection)
        bankAccount = result.first()

        # Fetch the user's bank account balance
        if not bankAccount:
            raise BankAccountNotFound()

        return bankAccount.balance

    async def update_account_balance(
        self, session: AsyncSession, account: BankAccount, new_balance: float
    ):
        account.balance = new_balance
        await session.commit()
        await session.refresh(account)
        return account

    def generate_debit_card_number(self):
        # Dummy debit card number generator (replace with actual implementation)
        start_digits = random.choice(["51", "52", "53", "54", "55"])
        return f"{start_digits}{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}"

    def generate_bank_account_number(self):
        # Dummy bank account number generator (replace with actual implementation)
        return f"{random.randint(1000000000, 9999999999)}"  # 10-digit account number
