"""API routes for agents."""

from fastapi import APIRouter
from typing import List
from app.agents.orchestrator import get_orchestrator

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/available", response_model=List[str])
async def list_available_agents():
    """List all available and configured agents."""
    orchestrator = get_orchestrator()
    return orchestrator.list_available_agents()


@router.get("/types", response_model=List[str])
async def list_agent_types():
    """List all supported agent types."""
    from app.models.database import AgentType
    return [agent.value for agent in AgentType]
