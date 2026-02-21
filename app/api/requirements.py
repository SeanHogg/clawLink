"""API routes for requirements (human-in-the-loop work items)."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Requirement, Tenant
from app.models.schemas import (
    RequirementCreate, RequirementUpdate, RequirementAssign, RequirementResponse,
)

router = APIRouter(prefix="/requirements", tags=["requirements"])


def _gates_to_str(gates: Optional[List]) -> Optional[str]:
    """Serialise LifecycleStage list to comma-separated string for storage."""
    if not gates:
        return None
    return ",".join(g.value for g in gates)


@router.get("", response_model=List[RequirementResponse])
async def list_requirements(
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List requirements, optionally filtered by tenant."""
    query = select(Requirement)
    if tenant_id is not None:
        query = query.where(Requirement.tenant_id == tenant_id)
    result = await db.execute(query)
    reqs = result.scalars().all()
    # Deserialise human_review_stages -> lifecycle_gates for response
    for req in reqs:
        req.lifecycle_gates = _str_to_gates(req.human_review_stages)
    return reqs


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(requirement_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific requirement."""
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    req.lifecycle_gates = _str_to_gates(req.human_review_stages)
    return req


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    req_data: RequirementCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new requirement."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == req_data.tenant_id))
    if not tenant_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tenant not found")

    req = Requirement(
        tenant_id=req_data.tenant_id,
        project_id=req_data.project_id,
        title=req_data.title,
        description=req_data.description,
        status=req_data.status,
        assigned_to=req_data.assigned_to,
        human_review_stages=_gates_to_str(req_data.lifecycle_gates),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    req.lifecycle_gates = _str_to_gates(req.human_review_stages)
    return req


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    req_data: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a requirement."""
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    update_data = req_data.model_dump(exclude_unset=True)
    if "lifecycle_gates" in update_data:
        req.human_review_stages = _gates_to_str(update_data.pop("lifecycle_gates"))
    for field, value in update_data.items():
        setattr(req, field, value)

    await db.commit()
    await db.refresh(req)
    req.lifecycle_gates = _str_to_gates(req.human_review_stages)
    return req


@router.post("/{requirement_id}/assign", response_model=RequirementResponse)
async def assign_requirement(
    requirement_id: int,
    assign_data: RequirementAssign,
    db: AsyncSession = Depends(get_db),
):
    """Assign a requirement to a user or agent (human-in-the-loop workflow)."""
    from app.models.database import RequirementStatus
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if req.status not in (RequirementStatus.DRAFT, RequirementStatus.OPEN):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign a requirement with status '{req.status}'",
        )

    req.assigned_to = assign_data.assigned_to
    req.status = RequirementStatus.ASSIGNED

    await db.commit()
    await db.refresh(req)
    req.lifecycle_gates = _str_to_gates(req.human_review_stages)
    return req


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(requirement_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a requirement."""
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    await db.delete(req)
    await db.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _str_to_gates(value: Optional[str]) -> Optional[List]:
    """Deserialise human_review_stages string to a list of LifecycleStage values."""
    if not value:
        return None
    from app.models.database import LifecycleStage
    return [LifecycleStage(s.strip()) for s in value.split(",") if s.strip()]
