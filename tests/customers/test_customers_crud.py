from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


CUSTOMER_PAYLOAD = {
    "name": "Ana Torres",
    "company": "Acme Corp",
    "email": "ana@acme.com",
    "phone": "+57 3001112233",
}


async def test_create_and_list_customer(client: AsyncClient, seller_headers: dict):
    res = await client.post("/api/v1/customers", json=CUSTOMER_PAYLOAD, headers=seller_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == CUSTOMER_PAYLOAD["name"]

    listing = await client.get("/api/v1/customers", headers=seller_headers)
    assert listing.status_code == 200
    ids = [c["id"] for c in listing.json()]
    assert body["id"] in ids


async def test_search_filters_by_name_or_company(client: AsyncClient, seller_headers: dict):
    await client.post(
        "/api/v1/customers",
        json={**CUSTOMER_PAYLOAD, "name": "Carlos Ruiz", "company": "Globex"},
        headers=seller_headers,
    )
    res = await client.get("/api/v1/customers", params={"q": "globex"}, headers=seller_headers)
    assert res.status_code == 200
    names = {c["company"].lower() for c in res.json()}
    assert "globex" in names


async def test_update_customer(client: AsyncClient, seller_headers: dict):
    created = (
        await client.post("/api/v1/customers", json=CUSTOMER_PAYLOAD, headers=seller_headers)
    ).json()
    res = await client.put(
        f"/api/v1/customers/{created['id']}",
        json={**CUSTOMER_PAYLOAD, "phone": "+57 3019998877"},
        headers=seller_headers,
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "+57 3019998877"


async def test_delete_customer_without_deals(client: AsyncClient, seller_headers: dict):
    created = (
        await client.post("/api/v1/customers", json=CUSTOMER_PAYLOAD, headers=seller_headers)
    ).json()
    res = await client.delete(f"/api/v1/customers/{created['id']}", headers=seller_headers)
    assert res.status_code == 204
    miss = await client.get(f"/api/v1/customers/{created['id']}", headers=seller_headers)
    assert miss.status_code == 404


async def test_seller_cannot_see_other_owners(
    client: AsyncClient, seller_headers: dict, other_seller_headers: dict
):
    await client.post("/api/v1/customers", json=CUSTOMER_PAYLOAD, headers=other_seller_headers)
    res = await client.get("/api/v1/customers", headers=seller_headers)
    assert res.status_code == 200
    assert all(c["name"] != CUSTOMER_PAYLOAD["name"] for c in res.json())
