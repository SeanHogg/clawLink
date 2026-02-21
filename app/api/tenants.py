"""API routes for tenants (multi-tenant management)."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.database import Tenant, TenantMembership
from app.models.schemas import (
    TenantCreate, TenantUpdate, TenantResponse,
    TenantMembershipCreate, TenantMembershipResponse,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    """List all tenants."""
    result = await db.execute(select(Tenant))
    return result.scalars().all()


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant (organisation)."""
    existing = await db.execute(select(Tenant).where(Tenant.slug == tenant_data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists",
        )

    tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        description=tenant_data.description,
        status=tenant_data.status,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    for field, value in tenant_data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.delete(tenant)
    await db.commit()


# ---------------------------------------------------------------------------
# Membership sub-resource
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/members", response_model=List[TenantMembershipResponse])
async def list_members(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """List all members of a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    memberships = await db.execute(
        select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
    )
    return memberships.scalars().all()


@router.post("/{tenant_id}/members", response_model=TenantMembershipResponse, status_code=201)
async def add_member(
    tenant_id: int,
    member_data: TenantMembershipCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a user to a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = await db.execute(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == member_data.user_id,
            TenantMembership.is_active == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"User '{member_data.user_id}' is already a member of this tenant",
        )

    membership = TenantMembership(
        tenant_id=tenant_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.delete("/{tenant_id}/members/{user_id}", status_code=204)
async def remove_member(
    tenant_id: int,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from a tenant."""
    result = await db.execute(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
            TenantMembership.is_active == True,  # noqa: E712
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.is_active = False
    await db.commit()
