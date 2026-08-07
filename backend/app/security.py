"""
Password hashing + JWT session tokens for the admin dashboard's login system.

Uses the `bcrypt` library directly rather than passlib. passlib 1.7.4's
bcrypt backend does its own version-detection against the installed
bcrypt package, and that detection code is broken against bcrypt>=4.1
(it references an attribute bcrypt removed) - it fails in a way that
surfaces as a bogus "password cannot be longer than 72 bytes" error even
for short passwords. Calling bcrypt directly avoids that broken shim
entirely.

SECRET_KEY should come from an environment variable in any real deployment
(see .env / app/database.py for the pattern already used for the DB URL).
It falls back to a fixed dev value here purely so the app runs out of the
box for the internship project - change this before deploying anywhere
that matters.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-secret-change-me-before-deploying")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days - a dashboard session, not an API key

# bcrypt has a hard 72-byte limit on the input it will hash.
_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        # A malformed/legacy hash in the DB - treat as "doesn't match" rather
        # than crashing the login endpoint.
        return False


def create_access_token(*, subject_email: str, user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject_email, "user_id": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
