from datetime import datetime, timedelta
from typing import Optional
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Bcrypt has a 72 byte limit, truncate if necessary
    plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    # Bcrypt has a 72 byte limit, truncate if necessary
    password = password[:72]
    return pwd_context.hash(password)


def create_token(user_id: str, email: str) -> str:
    """Create JWT access token."""
    # JWT "sub" must be a string; keep user_id as identity and store email as an extra claim.
    return create_access_token(
        identity=str(user_id),
        additional_claims={"email": email}
    )
