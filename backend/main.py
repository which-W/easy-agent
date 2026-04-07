"""FastAPI application entry point"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings, PROJECT_ROOT
from api import chat, upload

# Initialize settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup"""
    # Startup: initialize MCP connections
    from agent.session import session_manager
    await session_manager.factory.initialize()
    print(f"MCP initialized: {session_manager.factory.mcp_manager.tool_count} tools available")
    yield
    # Shutdown: disconnect MCP
    await session_manager.factory.shutdown()
    print("MCP connections closed")


# Create FastAPI app
app = FastAPI(
    title="Easy-Agent API",
    description="AgentScope-based multimodal agent system with streaming support",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(upload.router, prefix="/api", tags=["upload"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Serve frontend static files
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_dir / "index.html"))

    app.mount("/", StaticFiles(directory=str(frontend_dir)), name="frontend")
