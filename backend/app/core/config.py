import logging
import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RP_ID: str = "localhost"
    RP_NAME: str = "Hybrid Auth System"
    ORIGIN: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


logger = logging.getLogger("config")
try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration validation error: {e}")
    sys.exit(1)
