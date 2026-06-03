"""
File Upload API Endpoints
"""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.config import get_settings
from app.models.auth import User
from app.services.storage_service import get_file_extension, upload_bytes

router = APIRouter(prefix="/uploads", tags=["uploads"])

settings = get_settings()

# Ensure upload directories exist
UPLOAD_BASE = settings.UPLOAD_DIR
IMAGES_DIR = os.path.join(UPLOAD_BASE, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/images")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image file.
    Returns the URL to access the uploaded image.
    """
    # Validate file extension
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    try:
        result = await upload_bytes(
            content=content,
            original_filename=file.filename or "image.jpg",
            category="images",
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}") from e

    return result


@router.delete("/images/{filename}")
async def delete_image(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an uploaded image"""
    file_path = os.path.join(IMAGES_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        os.remove(file_path)
        return {"success": True, "message": "Image deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}") from e


# ============== General File Uploads ==============

FILES_DIR = os.path.join(UPLOAD_BASE, "files")
os.makedirs(FILES_DIR, exist_ok=True)

ALLOWED_FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".rtf",
    ".ppt", ".pptx", ".zip", ".rar", ".7z",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
}
MAX_GENERAL_FILE_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a general file (documents, images, videos, etc.).
    Returns the URL to access the uploaded file.
    Max size: 25MB.
    """
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed."
        )

    content = await file.read()

    if len(content) > MAX_GENERAL_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_GENERAL_FILE_SIZE // (1024 * 1024)}MB"
        )

    try:
        result = await upload_bytes(
            content=content,
            original_filename=file.filename or "file",
            category="files",
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}") from e

    return result


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an uploaded file."""
    file_path = os.path.join(FILES_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(file_path)
        return {"success": True, "message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}") from e


