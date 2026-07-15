"""Хеширование / проверка пароля, генерация и декордирование JWT, генерация refresh-токена."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from app.core import settings


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Захешировать пароль алгоритмом argon2."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Проверить пароль против его argon2id-хеша."""
    try:
        _hasher.verify(hashed, password)
        return True
    except (VerifyMismatchError, InvalidHash):
        return False


def create_access_token(user_id: UUID) -> str:
    """Выпустить короткоживущий access-токен, подписанный EdDSA."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        ),
    }
    return jwt.encode(
        payload, settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Проверить и раскодировать access-токен.

    Returns:
    Бросает jwt.PyJWTError (или подкласс) на любой невалидный токен.
    """
    payload = jwt.decode(
        token, settings.JWT_PUBLIC_KEY, algorithms=settings.JWT_ALGORITHM
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token.")
    return payload


def generate_refresh_token() -> str:
    """Сгенерировать случайный refresh-токен (не JWT)."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Захешировать refresh-токен для хранения / поиска в Redis."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
