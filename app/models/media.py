"""
Media and File models.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class MediaFolder(BaseModel, AuditMixin):
    """Media folder for organizing files."""

    __tablename__ = "media_folders"

    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("media_folders.id"), nullable=True)

    # Scope
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    is_public = Column(Boolean, default=False)


class Media(BaseModel, AuditMixin):
    """Media file (images, documents, etc.)."""

    __tablename__ = "media"

    # File info
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Type
    file_type = Column(String(20), nullable=True)  # image, document, video, audio

    # Image specific
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    thumbnail_path = Column(String(500), nullable=True)

    # Organization
    folder_id = Column(Integer, ForeignKey("media_folders.id"), nullable=True)

    # Metadata
    alt_text = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Tags
    tags = Column(JSON, nullable=True)

    # Access
    is_public = Column(Boolean, default=False)

    # Upload info
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    folder = relationship("MediaFolder", backref="files")


class Document(BaseModel, AuditMixin):
    """Document management."""

    __tablename__ = "documents"

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # File
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Type
    document_type = Column(String(50), nullable=True)  # policy, template, procedure, etc.
    category = Column(String(50), nullable=True)

    # Version
    version = Column(String(20), default="1.0")

    # Access control
    access_level = Column(String(20), default="internal")  # public, internal, confidential
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    # Approval
    status = Column(String(20), default="draft")  # draft, pending, approved, archived
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Expiry
    expiry_date = Column(DateTime, nullable=True)

    # Tags
    tags = Column(JSON, nullable=True)


class KnowledgeBase(BaseModel, AuditMixin):
    """Knowledge base article."""

    __tablename__ = "knowledge_base"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    content = Column(Text, nullable=False)

    # Category
    category = Column(String(100), nullable=True)

    # Author
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Status
    status = Column(String(20), default="draft")
    published_at = Column(DateTime, nullable=True)

    # Visibility
    is_public = Column(Boolean, default=False)  # Internal or public

    # Engagement
    views = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)

    # Related articles
    related = Column(JSON, nullable=True)  # Array of article IDs

    # Tags
    tags = Column(JSON, nullable=True)

