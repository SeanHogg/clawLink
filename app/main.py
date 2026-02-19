"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core.database import init_db
from app.core.config import get_settings
from app.api import projects, tasks, agents
from app.telegram_bot.bot import get_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    # Startup
    logger.info("Starting AI Agent Orchestrator Portal...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start Telegram bot if configured
    settings = get_settings()
    if settings.telegram_bot_token:
        try:
            bot = get_bot()
            # Start bot in background (don't await)
            import asyncio
            asyncio.create_task(bot.start())
            logger.info("Telegram bot started")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}")
    else:
        logger.warning("Telegram bot token not configured, bot not started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if settings.telegram_bot_token:
        try:
            bot = get_bot()
            await bot.stop()
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="AI Agent Orchestrator Portal",
    description="A telegram-aware agentic portal for project management and code generation",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(agents.router, prefix="/api")

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serve the main frontend page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {
        "message": "AI Agent Orchestrator Portal API",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
