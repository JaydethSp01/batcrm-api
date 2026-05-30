from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, get_current_user
from app.db.session import get_session
from app.customers.models import Customer
from app.deals.models import Deal  # asociacion bloqueante de borrado

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=40)


class CustomerOut(CustomerIn):
    id: uuid.UUID
    owner_id: uuid.UUID

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    q: Optional[str] = Query(default=None, max_length=120),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[Customer]:
    stmt = select(Customer).where(Customer.owner_id == user.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(like), Customer.company.ilike(like)))
    stmt = stmt.order_by(Customer.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Customer:
    customer = Customer(**payload.model_dump(), owner_id=user.id)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def _get_owned(
    customer_id: uuid.UUID, user: CurrentUser, db: AsyncSession
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None or customer.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Customer:
    return await _get_owned(customer_id, user, db)


@router.put("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Customer:
    customer = await _get_owned(customer_id, user, db)
    for field, value in payload.model_dump().items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    customer = await _get_owned(customer_id, user, db)
    has_deals = await db.scalar(
        select(Deal.id).where(Deal.customer_id == customer.id).limit(1)
    )
    if has_deals:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="El cliente tiene oportunidades asociadas",
        )
    await db.delete(customer)
    await db.commit()
