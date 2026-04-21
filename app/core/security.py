from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from typing import Optional
from uuid import UUID

from app.core.config import settings

# Argon2 hasher
ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    hash_len=settings.ARGON2_HASH_LEN,
    salt_len=settings.ARGON2_SALT_LEN
)

def hash_password(password: str) -> str:
    """Хэширует пароль используя Argon2"""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля хэшу"""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerificationError:
        return False

def create_access_token(user_id: UUID) -> str:
    """Создаёт JWT токен"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[UUID]:
    """Декодирует JWT токен и возвращает user_id"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id:
            return UUID(user_id)
        return None
    except JWTError:
        return None