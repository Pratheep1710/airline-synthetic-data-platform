from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict, cast

from fastapi import HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

TOKEN_URL = "/api/v1/auth/token"
SCOPES = {
    "dataset:read": "Read generated datasets",
    "dataset:generate": "Generate synthetic datasets",
    "validation:read": "Read validation reports",
    "admin": "Administrative access",
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_URL, scopes=SCOPES)


class TokenPayload(BaseModel):
    sub: str
    scopes: list[str] = []
    exp: int


class User(BaseModel):
    username: str
    scopes: list[str]
    disabled: bool = False


class UserRecord(TypedDict):
    username: str
    password: str
    scopes: list[str]


FAKE_USERS: dict[str, UserRecord] = {
    "reader": {"username": "reader", "password": "reader", "scopes": ["dataset:read"]},
    "generator": {
        "username": "generator",
        "password": "generator",
        "scopes": ["dataset:read", "dataset:generate", "validation:read"],
    },
    "admin": {
        "username": "admin",
        "password": "admin",
        "scopes": ["dataset:read", "dataset:generate", "validation:read", "admin"],
    },
    "gen_only_user": {
        "username": "gen_only_user",
        "password": "GenOnly@123",
        "scopes": ["dataset:generate"],
    },
    "read_only_user": {
        "username": "read_only_user",
        "password": "ReadOnly@123",
        "scopes": ["dataset:read", "validation:read"],
    },
}


def authenticate_user(username: str, password: str) -> User | None:
    user = FAKE_USERS.get(username)
    if not user or user["password"] != password:
        return None
    return User(username=user["username"], scopes=user["scopes"])


def create_access_token(subject: str, scopes: list[str], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "scopes": scopes, "exp": int(expire.timestamp())}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return cast(str, token)


def _credentials_exception(scopes: list[str] | None = None) -> HTTPException:
    scope_txt = " ".join(scopes or [])
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": f'Bearer scope="{scope_txt}"'},
    )


async def get_current_user(
    security_scopes: SecurityScopes, token: str = Security(oauth2_scheme)
) -> User:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_data = TokenPayload(**payload)
    except JWTError as exc:
        raise _credentials_exception(security_scopes.scopes) from exc

    user = FAKE_USERS.get(token_data.sub)
    if not user:
        raise _credentials_exception(security_scopes.scopes)

    user_obj = User(username=user["username"], scopes=user["scopes"])
    for required_scope in security_scopes.scopes:
        if required_scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}",
            )
    return user_obj


def require_scopes(scopes: list[str]):
    async def _dependency(current_user: User = Security(get_current_user, scopes=scopes)) -> User:
        return current_user

    return _dependency
