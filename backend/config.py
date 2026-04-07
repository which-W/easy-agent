"""Configuration management using Pydantic Settings"""

from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

# Find project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # DashScope API Configuration
    DASHSCOPE_API_KEY: str = Field(..., description="DashScope API key")

    # Model Configuration
    CHAT_MODEL: str = Field(default="qwen-max", description="Model for text chat")
    VISION_MODEL: str = Field(default="qwen-vl-max", description="Model for vision tasks")
    ENABLE_DEEP_THINKING: bool = Field(default=True, description="Enable deep thinking for research mode")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")

    # File Upload Configuration
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, description="Max upload file size in MB")
    UPLOAD_DIR: str = Field(default="./uploads", description="Upload directory path")

    # MCP Configuration
    MCP_CONFIG_PATH: str = Field(default="mcp_servers.json", description="Path to MCP servers configuration file")

    # Agent Configuration
    MAX_AGENT_ITERATIONS: int = Field(default=10, description="Max agent iteration rounds")
    TEMPERATURE: float = Field(default=0.7, description="Model temperature")
    TOP_P: float = Field(default=0.9, description="Model top_p")

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings singleton"""
    return Settings()
