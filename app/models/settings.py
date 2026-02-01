"""
Settings and Feature Flag models.
Super Settings for global/company/role level configuration.
"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text

from app.models.base import AuditMixin, BaseModel


class SuperSettings(BaseModel, AuditMixin):
    """
    Hierarchical settings system.
    Settings can be applied at global, company, or role level.
    """

    __tablename__ = "super_settings"

    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, bool, json
    scope = Column(String(20), default="global")  # global, company, role, user
    target_id = Column(Integer, nullable=True)  # company_id, role_id, or user_id based on scope
    category = Column(String(50), nullable=True)  # For grouping settings
    description = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=False)  # Whether setting is visible to users

    def get_typed_value(self):
        """Return value converted to appropriate type."""
        if self.value is None:
            return None

        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value


class FeatureFlag(BaseModel, AuditMixin):
    """
    Feature toggle system for enabling/disabling modules and features.
    Supports scoping to control features at different levels.
    """

    __tablename__ = "feature_flags"

    module = Column(String(50), nullable=False, index=True)
    feature = Column(String(100), nullable=False)
    name = Column(String(100), nullable=True)  # Display name
    description = Column(String(255), nullable=True)
    is_enabled = Column(Boolean, default=True)
    scope = Column(String(20), default="global")  # global, company, role
    target_id = Column(Integer, nullable=True)  # company_id or role_id based on scope
    config = Column(JSON, nullable=True)  # Additional configuration for the feature

    class Meta:
        unique_together = [("module", "feature", "scope", "target_id")]


class MaintenanceMode(BaseModel, AuditMixin):
    """
    System maintenance mode configuration.
    """

    __tablename__ = "maintenance_mode"

    is_enabled = Column(Boolean, default=False)
    message = Column(Text, nullable=True)
    allowed_ips = Column(JSON, nullable=True)  # IPs that can bypass maintenance
    allowed_roles = Column(JSON, nullable=True)  # Roles that can bypass
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)  # For company-specific maintenance

