"""
Tenant domain models (DDD aggregate).

Follows DDD principles:
  - Tenant is the aggregate root.
  - TenantMember is an entity owned by the Tenant aggregate.
  - TenantId and TenantMemberRole are value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.models.database import TenantRole, TenantStatus


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TenantId:
    """Typed, immutable tenant identifier."""
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("TenantId must be a positive integer")


@dataclass(frozen=True)
class TenantMemberRole:
    """Immutable value object representing a user's role within a tenant."""
    role: TenantRole

    @classmethod
    def owner(cls) -> "TenantMemberRole":
        return cls(TenantRole.OWNER)

    @classmethod
    def manager(cls) -> "TenantMemberRole":
        return cls(TenantRole.MANAGER)

    @classmethod
    def developer(cls) -> "TenantMemberRole":
        return cls(TenantRole.DEVELOPER)

    @classmethod
    def viewer(cls) -> "TenantMemberRole":
        return cls(TenantRole.VIEWER)

    def can_manage_requirements(self) -> bool:
        return self.role in (TenantRole.OWNER, TenantRole.MANAGER)

    def can_manage_integrations(self) -> bool:
        return self.role in (TenantRole.OWNER, TenantRole.MANAGER)

    def can_assign_work(self) -> bool:
        return self.role in (TenantRole.OWNER, TenantRole.MANAGER)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class TenantMember:
    """A user's membership within a tenant aggregate."""
    user_id: str
    role: TenantMemberRole
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def deactivate(self) -> None:
        self.is_active = False

    def change_role(self, new_role: TenantMemberRole) -> None:
        self.role = new_role


# ---------------------------------------------------------------------------
# Aggregate root
# ---------------------------------------------------------------------------

@dataclass
class Tenant:
    """
    Tenant aggregate root.

    Invariants:
    - A tenant must always have at least one OWNER member.
    - Slug must be unique across the system (enforced at DB level).
    """
    id: TenantId
    name: str
    slug: str
    status: TenantStatus = TenantStatus.ACTIVE
    description: Optional[str] = None
    members: List[TenantMember] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # ------------------------------------------------------------------
    # Tenant-level business rules (SOLID: SRP, OCP)
    # ------------------------------------------------------------------

    def add_member(self, user_id: str, role: TenantMemberRole) -> TenantMember:
        """Add a member to the tenant.  Raises if already a member."""
        existing = self._find_member(user_id)
        if existing and existing.is_active:
            raise ValueError(f"User '{user_id}' is already an active member of this tenant.")
        member = TenantMember(user_id=user_id, role=role)
        self.members.append(member)
        return member

    def remove_member(self, user_id: str) -> None:
        """Deactivate a member.  Raises if this would leave the tenant without an owner."""
        member = self._find_member(user_id)
        if not member:
            raise ValueError(f"User '{user_id}' is not a member of this tenant.")
        if member.role.role == TenantRole.OWNER and self._owner_count() <= 1:
            raise ValueError("Cannot remove the last owner of a tenant.")
        member.deactivate()

    def change_member_role(self, user_id: str, new_role: TenantMemberRole) -> None:
        """Change a member's role.  Raises if this would leave the tenant without an owner."""
        member = self._find_member(user_id)
        if not member:
            raise ValueError(f"User '{user_id}' is not a member of this tenant.")
        if (
            member.role.role == TenantRole.OWNER
            and new_role.role != TenantRole.OWNER
            and self._owner_count() <= 1
        ):
            raise ValueError("Cannot demote the last owner of a tenant.")
        member.change_role(new_role)

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_member(self, user_id: str) -> Optional[TenantMember]:
        return next((m for m in self.members if m.user_id == user_id), None)

    def _owner_count(self) -> int:
        return sum(
            1
            for m in self.members
            if m.is_active and m.role.role == TenantRole.OWNER
        )
