"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.database import (
    ProjectStatus, TaskStatus, TaskPriority, AgentType, ExecutionState,
    TenantStatus, TenantRole, RequirementStatus, LifecycleStage, IntegrationType,
)


# Project schemas
class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=1, max_length=50, description="Project key (e.g., 'PROJ')")
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    github_repo_url: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    github_repo_url: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: int
    github_repo_owner: Optional[str] = None
    github_repo_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Task schemas
class TaskBase(BaseModel):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agent_type: Optional[AgentType] = None


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    project_id: int


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_agent_type: Optional[AgentType] = None


class TaskResponse(TaskBase):
    """Schema for task response."""
    id: int
    project_id: int
    key: str
    agent_execution_status: Optional[str] = None
    github_pr_url: Optional[str] = None
    github_pr_number: Optional[int] = None
    github_branch_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Agent execution schemas
class AgentExecutionRequest(BaseModel):
    """Schema for requesting agent execution."""
    task_id: int
    agent_type: AgentType
    prompt: str = Field(..., min_length=1)


class AgentExecutionResponse(BaseModel):
    """Schema for agent execution response."""
    id: int
    task_id: int
    agent_type: AgentType
    prompt: str
    response: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Telegram command schemas
class TelegramCommandRequest(BaseModel):
    """Schema for Telegram command processing."""
    chat_id: str
    message: str
    user_id: Optional[str] = None


class TelegramCommandResponse(BaseModel):
    """Schema for Telegram command response."""
    success: bool
    message: str
    data: Optional[dict] = None


# Phase 2: Transport and distributed execution schemas
class SessionInfo(BaseModel):
    """Session information schema."""
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    permissions: List[str] = []
    
    class Config:
        from_attributes = True


class TaskSubmissionRequest(BaseModel):
    """Task submission for distributed execution."""
    agent_type: str
    prompt: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None


class TaskStateResponse(BaseModel):
    """Task state response."""
    task_id: str
    execution_uuid: str
    state: ExecutionState
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentInfoResponse(BaseModel):
    """Agent information response."""
    agent_type: str
    name: str
    description: Optional[str] = None
    available: bool
    capabilities: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class SkillInfoResponse(BaseModel):
    """Skill information response."""
    skill_id: str
    name: str
    description: Optional[str] = None
    required_permissions: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    event_id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    status: str
    details: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Tenant schemas
# ---------------------------------------------------------------------------

class TenantMembershipBase(BaseModel):
    """Base membership schema."""
    user_id: str
    role: TenantRole = TenantRole.DEVELOPER


class TenantMembershipCreate(TenantMembershipBase):
    """Schema for adding a member to a tenant."""
    pass


class TenantMembershipResponse(TenantMembershipBase):
    """Schema for membership response."""
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantBase(BaseModel):
    """Base tenant schema."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    status: TenantStatus = TenantStatus.ACTIVE


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""
    pass


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TenantStatus] = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Requirement schemas
# ---------------------------------------------------------------------------

class RequirementBase(BaseModel):
    """Base requirement schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: RequirementStatus = RequirementStatus.DRAFT
    project_id: Optional[int] = None
    assigned_to: Optional[str] = None
    lifecycle_gates: Optional[List[LifecycleStage]] = None


class RequirementCreate(RequirementBase):
    """Schema for creating a requirement."""
    tenant_id: int


class RequirementUpdate(BaseModel):
    """Schema for updating a requirement."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[RequirementStatus] = None
    project_id: Optional[int] = None
    assigned_to: Optional[str] = None
    lifecycle_gates: Optional[List[LifecycleStage]] = None


class RequirementAssign(BaseModel):
    """Schema for assigning a requirement to a user or agent."""
    assigned_to: str = Field(..., min_length=1)


class RequirementResponse(RequirementBase):
    """Schema for requirement response."""
    id: int
    tenant_id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Integration schemas
# ---------------------------------------------------------------------------

class IntegrationBase(BaseModel):
    """Base integration schema."""
    name: str = Field(..., min_length=1, max_length=255)
    integration_type: IntegrationType
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration."""
    tenant_id: int


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class IntegrationResponse(IntegrationBase):
    """Schema for integration response."""
    id: int
    tenant_id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
