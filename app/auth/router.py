from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

ROUTER_PREFIX = "/api/v1/auth"
SECRET_KEY = "change-me-in-env-batcrm-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

Role = Literal["seller", "manager"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{ROUTER_PREFIX}/login")
router = APIRouter(prefix=ROUTER_PREFIX, tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    expires_in: int
    redirect_to: str


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role


# Repositorio en memoria (placeholder hasta integrar SQLAlchemy + Alembic)
_FAKE_USERS_DB: dict[str, dict] = {
    "seller@batcrm.com": {
        "id": 1,
        "email": "seller@batcrm.com",
        "full_name": "Vendedor Demo",
        "role": "seller",
        "hashed_password": pwd_context.hash("seller123"),
    },
    "manager@batcrm.com": {
        "id": 2,
        "email": "manager@batcrm.com",
        "full_name": "Gerente Demo",
        "role": "manager",
        "hashed_password": pwd_context.hash("manager123"),
    },
}


def _authenticate(email: str, password: str) -> Optional[dict]:
    user = _FAKE_USERS_DB.get(email.lower())
    if not user or not pwd_context.verify(password, user["hashed_password"]):
        return None
    return user


def _create_access_token(sub: str, role: Role, user_id: int) -> tuple[str, int]:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": sub, "role": role, "uid": user_id, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, int(expires_delta.total_seconds())


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        uid = payload.get("uid")
        if not email or role not in ("seller", "manager") or uid is None:
            raise credentials_exc
    except JWTError as exc:
        raise credentials_exc from exc
    user = _FAKE_USERS_DB.get(email)
    if not user:
        raise credentials_exc
    return UserPublic(**{k: user[k] for k in ("id", "email", "full_name", "role")})


def require_role(*roles: Role):
    def _checker(current: UserPublic = Depends(get_current_user)) -> UserPublic:
        if current.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol no autorizado")
        return current
    return _checker


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = _authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    token, expires_in = _create_access_token(user["email"], user["role"], user["id"])
    redirect = "/dashboard/manager" if user["role"] == "manager" else "/dashboard/seller"
    return TokenResponse(
        access_token=token,
        role=user["role"],
        expires_in=expires_in,
        redirect_to=redirect,
    )


@router.get("/me", response_model=UserPublic)
def me(current: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current
