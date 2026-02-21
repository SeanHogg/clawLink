"""Role-based access control (RBAC) system."""

from enum import Enum
from typing import Set, Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    # Task permissions
    TASK_SUBMIT = "task:submit"
    TASK_CANCEL = "task:cancel"
    TASK_VIEW = "task:view"

    # Agent permissions
    AGENT_LIST = "agent:list"
    AGENT_EXECUTE = "agent:execute"
    AGENT_CONFIGURE = "agent:configure"

    # Skill permissions
    SKILL_LIST = "skill:list"
    SKILL_EXECUTE = "skill:execute"
    SKILL_INSTALL = "skill:install"

    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"

    # Requirement permissions (human-in-the-loop)
    REQUIREMENT_CREATE = "requirement:create"
    REQUIREMENT_READ = "requirement:read"
    REQUIREMENT_ASSIGN = "requirement:assign"
    REQUIREMENT_UPDATE = "requirement:update"
    REQUIREMENT_DELETE = "requirement:delete"

    # Work-assignment and lifecycle control
    WORK_ASSIGN = "work:assign"
    LIFECYCLE_CONTROL = "lifecycle:control"

    # Integration management
    INTEGRATION_MANAGE = "integration:manage"
    INTEGRATION_READ = "integration:read"

    # Tenant management
    TENANT_MANAGE = "tenant:manage"
    TENANT_READ = "tenant:read"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"


class Role(str, Enum):
    """System roles."""
    ADMIN = "admin"
    MANAGER = "manager"       # Human-in-the-loop: creates requirements and assigns work
    DEVELOPER = "developer"
    VIEWER = "viewer"
    GUEST = "guest"


# Role permission mappings
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # All permissions
        Permission.TASK_SUBMIT,
        Permission.TASK_CANCEL,
        Permission.TASK_VIEW,
        Permission.AGENT_LIST,
        Permission.AGENT_EXECUTE,
        Permission.AGENT_CONFIGURE,
        Permission.SKILL_LIST,
        Permission.SKILL_EXECUTE,
        Permission.SKILL_INSTALL,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
        Permission.REQUIREMENT_CREATE,
        Permission.REQUIREMENT_READ,
        Permission.REQUIREMENT_ASSIGN,
        Permission.REQUIREMENT_UPDATE,
        Permission.REQUIREMENT_DELETE,
        Permission.WORK_ASSIGN,
        Permission.LIFECYCLE_CONTROL,
        Permission.INTEGRATION_MANAGE,
        Permission.INTEGRATION_READ,
        Permission.TENANT_MANAGE,
        Permission.TENANT_READ,
        Permission.ADMIN_USERS,
        Permission.ADMIN_SYSTEM,
    },
    Role.MANAGER: {
        # Managers direct agents and review work; they do NOT run agents directly
        Permission.TASK_VIEW,
        Permission.TASK_CANCEL,
        Permission.AGENT_LIST,
        Permission.SKILL_LIST,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.REQUIREMENT_CREATE,
        Permission.REQUIREMENT_READ,
        Permission.REQUIREMENT_ASSIGN,
        Permission.REQUIREMENT_UPDATE,
        Permission.WORK_ASSIGN,
        Permission.LIFECYCLE_CONTROL,
        Permission.INTEGRATION_MANAGE,
        Permission.INTEGRATION_READ,
        Permission.TENANT_READ,
    },
    Role.DEVELOPER: {
        Permission.TASK_SUBMIT,
        Permission.TASK_CANCEL,
        Permission.TASK_VIEW,
        Permission.AGENT_LIST,
        Permission.AGENT_EXECUTE,
        Permission.SKILL_LIST,
        Permission.SKILL_EXECUTE,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.REQUIREMENT_READ,
        Permission.INTEGRATION_READ,
        Permission.TENANT_READ,
    },
    Role.VIEWER: {
        Permission.TASK_VIEW,
        Permission.AGENT_LIST,
        Permission.SKILL_LIST,
        Permission.PROJECT_READ,
        Permission.REQUIREMENT_READ,
        Permission.INTEGRATION_READ,
        Permission.TENANT_READ,
    },
    Role.GUEST: {
        Permission.AGENT_LIST,
        Permission.SKILL_LIST,
    },
}


@dataclass
class AccessPolicy:
    """Access policy for resources."""
    resource_type: str  # "project", "task", "agent", etc.
    resource_id: Optional[str] = None
    allowed_roles: Set[Role] = field(default_factory=set)
    allowed_users: Set[str] = field(default_factory=set)
    denied_users: Set[str] = field(default_factory=set)
    required_permissions: Set[Permission] = field(default_factory=set)


class RBACManager:
    """
    Role-Based Access Control Manager.
    
    Manages:
    - User roles and permissions (global and per-tenant)
    - Resource-level access policies
    - Agent-level authorization
    - Skill-level execution controls
    """
    
    def __init__(self):
        """Initialize RBAC manager."""
        self._user_roles: Dict[str, Set[Role]] = {}
        self._user_permissions: Dict[str, Set[Permission]] = {}
        self._resource_policies: Dict[str, AccessPolicy] = {}
        # Tenant-scoped roles: {tenant_id -> {user_id -> Set[Role]}}
        self._tenant_roles: Dict[str, Dict[str, Set[Role]]] = {}
        logger.info("RBAC manager initialized")
    
    def assign_role(self, user_id: str, role: Role):
        """Assign a role to a user."""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role)
        logger.info(f"Assigned role {role} to user {user_id}")
    
    def revoke_role(self, user_id: str, role: Role):
        """Revoke a role from a user."""
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role)
            logger.info(f"Revoked role {role} from user {user_id}")
    
    def grant_permission(self, user_id: str, permission: Permission):
        """Grant a specific permission to a user."""
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = set()
        
        self._user_permissions[user_id].add(permission)
        logger.info(f"Granted permission {permission} to user {user_id}")
    
    def revoke_permission(self, user_id: str, permission: Permission):
        """Revoke a specific permission from a user."""
        if user_id in self._user_permissions:
            self._user_permissions[user_id].discard(permission)
            logger.info(f"Revoked permission {permission} from user {user_id}")
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        permissions = set()
        
        # Add role-based permissions
        user_roles = self._user_roles.get(user_id, set())
        for role in user_roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        
        # Add user-specific permissions
        permissions.update(self._user_permissions.get(user_id, set()))
        
        return permissions
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.get_user_permissions(user_id)
    
    def has_any_permission(self, user_id: str, permissions: Set[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        user_perms = self.get_user_permissions(user_id)
        return bool(user_perms & permissions)
    
    def has_all_permissions(self, user_id: str, permissions: Set[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        user_perms = self.get_user_permissions(user_id)
        return permissions.issubset(user_perms)
    
    def set_resource_policy(self, policy: AccessPolicy):
        """Set access policy for a resource."""
        policy_key = f"{policy.resource_type}:{policy.resource_id or '*'}"
        self._resource_policies[policy_key] = policy
        logger.info(f"Set policy for {policy_key}")
    
    def check_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        required_permission: Optional[Permission] = None
    ) -> bool:
        """
        Check if user has access to a resource.
        
        Args:
            user_id: User identifier
            resource_type: Type of resource (project, task, etc.)
            resource_id: Specific resource ID (None for general access)
            required_permission: Required permission for access
            
        Returns:
            True if user has access
        """
        # Check explicit denial
        policy_key = f"{resource_type}:{resource_id or '*'}"
        policy = self._resource_policies.get(policy_key)
        
        if policy and user_id in policy.denied_users:
            return False
        
        # Check if user has required permission
        if required_permission and not self.has_permission(user_id, required_permission):
            return False
        
        # Check policy requirements
        if policy:
            # Check user allowlist
            if policy.allowed_users and user_id not in policy.allowed_users:
                return False
            
            # Check role requirements
            if policy.allowed_roles:
                user_roles = self._user_roles.get(user_id, set())
                if not (user_roles & policy.allowed_roles):
                    return False
            
            # Check permission requirements
            if policy.required_permissions:
                if not self.has_all_permissions(user_id, policy.required_permissions):
                    return False
        
        return True

    # ------------------------------------------------------------------
    # Tenant-scoped RBAC
    # ------------------------------------------------------------------

    def assign_tenant_role(self, tenant_id: str, user_id: str, role: Role) -> None:
        """Assign a role to a user within a specific tenant."""
        if tenant_id not in self._tenant_roles:
            self._tenant_roles[tenant_id] = {}
        if user_id not in self._tenant_roles[tenant_id]:
            self._tenant_roles[tenant_id][user_id] = set()
        self._tenant_roles[tenant_id][user_id].add(role)
        logger.info(f"Assigned tenant role {role} to user {user_id} in tenant {tenant_id}")

    def revoke_tenant_role(self, tenant_id: str, user_id: str, role: Role) -> None:
        """Revoke a role from a user within a specific tenant."""
        self._tenant_roles.get(tenant_id, {}).get(user_id, set()).discard(role)
        logger.info(f"Revoked tenant role {role} from user {user_id} in tenant {tenant_id}")

    def get_tenant_roles(self, tenant_id: str, user_id: str) -> Set[Role]:
        """Return the roles held by a user within a tenant."""
        return self._tenant_roles.get(tenant_id, {}).get(user_id, set()).copy()

    def get_tenant_permissions(self, tenant_id: str, user_id: str) -> Set[Permission]:
        """Return all permissions derived from tenant-scoped roles plus global permissions."""
        permissions: Set[Permission] = set()
        for role in self.get_tenant_roles(tenant_id, user_id):
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        # Merge global permissions
        permissions.update(self.get_user_permissions(user_id))
        return permissions

    def has_tenant_permission(
        self, tenant_id: str, user_id: str, permission: Permission
    ) -> bool:
        """Check if a user holds a permission within a specific tenant."""
        return permission in self.get_tenant_permissions(tenant_id, user_id)

    def can_execute_agent(self, user_id: str, agent_type: str) -> bool:
        """Check if user can execute a specific agent."""
        return self.check_resource_access(
            user_id=user_id,
            resource_type="agent",
            resource_id=agent_type,
            required_permission=Permission.AGENT_EXECUTE
        )
    
    def can_execute_skill(self, user_id: str, skill_id: str) -> bool:
        """Check if user can execute a specific skill."""
        return self.check_resource_access(
            user_id=user_id,
            resource_type="skill",
            resource_id=skill_id,
            required_permission=Permission.SKILL_EXECUTE
        )


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager instance."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager
