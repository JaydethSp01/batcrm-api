from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.api.customers import Base, Customer, Opportunity, router, get_db


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db: Session = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c, SessionLocal


def _valid_payload(**over):
    base = {
        "name": "Acme Corp Contact",
        "email": "contact@acme.com",
        "phone": "+571234567",
        "company": "Acme Corp",
    }
    base.update(over)
    return base


def test_create_and_list_customer(client):
    c, _ = client
    r = c.post("/api/customers", json=_valid_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "contact@acme.com"

    lst = c.get("/api/customers").json()
    assert len(lst) == 1
    assert lst[0]["company"] == "Acme Corp"


def test_invalid_email_returns_422(client):
    c, _ = client
    r = c.post("/api/customers", json=_valid_payload(email="no-es-email"))
    assert r.status_code == 422


def test_missing_required_field_returns_422(client):
    c, _ = client
    payload = _valid_payload()
    payload.pop("name")
    r = c.post("/api/customers", json=payload)
    assert r.status_code == 422


def test_update_customer_reflects_changes(client):
    c, _ = client
    created = c.post("/api/customers", json=_valid_payload()).json()
    cid = created["id"]
    r = c.put(f"/api/customers/{cid}", json=_valid_payload(name="Nuevo Nombre", email="new@acme.com"))
    assert r.status_code == 200
    assert r.json()["name"] == "Nuevo Nombre"
    assert r.json()["email"] == "new@acme.com"


def test_delete_without_opportunities_succeeds(client):
    c, _ = client
    created = c.post("/api/customers", json=_valid_payload()).json()
    r = c.delete(f"/api/customers/{created['id']}")
    assert r.status_code == 204
    assert c.get("/api/customers").json() == []


def test_delete_with_opportunities_is_blocked(client):
    c, SessionLocal = client
    created = c.post("/api/customers", json=_valid_payload()).json()
    with SessionLocal() as db:
        db.add(Opportunity(customer_id=created["id"], title="Deal 1"))
        db.commit()
    r = c.delete(f"/api/customers/{created['id']}")
    assert r.status_code == 409
    assert r.json()["detail"] == "customer_has_opportunities"
