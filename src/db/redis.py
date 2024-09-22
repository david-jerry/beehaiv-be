from typing import Optional
import uuid
import redis.asyncio as aioredis
from src.app.auth.models import User
from src.config.settings import (
    broker_url,
)

# Redis connection pool settings
REDIS_POOL_SIZE = 10
REDIS_TIMEOUT = 5
JTI_EXPIRY = 3600
VERIFICATION_CODE_EXPIRY = 900  # 15 minutes
SECURITY_EXPIRY = 2592000  # 1 month

# Initialize Redis with connection pooling
redis_pool = aioredis.ConnectionPool.from_url(
    broker_url, max_connections=REDIS_POOL_SIZE, socket_timeout=REDIS_TIMEOUT
)
redis_client = aioredis.Redis(connection_pool=redis_pool)


# Password Reset Code
async def store_password_reset_code(
    user_id: uuid.UUID, code: str, expiry: int = VERIFICATION_CODE_EXPIRY
):
    await redis_client.set(f"reset_code:{user_id}", code, ex=expiry)


async def block_ip_attempts(user: User, new_ip: str) -> bool:
    """
    Checks the current number of IP attempts stored in Redis.

    Args:
        user_id (uuid.UUID): The user's unique ID.
        new_ip (str): The IP address to check.

    Returns:
        int: The number of attempts for the specific IP.
    """
    if user.ip_address != new_ip:
        attempts = await redis_client.get(f"new_ip:{user.uid}:{new_ip}")
        calc_attempts = int(attempts.decode("utf-8")) + 1

        # Redis returns None if the key doesn't exist
        if calc_attempts < 4:
            await store_new_ip(user.uid, new_ip, calc_attempts)
            return False # If there are no attempts greater than 3, do not block

        # block the user
        return True
    return False


async def store_new_ip(
    user_id: uuid.UUID, new_ip: str, attempts: int
):
    await redis_client.set(f"new_ip:{user_id}:{new_ip}", attempts, exp=SECURITY_EXPIRY)


async def delete_ip_security(
    user_id: uuid.UUID, new_ip: str
):
    await redis_client.delete(f"new_ip:{user_id}:{new_ip}")

# Get the reset code from Redis
async def get_password_reset_code(user_id: uuid.UUID) -> Optional[str]:
    return await redis_client.get(f"reset_code:{user_id}")


# Email Verification Code
async def store_verification_code(user_id: uuid.UUID, code: str) -> None:
    """Stores the verification code in Redis with an expiry time."""
    await redis_client.hset(
        f"verification_code:{user_id}", mapping={"code": code, "verified": "false"}
    )
    await redis_client.expire(f"verification_code:{user_id}", VERIFICATION_CODE_EXPIRY)


async def get_verification_status(user_id: uuid.UUID) -> dict:
    """Retrieves the verification code and status from Redis."""
    data = await redis_client.hgetall(f"verification_code:{user_id}")
    return {k.decode("utf-8"): v.decode("utf-8") for k, v in data.items()}


async def mark_email_verified(user_id: uuid.UUID) -> None:
    """Marks the email as verified."""
    await redis_client.hset(f"verification_code:{user_id}", "verified", "true")


# Blacklisting
async def add_jti_to_blocklist(jti: str) -> None:
    """Adds a JTI (JWT ID) to the Redis blocklist with an expiry."""
    # Use the 'set' command with an expiry to add the JTI to the blocklist
    await redis_client.set(jti, "", ex=JTI_EXPIRY)


async def token_in_blocklist(jti: str) -> bool:
    """Checks if a JTI (JWT ID) is in the Redis blocklist."""
    # Use 'exists' instead of 'get' for better performance
    is_blocked = await redis_client.exists(jti)
    return is_blocked == 1
