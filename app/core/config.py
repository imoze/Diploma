from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str = 'JWT_KEY$'
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # Argon2
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 102400  # 100 MB
    ARGON2_PARALLELISM: int = 8
    ARGON2_HASH_LEN: int = 32
    ARGON2_SALT_LEN: int = 16
    
    class Config:
        env_file = ".env"

settings = Settings()
