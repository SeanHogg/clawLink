"""Tests for Phase 3: RBAC, multi-tenant structure, requirements, and integrations."""

import pytest
from app.security.rbac import RBACManager, Role, Permission
from app.domain.tenant.models import (
    Tenant, TenantId, TenantMember, TenantMemberRole,
)
from app.domain.requirement.models import (
    Requirement, RequirementId, LifecycleGate,
)
from app.domain.integration.models import (
    Integration, IntegrationId, IntegrationConfig,
)
from app.models.database import (
    TenantStatus, TenantRole, RequirementStatus, LifecycleStage, IntegrationType,
)


# ---------------------------------------------------------------------------
# RBAC – Manager role and new permissions
# ---------------------------------------------------------------------------

def test_manager_role_permissions():
    """Manager role has the expected subset of permissions."""
    rbac = RBACManager()
    user_id = "manager-1"
    rbac.assign_role(user_id, Role.MANAGER)

    # Managers can do these things
    assert rbac.has_permission(user_id, Permission.REQUIREMENT_CREATE)
    assert rbac.has_permission(user_id, Permission.REQUIREMENT_ASSIGN)
    assert rbac.has_permission(user_id, Permission.WORK_ASSIGN)
    assert rbac.has_permission(user_id, Permission.LIFECYCLE_CONTROL)
    assert rbac.has_permission(user_id, Permission.INTEGRATION_MANAGE)
    assert rbac.has_permission(user_id, Permission.PROJECT_READ)

    # Managers cannot do these things
    assert not rbac.has_permission(user_id, Permission.ADMIN_SYSTEM)
    assert not rbac.has_permission(user_id, Permission.AGENT_EXECUTE)
    assert not rbac.has_permission(user_id, Permission.TASK_SUBMIT)


def test_developer_new_permissions():
    """Developer role has the new read-only permissions."""
    rbac = RBACManager()
    user_id = "dev-1"
    rbac.assign_role(user_id, Role.DEVELOPER)

    assert rbac.has_permission(user_id, Permission.REQUIREMENT_READ)
    assert rbac.has_permission(user_id, Permission.INTEGRATION_READ)
    assert rbac.has_permission(user_id, Permission.TENANT_READ)
    assert not rbac.has_permission(user_id, Permission.REQUIREMENT_CREATE)
    assert not rbac.has_permission(user_id, Permission.INTEGRATION_MANAGE)


def test_viewer_new_permissions():
    """Viewer role has read-only access to requirements and integrations."""
    rbac = RBACManager()
    user_id = "viewer-1"
    rbac.assign_role(user_id, Role.VIEWER)

    assert rbac.has_permission(user_id, Permission.REQUIREMENT_READ)
    assert rbac.has_permission(user_id, Permission.INTEGRATION_READ)
    assert not rbac.has_permission(user_id, Permission.REQUIREMENT_CREATE)


def test_tenant_scoped_rbac():
    """Tenant-scoped roles are independent of global roles."""
    rbac = RBACManager()
    user_id = "user-tenant"
    tenant_id = "tenant-1"

    # No global role
    assert not rbac.has_permission(user_id, Permission.REQUIREMENT_CREATE)

    # Assign manager role within a tenant
    rbac.assign_tenant_role(tenant_id, user_id, Role.MANAGER)

    # Now has tenant permission
    assert rbac.has_tenant_permission(tenant_id, user_id, Permission.REQUIREMENT_CREATE)
    assert rbac.has_tenant_permission(tenant_id, user_id, Permission.LIFECYCLE_CONTROL)

    # But NOT in another tenant
    assert not rbac.has_tenant_permission("other-tenant", user_id, Permission.REQUIREMENT_CREATE)

    # Revoke
    rbac.revoke_tenant_role(tenant_id, user_id, Role.MANAGER)
    assert not rbac.has_tenant_permission(tenant_id, user_id, Permission.REQUIREMENT_CREATE)


def test_tenant_scoped_roles_list():
    """get_tenant_roles returns correct roles for the tenant."""
    rbac = RBACManager()
    rbac.assign_tenant_role("t1", "alice", Role.MANAGER)
    rbac.assign_tenant_role("t1", "alice", Role.VIEWER)

    roles = rbac.get_tenant_roles("t1", "alice")
    assert Role.MANAGER in roles
    assert Role.VIEWER in roles
    assert Role.DEVELOPER not in roles


# ---------------------------------------------------------------------------
# Tenant domain aggregate
# ---------------------------------------------------------------------------

def test_tenant_creation():
    """A Tenant aggregate can be created."""
    tenant = Tenant(
        id=TenantId(1),
        name="Acme Corp",
        slug="acme-corp",
        description="Test organisation",
    )
    assert tenant.name == "Acme Corp"
    assert tenant.slug == "acme-corp"
    assert tenant.is_active()


def test_tenant_add_member():
    """Adding a member to a tenant succeeds."""
    tenant = Tenant(id=TenantId(1), name="Acme", slug="acme")
    owner_role = TenantMemberRole.owner()
    member = tenant.add_member("alice", owner_role)
    assert member.user_id == "alice"
    assert member.role.role == TenantRole.OWNER
    assert len(tenant.members) == 1


def test_tenant_remove_last_owner_raises():
    """Removing the last owner should raise ValueError."""
    tenant = Tenant(id=TenantId(1), name="Acme", slug="acme")
    tenant.add_member("alice", TenantMemberRole.owner())

    with pytest.raises(ValueError, match="last owner"):
        tenant.remove_member("alice")


def test_tenant_add_duplicate_member_raises():
    """Adding the same user twice raises ValueError."""
    tenant = Tenant(id=TenantId(1), name="Acme", slug="acme")
    tenant.add_member("alice", TenantMemberRole.owner())

    with pytest.raises(ValueError, match="already an active member"):
        tenant.add_member("alice", TenantMemberRole.developer())


def test_tenant_member_role_capabilities():
    """TenantMemberRole value object exposes correct capability checks."""
    owner = TenantMemberRole.owner()
    manager = TenantMemberRole.manager()
    developer = TenantMemberRole.developer()
    viewer = TenantMemberRole.viewer()

    assert owner.can_manage_requirements()
    assert manager.can_manage_requirements()
    assert not developer.can_manage_requirements()
    assert not viewer.can_manage_requirements()

    assert owner.can_assign_work()
    assert manager.can_assign_work()
    assert not developer.can_assign_work()


def test_tenant_id_must_be_positive():
    """TenantId must be positive."""
    with pytest.raises(ValueError):
        TenantId(0)
    with pytest.raises(ValueError):
        TenantId(-1)


# ---------------------------------------------------------------------------
# Requirement domain aggregate
# ---------------------------------------------------------------------------

def test_requirement_lifecycle():
    """A requirement transitions through the expected status states."""
    req = Requirement(
        id=RequirementId(1),
        tenant_id=1,
        title="Implement login page",
    )
    assert req.status == RequirementStatus.DRAFT

    req.open()
    assert req.status == RequirementStatus.OPEN

    req.assign("agent:claude")
    assert req.status == RequirementStatus.ASSIGNED
    assert req.assigned_to == "agent:claude"

    req.start()
    assert req.status == RequirementStatus.IN_PROGRESS

    req.request_review()
    assert req.status == RequirementStatus.IN_REVIEW

    req.complete()
    assert req.status == RequirementStatus.DONE


def test_requirement_invalid_transition_raises():
    """An invalid status transition raises ValueError."""
    req = Requirement(id=RequirementId(2), tenant_id=1, title="Build API")
    # Cannot start from DRAFT directly
    with pytest.raises(ValueError):
        req.start()


def test_requirement_reject():
    """A requirement can be rejected from any active state."""
    req = Requirement(id=RequirementId(3), tenant_id=1, title="Design DB schema")
    req.open()
    req.assign("bob")
    req.reject("Out of scope")
    assert req.status == RequirementStatus.REJECTED
    assert "Out of scope" in req.description


def test_lifecycle_gates():
    """Lifecycle gates can be added, queried, and removed."""
    req = Requirement(id=RequirementId(4), tenant_id=1, title="Refactor module")

    planning_gate = LifecycleGate.planning_gate()
    review_gate = LifecycleGate.review_gate()

    req.add_lifecycle_gate(planning_gate)
    req.add_lifecycle_gate(review_gate)

    assert req.requires_human_approval_at(LifecycleStage.PLANNING)
    assert req.requires_human_approval_at(LifecycleStage.REVIEW)
    assert not req.requires_human_approval_at(LifecycleStage.EXECUTION)

    req.remove_lifecycle_gate(planning_gate)
    assert not req.requires_human_approval_at(LifecycleStage.PLANNING)


def test_lifecycle_gates_serialisation():
    """lifecycle_gates_as_str round-trips correctly."""
    req = Requirement(id=RequirementId(5), tenant_id=1, title="Test gates")
    req.add_lifecycle_gate(LifecycleGate.planning_gate())
    req.add_lifecycle_gate(LifecycleGate.review_gate())

    serialised = req.lifecycle_gates_as_str()
    # Both stages present
    assert LifecycleStage.PLANNING.value in serialised
    assert LifecycleStage.REVIEW.value in serialised

    restored = Requirement.lifecycle_gates_from_str(serialised)
    assert len(restored) == 2
    restored_stages = {g.stage for g in restored}
    assert LifecycleStage.PLANNING in restored_stages
    assert LifecycleStage.REVIEW in restored_stages


def test_lifecycle_gates_from_empty_string():
    """Empty/None string returns empty list."""
    assert Requirement.lifecycle_gates_from_str(None) == []
    assert Requirement.lifecycle_gates_from_str("") == []


# ---------------------------------------------------------------------------
# Integration domain aggregate
# ---------------------------------------------------------------------------

def test_integration_creation():
    """An Integration aggregate can be created."""
    integration = Integration(
        id=IntegrationId(1),
        tenant_id=1,
        name="GitHub Main",
        integration_type=IntegrationType.GITHUB,
        config=IntegrationConfig(data={"token": "ghp_xxx", "owner": "acme"}),
    )
    assert integration.name == "GitHub Main"
    assert integration.integration_type == IntegrationType.GITHUB
    assert integration.is_active
    assert integration.config.get("owner") == "acme"


def test_integration_deactivate_and_activate():
    """An Integration can be deactivated and re-activated."""
    integration = Integration(
        id=IntegrationId(2),
        tenant_id=1,
        name="Jira",
        integration_type=IntegrationType.JIRA,
    )
    assert integration.is_active

    integration.deactivate()
    assert not integration.is_active

    integration.activate()
    assert integration.is_active


def test_integration_config_update():
    """update_config replaces the existing configuration."""
    integration = Integration(
        id=IntegrationId(3),
        tenant_id=1,
        name="Slack",
        integration_type=IntegrationType.SLACK,
        config=IntegrationConfig(data={"webhook": "https://hooks.example.com/old"}),
    )
    integration.update_config({"webhook": "https://hooks.example.com/new"})
    assert integration.config.get("webhook") == "https://hooks.example.com/new"


def test_integration_config_json_roundtrip():
    """IntegrationConfig serialises and deserialises to/from JSON."""
    original = IntegrationConfig(data={"key": "value", "count": 42})
    serialised = original.to_json()
    restored = IntegrationConfig.from_json(serialised)
    assert restored.get("key") == "value"
    assert restored.get("count") == 42


def test_integration_id_must_be_positive():
    """IntegrationId must be a positive integer."""
    with pytest.raises(ValueError):
        IntegrationId(0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
