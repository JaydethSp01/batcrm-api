from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.router import router as auth_router, REVOKED_TOKENS

app = FastAPI()
app.include_router(auth_router)
client = TestClient(app)


def _login(email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_ok_vendedor_redirige_a_dashboard_vendedor():
    r = _login("vendedor@batcrm.com", "vendedor123")
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["role"] == "vendedor"
    assert data["redirect_to"] == "/dashboard/vendedor"
    assert data["access_token"]


def test_login_ok_gerente_redirige_a_dashboard_gerente():
    r = _login("gerente@batcrm.com", "gerente123")
    assert r.status_code == 200
    assert r.json()["redirect_to"] == "/dashboard/gerente"


def test_login_credenciales_invalidas():
    r = _login("vendedor@batcrm.com", "wrong-pass")
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciales incorrectas"


def test_vendedor_no_accede_a_area_de_gerente():
    token = _login("vendedor@batcrm.com", "vendedor123").json()["access_token"]
    r = client.get(
        "/auth/manager-area", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403
    assert r.json()["detail"]["redirect_to"] == "/403"


def test_gerente_accede_a_area_de_gerente():
    token = _login("gerente@batcrm.com", "gerente123").json()["access_token"]
    r = client.get(
        "/auth/manager-area", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "gerente"


def test_logout_invalida_sesion():
    token = _login("gerente@batcrm.com", "gerente123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert token in REVOKED_TOKENS
    assert client.get("/auth/me", headers=headers).status_code == 401
