"""Response models"""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="ok")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    code: str = Field(default="unknown", description="Error code")
    details: Optional[str] = Field(None, description="Error details")


class SessionResponse(BaseModel):
    """Session creation response"""
    session_id: str = Field(..., description="Session ID")
    created: bool = Field(..., description="Whether a new session was created")
