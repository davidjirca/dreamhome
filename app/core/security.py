from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_password(password: str) -> str:
    """
    Truncate password to 72 bytes for bcrypt compatibility.
    Bcrypt has a maximum password length of 72 bytes.
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes
        password_bytes = password_bytes[:72]
        # Decode back, ignoring errors for incomplete UTF-8 sequences
        return password_bytes.decode('utf-8', errors='ignore')
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    Automatically truncates password to 72 bytes for bcrypt.
    """
    truncated_password = _truncate_password(plain_password)
    return pwd_context.verify(truncated_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate password hash.
    Automatically truncates password to 72 bytes for bcrypt.
    """
    truncated_password = _truncate_password(password)
    return pwd_context.hash(truncated_password)


def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        subject: Usually the user ID
        expires_delta: Optional custom expiration time

    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any) -> str:
    """
    Create JWT refresh token

    Args:
        subject: Usually the user ID

    Returns:
        JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None