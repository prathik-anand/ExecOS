"""
Auth Service — JWT signing/verification and password hashing.

Single responsibility: authentication primitives only.
No HTTP, no DB queries, no routing.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
