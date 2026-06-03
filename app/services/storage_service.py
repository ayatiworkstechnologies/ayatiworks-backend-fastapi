"""
File storage helpers.

Uses ImageKit when IMAGEKIT_PRIVATE_KEY is configured, otherwise stores files
locally under UPLOAD_DIR to keep local development and tests simple.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings

IMAGEKIT_UPLOAD_URL = "https://upload.imagekit.io/api/v1/files/upload"

IMAGEKIT_CATEGORY_FOLDERS = {
    "avatars": "profile",
    "profile": "profile",
    "files": "documents",
    "documents": "documents",
    "images": "images",
    "resumes": "resumes",
}


def get_file_extension(filename: str) -> str:
    """Return a normalized file extension."""
    return os.path.splitext(filename or "")[1].lower()


def generate_unique_filename(original_filename: str, prefix: str | None = None) -> str:
    """Generate a readable unique filename while preserving the extension."""
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_prefix = f"{prefix}_" if prefix else ""
    return f"{name_prefix}{timestamp}_{unique_id}{ext}"


def _imagekit_enabled() -> bool:
    return bool(settings.IMAGEKIT_PRIVATE_KEY)


def _folder_path(category: str) -> str:
    base = (settings.IMAGEKIT_BASE_FOLDER or "/ayati-admin").strip("/")
    clean_category = category.strip("/").replace("\\", "/")
    clean_category = IMAGEKIT_CATEGORY_FOLDERS.get(clean_category, clean_category)
    return f"/{base}/{clean_category}"


async def upload_bytes(
    *,
    content: bytes,
    original_filename: str,
    category: str,
    content_type: str | None = None,
    prefix: str | None = None,
) -> dict:
    """Upload bytes to ImageKit or local storage and return a common payload."""
    filename = generate_unique_filename(original_filename, prefix=prefix)

    if _imagekit_enabled():
        return await _upload_to_imagekit(
            content=content,
            filename=filename,
            folder=_folder_path(category),
            content_type=content_type,
            original_filename=original_filename,
        )

    return _save_local(
        content=content,
        filename=filename,
        category=category,
        content_type=content_type,
        original_filename=original_filename,
    )


async def _upload_to_imagekit(
    *,
    content: bytes,
    filename: str,
    folder: str,
    content_type: str | None,
    original_filename: str,
) -> dict:
    files = {
        "file": (filename, content, content_type or "application/octet-stream"),
    }
    data = {
        "fileName": filename,
        "folder": folder,
        "useUniqueFileName": "false",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            IMAGEKIT_UPLOAD_URL,
            data=data,
            files=files,
            auth=(settings.IMAGEKIT_PRIVATE_KEY or "", ""),
        )

    if response.status_code >= 400:
        raise RuntimeError(f"ImageKit upload failed: {response.text}")

    payload = response.json()
    return {
        "success": True,
        "storage": "imagekit",
        "url": payload.get("url"),
        "file_id": payload.get("fileId"),
        "filename": payload.get("name") or filename,
        "original_filename": original_filename,
        "size": len(content),
        "content_type": content_type,
        "folder": folder,
    }


def _save_local(
    *,
    content: bytes,
    filename: str,
    category: str,
    content_type: str | None,
    original_filename: str,
) -> dict:
    local_dir = Path(settings.UPLOAD_DIR) / category
    local_dir.mkdir(parents=True, exist_ok=True)
    file_path = local_dir / filename
    file_path.write_bytes(content)

    return {
        "success": True,
        "storage": "local",
        "url": f"/uploads/{category}/{filename}",
        "filename": filename,
        "original_filename": original_filename,
        "size": len(content),
        "content_type": content_type,
        "folder": f"/uploads/{category}",
    }
