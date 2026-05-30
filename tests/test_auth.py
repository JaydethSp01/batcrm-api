from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from backend.app.auth.router import (
    ALGORITHM,
    SECRET_KEY,
    router as auth_router,
)


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(auth_router)
    return TestClient(app)


def test_seller_login_returns_token_and_seller_redirect(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "seller@batcrm.com", "password": "seller123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "seller"
    assert body["redirect_to"] == "/dashboard/seller"
    assert body["access_token"]


def test_manager_login_returns_manager_redirect(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@batcrm.com", "password": "manager123"},
    )
    assert res.status_code == 200
    assert res.json()["redirect_to"] == "/dashboard/manager"


def test_invalid_credentials_returns_401(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "seller@batcrm.com", "password": "wrong"},
    )
    assert res.status_code == 401
    assert "access_token" not in res.json()


def test_me_with_valid_token(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "seller@batcrm.com", "password": "seller123"},
    ).json()
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "seller"


def test_expired_token_is_rejected(client: TestClient) -> None:
    expired = jwt.encode(
        {
            "sub": "seller@batcrm.com",
            "role": "seller",
            "uid": 1,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
