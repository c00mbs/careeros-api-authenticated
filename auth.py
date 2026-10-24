"""Password hashing and signed bearer-token helpers."""

import os
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


load_dotenv()

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set to a random value of at least 32 characters")
    return secret


def access_token_lifetime() -> timedelta:
    raw_minutes = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    try:
        minutes = int(raw_minutes)
    except ValueError as exc:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc
    if not 1 <= minutes <= 1440:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
    return timedelta(minutes=minutes)


def validate_auth_settings() -> None:
    """Fail startup on weak or invalid token configuration."""
    jwt_secret()
    access_token_lifetime()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: int) -> tuple[str, int]:
    lifetime = access_token_lifetime()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(claims, jwt_secret(), algorithm=ALGORITHM), int(lifetime.total_seconds())


def decode_access_token(token: str) -> int:
    claims = jwt.decode(
        token,
        jwt_secret(),
        algorithms=[ALGORITHM],
        options={"require": ["sub", "exp", "iat", "type"]},
    )
    if claims.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Invalid token subject") from exc
    if user_id < 1:
        raise jwt.InvalidTokenError("Invalid token subject")
    return user_id
