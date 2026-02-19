"""API routes for projects."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.database import Project
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.github_integration.client import get_github_integration

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    # Check if project key already exists
    result = await db.execute(select(Project).where(Project.key == project_data.key))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Project with key '{project_data.key}' already exists")
    
    # Parse GitHub URL if provided
    github_owner = None
    github_repo_name = None
    if project_data.github_repo_url:
        github = get_github_integration()
        github_owner, github_repo_name = github.parse_repo_url(project_data.github_repo_url)
    
    # Create project
    project = Project(
        name=project_data.name,
        key=project_data.key.upper(),
        description=project_data.description,
        status=project_data.status,
        github_repo_url=project_data.github_repo_url,
        github_repo_owner=github_owner,
        github_repo_name=github_repo_name,
        telegram_chat_id=project_data.telegram_chat_id
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    
    # Update GitHub info if URL changed
    if "github_repo_url" in update_data and update_data["github_repo_url"]:
        github = get_github_integration()
        owner, repo_name = github.parse_repo_url(update_data["github_repo_url"])
        update_data["github_repo_owner"] = owner
        update_data["github_repo_name"] = repo_name
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
