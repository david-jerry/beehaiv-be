from datetime import datetime, timedelta

from typing import Optional, List
import uuid
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    status,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.models import User, UserRole
from src.db.redis import add_jti_to_blocklist, block_ip_attempts
from src.utils.logger import LOGGER

from .dependencies import (
    get_current_user,
    RoleChecker,
    RefreshTokenBearer,
    AccessTokenBearer,
)
from .schemas import (
    UserCreate,
    UserLoginModel,
    UserPinModel,
    UserRead,
    PasswordResetConfirmModel,
    PasswordResetRequestModel,
    BusinessProfileRead,
    BusinessProfileCreate,
    BusinessProfileUpdate,
    CardRead,
    BankAccountUpdate,
    BankAccountRead,
)
from .services import UserService, BusinessService
from .utils import (
    create_access_token,
    send_password_reset_code,
    send_verification_code,
    verify_password,
    decode_url_safe_token,
    generate_passwd_hash,
)
from src.errors import (
    DebitCardNotFound,
    InvalidCredentials,
    InvalidToken,
    InsufficientPermission,
    InvalidTransactionPin,
    UserAlreadyExists,
    UserBlocked,
    UserNotFound,
)
from src.db.db import get_session

auth_router = APIRouter()
user_router = APIRouter()
business_router = APIRouter()
card_router = APIRouter()
bank_router = APIRouter()

user_service = UserService()
business_service = BusinessService()

role_checker = RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.USER])
admin_checker = RoleChecker([UserRole.ADMIN, UserRole.MANAGER])

REFRESH_TOKEN_EXPIRY = 2


# Auth Routers
@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_Account(
    user_data: UserCreate,
    domain: str,
    ip_address: str,
    bg_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new user account with the provided details.

    Args:
        user_data (UserCreate): User account information.
        domain (str): Domain for the user.
        bg_tasks (BackgroundTasks): Background task manager for async operations.
        session (AsyncSession): Database session dependency.

    Returns:
        dict: A message indicating the account creation and a verification code.
    """
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    code, user = await user_service.create_user(
        user_data=user_data,
        domain=domain,
        ip_address=ip_address,
        role="user",
        session=session,
    )

    return {
        "message": "Account Created! Check email to verify your account",
        "code": code,
        "user": user,
    }


@auth_router.post("/create-superuser", status_code=status.HTTP_201_CREATED)
async def create_super_user_Account(
    user_data: UserCreate,
    domain: str,
    ip_address: str,
    bg_tasks: BackgroundTasks,
    role: str = "admin",
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new superuser account with the provided details.

    Args:
        user_data (UserCreate): Superuser account information.
        domain (str): Domain for the user.
        bg_tasks (BackgroundTasks): Background task manager for async operations.
        role (str): User role for the superuser account.
        session (AsyncSession): Database session dependency.

    Returns:
        dict: A message indicating the superuser account creation and a verification code.
    """
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    code, user = await user_service.create_user(
        user_data=user_data,
        domain=domain,
        ip_address=ip_address,
        role=role,
        session=session,
    )

    return {
        "message": "Superuser Account Created! Check email to verify your account",
        "code": code,
        "user": user,
    }


@auth_router.get("/verify-email/{token}", status_code=status.HTTP_200_OK)
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    """
    Verify the user's email address using the provided token.

    Args:
        token (str): Verification token sent to the user.
        session (AsyncSession): Database session dependency.

    Returns:
        JSONResponse: A response indicating whether the email verification was successful.
    """
    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise UserNotFound()

        await user_service.save_verified_email(
            user=user, email_data=user_email, session=session
        )

        return (
            {
                "message": "Account verified successfully. Login with your credentials",
                "status": status.HTTP_200_OK,
                "user": user,
            },
        )

    return JSONResponse(
        content={"message": "Error occurred during verification"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@auth_router.post("/transfer-pin", status_code=status.HTTP_200_OK)
async def verify_transfer_pin(
    ip_address: str,
    pin_data: UserPinModel,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Verify the user's transfer PIN.

    Args:
        pin_data (UserPinModel): Transfer PIN provided by the user.
        user (User): The currently authenticated user.

    Returns:
        dict: A message indicating whether the transfer PIN is valid.
    """
    pin = pin_data.transfer_pin

    if user is not None:
        should_block_user = await block_ip_attempts(user, ip_address)
        if should_block_user:
            await user_service.block_user(user, True, session)
            raise UserBlocked()
        pin_valid = verify_password(pin, user.transfer_pin_hash)
        LOGGER.info(f"Is Pin valid: {pin_valid}")
        if pin_valid:
            return {"message": "Transfer pin is correct", "valid": True}
        raise InvalidTransactionPin()

    raise UserNotFound()


@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login_users(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    """
    Log in a user using email and password.

    Args:
        login_data (UserLoginModel): User login credentials.
        session (AsyncSession): Database session dependency.

    Returns:
        JSONResponse: A response with the access token, refresh token, and user details.
    """
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is not None:
        if len(user.verified_emails) < 1:
            code = await send_verification_code(user, user.domain)
            return {
                "message": """
Please check your email, a new verification code has been sent to you
                """,
                "code": code,
                "user": user,
            }

        password_valid = verify_password(password, user.password_hash)
        if password_valid:
            access_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                }
            )
            refresh_token = create_access_token(
                user_data={"email": user.email, "user_uid": str(user.uid)},
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
            )

            return {
                "message": "Login successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user,
            }

    raise InvalidCredentials()


@auth_router.get("/refresh-token", status_code=status.HTTP_200_OK)
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    """
    Get a new access token using a valid refresh token.

    Args:
        token_details (dict): Details of the provided refresh token.

    Returns:
        JSONResponse: A response with the new access token.
    """
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(user_data=token_details["user"])
        return JSONResponse(content={"access_token": new_access_token})

    raise InvalidToken


@auth_router.get("/logout", status_code=status.HTTP_200_OK)
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    """
    Revoke the current access token, logging the user out.

    Args:
        token_details (dict): Details of the token to be revoked.

    Returns:
        JSONResponse: A response indicating that the token was revoked and the user was logged out.
    """
    jti = token_details["jti"]
    await add_jti_to_blocklist(jti)

    return JSONResponse(
        content={"message": "Logged Out Successfully"}, status_code=status.HTTP_200_OK
    )


@auth_router.post("/password-reset-request", status_code=status.HTTP_200_OK)
async def password_reset_request(
    domain: str,
    email_data: PasswordResetRequestModel,
    session: AsyncSession = Depends(get_session),
):
    """
    Request a password reset by providing an email address.

    Args:
        domain (str): The domain for the reset email.
        email_data (PasswordResetRequestModel): The email address to send the reset instructions to.
        session (AsyncSession): Database session dependency.

    Returns:
        JSONResponse: A response with the password reset code.
    """
    email = email_data.email
    user = await user_service.get_user_by_email(email, session)
    code = await send_password_reset_code(user, domain)
    return JSONResponse(
        content={
            "message": "Please check your email for instructions to reset your password",
            "password_reset_code": code,
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/password-reset-confirm/{token}", status_code=status.HTTP_200_OK)
async def reset_account_password(
    token: str,
    passwords: PasswordResetConfirmModel,
    session: AsyncSession = Depends(get_session),
):
    """
    Confirm a password reset using the provided token and new password.

    Args:
        token (str): The password reset token.
        passwords (PasswordResetConfirmModel): The new and confirmed password.
        session (AsyncSession): Database session dependency.

    Returns:
        JSONResponse: A response indicating whether the password reset was successful.
    """
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )

    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise UserNotFound()

        passwd_hash = generate_passwd_hash(new_password)
        await user_service.update_user(user, {"password_hash": passwd_hash}, session)

        return JSONResponse(
            content={"message": "Password reset Successfully"},
            status_code=status.HTTP_200_OK,
        )

    return JSONResponse(
        content={"message": "Error occurred during password reset."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# User Routes
@user_router.get("/me", response_model=UserRead)
async def get_current_active_user(
    user: User = Depends(get_current_user), _: bool = Depends(role_checker)
):
    """
    Get the currently authenticated user's details.

    Args:
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.

    Returns:
        UserRead: The current user's details.
    """
    return user


@user_router.get("/me/request-new-verification", status_code=status.HTTP_200_OK)
async def resend_verification_code_view(user: User = Depends(get_current_user)):
    """
    Resend a new verification code to the current user's email.

    This view generates and sends a new verification code to the email
    address associated with the current user, based on the domain the user is
    registered under.

    Args:
        user (User): The current authenticated user, retrieved via the
                     `get_current_user` dependency.

    Returns:
        dict: A dictionary containing:
              - "message" (str): A message indicating the verification code has been sent.
              - "code" (str): The newly generated verification code.

    Status Code:
        HTTP_200_OK: The request was successful and a new verification code was sent.
    """
    code = await send_verification_code(user, user.domain)

    return {"message": "Verification code sent", "code": code}


@user_router.get("/{uid}", response_model=UserRead)
async def get_current_user_by_uid(
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    _: bool = Depends(role_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Get user details by their unique ID.

    Args:
        uid (uuid.UUID): The unique ID of the user.
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        UserRead: The user's details.
    """
    if user.role in (UserRole.ADMIN, UserRole.MANAGER) or user.uid == uid:
        user = await user_service.get_user_by_uid(uid, session)
        return user
    raise InsufficientPermission()


@user_router.patch("/{uid}", response_model=UserRead)
async def update_user_by_uid(
    update_data: dict,
    uid: uuid.UUID,
    user: User = Depends(get_current_user),
    _: bool = Depends(role_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user details by their unique ID.

    Args:
        update_data (dict): The data to update.
        uid (uuid.UUID): The unique ID of the user.
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        UserRead: The updated user's details.
    """
    if user.role in (UserRole.ADMIN, UserRole.MANAGER) or user.uid == uid:
        user = await user_service.update_user(user, update_data, session)
        return user
    raise InsufficientPermission()


@user_router.get("", response_model=List[UserRead])
async def get_users(
    domain: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a list of all users in the specified domain.

    Args:
        domain (str): The domain to filter users by.
        user (User): The currently authenticated user.
        session (AsyncSession): Database session dependency.

    Returns:
        List[UserRead]: A list of users in the domain.
    """
    if user.domain != domain:
        raise InsufficientPermission()
    users = await user_service.get_all_users(user, domain, session)
    return users


@user_router.patch("/me/photo", response_model=UserRead)
async def update_user_photo(
    image: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update the profile photo of the currently authenticated user.

    Args:
        image (UploadFile): The new profile photo.
        current_user (User): The currently authenticated user.
        session (AsyncSession): Database session dependency.

    Returns:
        UserRead: The updated user's details.
    """
    updated_user = await user_service.update_image(current_user, image, session)
    return updated_user


@user_router.patch("/{uid}/block", response_model=UserRead)
async def block_user(
    uid: uuid.UUID,
    block: bool,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(role_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Block or unblock a user by their unique ID.

    Args:
        uid (uuid.UUID): The unique ID of the user to block or unblock.
        block (bool): Whether to block or unblock the user.
        current_user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        UserRead: The updated user's details.
    """
    user_to_block = await user_service.get_user_by_uid(uid, session)
    if not user_to_block:
        raise UserNotFound()

    blocked_user = await user_service.block_user(user_to_block, block, session)
    return blocked_user


# Business Routes
@business_router.post("", response_model=BusinessProfileRead)
async def create_new_business(
    business_data: BusinessProfileCreate,
    user_id: Optional[uuid.UUID],
    user: User = Depends(get_current_user),
    _: bool = Depends(admin_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new business profile.

    Args:
        business_data (BusinessProfileCreate): Information for the new business.
        user_id (Optional[uuid.UUID]): The ID of the user associated with the business (if any).
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        BusinessProfileRead: The newly created business profile.
    """
    business_user = user
    if user_id is not None:
        business_user = await user_service.get_user_by_uid(user_id, session)
        if business_user is None:
            raise UserNotFound()
    business = await business_service.create_business(
        business_user, business_data, session
    )
    return business


@business_router.get("/{business_id}", response_model=Optional[BusinessProfileRead])
async def get_business(
    business_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get details of a business profile by its ID.

    Args:
        business_id (str): The ID of the business.
        user (User): The currently authenticated user.
        session (AsyncSession): Database session dependency.

    Returns:
        Optional[BusinessProfileRead]: The business profile details or None if not found.
    """
    business = await business_service.get_business_by_id(business_id, session)
    return business


@business_router.patch("/{business_id}", response_model=Optional[BusinessProfileRead])
async def update_existing_business(
    business_id: str,
    update_data: BusinessProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an existing business profile by its ID.

    Args:
        business_id (str): The ID of the business.
        update_data (BusinessProfileUpdate): The data to update.
        user (User): The currently authenticated user.
        session (AsyncSession): Database session dependency.

    Returns:
        Optional[BusinessProfileRead]: The updated business profile details or None if not found.
    """
    existing_business = await business_service.get_business_by_id(business_id, session)
    business = await business_service.update_business(
        existing_business, update_data, session
    )
    return business


# Card Routes
@card_router.patch("/{card_id}", response_model=Optional[CardRead])
async def update_existing_card_expiry_date(
    card_id: str,
    user: User = Depends(get_current_user),
    _: bool = Depends(admin_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Update the expiry date of a card by its ID.

    Args:
        card_id (str): The ID of the card.
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        Optional[CardRead]: The updated card details or None if not found.
    """
    if user.role == UserRole.USER:
        raise InsufficientPermission()

    card = await business_service.get_card_by_uid(card_id, session)
    if card is None:
        raise DebitCardNotFound()

    card = await business_service.update_card_expiry(card, session)
    return card


# Bank Account Routes
@bank_router.patch("/{account_number}", response_model=Optional[BankAccountRead])
async def update_bank_account_balance(
    account_number: str,
    update_data: BankAccountUpdate,
    user: User = Depends(get_current_user),
    _: bool = Depends(admin_checker),
    session: AsyncSession = Depends(get_session),
):
    """
    Update the balance of a bank account by its account number.

    Args:
        account_number (str): The account number of the bank account.
        update_data (BankAccountUpdate): The data to update.
        user (User): The currently authenticated user.
        _: bool: Role check to ensure the user has the required permissions.
        session (AsyncSession): Database session dependency.

    Returns:
        Optional[BankAccountRead]: The updated bank account details or None if not found.
    """
    if user.role == UserRole.USER:
        raise InsufficientPermission()

    bank = await business_service.get_bank_by_account_number(account_number, session)
    if bank is None:
        raise DebitCardNotFound()

    bank = await business_service.update_account_balance(
        session, bank, update_data.balance
    )
    return bank


# # Auth Routers
# @auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
# async def create_user_Account(
#     user_data: UserCreate,
#     domain: str,
#     bg_tasks: BackgroundTasks,
#     session: AsyncSession = Depends(get_session),
# ):
#     """
#     Create user account using email, username, first_name, last_name
#     params:
#         user_data: UserCreateModel
#     """
#     email = user_data.email

#     user_exists = await user_service.user_exists(email, session)

#     if user_exists:
#         raise UserAlreadyExists()

#     new_user, code = await user_service.create_user(
#         user_data=user_data, domain=domain, role="user", session=session
#     )

#     return {
#         "message": "Account Created! Check email to verify your account",
#         # "user": new_user,
#         "email_verification_code": code,
#     }


# @auth_router.post("/create-superuser", status_code=status.HTTP_201_CREATED)
# async def create_super_user_Account(
#     user_data: UserCreate,
#     domain: str,
#     bg_tasks: BackgroundTasks,
#     role: str = "admin",
#     session: AsyncSession = Depends(get_session),
# ):
#     """
#     Create user account using email, username, first_name, last_name
#     params:
#         user_data: UserCreateModel
#     """
#     email = user_data.email

#     user_exists = await user_service.user_exists(email, session)

#     if user_exists:
#         raise UserAlreadyExists()

#     new_user, code = await user_service.create_user(
#         user_data=user_data, domain=domain, role=role, session=session
#     )

#     return {
#         "message": "Superuser Account Created! Check email to verify your account",
#         # "user": new_user,
#         "email_verification_code": code,
#     }


# @auth_router.get("/verify-email/{token}", status_code=status.HTTP_200_OK)
# async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):

#     token_data = decode_url_safe_token(token)

#     user_email = token_data.get("email")

#     if user_email:
#         user = await user_service.get_user_by_email(user_email, session)

#         if not user:
#             raise UserNotFound()

#         await user_service.save_verified_email(
#             user=user, email_data=user_email, session=session
#         )

#         return JSONResponse(
#             content={
#                 "message": "Account verified successfully. Login with your credentials"
#             },
#             status_code=status.HTTP_200_OK,
#         )

#     return JSONResponse(
#         content={"message": "Error occurred during verification"},
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#     )


# @auth_router.post("/transfer-pin/", status_code=status.HTTP_200_OK)
# async def verify_transfer_pin(
#     pin_data: UserPinModel, user: User = Depends(get_current_user)
# ):

#     pin = pin_data.transfer_pin

#     if user is not None:
#         pin_valid = verify_password(pin, user.transfer_pin_hash)

#         if pin_valid:
#             return {
#                 "message": "Transfer pin is correct",
#                 "valid": True,
#             }
#         raise InvalidCredentials()
#     raise UserNotFound()


# @auth_router.post("/login", status_code=status.HTTP_200_OK)
# async def login_users(
#     login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
# ):
#     email = login_data.email
#     password = login_data.password

#     user = await user_service.get_user_by_email(email, session)

#     if user is not None:
#         password_valid = verify_password(password, user.password_hash)

#         if password_valid:
#             access_token = create_access_token(
#                 user_data={
#                     "email": user.email,
#                     "user_uid": str(user.uid),
#                     "role": user.role,
#                 }
#             )

#             refresh_token = create_access_token(
#                 user_data={"email": user.email, "user_uid": str(user.uid)},
#                 refresh=True,
#                 expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
#             )

#             return JSONResponse(
#                 content={
#                     "message": "Login successful",
#                     "access_token": access_token,
#                     "refresh_token": refresh_token,
#                     "user": {"email": user.email, "uid": str(user.uid)},
#                 }
#             )

#     raise InvalidCredentials()


# @auth_router.get("/refresh-token", status_code=status.HTTP_200_OK)
# async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
#     expiry_timestamp = token_details["exp"]

#     if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
#         new_access_token = create_access_token(user_data=token_details["user"])

#         return JSONResponse(content={"access_token": new_access_token})

#     raise InvalidToken


# @auth_router.get("/logout", status_code=status.HTTP_200_OK)
# async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
#     jti = token_details["jti"]

#     await add_jti_to_blocklist(jti)

#     return JSONResponse(
#         content={"message": "Logged Out Successfully"}, status_code=status.HTTP_200_OK
#     )


# @auth_router.post("/password-reset-request", status_code=status.HTTP_200_OK)
# async def password_reset_request(
#     domain: str,
#     email_data: PasswordResetRequestModel,
#     session: AsyncSession = Depends(get_session),
# ):
#     email = email_data.email

#     user = await user_service.get_user_by_email(email, session)

#     code = await send_password_reset_code(user, domain)
#     return JSONResponse(
#         content={
#             "message": "Please check your email for instructions to reset your password",
#             "password_reset_code": code,
#         },
#         status_code=status.HTTP_200_OK,
#     )


# @auth_router.post("/password-reset-confirm/{token}", status_code=status.HTTP_200_OK)
# async def reset_account_password(
#     token: str,
#     passwords: PasswordResetConfirmModel,
#     session: AsyncSession = Depends(get_session),
# ):
#     new_password = passwords.new_password
#     confirm_password = passwords.confirm_new_password

#     if new_password != confirm_password:
#         raise HTTPException(
#             detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
#         )

#     token_data = decode_url_safe_token(token)

#     user_email = token_data.get("email")

#     if user_email:
#         user = await user_service.get_user_by_email(user_email, session)

#         if not user:
#             raise UserNotFound()

#         passwd_hash = generate_passwd_hash(new_password)
#         await user_service.update_user(user, {"password_hash": passwd_hash}, session)

#         return JSONResponse(
#             content={"message": "Password reset Successfully"},
#             status_code=status.HTTP_200_OK,
#         )

#     return JSONResponse(
#         content={"message": "Error occurred during password reset."},
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#     )


# # User Routes
# @user_router.get("/me", response_model=UserRead)
# async def get_current_active_user(
#     user: User = Depends(get_current_user), _: bool = Depends(role_checker)
# ):
#     return user


# @user_router.get("/{uid}", response_model=UserRead)
# async def get_current_user_by_uid(
#     uid: uuid.UUID,
#     user: User = Depends(get_current_user),
#     _: bool = Depends(role_checker),
#     session: AsyncSession = Depends(get_session),
# ):

#     if user.role in (UserRole.ADMIN, UserRole.MANAGER) or user.uid == uid:
#         return await user_service.get_user_by_uid(uid, session)
#     raise InsufficientPermission()


# @user_router.patch("/{uid}", response_model=UserRead)
# async def update_user_by_uid(
#     update_data: dict,
#     uid: uuid.UUID,
#     user: User = Depends(get_current_user),
#     _: bool = Depends(role_checker),
#     session: AsyncSession = Depends(get_session),
# ):

#     if user.role in (UserRole.ADMIN, UserRole.MANAGER) or user.uid == uid:
#         return await user_service.update_user(user, update_data, session)
#     raise InsufficientPermission()


# @user_router.get("", response_model=List[UserRead])
# async def get_users(
#     domain: str,
#     user: User = Depends(get_current_user),
#     # _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     if user.domain != domain:
#         raise InsufficientPermission()
#     users = await user_service.get_all_users(user, domain, session)
#     return users


# @user_router.patch("/me/photo", response_model=UserRead)
# async def update_user_photo(
#     image: UploadFile,
#     current_user: User = Depends(get_current_user),
#     session: AsyncSession = Depends(get_session),
# ):
#     updated_user = await user_service.update_image(current_user, image, session)
#     return updated_user


# @user_router.patch("/{uid}/block", response_model=UserRead)
# async def block_user(
#     uid: uuid.UUID,
#     block: bool,
#     current_user: User = Depends(get_current_user),
#     _: bool = Depends(role_checker),  # Ensure the current user has the necessary role
#     session: AsyncSession = Depends(get_session),
# ):
#     user_to_block = await user_service.get_user_by_uid(uid, session)
#     if not user_to_block:
#         raise UserNotFound()

#     blocked_user = await user_service.block_user(user_to_block, block, session)
#     return blocked_user


# # Business Routes
# @business_router.post("", response_model=BusinessProfileRead)
# async def create_new_business(
#     business_data: BusinessProfileCreate,
#     user_id: Optional[uuid.UUID],
#     user: User = Depends(get_current_user),
#     _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     business_user = user
#     if user_id is not None:
#         business_user = await user_service.get_user_by_uid(user_id, session)
#         if business_user is None:
#             raise UserNotFound()
#     business = await business_service.create_business(
#         business_user, business_data, session
#     )
#     return business


# @business_router.get("{business_id}", response_model=Optional[BusinessProfileRead])
# async def get_business(
#     business_id: str,
#     user: User = Depends(get_current_user),
#     # _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     business = await business_service.get_business_by_id(business_id, session)
#     return business


# @business_router.patch("{business_id}", response_model=Optional[BusinessProfileRead])
# async def update_existing_business(
#     business_id: str,
#     update_data: BusinessProfileUpdate,
#     user: User = Depends(get_current_user),
#     # _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     existing_business = await business_service.get_business_by_id(business_id, session)
#     business = await business_service.update_business(
#         existing_business, update_data, session
#     )
#     return business


# # Card Routes
# @card_router.patch("{card_id}", response_model=Optional[CardRead])
# async def update_existing_card_expiry_date(
#     card_id: str,
#     # update_data: BusinessProfileUpdate,
#     user: User = Depends(get_current_user),
#     _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     if user.role == UserRole.USER:
#         raise InsufficientPermission()
#     card = await business_service.get_card_by_uid(card_id, session)
#     if card is None:
#         raise DebitCardNotFound()
#     card = await business_service.update_card_expiry(card, session)
#     return card


# # Bank Account Routes
# @bank_router.patch("{account_number}", response_model=Optional[BankAccountRead])
# async def update_bank_account_balance(
#     account_number: str,
#     update_data: BankAccountUpdate,
#     user: User = Depends(get_current_user),
#     _: bool = Depends(admin_checker),
#     session: AsyncSession = Depends(get_session),
# ):
#     if user.role == UserRole.USER:
#         raise InsufficientPermission()
#     bank = await business_service.get_bank_by_account_number(account_number, session)
#     if bank is None:
#         raise DebitCardNotFound()
#     bank = await business_service.update_account_balance(session, bank, update_data.balance)
#     return bank
