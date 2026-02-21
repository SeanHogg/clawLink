"""
Requirement repository abstract interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.requirement.models import Requirement, RequirementId


class RequirementRepository(ABC):
    """Abstract repository for the Requirement aggregate."""

    @abstractmethod
    async def get_by_id(self, requirement_id: RequirementId) -> Optional[Requirement]:
        """Retrieve a Requirement by its ID."""

    @abstractmethod
    async def list_by_tenant(self, tenant_id: int) -> List[Requirement]:
        """Return all requirements for a given tenant."""

    @abstractmethod
    async def save(self, requirement: Requirement) -> Requirement:
        """Persist a new or updated Requirement; returns the saved aggregate."""

    @abstractmethod
    async def delete(self, requirement_id: RequirementId) -> bool:
        """Delete a requirement.  Returns True if deleted, False if not found."""
