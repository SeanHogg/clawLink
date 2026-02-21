"""
Requirement domain models (DDD aggregate).

A Requirement is a human-created work item that can be assigned to agents
or developers.  Managers choose at which lifecycle stages they want to
engage (approve, review, etc.) before work continues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.models.database import LifecycleStage, RequirementStatus


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequirementId:
    """Typed, immutable requirement identifier."""
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("RequirementId must be a positive integer")


@dataclass(frozen=True)
class LifecycleGate:
    """
    A lifecycle stage where a human manager must approve before work continues.

    This value object captures the concept of 'humans choose where in the
    lifecycle to engage'.
    """
    stage: LifecycleStage

    @classmethod
    def planning_gate(cls) -> "LifecycleGate":
        """Gate before any execution starts."""
        return cls(LifecycleStage.PLANNING)

    @classmethod
    def execution_gate(cls) -> "LifecycleGate":
        """Gate during agent execution (e.g., approve mid-way)."""
        return cls(LifecycleStage.EXECUTION)

    @classmethod
    def review_gate(cls) -> "LifecycleGate":
        """Gate before the requirement is closed/merged."""
        return cls(LifecycleStage.REVIEW)


# ---------------------------------------------------------------------------
# Aggregate root
# ---------------------------------------------------------------------------

@dataclass
class Requirement:
    """
    Requirement aggregate root.

    Business rules enforced here:
    - Only DRAFT requirements can be edited freely.
    - A requirement must be OPEN before it can be assigned.
    - A requirement must be ASSIGNED before it can transition to IN_PROGRESS.
    """

    id: RequirementId
    tenant_id: int
    title: str
    status: RequirementStatus = RequirementStatus.DRAFT
    description: Optional[str] = None
    project_id: Optional[int] = None
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    lifecycle_gates: List[LifecycleGate] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Publish the requirement so it can be assigned."""
        if self.status != RequirementStatus.DRAFT:
            raise ValueError(f"Only DRAFT requirements can be opened; current status: {self.status}")
        self.status = RequirementStatus.OPEN
        self.updated_at = datetime.utcnow()

    def assign(self, assignee: str) -> None:
        """Assign the requirement to a user or agent."""
        if self.status not in (RequirementStatus.OPEN, RequirementStatus.DRAFT):
            raise ValueError(
                f"Cannot assign a requirement in status '{self.status}'. "
                "It must be OPEN or DRAFT first."
            )
        self.assigned_to = assignee
        self.status = RequirementStatus.ASSIGNED
        self.updated_at = datetime.utcnow()

    def start(self) -> None:
        """Mark the requirement as in-progress (agent has started work)."""
        if self.status != RequirementStatus.ASSIGNED:
            raise ValueError(
                f"Only ASSIGNED requirements can be started; current status: {self.status}"
            )
        self.status = RequirementStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def request_review(self) -> None:
        """Move to IN_REVIEW after work is complete."""
        if self.status != RequirementStatus.IN_PROGRESS:
            raise ValueError(
                f"Only IN_PROGRESS requirements can move to review; current status: {self.status}"
            )
        self.status = RequirementStatus.IN_REVIEW
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark the requirement as done."""
        if self.status != RequirementStatus.IN_REVIEW:
            raise ValueError(
                f"Only IN_REVIEW requirements can be completed; current status: {self.status}"
            )
        self.status = RequirementStatus.DONE
        self.updated_at = datetime.utcnow()

    def reject(self, reason: Optional[str] = None) -> None:
        """Reject the requirement (returns it to DRAFT)."""
        self.status = RequirementStatus.REJECTED
        if reason:
            self.description = (self.description or "") + f"\n\nRejected: {reason}"
        self.updated_at = datetime.utcnow()

    def add_lifecycle_gate(self, gate: LifecycleGate) -> None:
        """Register a stage at which a human must approve before work continues."""
        if gate not in self.lifecycle_gates:
            self.lifecycle_gates.append(gate)

    def remove_lifecycle_gate(self, gate: LifecycleGate) -> None:
        """Remove a lifecycle gate."""
        self.lifecycle_gates = [g for g in self.lifecycle_gates if g != gate]

    def requires_human_approval_at(self, stage: LifecycleStage) -> bool:
        """Return True if a human must approve at the given lifecycle stage."""
        return any(g.stage == stage for g in self.lifecycle_gates)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def lifecycle_gates_as_str(self) -> str:
        """Serialise lifecycle gates for DB storage (comma-separated)."""
        return ",".join(g.stage.value for g in self.lifecycle_gates)

    @classmethod
    def lifecycle_gates_from_str(cls, value: Optional[str]) -> List[LifecycleGate]:
        """Deserialise lifecycle gates from DB string."""
        if not value:
            return []
        return [LifecycleGate(LifecycleStage(s.strip())) for s in value.split(",") if s.strip()]
