"""
File storage helpers.

Stores uploaded files locally under UPLOAD_DIR, served via the app's
/uploads static mount.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings


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


async def upload_bytes(
    *,
    content: bytes,
    original_filename: str,
    category: str,
    content_type: str | None = None,
    prefix: str | None = None,
) -> dict:
    """Save uploaded bytes to local storage and return a common payload."""
    filename = generate_unique_filename(original_filename, prefix=prefix)

    local_dir = Path(settings.UPLOAD_DIR) / category
    local_dir.mkdir(parents=True, exist_ok=True)
    file_path = local_dir / filename
    file_path.write_bytes(content)

    url_prefix = getattr(settings, "STORAGE_URL_PREFIX", "/storage")
    return {
        "success": True,
        "storage": "local_storage_server",
        "url": f"{url_prefix}/{category}/{filename}",
        "filename": filename,
        "original_filename": original_filename,
        "size": len(content),
        "content_type": content_type,
        "folder": f"{url_prefix}/{category}",
    }


def _folder_path(category: str) -> str:
    """Map categories to standardized storage paths."""
    category_map = {
        "avatars": "profile",
        "profile": "profile",
        "files": "documents",
        "documents": "documents",
    }
    target = category_map.get(category, category)
    return f"/ayati-admin/{target}"
