"""File upload API"""

import uuid
import base64
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from config import get_settings
from models.request import UploadResponse

router = APIRouter()
settings = get_settings()

# Allowed file types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a file (image or video) for multimodal chat

    Args:
        file: The file to upload

    Returns:
        UploadResponse with file metadata and base64 content
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed: {ALLOWED_TYPES}"
        )

    # Read file content
    file_content = await file.read()

    # Validate file size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Generate file ID
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename or "").suffix or ".bin"
    file_name = f"{file_id}{file_extension}"

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file_name

    with open(file_path, "wb") as f:
        f.write(file_content)

    # Convert to base64
    file_base64 = base64.b64encode(file_content).decode("utf-8")

    # Determine file type
    file_type = "image" if file.content_type in ALLOWED_IMAGE_TYPES else "video"

    return UploadResponse(
        file_id=file_id,
        type=file_type,
        mime_type=file.content_type,
        url=f"/uploads/{file_name}",
        base64=file_base64
    )
