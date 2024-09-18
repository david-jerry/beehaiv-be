from typing import Any, List

from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.auth.mails import send_blocked_email
from src.db.db import get_session
from src.app.auth.models import User, UserRole
from src.db.redis import token_in_blocklist

from .services import UserService
from .utils import decode_token, send_verification_code
from src.errors import (
    InvalidToken,
    RefreshTokenRequired,
    AccessTokenRequired,
    InsufficientPermission,
)

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        creds = await super().__call__(request)

        token = creds.credentials

        token_data = decode_token(token)

        if not self.token_valid(token):
            raise InvalidToken()

        if await token_in_blocklist(token_data["jti"]):
            raise InvalidToken()

        self.verify_token_data(token_data)

        return token_data

    def token_valid(self, token: str) -> bool:
        token_data = decode_token(token)

        return token_data is not None

    def verify_token_data(self, token_data):
        raise NotImplementedError("Please Override this method in child classes")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data["refresh"]:
            raise AccessTokenRequired()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data["refresh"]:
            raise RefreshTokenRequired()


async def get_current_user(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_email = token_details["user"]["email"]

    user = await user_service.get_user_by_email(user_email, session)

    if user.is_blocked:
        await send_blocked_email(user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account under surveillance. Please contact customer care or your account manager for rectification.",
        )

    # Check if the user has at least one verified email
    if user is not None and not user.verified_emails:
        # If no verified email, send a verification email
        await send_verification_code(user, user.domain)
        raise HTTPException(
            status_code=403,
            detail="Email not verified. A verification email has been sent to your registered email address.",
        )

    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        # Check if the user has the necessary role
        if current_user.role in self.allowed_roles:
            return True

        raise InsufficientPermission()
