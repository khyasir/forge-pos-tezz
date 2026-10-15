import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .database import get_db

settings = get_settings()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    return pwd_context.verify(pin, pin_hash)


def generate_api_key(sandbox: bool = True) -> str:
    prefix = "tz_test_" if sandbox else "tz_live_"
    return prefix + secrets.token_hex(16)


def create_access_token(user: models.User, branch_id: str, terminal_id: str | None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": user.id,
        "company_id": user.company_id,
        "role": user.role,
        "branch_id": branch_id,
        "terminal_id": terminal_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthContext:
    def __init__(self, company_id: str, user: models.User | None = None, api_key: models.ApiKey | None = None, claims: dict | None = None):
        self.company_id = company_id
        self.user = user
        self.api_key = api_key
        self.claims = claims or {}


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
    token = credentials.credentials

    if token.startswith("tz_"):
        api_key = db.query(models.ApiKey).filter(models.ApiKey.key == token, models.ApiKey.active == True).first()  # noqa: E712
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return AuthContext(company_id=api_key.company_id, api_key=api_key)

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(models.User).filter(models.User.id == payload.get("sub")).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthContext(company_id=user.company_id, user=user, claims=payload)
