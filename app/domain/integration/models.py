"""
Integration domain models (DDD aggregate).

An Integration connects a tenant to a third-party system (GitHub, Jira, …).
Managers are responsible for creating and managing integrations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.database import IntegrationType


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationId:
    """Typed, immutable integration identifier."""
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("IntegrationId must be a positive integer")


@dataclass(frozen=True)
class IntegrationConfig:
    """
    Immutable configuration snapshot for an integration.

    Wraps arbitrary key-value config so callers never manipulate raw dicts.
    """
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def to_json(self) -> str:
        return json.dumps(self.data)

    @classmethod
    def from_json(cls, value: Optional[str]) -> "IntegrationConfig":
        if not value:
            return cls(data={})
        return cls(data=json.loads(value))


# ---------------------------------------------------------------------------
# Aggregate root
# ---------------------------------------------------------------------------

@dataclass
class Integration:
    """
    Integration aggregate root.

    Business rules:
    - Only active integrations can be used.
    - Configuration changes must go through the aggregate (not direct DB write).
    """

    id: IntegrationId
    tenant_id: int
    name: str
    integration_type: IntegrationType
    config: IntegrationConfig = field(default_factory=IntegrationConfig)
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Replace the configuration (immutable value object is recreated)."""
        object.__setattr__(self, "config", IntegrationConfig(data=dict(new_config)))
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Re-enable a disabled integration."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Disable the integration without deleting it."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
