"""
Audit service for logging user actions.
"""

from typing import Optional, Any, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit import AuditLog


class AuditService:
    """Service for creating and querying audit logs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        user_id: Optional[int],
        action: str,
        module: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        description: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            user_id: ID of user performing action
            action: Action type (create, update, delete, login, etc.)
            module: Module name (employee, attendance, etc.)
            entity_type: Model/entity name
            entity_id: ID of affected entity
            old_value: Previous values (for updates)
            new_value: New values (for creates/updates)
            description: Human-readable description
            request: FastAPI request object for context
        
        Returns:
            Created AuditLog instance
        """
        audit = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            description=description
        )
        
        # Add request context if available
        if request:
            audit.ip_address = request.client.host if request.client else None
            audit.user_agent = request.headers.get("user-agent", "")[:255]
            audit.request_path = str(request.url.path)
            audit.request_method = request.method
        
        self.db.add(audit)
        self.db.commit()
        
        return audit
    
    def log_create(
        self,
        user_id: int,
        module: str,
        entity_type: str,
        entity_id: int,
        new_value: Dict,
        description: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log entity creation."""
        return self.log(
            user_id=user_id,
            action="create",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            new_value=new_value,
            description=description or f"Created {entity_type} #{entity_id}",
            request=request
        )
    
    def log_update(
        self,
        user_id: int,
        module: str,
        entity_type: str,
        entity_id: int,
        old_value: Dict,
        new_value: Dict,
        description: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log entity update."""
        return self.log(
            user_id=user_id,
            action="update",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            description=description or f"Updated {entity_type} #{entity_id}",
            request=request
        )
    
    def log_delete(
        self,
        user_id: int,
        module: str,
        entity_type: str,
        entity_id: int,
        old_value: Optional[Dict] = None,
        description: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log entity deletion."""
        return self.log(
            user_id=user_id,
            action="delete",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            description=description or f"Deleted {entity_type} #{entity_id}",
            request=request
        )
    
    def log_login(
        self,
        user_id: int,
        success: bool = True,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log login attempt."""
        return self.log(
            user_id=user_id,
            action="login" if success else "login_failed",
            module="auth",
            description="User logged in" if success else "Login attempt failed",
            request=request
        )
    
    def log_logout(
        self,
        user_id: int,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log logout."""
        return self.log(
            user_id=user_id,
            action="logout",
            module="auth",
            description="User logged out",
            request=request
        )
    
    def get_by_entity(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50
    ) -> list[AuditLog]:
        """Get audit logs for a specific entity."""
        return self.db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def get_by_user(
        self,
        user_id: int,
        limit: int = 50
    ) -> list[AuditLog]:
        """Get audit logs for a specific user."""
        return self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def get_recent(
        self,
        module: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50
    ) -> list[AuditLog]:
        """Get recent audit logs with optional filters."""
        query = self.db.query(AuditLog)
        
        if module:
            query = query.filter(AuditLog.module == module)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
