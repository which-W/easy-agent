"""Request models"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FileReference(BaseModel):
    """File reference for multimodal input"""
    type: str = Field(..., description="File type: image or video")
    base64: str = Field(..., description="Base64 encoded file content")
    mime_type: str = Field(..., description="MIME type of the file")


class ChatRequest(BaseModel):
    """Chat request model"""
    session_id: Optional[str] = Field(None, description="Session ID, will create new if None")
    message: str = Field(..., description="User message")
    files: List[FileReference] = Field(default=[], description="Attached files")
    deep_research: bool = Field(default=False, description="Enable deep research mode")


class UploadResponse(BaseModel):
    """Upload response model"""
    file_id: str = Field(..., description="Unique file ID")
    type: str = Field(..., description="File type: image or video")
    mime_type: str = Field(..., description="MIME type")
    url: str = Field(..., description="File URL")
    base64: str = Field(..., description="Base64 encoded content")


class SkillInfo(BaseModel):
    """Skill information"""
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    version: str = Field(default="1.0.0", description="Skill version")
    enabled: bool = Field(default=True, description="Whether skill is enabled")
