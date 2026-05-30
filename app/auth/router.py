from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = "change-me-in-env"
JWT_ALG = "HS256"
ACCESS_TOKEN_TTL_MIN = 60

pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

Role = Literal["vendedor", "gerente"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    redirect_to: str


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    role: Role


# Repositorio en memoria (sustituir por SQLAlchemy en S-003).
USERS_DB: dict[str, dict] = {
    "vendedor@batcrm.com": {
        "id": 1,
        "email": "vendedor@batcrm.com",
        "role": "vendedor",
        "password_hash": pwd_ctx.hash("vendedor123"),
    },
    "gerente@batcrm.com": {
        "id": 2,
        "email": "gerente@batcrm.com",
        "role": "gerente",
        "password_hash": pwd_ctx.hash("gerente123"),
    },
}

REVOKED_TOKENS: set[str] = set()


def _create_access_token(sub: str, role: Role) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_TTL_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _redirect_for_role(role: Role) -> str:
    return "/dashboard/gerente" if role == "gerente" else "/dashboard/vendedor"


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    if token in REVOKED_TOKENS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesion invalidada")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    user = USERS_DB.get(payload.get("sub", ""))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inexistente")
    return UserPublic(id=user["id"], email=user["email"], role=user["role"])


def require_role(*allowed: Role):
    def _checker(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={"message": "Acceso denegado", "redirect_to": "/403"},
            )
        return user
    return _checker


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = USERS_DB.get(payload.email.lower())
    if not user or not pwd_ctx.verify(payload.password, user["password_hash"]):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )
    token = _create_access_token(user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        role=user["role"],
        redirect_to=_redirect_for_role(user["role"]),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(oauth2_scheme)) -> None:
    REVOKED_TOKENS.add(token)


@router.get("/me", response_model=UserPublic)
def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user


@router.get("/manager-area", response_model=UserPublic)
def manager_area(user: UserPublic = Depends(require_role("gerente"))) -> UserPublic:
    return user
