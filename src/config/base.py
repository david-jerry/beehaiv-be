from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
BASE_URL = Path(__file__).resolve().parent.parent.parent
class BaseConfig(BaseSettings):
    ENVIRONMENT: str
    SECRET_KEY: str
    ALGORITHM: str
    BASE_DIR: Path = BASE_URL
    APP_DIR: Path = BASE_DIR / 'src/app'

    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_KEY: str
    CLOUDINARY_SECRET: str
    CLOUDINARY_URL: str


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding='utf-8'
    )

BaseConfigSettings = BaseConfig()

