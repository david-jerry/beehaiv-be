from .base import BaseConfig
from pydantic_settings import SettingsConfigDict

class LocalConfig(BaseConfig):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_TLS: bool
    MAIL_SSL: bool
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = False
    VALIDATE_CERTS: bool = False
    DOMAIN: str

    model_config = SettingsConfigDict(
        env_file=".env.local",
        extra="ignore",
        env_file_encoding='utf-8'
    )

LocalConfigSettings = LocalConfig()
