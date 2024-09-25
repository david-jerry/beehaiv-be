import logging
import uuid
from datetime import datetime, timedelta

from itsdangerous import URLSafeTimedSerializer

import jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore

from src.app.auth.mails import send_reset_password_email, send_verification_email
from src.app.auth.models import User
from src.config.settings import Config
from src.db.redis import (
    get_password_reset_code,
    get_verification_status,
    store_password_reset_code,
    store_verification_code,
)
from src.utils.logger import LOGGER

passwd_context = CryptContext(schemes=["bcrypt"], deprecated='auto')

ACCESS_TOKEN_EXPIRY = 3600


def generate_verification_code(email: str) -> str:
    token = create_url_safe_token({"email": email})
    return token


def generate_transfer_pin(pin: str) -> str:
    token = create_url_safe_token({"pin": pin})
    return token


async def send_verification_code(user: User, domain: str):
    verification_data = await get_verification_status(user.uid)
    if not verification_data or verification_data.get("verified") == "true":
        LOGGER.info(f"User Email: {user.email}")
        # No code exists or already verified; generate a new one
        code = generate_verification_code(user.email)
        await store_verification_code(user.uid, code)
        # Send the code via email
        # await send_verification_email(user, code, domain)
        return code
    elif verification_data.get("verified") == "false":
        # Code exists but not verified; resend the existing code
        # await send_verification_email(user, verification_data.get("code"), domain)
        return verification_data.get("code")


async def send_password_reset_code(user: User, domain: str):
    verification_data = await get_password_reset_code(user.uid)
    LOGGER.info(verification_data)
    if not verification_data:
        # No code exists or already verified; generate a new one
        code = generate_verification_code(user.email)
        await store_password_reset_code(user.uid, code)
        # Send the code via email
        # await send_reset_password_email(user, domain, code)
        return code
    else:
        # Code exists but not verified; resend the existing code
        # await send_reset_password_email(user, domain, verification_data)
        return verification_data.decode("utf-8")


def generate_passwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)

    return hash


def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
):
    payload = {}

    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())

    payload["refresh"] = refresh

    token = jwt.encode(
        payload=payload, key=Config.SECRET_KEY, algorithm=Config.ALGORITHM
    )

    return token


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=Config.SECRET_KEY, algorithms=[Config.ALGORITHM]
        )

        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


serializer = URLSafeTimedSerializer(
    secret_key=Config.SECRET_KEY, salt="email-configuration"
)


def create_url_safe_token(data: dict):

    token = serializer.dumps(data)

    return token


def decode_url_safe_token(token: str):
    try:
        token_data = serializer.loads(token)

        return token_data

    except Exception as e:
        logging.error(str(e))
