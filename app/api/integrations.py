"""API routes for integrations (third-party connections per tenant)."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Integration, Tenant
from app.models.schemas import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List integrations, optionally filtered by tenant."""
    query = select(Integration)
    if tenant_id is not None:
        query = query.where(Integration.tenant_id == tenant_id)
    result = await db.execute(query)
    integrations = result.scalars().all()
    for integration in integrations:
        integration.config = _parse_config(integration.config)
    return integrations


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(integration_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific integration."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration.config = _parse_config(integration.config)
    return integration


@router.post("", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    data: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new integration for a tenant."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == data.tenant_id))
    if not tenant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    integration = Integration(
        tenant_id=data.tenant_id,
        name=data.name,
        integration_type=data.integration_type,
        config=json.dumps(data.config) if data.config else None,
        is_active=data.is_active,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    integration.config = _parse_config(integration.config)
    return integration


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: int,
    data: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an integration."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if "config" in update_data:
        config_value = update_data.pop("config")
        integration.config = json.dumps(config_value) if config_value is not None else None
    for field, value in update_data.items():
        setattr(integration, field, value)

    await db.commit()
    await db.refresh(integration)
    integration.config = _parse_config(integration.config)
    return integration


@router.delete("/{integration_id}", status_code=204)
async def delete_integration(integration_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an integration."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(integration)
    await db.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_config(raw: Optional[str]) -> Optional[dict]:
    """Deserialise the JSON config column for responses."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
