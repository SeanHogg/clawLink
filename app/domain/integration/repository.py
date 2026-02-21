"""
Integration repository abstract interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.integration.models import Integration, IntegrationId


class IntegrationRepository(ABC):
    """Abstract repository for the Integration aggregate."""

    @abstractmethod
    async def get_by_id(self, integration_id: IntegrationId) -> Optional[Integration]:
        """Retrieve an Integration by its ID."""

    @abstractmethod
    async def list_by_tenant(self, tenant_id: int) -> List[Integration]:
        """Return all integrations for a given tenant."""

    @abstractmethod
    async def save(self, integration: Integration) -> Integration:
        """Persist a new or updated Integration; returns the saved aggregate."""

    @abstractmethod
    async def delete(self, integration_id: IntegrationId) -> bool:
        """Delete an integration.  Returns True if deleted, False if not found."""
