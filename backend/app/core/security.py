import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import jwt

from app.core.config import settings


# ============================================================================
# Password Hashing Utilities
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password securely.
    Uses bcrypt if available; otherwise uses PBKDF2-HMAC-SHA256.
    """
    try:
        import bcrypt
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")
    except Exception:
        # Fallback to standard library PBKDF2-HMAC-SHA256
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000
        )
        return f"$pbkdf2-sha256$100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its stored hash.
    Supports both bcrypt and PBKDF2-HMAC-SHA256 formats.
    """
    if not hashed_password or not plain_password:
        return False

    # Check for PBKDF2 format
    if hashed_password.startswith("$pbkdf2-sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 5:
            iterations = int(parts[2])
            salt = parts[3]
            stored_hash = parts[4]
            key = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations=iterations
            )
            return hmac.compare_digest(key.hex(), stored_hash)

    # Check for bcrypt format
    try:
        import bcrypt
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ============================================================================
# JWT Token Utilities
# ============================================================================

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token with expiration."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None
