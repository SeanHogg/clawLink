"""
Tenant repository abstract interface (DDD repository pattern).

Infrastructure implementations (SQLAlchemy, in-memory, …) satisfy this
contract — domain code depends only on the abstract interface (DIP / SOLID).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.tenant.models import Tenant, TenantId


class TenantRepository(ABC):
    """Abstract repository for the Tenant aggregate."""

    @abstractmethod
    async def get_by_id(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Retrieve a Tenant by its ID."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Retrieve a Tenant by its slug."""

    @abstractmethod
    async def list_all(self) -> List[Tenant]:
        """Return all tenants."""

    @abstractmethod
    async def save(self, tenant: Tenant) -> Tenant:
        """Persist a new or updated Tenant; returns the saved aggregate."""

    @abstractmethod
    async def delete(self, tenant_id: TenantId) -> bool:
        """Delete a tenant.  Returns True if deleted, False if not found."""
