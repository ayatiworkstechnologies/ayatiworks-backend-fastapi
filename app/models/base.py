"""
Base model classes with common fields and mixins.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, String
from sqlalchemy.ext.declarative import declared_attr

from app.database import Base


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality."""
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, nullable=True)
    
    def soft_delete(self, user_id: int = None):
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Abstract base model with common fields.
    All models should inherit from this class.
    """
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name (snake_case)."""
        import re
        name = cls.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def update(self, **kwargs):
        """Update model attributes from kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self


class AuditMixin:
    """Mixin for tracking who created/modified records."""
    
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
